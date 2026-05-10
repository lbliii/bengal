"""Cache invalidation helpers for derived Section views."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.section import Section


_LOCAL_CACHE_KEYS = frozenset(
    {
        "icon",
        "sorted_subsections",
        "regular_pages",
        "sorted_pages",
        "regular_pages_recursive",
        "href",
        "_path",
        "subsection_index_urls",
        "has_nav_children",
        "content_pages",
        "post_count",
        "post_count_recursive",
        "word_count",
        "total_reading_time",
    }
)

_ANCESTOR_CACHE_KEYS = frozenset(
    {
        "regular_pages_recursive",
        "subsection_index_urls",
        "has_nav_children",
        "content_pages",
        "post_count",
        "post_count_recursive",
        "word_count",
        "total_reading_time",
    }
)

_HIERARCHY_CACHE_KEYS = frozenset({"hierarchy", "depth"})


def invalidate_section_derived_caches(section: Section) -> None:
    """Clear cached section views affected by page/subsection membership changes."""
    current: Section | None = section
    first = True
    while current is not None:
        keys = _LOCAL_CACHE_KEYS if first else _ANCESTOR_CACHE_KEYS
        for key in keys:
            current.__dict__.pop(key, None)
        first = False
        current = current.parent


def invalidate_section_hierarchy_caches(section: Section) -> None:
    """Clear cached hierarchy/depth values for a section subtree."""
    stack = [section]
    while stack:
        current = stack.pop()
        for key in _HIERARCHY_CACHE_KEYS:
            current.__dict__.pop(key, None)
        stack.extend(current.subsections)
