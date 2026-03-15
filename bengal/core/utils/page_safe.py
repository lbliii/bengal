"""
Safe page attribute access for mixed page collections.

Provides defensive accessors for pages that may be Page, PageProxy,
generated pages, or other page-like objects with varying attributes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.protocols import PageLike


def get_tags_safe(page: PageLike) -> tuple[str, ...]:
    """
    Safe tag access for pages that may not have a tags attribute.

    Use when iterating over mixed collections (content + generated pages)
    where some pages may lack tags (e.g., tag-index, archive pages).

    Returns:
        Tuple of tag strings (empty if page has no tags)
    """
    tags = getattr(page, "tags", None)
    if tags is not None and isinstance(tags, (list, tuple)):
        return tuple(str(t) for t in tags if t is not None)
    return ()
