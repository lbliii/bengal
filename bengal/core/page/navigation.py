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

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

_index_cache: WeakKeyDictionary[Any, dict[int, int]] = WeakKeyDictionary()
_index_cache_lock = threading.Lock()


def _page_index_map(pages: list[Page] | tuple[Page, ...]) -> dict[int, int]:
    """Build id(page)->index map, cached per list identity."""
    key_id = id(pages)
    cached = _index_cache.get(pages)
    if cached is not None and getattr(cached, "_list_id", None) == key_id:
        return cached
    with _index_cache_lock:
        cached = _index_cache.get(pages)
        if cached is not None and getattr(cached, "_list_id", None) == key_id:
            return cached
        mapping: dict[int, int] = {id(p): i for i, p in enumerate(pages)}
        mapping._list_id = key_id  # type: ignore[attr-defined]
        _index_cache[pages] = mapping  # type: ignore[index]
        return mapping


def _find_index(page: Page, pages: list[Page] | tuple[Page, ...]) -> int | None:
    """O(1) index lookup via cached identity map."""
    mapping = _page_index_map(pages)
    return mapping.get(id(page))


def get_next_page(page: Page, site: Site | None) -> Page | None:
    """Get the next page in the site's collection."""
    if not site or not hasattr(site, "pages"):
        return None
    pages = site.pages
    idx = _find_index(page, pages)
    if idx is not None and idx < len(pages) - 1:
        return pages[idx + 1]
    return None


def get_prev_page(page: Page, site: Site | None) -> Page | None:
    """Get the previous page in the site's collection."""
    if not site or not hasattr(site, "pages"):
        return None
    pages = site.pages
    idx = _find_index(page, pages)
    if idx is not None and idx > 0:
        return pages[idx - 1]
    return None


def get_next_in_section(page: Page, section: Section | None) -> Page | None:
    """Get the next page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    sorted_pages = section.sorted_pages
    idx = _find_index(page, sorted_pages)
    if idx is None:
        return None
    next_idx = idx + 1
    while next_idx < len(sorted_pages):
        next_page = sorted_pages[next_idx]
        if next_page.source_path.stem not in ("_index", "index"):
            return next_page
        next_idx += 1
    return None


def get_prev_in_section(page: Page, section: Section | None) -> Page | None:
    """Get the previous page within the same section, respecting weight order."""
    if not section or not hasattr(section, "sorted_pages"):
        return None
    sorted_pages = section.sorted_pages
    idx = _find_index(page, sorted_pages)
    if idx is None:
        return None
    prev_idx = idx - 1
    while prev_idx >= 0:
        prev_page = sorted_pages[prev_idx]
        if prev_page.source_path.stem not in ("_index", "index"):
            return prev_page
        prev_idx -= 1
    return None


def is_root_level_page(page: Any, content_dir: Path) -> bool:
    """
    Check if a page is at content root (e.g. content/about.md, not content/posts/foo.md).

    Excludes index.md (homepage) and section indices (_index.md).
    """
    try:
        src = Path(page.source_path)
        if src.is_absolute():
            rel = src.relative_to(content_dir)
        else:
            rel_str = to_posix(str(src))
            rel = Path(rel_str[8:]) if rel_str.startswith("content/") else Path(rel_str)
        parts = to_posix(str(rel)).split("/")
        return len(parts) == 1 and parts[0] not in ("index.md", "_index.md")
    except ValueError, AttributeError:
        return False


def get_ancestors(section: Section | None) -> list[Section]:
    """Get all ancestor sections from immediate parent to root."""
    result: list[Section] = []
    current = section
    while current:
        result.append(current)
        current = getattr(current, "parent", None)
    return result
