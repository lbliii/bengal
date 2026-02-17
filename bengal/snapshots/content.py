"""
Content snapshotting for snapshot engine.

Functions for creating immutable PageSnapshot and SectionSnapshot objects
from mutable Page and Section instances. Handles the initial snapshot pass,
section tree recursion, and navigation resolution.

"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SectionLike, SiteLike

from bengal.config.utils import coerce_int
from bengal.snapshots.scheduling import (
    _compute_attention_score,
    _estimate_render_time,
    _find_index_page,
    _most_common_template,
)
from bengal.snapshots.types import (
    PageSnapshot,
    SectionSnapshot,
)
from bengal.snapshots.utils import (
    compute_page_hash,
    resolve_template_name,
    update_frozen,
)


def _safe_weight(value: object) -> float:
    """Coerce a weight value to float for safe sorting.

    Weight may arrive as int, str, float, or None from YAML/cascade.
    Comparing mixed types (e.g. int <= str) raises TypeError in Python,
    so we normalise to float before any sort key uses the value.
    """
    if value is None:
        return float("inf")
    try:
        return float(value)
    except ValueError, TypeError:
        return float("inf")


def _snapshot_page_initial(page: PageLike, site: SiteLike) -> PageSnapshot:
    """Create initial page snapshot (section resolved later)."""
    metadata = dict(page.metadata) if page.metadata else {}

    # Get href (includes baseurl for public URLs)
    # Note: page.href applies baseurl; _path is site-relative without baseurl
    href = getattr(page, "href", None) or getattr(page, "_path", "") or ""

    # Get output_path
    output_path = getattr(page, "output_path", None)
    if output_path is None:
        # Compute from source_path if not set
        source_path = page.source_path
        if source_path:
            # Convert .md to .html, preserve directory structure
            output_path = site.output_dir / source_path.relative_to(
                site.root_path / "content"
            ).with_suffix(".html")
        else:
            output_path = site.output_dir / "index.html"

    # Determine template name
    template_name = resolve_template_name(page)

    # Get raw markdown content (for reference/debugging/incremental comparison)
    raw_content = getattr(page, "_source", "") or getattr(page, "content", "") or ""

    # Get parsed HTML (pre-parsed during parsing phase - RFC: rfc-bengal-snapshot-engine)
    # This is what rendering should use, eliminating re-parsing during render
    parsed_html = getattr(page, "html_content", "") or ""

    # Get TOC
    toc = getattr(page, "toc", "") or ""

    # Get TOC items
    toc_items = tuple(getattr(page, "toc_items", []) or [])

    # Get excerpt and meta_description
    excerpt = getattr(page, "excerpt", "") or ""
    meta_description = getattr(page, "meta_description", "") or ""

    # Get reading_time and word_count (coerce in case from cache/YAML as str)
    reading_time = coerce_int(getattr(page, "reading_time", 0), 0)
    word_count = coerce_int(getattr(page, "word_count", 0), 0)

    # Compute content hash
    content_hash = compute_page_hash(page)

    # Compute attention score
    attention_score = _compute_attention_score(page)

    # Estimate render time
    estimated_render_ms = _estimate_render_time(page)

    return PageSnapshot(
        title=page.title or "",
        href=href,
        source_path=page.source_path,
        output_path=output_path,
        template_name=template_name,
        content=raw_content,  # Raw markdown for reference/debugging
        parsed_html=parsed_html,  # Pre-parsed HTML (rendering uses this)
        toc=toc,
        toc_items=toc_items,
        excerpt=excerpt,
        meta_description=meta_description,
        metadata=MappingProxyType(metadata),
        tags=tuple(metadata.get("tags", []) or []),
        categories=tuple(metadata.get("categories", []) or []),
        reading_time=reading_time,
        word_count=word_count,
        content_hash=content_hash,
        attention_score=attention_score,
        estimated_render_ms=estimated_render_ms,
    )


def _snapshot_section_recursive(
    section: SectionLike,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
    depth: int,
    parent: SectionSnapshot | None = None,
) -> SectionSnapshot:
    """Recursively snapshot section tree."""
    # Check cache first (handles re-visits)
    if id(section) in section_cache:
        return section_cache[id(section)]

    metadata = dict(section.metadata) if section.metadata else {}

    # Snapshot pages in this section
    pages = tuple(page_cache[id(p)] for p in section.pages if id(p) in page_cache)

    # Compute sorted variants
    sorted_pages = tuple(
        sorted(
            pages,
            key=lambda p: (
                _safe_weight(p.metadata.get("weight")),
                p.title.lower(),
            ),
        )
    )

    regular_pages = tuple(p for p in sorted_pages if p.source_path.stem not in ("index", "_index"))

    # Get href (_path property)
    href = getattr(section, "_path", None) or getattr(section, "href", "") or ""

    # Get title and nav_title
    title = section.title or section.name
    nav_title = getattr(section, "nav_title", None) or title

    # Get icon
    icon = metadata.get("icon")

    # Get weight
    weight = _safe_weight(metadata.get("weight"))

    # Compute hierarchy
    hierarchy = tuple([*parent.hierarchy, section.name] if parent else [section.name])

    # Get is_virtual
    is_virtual = getattr(section, "is_virtual", False) or section.path is None

    # Most common template
    template_name = _most_common_template(pages)

    # Create snapshot (subsections filled in below)
    snapshot = SectionSnapshot(
        name=section.name,
        title=title,
        nav_title=nav_title,
        href=href,
        path=section.path,
        pages=pages,
        sorted_pages=sorted_pages,
        regular_pages=regular_pages,
        subsections=(),  # Filled below
        sorted_subsections=(),  # Filled below
        parent=parent,
        metadata=MappingProxyType(metadata),
        icon=icon,
        weight=weight,
        depth=depth,
        hierarchy=hierarchy,
        is_virtual=is_virtual,
        template_name=template_name,
        total_pages=len(pages),
    )

    # Cache before recursing (handles cycles)
    section_cache[id(section)] = snapshot

    # Recurse into subsections
    subsections = tuple(
        _snapshot_section_recursive(sub, page_cache, section_cache, depth + 1, snapshot)
        for sub in section.subsections
    )

    sorted_subsections = tuple(sorted(subsections, key=lambda s: (s.weight, s.title.lower())))

    # Find index page
    index_page = _find_index_page(pages)

    # Update total_pages to include subsections
    total = len(pages) + sum(s.total_pages for s in subsections)

    # Update with subsections (frozen, can't mutate)
    snapshot = update_frozen(
        snapshot,
        subsections=subsections,
        sorted_subsections=sorted_subsections,
        index_page=index_page,
        total_pages=total,
    )

    section_cache[id(section)] = snapshot
    return snapshot


def _resolve_navigation(page_cache: dict[int, PageSnapshot], site: SiteLike) -> None:
    """Resolve next/prev navigation links."""
    # Create mapping from source_path to page snapshot for lookup
    pages_by_path: dict[Path, PageSnapshot] = {
        page.source_path: page for page in page_cache.values()
    }

    # Sort pages by source_path for consistent ordering
    sorted_paths = sorted(pages_by_path.keys())

    # Update pages with next/prev refs
    for idx, path in enumerate(sorted_paths):
        page = pages_by_path[path]
        next_page = (
            pages_by_path.get(sorted_paths[idx + 1]) if idx + 1 < len(sorted_paths) else None
        )
        prev_page = pages_by_path.get(sorted_paths[idx - 1]) if idx > 0 else None

        # Only update if navigation changed
        if page.next_page != next_page or page.prev_page != prev_page:
            # Find original page in cache by source_path
            for orig_id, orig_page in list(page_cache.items()):
                if orig_page.source_path == path:
                    # Update snapshot with navigation refs
                    page_cache[orig_id] = update_frozen(
                        page, next_page=next_page, prev_page=prev_page
                    )
                    break
