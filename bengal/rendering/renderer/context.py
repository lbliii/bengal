"""
Renderer-owned page context helpers.

``build_page_context`` in ``bengal.rendering.context`` stays the unified builder.
This module holds Renderer-only assembly: pagination coercion, top-level nav
content, section-snapshot conversion, generated archive pages, cached blocks,
and root-index posts/subsections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.section.utils import get_page_section
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.protocols import PageLike, SectionLike
    from bengal.snapshots.types import SectionSnapshot, SiteSnapshot

logger = get_logger(__name__)


def default_pagination(base_url: str) -> dict[str, Any]:
    """Return default single-page pagination dict."""
    return {
        "current_page": 1,
        "total_pages": 1,
        "has_next": False,
        "has_prev": False,
        "base_url": base_url,
    }


def coerce_pagination_ints(pagination: dict[str, Any]) -> dict[str, Any]:
    """Coerce YAML string pagination values to int."""
    result = dict(pagination)
    for key in ("current_page", "total_pages"):
        if key in result and result[key] is not None:
            try:
                result[key] = int(result[key])
            except ValueError, TypeError:
                result[key] = 1
    return result


def get_top_level_content(renderer: Any) -> tuple[list[PageLike], list[SectionLike]]:
    """
    Get top-level pages and sections (not nested in any section).

    Fast path (lock-free): If snapshot has pre-computed top_level_pages/sections,
    returns them directly — no lock needed.

    Fallback path: Uses O(n) algorithm with set-based filtering.
    Result is cached for the lifetime of the Renderer instance.
    """
    if renderer._top_level_cache is not None:
        return renderer._top_level_cache

    # Fast path: use pre-computed snapshot data (lock-free)
    snapshot = getattr(renderer.build_context, "snapshot", None) if renderer.build_context else None
    if snapshot is not None and snapshot.navigation.top_level_pages:
        renderer._top_level_cache = (
            list(snapshot.navigation.top_level_pages),
            list(snapshot.navigation.top_level_sections),
        )
        return renderer._top_level_cache

    # Fallback: compute from mutable site data
    # Build set of all pages that are in any section (O(sections × pages_per_section))
    pages_in_sections: set[int] = set()
    for section in renderer.site.sections:
        for p in section.pages:
            pages_in_sections.add(id(p))

    # Build set of all sections that are subsections of another (O(sections × subsections))
    nested_sections: set[int] = set()
    for parent in renderer.site.sections:
        for s in parent.subsections:
            nested_sections.add(id(s))

    # Filter using O(1) set membership
    top_level_pages = [p for p in renderer.site.regular_pages if id(p) not in pages_in_sections]
    top_level_subsections = [s for s in renderer.site.sections if id(s) not in nested_sections]

    renderer._top_level_cache = (top_level_pages, top_level_subsections)
    return renderer._top_level_cache


def to_section_snapshot(
    renderer: Any,
    section: SectionLike | SectionSnapshot | None,
    snapshot: SiteSnapshot | None,
) -> SectionSnapshot | None:
    """
    Convert a mutable Section to its SectionSnapshot equivalent.

    PERF: Uses BuildContext.get_section_snapshot() for O(1) cached lookup
    instead of O(S) iteration over snapshot.sections.
    """
    from bengal.snapshots.types import NO_SECTION, SectionSnapshot

    if section is None:
        return NO_SECTION

    # If already a SectionSnapshot, return as-is
    if isinstance(section, SectionSnapshot):
        return section

    # PERF: Use BuildContext cached lookup if available (O(1) vs O(S))
    if renderer.build_context:
        return renderer.build_context.get_section_snapshot(section)

    # Fallback: O(S) iteration (when no build_context available)
    if snapshot:
        for sec_snap in snapshot.sections:
            if sec_snap.path == getattr(section, "path", None) or sec_snap.name == getattr(
                section, "name", ""
            ):
                return sec_snap

    # Fallback: return NO_SECTION sentinel
    return NO_SECTION


def to_section_snapshots(
    renderer: Any,
    sections: Sequence[SectionLike | SectionSnapshot],
    snapshot: SiteSnapshot | None,
) -> list[SectionSnapshot]:
    """Convert a list of mutable Sections to SectionSnapshots."""
    from bengal.snapshots.types import NO_SECTION

    result = []
    for section in sections:
        if section is None:
            continue
        snap = renderer._to_section_snapshot(section, snapshot)
        if snap != NO_SECTION:
            result.append(snap)
    return result


def inject_cached_blocks(renderer: Any, context: dict[str, Any], template_name: str) -> None:
    """Inject pre-warmed KIDA site-scoped blocks into template context."""
    if not (renderer.block_cache and renderer.block_cache._site_blocks):
        return

    # Get all cached blocks from base.html (the primary parent template)
    # We use the cache directly - no introspection needed during rendering
    cached_blocks = {}
    for key, html in renderer.block_cache._site_blocks.items():
        # Keys are formatted as "template:block", e.g., "base.html:site_footer"
        if ":" in key:
            cached_template, block_name = key.split(":", 1)
            # Only inject blocks from parent templates (base.html)
            # Skip empty cached blocks (they'd just add overhead)
            if cached_template == "base.html" and html:
                cached_blocks[block_name] = html

    # Inject cached blocks into context for template to use
    if cached_blocks:
        context["_cached_blocks"] = cached_blocks
        # Inject stats object so CachedBlocksDict can record hits
        if hasattr(renderer.block_cache, "_stats"):
            context["_cached_stats"] = renderer.block_cache._stats

        logger.debug(
            "renderer_using_cached_blocks",
            template=template_name,
            cached_blocks=list(cached_blocks.keys()),
        )


def add_root_index_context(
    renderer: Any,
    page: PageLike,
    context: dict[str, Any],
    snapshot: SiteSnapshot | None,
) -> None:
    """Add site-level posts/subsections for a root index that is not generated."""
    page_type = page.metadata.get("type")
    is_index_page = page.source_path.stem in ("_index", "index")

    if not (
        is_index_page
        and get_page_section(page) is None
        and not page.metadata.get("_generated")
        and page_type not in ("tag", "tag-index")
    ):
        return

    # For root home page, provide site-level context as fallback
    # Filter to top-level items only (exclude nested sections/pages)
    # PERF: Use cached sets for O(n) instead of O(n²) filtering
    top_level_pages, top_level_subsections = renderer._get_top_level_content()

    # Convert subsections to SectionSnapshots (no wrapper needed)
    # SectionSnapshot has params property and __bool__ for template compatibility
    subsections_for_context = renderer._to_section_snapshots(top_level_subsections, snapshot)

    context.update(
        {
            "posts": top_level_pages,
            "pages": top_level_pages,  # Alias
            "subsections": subsections_for_context,
        }
    )


def add_generated_page_context(renderer: Any, page: PageLike, context: dict[str, Any]) -> None:
    """Add special context variables for generated pages (archives, tags, etc.)."""
    page_type = page.metadata.get("type")

    archive_like_types = {
        "archive",
        "blog",
        "autodoc/python",
        "autodoc-cli",
        "tutorial",
        "changelog",
    }

    if page_type in archive_like_types:
        renderer._add_archive_like_generated_page_context(page, context)
        return

    if page_type == "tag":
        renderer._add_tag_generated_page_context(page, context)
        return

    if page_type == "tag-index":
        renderer._add_tag_index_generated_page_context(page, context)
        return


def add_archive_like_generated_page_context(
    renderer: Any, page: PageLike, context: dict[str, Any]
) -> None:
    """
    Add context for archive/reference/blog-like generated pages.

    Note: Posts are already filtered and sorted by the content type strategy
    in the SectionOrchestrator, so we do not re-sort here.
    """
    section = page.metadata.get("_section") if page.metadata is not None else None
    all_posts = (
        page.metadata.get("_posts", []) if page.metadata is not None else []
    )  # Already filtered & sorted!
    page_metadata = page.metadata if page.metadata is not None else {}
    subsections = page_metadata.get("_subsections", [])
    paginator = page_metadata.get("_paginator")
    page_num = int(page_metadata.get("_page_num") or 1)

    if paginator:
        posts = paginator.page(page_num)
        section_name = section.name if section is not None else ""
        # Guard against empty section name to avoid double-slash URLs like "//page/"
        base_url = f"/{section_name}/" if section_name else "/"
        pagination = paginator.page_context(page_num, base_url)
    else:
        posts = all_posts
        pagination = renderer._default_pagination(f"/{section.name}/" if section else "/")

    # Convert section to SectionSnapshot (no wrapper needed)
    snapshot = None
    if hasattr(renderer, "build_context") and renderer.build_context:
        snapshot = getattr(renderer.build_context, "snapshot", None)
    section_for_context = renderer._to_section_snapshot(section, snapshot)

    safe_pagination = renderer._coerce_pagination_ints(pagination)

    context.update(
        {
            "section": section_for_context,
            "posts": posts,
            "pages": posts,  # Alias
            "subsections": subsections,
            "total_posts": len(all_posts),
            **safe_pagination,
        }
    )
