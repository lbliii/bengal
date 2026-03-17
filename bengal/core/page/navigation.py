"""
Page Navigation - Free functions for navigation and hierarchy.

Functions accept explicit parameters (page, site, section) instead of
accessing them through mixin self-reference.

Related Modules:
- bengal.core.section: Section class with page containment
- bengal.rendering.template_functions.navigation: Template navigation helpers

See Also:
- bengal/core/page/__init__.py: Page class that wraps these functions as properties

"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


def _get_site_page_index(site: Site) -> dict:
    """Return a lazily-built and cached page→index mapping for site.pages.

    The cache is stored directly on the site object and rebuilt whenever the
    number of pages changes (covers the common case of pages being appended
    during taxonomy/archive generation).
    """
    pages = site.pages
    cached: dict | None = getattr(site, "_page_index_cache", None)
    if cached is None or len(cached) != len(pages):
        cached = {p: i for i, p in enumerate(pages)}
        with suppress(AttributeError):
            site._page_index_cache = cached  # type: ignore[attr-defined]
    return cached


def _get_section_page_index(section: Section) -> dict:
    """Return a lazily-built and cached page→index mapping for section.sorted_pages.

    sorted_pages is itself a @cached_property so the underlying list is stable;
    we only rebuild when its length changes.
    """
    sorted_pages = section.sorted_pages
    cached: dict | None = getattr(section, "_sorted_page_index_cache", None)
    if cached is None or len(cached) != len(sorted_pages):
        cached = {p: i for i, p in enumerate(sorted_pages)}
        with suppress(AttributeError):
            section._sorted_page_index_cache = cached  # type: ignore[attr-defined]
    return cached


def get_next_page(page: Page, site: Site | None) -> Page | None:
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


def get_prev_page(page: Page, site: Site | None) -> Page | None:
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


def get_next_in_section(page: Page, section: Section | None) -> Page | None:
    """Get the next page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    try:
        sorted_pages = section.sorted_pages
        idx = _get_section_page_index(section).get(page)
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


def get_prev_in_section(page: Page, section: Section | None) -> Page | None:
    """Get the previous page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    try:
        sorted_pages = section.sorted_pages
        idx = _get_section_page_index(section).get(page)
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


def get_ancestors(section: Section | None) -> list[Section]:
    """Get all ancestor sections from immediate parent to root."""
    result: list[Section] = []
    current = section
    while current:
        result.append(current)
        current = getattr(current, "parent", None)
    return result
