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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


def get_next_page(page: Page, site: Site | None) -> Page | None:
    """Get the next page in the site's collection."""
    if not site or not hasattr(site, "pages"):
        return None
    try:
        pages = site.pages
        idx = pages.index(page)
        if idx < len(pages) - 1:
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
        idx = pages.index(page)
        if idx > 0:
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
        idx = sorted_pages.index(page)
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
        idx = sorted_pages.index(page)
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
