"""
Shared helper functions for navigation modules.

Internal utilities used across navigation function implementations.
"""

from __future__ import annotations

from typing import Any


def get_nav_title(obj: Any, fallback: str = "Untitled") -> str:
    """
    Get navigation title for a page or section, falling back to title.

    Uses nav_title if available, otherwise falls back to title.
    This allows pages to specify shorter titles for menus/navigation.

    Args:
        obj: Page, Section, or any object with title/nav_title attributes
        fallback: Fallback if neither nav_title nor title is available

    Returns:
        Navigation title string
    """
    # First try nav_title (short title for navigation)
    nav_title = getattr(obj, "nav_title", None)
    if nav_title:
        return str(nav_title)
    # Fall back to title
    title = getattr(obj, "title", None)
    if title:
        return str(title)
    return fallback
