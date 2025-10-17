"""
Section-related utility helpers.

Provides safe normalization helpers for section references that may be either
`Section` objects or precomputed string paths depending on context (e.g.,
runtime vs cached/incremental data structures).
"""

from typing import Any


def resolve_page_section_path(page: Any) -> str | None:
    """
    Resolve a page's section path as a string, handling multiple representations.

    The page may expose its section association in different ways depending on
    build phase or caching:
    - `page.section` may be a `Section` object with a `.path` attribute
    - `page.section` may already be a string path
    - It may be missing or falsy for root-level pages

    Args:
        page: Page-like object which may have a `section` attribute

    Returns:
        String path to the section (e.g., "docs/tutorials") or None if not set.
    """
    if page is None:
        return None

    # Some page proxies may raise on getattr; guard with try/except
    try:
        section_value = getattr(page, "section", None)
    except Exception:
        section_value = None

    if not section_value:
        return None

    # If it's a Section-like object with a `.path`, return its string form
    if hasattr(section_value, "path"):
        try:
            return str(section_value.path)
        except Exception:
            # Fallback to str(section_value) if `.path` isn't convertible
            return str(section_value)

    # Already a string or stringable value
    return str(section_value)
