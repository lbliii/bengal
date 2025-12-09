"""
Shared SVG icon utilities for directive rendering.

Provides inline SVG icons from Bengal's icon library for use in cards, buttons,
and other directives without requiring the full icon directive.

Performance:
    - Icons are lazily loaded on first access and cached
    - Rendered output is LRU cached by (name, size, css_class, aria_label)
    - Regex patterns are pre-compiled at module load

Usage:

```python
from bengal.rendering.plugins.directives._icons import render_svg_icon

icon_html = render_svg_icon("terminal", size=20)
```
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = ["render_svg_icon", "get_icon_svg", "ICON_MAP", "render_icon"]

# Icon registry - maps icon names to SVG content (lazy loaded)
_icon_cache: dict[str, str] = {}

# Pre-compiled regex patterns for SVG manipulation
_RE_WIDTH_HEIGHT = re.compile(r'\s+(width|height)="[^"]*"')
_RE_CLASS = re.compile(r'\s+class="[^"]*"')
_RE_SVG_TAG = re.compile(r"<svg\s")


def _get_icons_directory() -> Path:
    """Get the icons directory from the default theme."""
    return Path(__file__).parents[3] / "themes" / "default" / "assets" / "icons"


def _load_icon(name: str) -> str | None:
    """
    Load an icon SVG by name (with caching).

    Args:
        name: Icon name (without .svg extension)

    Returns:
        SVG content string, or None if not found
    """
    if name in _icon_cache:
        return _icon_cache[name]

    icons_dir = _get_icons_directory()
    if not icons_dir.exists():
        return None

    icon_path = icons_dir / f"{name}.svg"
    if not icon_path.exists():
        return None

    try:
        svg_content = icon_path.read_text(encoding="utf-8")
        _icon_cache[name] = svg_content
        return svg_content
    except OSError:
        return None


def get_icon_svg(name: str) -> str | None:
    """
    Get raw SVG content for an icon.

    Args:
        name: Icon name (e.g., "terminal", "search", "info")

    Returns:
        Raw SVG string, or None if not found
    """
    return _load_icon(name)


def _escape_attr(value: str) -> str:
    """Escape HTML attribute value."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


@lru_cache(maxsize=512)
def render_svg_icon(
    name: str,
    size: int = 20,
    css_class: str = "",
    aria_label: str = "",
) -> str:
    """
    Render an SVG icon for use in directives.

    Uses LRU caching to avoid repeated regex processing for identical
    icon render calls. Typical hit rate >95% for navigation icons.

    Args:
        name: Icon name (e.g., "terminal", "search", "info")
        size: Icon size in pixels (default: 20)
        css_class: Additional CSS classes
        aria_label: Accessibility label

    Returns:
        Inline SVG HTML string, or empty string if icon not found

    Example:
        >>> render_svg_icon("terminal", size=16, css_class="button-icon")
        '<svg width="16" height="16" class="bengal-icon icon-terminal button-icon" ...'
    """
    svg_content = _load_icon(name)
    if svg_content is None:
        return ""

    # Build class list
    classes = ["bengal-icon", f"icon-{name}"]
    if css_class:
        classes.extend(css_class.split())
    class_attr = " ".join(classes)

    # Accessibility attributes
    if aria_label:
        aria_attrs = f'aria-label="{_escape_attr(aria_label)}" role="img"'
    else:
        aria_attrs = 'aria-hidden="true"'

    # Remove existing width/height/class attributes from SVG (use pre-compiled regex)
    svg_modified = _RE_WIDTH_HEIGHT.sub("", svg_content)
    svg_modified = _RE_CLASS.sub("", svg_modified)

    # Add our attributes to <svg> tag
    svg_modified = _RE_SVG_TAG.sub(
        f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
        svg_modified,
        count=1,
    )

    return svg_modified


# Icon mapping from semantic names to Phosphor icon names
# This provides backwards compatibility and semantic naming
ICON_MAP: dict[str, str] = {
    # Navigation & Actions
    "arrow-right": "arrow-right",
    "arrow-left": "arrow-left",
    "arrow-up": "arrow-up",
    "arrow-down": "arrow-down",
    "chevron-right": "chevron-right",
    "chevron-left": "chevron-left",
    "chevron-up": "chevron-up",
    "chevron-down": "chevron-down",
    "external": "arrow-square-out",
    "link": "link",
    "search": "magnifying-glass",
    "menu": "list",
    "close": "x",
    # Status & Feedback
    "info": "info",
    "warning": "warning",
    "error": "x-circle",
    "check": "check",
    "success": "check-circle",
    # Files & Content
    "file": "file",
    "file-text": "file-text",
    "folder": "folder",
    "document": "file",
    "code": "code",
    "copy": "copy",
    "edit": "pencil",
    "trash": "trash",
    "download": "download",
    "upload": "upload",
    # UI & Metadata
    "settings": "settings",
    "star": "star",
    "heart": "heart",
    "bookmark": "bookmark",
    "tag": "tag",
    "calendar": "calendar",
    "clock": "clock",
    "pin": "map-pin",
    "user": "user",
    "arrow-clockwise": "arrow-clockwise",
    # Theme
    "sun": "sun",
    "moon": "moon",
    "palette": "palette",
    # Admonitions (use dedicated admonition icons from icons directory)
    "tip": "tip",
    "note": "note",
    "example": "example",
    "danger": "danger",
    "caution": "caution",
    "lightbulb": "tip",  # Backwards compatibility alias
    # Bengal-specific
    "terminal": "terminal",
    "docs": "file-text",
    "notepad": "note",
    # Mid-century modern (Bengal custom icons)
    "atomic": "atomic",
    "starburst": "starburst",
    "boomerang": "boomerang",
}


def render_icon(name: str, size: int = 20) -> str:
    """
    Render an icon by name, preferring Phosphor SVG icons.

    This function maps common icon names to Phosphor icons and always
    attempts to render SVG first. Only returns empty string if icon not found.

    Args:
        name: Icon name (semantic name like "book", "rocket", etc.)
        size: Icon size in pixels

    Returns:
        HTML for icon (SVG only, empty string if not found)
    """
    if not name:
        return ""

    # Map semantic name to Phosphor icon name
    icon_name = ICON_MAP.get(name, name)

    # Try SVG icon first (uses LRU cache)
    svg = render_svg_icon(icon_name, size=size)
    if svg:
        return svg

    # If direct name didn't work, try common variations
    # This handles cases where frontmatter might use different naming
    variations = {
        "book": "book",
        "rocket": "rocket",
        "users": "users",
        "user": "user",
        "database": "database",
        "tools": "wrench",
        "tool": "wrench",
        "shield": "shield",
        "graduation-cap": "graduation-cap",
        "mortar-board": "graduation-cap",
        "package": "package",
        "graph": "chart-line",
        "chart": "chart-line",
        "shield-lock": "lock",
        "lock": "lock",
        "github": "github-logo",
        "home": "house",
        "house": "house",
        "arrow-up": "arrow-up",
        "arrow-down": "arrow-down",
        "arrow-left": "arrow-left",
        "arrow-right": "arrow-right",
    }

    # Try variation if original didn't work
    if name in variations:
        icon_name = variations[name]
        svg = render_svg_icon(icon_name, size=size)
        if svg:
            return svg

    # Return empty string if no icon found (no emoji fallback)
    return ""


def clear_icon_cache() -> None:
    """
    Clear both the raw icon cache and the render cache.

    Useful for testing or when icons are modified during development.
    """
    _icon_cache.clear()
    render_svg_icon.cache_clear()
