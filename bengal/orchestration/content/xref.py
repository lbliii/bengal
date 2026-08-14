"""Cross-reference index and target-directive indexing for ContentOrchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import xref_path_key
from bengal.content.discovery_facts import extract_target_directives_from_content
from bengal.content.page_source import get_raw_source

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import PageLike


def _build_xref_index(orchestrator: Any) -> None:
    """
    Build cross-reference index for O(1) page lookups.

    Creates multiple indices to support different reference styles:
    - by_path: Reference by file path (e.g., 'docs/installation')
    - by_slug: Reference by slug (e.g., 'installation')
    - by_id: Reference by custom ID from frontmatter (e.g., 'install-guide')
    - by_heading: Reference by heading text for anchor links
    - by_anchor: Reference by explicit anchor ID (e.g., {#install})

    Each index is populated by a focused per-page helper so the five
    orthogonal concerns can also be re-run for only the changed-page set
    during incremental discovery (see #332).

    Performance: O(n) build time, O(1) lookup time
    Thread-safe: Read-only after building, safe for parallel rendering
    """
    orchestrator.site.xref_index = {
        "by_path": {},  # 'docs/getting-started' -> PageLike
        "by_slug": {},  # 'getting-started' -> [Pages]
        "by_id": {},  # Custom IDs from frontmatter -> PageLike
        "by_heading": {},  # Heading text -> [(Page, anchor)]
        "by_anchor": {},  # Explicit anchor ID -> [(Page, anchor, version_id), ...] for [[#anchor]] resolution (version-scoped)
    }

    content_dir = orchestrator.site.root_path / "content"

    for page in orchestrator.site.pages:
        orchestrator._index_by_path(page, content_dir)
        orchestrator._index_by_slug(page)
        orchestrator._index_by_id(page)
        orchestrator._index_headings(page)
        orchestrator._index_target_directives(page)


def _index_by_path(orchestrator: Any, page: PageLike, content_dir: Path) -> None:
    """Index a page by its content-relative path (without extension)."""
    try:
        page.source_path.relative_to(content_dir)
    except ValueError:
        # Page is not relative to content_dir (e.g., generated page)
        return
    path_key = xref_path_key(page.source_path, orchestrator.site.root_path)
    orchestrator.site.xref_index["by_path"][path_key] = page


def _index_by_slug(orchestrator: Any, page: PageLike) -> None:
    """Index a page by slug (multiple pages can share a slug)."""
    if hasattr(page, "slug") and page.slug:
        orchestrator.site.xref_index["by_slug"].setdefault(page.slug, []).append(page)


def _index_by_id(orchestrator: Any, page: PageLike) -> None:
    """Index a page by its custom frontmatter ``id``."""
    if "id" in page.metadata:
        ref_id = page.metadata["id"]
        orchestrator.site.xref_index["by_id"][ref_id] = page


def _index_headings(orchestrator: Any, page: PageLike) -> None:
    """Index heading anchors from a page's TOC.

    Each heading is added to ``by_heading`` and also to ``by_anchor`` for
    direct ``[[#anchor]]`` resolution. On a same-version anchor collision
    the *existing* entry is kept (heading rule); a later target directive
    may still take precedence.

    NOTE: This accesses toc_items BEFORE parsing (during discovery phase).
    This is safe because toc_items returns [] when toc is not set and does
    NOT cache the empty result; after parsing, the real structure is used.
    """
    if not (hasattr(page, "toc_items") and page.toc_items):
        return

    page_version = getattr(page, "version", None)
    for toc_item in page.toc_items:
        heading_text = toc_item.get("title", "").lower()
        anchor_id = toc_item.get("id", "")
        if not (heading_text and anchor_id):
            continue
        orchestrator.site.xref_index["by_heading"].setdefault(heading_text, []).append(
            (page, anchor_id)
        )
        anchor_key = anchor_id.lower()
        existing_entries = orchestrator.site.xref_index["by_anchor"].setdefault(anchor_key, [])
        same_version_entry = next(
            ((p, a, v) for p, a, v in existing_entries if v == page_version),
            None,
        )
        if same_version_entry:
            # Collision within same version - warn but keep existing
            # (target directives will overwrite later).
            existing_page, existing_anchor, _ = same_version_entry
            orchestrator._warn_anchor_collision(
                page=page,
                anchor_id=anchor_id,
                existing_page=existing_page,
                existing_anchor=existing_anchor,
                page_version=page_version,
                details=(
                    f"Heading anchor '{anchor_id}' collides within version '{page_version or 'unversioned'}'. "
                    f"Heading in {page.source_path} conflicts with existing anchor '{existing_anchor}' "
                    f"in {existing_page.source_path}. Target directives will take precedence if added later."
                ),
            )
            # Don't add duplicate - keep existing entry
        else:
            existing_entries.append((page, anchor_id, page_version))


def _index_target_directives(orchestrator: Any, page: PageLike) -> None:
    """Index ``:::{target} id`` directives from a page's raw source.

    Target directives are explicit and take precedence over heading
    anchors: on a same-version anchor collision the existing same-version
    entries are *evicted* before the directive entry is appended (eviction
    rule), the opposite of :meth:`_index_headings`.
    """
    source = get_raw_source(page)
    if not source:
        cached_anchors = getattr(page, "_target_anchors_cache", None)
        if cached_anchors:
            target_anchors = list(cached_anchors)
        else:
            return
    elif hasattr(page, "content") and source:
        target_anchors = orchestrator._extract_target_directives(source)
    else:
        return

    page_version = getattr(page, "version", None)
    for anchor_id in target_anchors:
        anchor_key = anchor_id.lower()
        existing_entries = orchestrator.site.xref_index["by_anchor"].setdefault(anchor_key, [])
        same_version_entry = next(
            ((p, a, v) for p, a, v in existing_entries if v == page_version),
            None,
        )
        if same_version_entry:
            # Collision within same version - target directives take
            # precedence: evict existing same-version entries first.
            orchestrator.site.xref_index["by_anchor"][anchor_key] = [
                (p, a, v) for p, a, v in existing_entries if v != page_version
            ]
            existing_page, existing_anchor, _ = same_version_entry
            orchestrator._warn_anchor_collision(
                page=page,
                anchor_id=anchor_id,
                existing_page=existing_page,
                existing_anchor=existing_anchor,
                page_version=page_version,
                details=(
                    f"Target directive '::{{target}} {anchor_id}' in version '{page_version or 'unversioned'}' "
                    f"collides with existing anchor '{existing_anchor}' in {existing_page.source_path}. "
                    f"Target directive takes precedence. Use '[[!{anchor_id}]]' to explicitly reference it."
                ),
            )
        # Add target directive entry (takes precedence over heading anchors in same version)
        orchestrator.site.xref_index["by_anchor"][anchor_key].append(
            (page, anchor_id, page_version)
        )


def _extract_target_directives(_orchestrator: Any, content: str) -> list[str]:
    """
    Extract target directive anchor IDs from markdown content.

    Finds all :::{target} id directives and returns their anchor IDs.
    This enables indexing target anchors for cross-reference resolution.

    Args:
        content: Markdown content to search

    Returns:
        List of anchor IDs found in target directives
    """
    return extract_target_directives_from_content(content)
