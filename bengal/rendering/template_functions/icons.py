"""
Template functions for rendering SVG icons.

Provides optimized icon rendering functions for use in Jinja2 templates.
Icons are pre-loaded at registration time and rendered output is cached
by (name, size, css_class, aria_label) to minimize per-render overhead.

Performance:
    - All icons pre-loaded at template engine initialization (~86 icons, ~50KB)
    - Rendered SVG cached by parameters (typical hit rate: >95%)
    - Regex processing only on cache miss
    - Zero file I/O during template rendering
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from markupsafe import Markup

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

from bengal.directives._icons import ICON_MAP
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Pre-loaded icon cache: icon_name -> raw SVG content
_preloaded_icons: dict[str, str] = {}

# Flag to track if icons have been preloaded
_icons_preloaded: bool = False

# Site instance for theme config access (set during registration)
_site_instance: Site | None = None


def _get_icons_directory() -> Path:
    """Get the icons directory from the default theme."""
    return Path(__file__).parents[2] / "themes" / "default" / "assets" / "icons"


def _preload_all_icons() -> None:
    """
    Pre-load all icons into memory at startup.

    Called once during template engine initialization. Loads all SVG files
    from the icons directory into the _preloaded_icons cache.
    """
    global _icons_preloaded
    if _icons_preloaded:
        return

    icons_dir = _get_icons_directory()
    if not icons_dir.exists():
        _icons_preloaded = True
        return

    for icon_path in icons_dir.glob("*.svg"):
        try:
            svg_content = icon_path.read_text(encoding="utf-8")
            icon_name = icon_path.stem
            _preloaded_icons[icon_name] = svg_content
        except OSError as e:
            # Skip unreadable files (graceful degradation)
            logger.debug("icon_preload_skipped", path=str(icon_path), error=str(e))

    _icons_preloaded = True


def _escape_attr(value: str) -> str:
    """Escape HTML attribute value."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# Regex patterns compiled once at module load
_RE_WIDTH_HEIGHT = re.compile(r'\s+(width|height)="[^"]*"')
_RE_CLASS = re.compile(r'\s+class="[^"]*"')
_RE_SVG_TAG = re.compile(r"<svg\s")


@lru_cache(maxsize=512)
def _render_icon_cached(
    name: str,
    size: int,
    css_class: str,
    aria_label: str,
) -> str:
    """
    Render an icon with LRU caching for repeated calls.

    The cache key is (name, size, css_class, aria_label). This captures
    the vast majority of repeated icon renders (e.g., navigation icons
    appear on every page with the same parameters).

    Args:
        name: Icon name (already mapped through ICON_MAP)
        size: Icon size in pixels
        css_class: Additional CSS classes
        aria_label: Accessibility label

    Returns:
        Rendered SVG HTML string, or empty string if icon not found
    """
    svg_content = _preloaded_icons.get(name)
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

    # Remove existing width/height/class attributes from SVG
    svg_modified = _RE_WIDTH_HEIGHT.sub("", svg_content)
    svg_modified = _RE_CLASS.sub("", svg_modified)

    # Add our attributes to <svg> tag
    svg_modified = _RE_SVG_TAG.sub(
        f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
        svg_modified,
        count=1,
    )

    return svg_modified


def icon(name: str, size: int = 24, css_class: str = "", aria_label: str = "") -> Markup:
    """
    Render an SVG icon for use in templates.

    Uses pre-loaded icons and LRU caching for optimal performance.
    Icons are loaded once at startup and rendered output is cached
    by (name, size, css_class, aria_label) to minimize repeated work.

    Icon name mapping priority:
    1. theme.yaml aliases (if theme config available)
    2. ICON_MAP (fallback for backwards compatibility)

    Args:
        name: Icon name (e.g., "search", "menu", "close", "arrow-up")
        size: Icon size in pixels (default: 24)
        css_class: Additional CSS classes
        aria_label: Accessibility label (if empty, uses aria-hidden)

    Returns:
        Markup object containing inline SVG HTML, or empty Markup if icon not found

    Example:
        {{ icon("search", size=20) }}
        {{ icon("menu", size=24, css_class="nav-icon") }}
        {{ icon("arrow-up", size=18, aria_label="Back to top") }}
    """
    if not name:
        return Markup("")

    # Try theme config aliases first (if available)
    mapped_name = name
    if _site_instance:
        try:
            theme_config = _site_instance.theme_config
            if theme_config.config is not None:
                icon_aliases = theme_config.config.get("icons", {}).get("aliases", {})
                if icon_aliases and name in icon_aliases:
                    mapped_name = icon_aliases[name]
                else:
                    # Fall back to ICON_MAP
                    mapped_name = ICON_MAP.get(name, name)
            else:
                # Fall back to ICON_MAP
                mapped_name = ICON_MAP.get(name, name)
        except Exception as e:
            # Graceful degradation: fall back to ICON_MAP
            logger.debug(
                "icon_mapping_failed",
                icon_name=name,
                error=str(e),
                error_type=type(e).__name__,
                action="falling_back_to_icon_map",
            )
            mapped_name = ICON_MAP.get(name, name)
    else:
        # No site instance available, use ICON_MAP
        mapped_name = ICON_MAP.get(name, name)

    # Try the mapped name first (uses LRU cache)
    svg_html = _render_icon_cached(mapped_name, size, css_class, aria_label)

    # If mapped name didn't work and it's different from original, try the original
    if not svg_html and mapped_name != name:
        svg_html = _render_icon_cached(name, size, css_class, aria_label)

    # Return as Markup to prevent Jinja2 auto-escaping
    return Markup(svg_html)


def register(env: Environment, site: Site) -> None:
    """
    Register icon template functions and pre-load all icons.

    Pre-loads all SVG icons into memory at registration time for
    optimal render performance. Icons are typically ~50KB total.

    Args:
        env: Jinja2 environment
        site: Site instance (stored for theme config access)
    """
    global _site_instance
    _site_instance = site

    # Pre-load all icons at startup
    _preload_all_icons()

    env.globals["icon"] = icon
    env.globals["render_icon"] = icon  # Alias


def get_icon_cache_stats() -> dict[str, int]:
    """
    Get icon cache statistics for debugging/profiling.

    Returns:
        Dictionary with cache hit/miss information
    """
    cache_info = _render_icon_cached.cache_info()
    return {
        "preloaded_icons": len(_preloaded_icons),
        "cache_hits": cache_info.hits,
        "cache_misses": cache_info.misses,
        "cache_size": cache_info.currsize,
        "cache_maxsize": cache_info.maxsize or 0,
    }


def clear_icon_cache() -> None:
    """
    Clear the icon render cache.

    Useful for testing or when icons are modified during development.
    """
    _render_icon_cached.cache_clear()
