"""
Shared SVG icon utilities for directive rendering.

Provides inline SVG icons from Bengal's icon library for use in cards, buttons,
and other directives without requiring the full icon directive.

Usage:
    from bengal.rendering.plugins.directives._icons import render_svg_icon

    icon_html = render_svg_icon("terminal", size=20)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = ["render_svg_icon", "get_icon_svg"]

# Icon registry - maps icon names to SVG content (lazy loaded)
_icon_cache: dict[str, str] = {}


def _get_icons_directory() -> Path:
    """Get the icons directory from the default theme."""
    return Path(__file__).parents[3] / "themes" / "default" / "assets" / "icons"


def _load_icon(name: str) -> str | None:
    """
    Load an icon SVG by name.

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


def render_svg_icon(
    name: str,
    size: int = 20,
    css_class: str = "",
    aria_label: str = "",
) -> str:
    """
    Render an SVG icon for use in directives.

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

    import re

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

    # Remove existing width/height/class attributes from SVG
    svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
    svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

    # Add our attributes to <svg> tag
    svg_modified = re.sub(
        r"<svg\s",
        f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
        svg_modified,
        count=1,
    )

    return svg_modified


def _escape_attr(value: str) -> str:
    """Escape HTML attribute value."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# Icon mapping from semantic names to Bengal SVG icons
# Used for backwards compatibility with emoji icon names
ICON_MAP: dict[str, str] = {
    # Navigation & Actions
    "arrow-right": "chevron-right",
    "arrow-left": "chevron-left",
    "arrow-up": "chevron-up",
    "arrow-down": "chevron-down",
    "external": "external",
    "link": "link",
    "search": "search",
    "menu": "menu",
    "close": "close",
    # Status & Feedback
    "info": "info",
    "warning": "warning",
    "error": "error",
    "check": "check",
    "success": "check",
    # Files & Content
    "file": "file",
    "folder": "folder",
    "document": "file",
    "code": "code",
    "copy": "copy",
    "edit": "edit",
    "trash": "trash",
    "download": "download",
    "upload": "upload",
    # UI
    "settings": "settings",
    "star": "star",
    "heart": "heart",
    "bookmark": "bookmark",
    "tag": "tag",
    "calendar": "calendar",
    "clock": "clock",
    "pin": "pin",
    # Theme
    "sun": "sun",
    "moon": "moon",
    "palette": "palette",
    # Bengal-specific
    "terminal": "terminal",
    "docs": "docs",
    "notepad": "notepad",
    # Mid-century modern
    "atomic": "atomic",
    "starburst": "starburst",
    "boomerang": "boomerang",
}


def render_icon(name: str, size: int = 20) -> str:
    """
    Render an icon by name, with fallback to emoji.

    This function provides backwards compatibility with emoji icons
    while preferring SVG icons when available.

    Args:
        name: Icon name (semantic name like "book", "rocket", etc.)
        size: Icon size in pixels

    Returns:
        HTML for icon (SVG or emoji fallback)
    """
    # Map semantic name to Bengal icon name
    icon_name = ICON_MAP.get(name, name)

    # Try SVG icon first
    svg = render_svg_icon(icon_name, size=size)
    if svg:
        return svg

    # Fallback to emoji for icons not in SVG library
    emoji_fallback: dict[str, str] = {
        "book": "📖",
        "rocket": "🚀",
        "users": "👥",
        "database": "🗄️",
        "tools": "🔧",
        "shield": "🛡️",
        "graduation-cap": "🎓",
        "mortar-board": "🎓",
        "package": "📦",
        "graph": "📊",
        "shield-lock": "🔒",
        "github": "🐙",
        "home": "🏠",
    }

    return emoji_fallback.get(name, "")

