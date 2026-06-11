"""
Page Navigation - Free functions for navigation and hierarchy.

Functions accept explicit parameters (page, site, section) instead of
accessing them through mixin self-reference.

Related Modules:
- bengal.core.section: SectionLike class with page containment
- bengal.rendering.template_functions.navigation: Template navigation helpers

See Also:
- bengal/core/page/__init__.py: Page class that wraps these functions as properties

"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site.context import SiteContext
    from bengal.protocols.core import PageLike, SectionLike


def _get_site_page_index(site: SiteContext) -> dict:
    """Return the registry-cached page→index mapping for site.pages.

    Delegates to ContentRegistry.page_index, which memoizes the mapping and
    rebuilds it whenever the pages-list length changes (covers the common
    case of pages being appended during taxonomy/archive generation).
    """
    return site.registry.page_index(site.pages)


def _get_section_page_index(section: SectionLike) -> dict:
    """Return a lazily-built and cached source_path→index mapping for section.sorted_pages.

    Keyed by ``source_path`` (a page's stable identity), not the page object: the shard
    render path resolves ``page._section`` to a *snapshot* section whose ``sorted_pages`` are
    PageSnapshots/PageViews, never the live ``page`` object, so object-identity keying would
    miss every lookup there (and silently drop prev/next from the per-page JSON). source_path
    is unique per page within a section, so this is identical to object keying on the live
    path. sorted_pages is a @cached_property so the list is stable; rebuild only when its
    length changes. The cache write is best-effort: a frozen section rejects assignment
    (AttributeError on a frozen dataclass; TypeError from the SectionSnapshot's generated
    __setattr__) — fine, the tiny index is just recomputed per call there.
    """
    sorted_pages = section.sorted_pages
    cached: dict | None = getattr(section, "_sorted_page_index_cache", None)
    if cached is None or len(cached) != len(sorted_pages):
        cached = {p.source_path: i for i, p in enumerate(sorted_pages)}
        with suppress(AttributeError, TypeError):
            section._sorted_page_index_cache = cached  # type: ignore[attr-defined]
    return cached


def get_next_page(page: PageLike, site: SiteContext | None) -> PageLike | None:
    """Get the next page in the site's collection."""
    if not site or not hasattr(site, "pages"):
        return None
    try:
        pages = site.pages
        idx = _get_site_page_index(site).get(page)
        if idx is not None and idx < len(pages) - 1:
            return pages[idx + 1]
    except ValueError, IndexError:
        pass
    return None


def get_prev_page(page: PageLike, site: SiteContext | None) -> PageLike | None:
    """Get the previous page in the site's collection."""
    if not site or not hasattr(site, "pages"):
        return None
    try:
        pages = site.pages
        idx = _get_site_page_index(site).get(page)
        if idx is not None and idx > 0:
            return pages[idx - 1]
    except ValueError, IndexError:
        pass
    return None


def get_next_in_section(page: PageLike, section: SectionLike | None) -> PageLike | None:
    """Get the next page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    # A section index page (_index/index) is the section's landing page, not a content
    # sibling — it has no in-section prev/next. The live Section excludes it from
    # sorted_pages (so the lookup below misses), but a snapshot section INCLUDES it, so guard
    # explicitly to keep the two paths byte-identical.
    if page.source_path.stem in ("_index", "index"):
        return None
    try:
        sorted_pages = section.sorted_pages
        idx = _get_section_page_index(section).get(page.source_path)
        if idx is None:
            return None
        next_idx = idx + 1
        while next_idx < len(sorted_pages):
            next_page = sorted_pages[next_idx]
            if next_page.source_path.stem not in ("_index", "index"):
                return next_page
            next_idx += 1
    except ValueError, IndexError:
        pass
    return None


def get_prev_in_section(page: PageLike, section: SectionLike | None) -> PageLike | None:
    """Get the previous page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    # A section index page (_index/index) is the section's landing page, not a content
    # sibling — it has no in-section prev/next. The live Section excludes it from
    # sorted_pages (so the lookup below misses), but a snapshot section INCLUDES it, so guard
    # explicitly to keep the two paths byte-identical.
    if page.source_path.stem in ("_index", "index"):
        return None
    try:
        sorted_pages = section.sorted_pages
        idx = _get_section_page_index(section).get(page.source_path)
        if idx is None:
            return None
        prev_idx = idx - 1
        while prev_idx >= 0:
            prev_page = sorted_pages[prev_idx]
            if prev_page.source_path.stem not in ("_index", "index"):
                return prev_page
            prev_idx -= 1
    except ValueError, IndexError:
        pass
    return None


def get_ancestors(section: SectionLike | None) -> list[SectionLike]:
    """Get all ancestor sections from immediate parent to root."""
    result: list[SectionLike] = []
    current = section
    while current:
        result.append(current)
        current = getattr(current, "parent", None)
    return result
