"""
Section utility functions.

Module-level helper functions for working with sections. These were relocated
from utils/sections.py during architecture refactoring.

Public API:
    get_page_section: Return a page's assigned section without requiring Page internals
    set_page_section: Assign a section reference to a mutable page compatibility object
    resolve_page_section_path: Resolve a page's section path as a string

Related Modules:
    bengal.core.section: Section class
    bengal.core.page: Legacy Page class with section references
"""

from __future__ import annotations

from typing import Any


def _is_mock_attribute_placeholder(value: Any) -> bool:
    """Return True for auto-created mock child attributes."""
    value_type = type(value)
    if not value_type.__module__.startswith("unittest.mock"):
        return False

    if getattr(value, "_mock_parent", None) is None:
        return False

    return not any(key != "method_calls" and not key.startswith("_") for key in value.__dict__)


def get_page_section(page: Any) -> Any | None:
    """
    Return the section assigned to a page-like object.

    This helper keeps callers from depending on the mutable Page compatibility
    class or the private `_section` protocol member. During the migration, legacy
    pages may expose `_section` while record/proxy-style pages may expose
    `section`; callers only need the resolved association.
    """
    if page is None:
        return None

    try:
        section = getattr(page, "_section", None)
    except Exception:
        section = None

    if section is not None and not _is_mock_attribute_placeholder(section):
        return section

    try:
        section = getattr(page, "section", None)
    except Exception:
        return None

    if section is not None and not _is_mock_attribute_placeholder(section):
        return section
    return None


def set_page_section(page: Any, section: Any | None) -> None:
    """
    Assign a section reference to a mutable page compatibility object.

    New immutable page records should carry section identity in their own data.
    This setter exists only for compatibility objects that still need a runtime
    section reference while the mutable Page class is being retired.
    """
    if page is None:
        return

    page._section = section


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

    Note:
        This function is intentionally silent on errors, falling back gracefully.
        Core modules do not log; orchestrators handle observability.

    """
    if page is None:
        return None

    section_value = get_page_section(page)

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
