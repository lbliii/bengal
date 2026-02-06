"""
Template functions for rendering SVG icons.

Provides optimized icon rendering functions for use in Jinja2 templates.
Icons are loaded via the theme-aware resolver and rendered output is cached
by (name, size, css_class, aria_label) to minimize per-render overhead.

Performance:
- Icons loaded via bengal.icons.resolver (theme-aware, cached)
- Rendered SVG cached by parameters (typical hit rate: >95%)
- Regex processing only on cache miss
- Zero file I/O during template rendering (after first load)

"""

from __future__ import annotations

import re
import threading
from typing import TYPE_CHECKING

from kida import Markup

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment

from bengal.icons.svg import ICON_MAP
from bengal.errors import ErrorCode
from bengal.icons import resolver as icon_resolver
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.lru_cache import LRUCache

logger = get_logger(__name__)

# Track warned icons to avoid duplicate warnings (reset per build)
# Thread-safe: protected by _warned_lock for concurrent access
_warned_lock = threading.Lock()
_warned_icons: set[str] = set()

# Site instance for theme config access (set during registration)
# Thread-safe: protected by _site_lock for concurrent access
_site_lock = threading.Lock()
_site_instance: SiteLike | None = None


def _get_mapped_icon_name(name: str) -> str:
    """
    Get mapped icon name from theme config or ICON_MAP.

    Thread-safe: All site access happens under lock to prevent TOCTOU race.
    Copies needed values while holding lock, then releases before return.

    Args:
        name: Original icon name

    Returns:
        Mapped icon name (may be same as input if no mapping found)
    """
    # Thread-safe: read _site_instance and extract needed config under lock
    with _site_lock:
        site = _site_instance
        if site is None:
            # No site instance, use ICON_MAP
            return ICON_MAP.get(name, name)

        # Extract icon aliases while holding lock
        try:
            theme_config = site.theme_config
            if theme_config.config is not None:
                icon_aliases = theme_config.config.get("icons", {}).get("aliases", {})
                if icon_aliases and name in icon_aliases:
                    return icon_aliases[name]
        except Exception as e:
            # Graceful degradation: fall back to ICON_MAP
            logger.debug(
                "icon_mapping_failed",
                icon_name=name,
                error=str(e),
                error_type=type(e).__name__,
                action="falling_back_to_icon_map",
            )

    # Fall back to ICON_MAP (outside lock, ICON_MAP is module-level constant)
    return ICON_MAP.get(name, name)


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

# Thread-safe LRU cache for icon rendering (replaces @lru_cache for free-threading)
_icon_render_cache: LRUCache[tuple[str, int, str, str], str] = LRUCache(
    maxsize=512, name="icon_render"
)


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

    Thread-safe: Uses LRUCache with RLock for safe concurrent access
    under free-threading (PEP 703).

    Args:
        name: Icon name (already mapped through ICON_MAP)
        size: Icon size in pixels
        css_class: Additional CSS classes
        aria_label: Accessibility label

    Returns:
        Rendered SVG HTML string, or empty string if icon not found

    """
    key = (name, size, css_class, aria_label)

    def _render_impl() -> str:
        # Load icon via theme-aware resolver
        svg_content = icon_resolver.load_icon(name)
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

    return _icon_render_cache.get_or_set(key, _render_impl)


def icon(name: str, size: int = 24, css_class: str = "", aria_label: str = "") -> Markup:
    """
    Render an SVG icon for use in templates.

    Uses theme-aware icon resolution and LRU caching for optimal performance.
    Icons are loaded from the theme asset chain (site > theme > parent > default).

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

    # Get icon aliases from theme config (if available)
    # Thread-safe: copy all needed values under lock to prevent TOCTOU race
    mapped_name = _get_mapped_icon_name(name)

    # Try the mapped name first (uses LRU cache)
    svg_html = _render_icon_cached(mapped_name, size, css_class, aria_label)

    # If mapped name didn't work and it's different from original, try the original
    if not svg_html and mapped_name != name:
        svg_html = _render_icon_cached(name, size, css_class, aria_label)

    # Warn if icon not found (deduplicated per icon name, thread-safe)
    if not svg_html:
        with _warned_lock:
            if name not in _warned_icons:
                _warned_icons.add(name)
                logger.warning(
                    "icon_not_found",
                    icon=name,
                    error_code=ErrorCode.T010.value,
                    searched=[str(p) for p in icon_resolver.get_search_paths()],
                    suggestion="Check icon name spelling. Run 'bengal icons list' to see available icons.",
                    hint=f"Add to theme: themes/{{theme}}/assets/icons/{name}.svg",
                )

    # Return as Markup to prevent Jinja2 auto-escaping
    return Markup(svg_html)


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """
    Register icon template functions.

    Icons are loaded on-demand via the theme-aware resolver, which is
    initialized during Site setup.

    Thread-safe: Site instance assignment protected by lock.

    Args:
        env: Jinja2 environment
        site: Site instance (stored for theme config access)

    """
    global _site_instance
    with _site_lock:
        _site_instance = site

    env.globals["icon"] = icon
    env.globals["render_icon"] = icon  # Alias


def get_icon_cache_stats() -> dict[str, int]:
    """
    Get icon cache statistics for debugging/profiling.

    Returns:
        Dictionary with cache hit/miss information

    """
    stats = _icon_render_cache.stats()
    return {
        "available_icons": len(icon_resolver.get_available_icons()),
        "cache_hits": stats["hits"],
        "cache_misses": stats["misses"],
        "cache_size": stats["size"],
        "cache_maxsize": stats["max_size"],
    }


def clear_icon_cache() -> None:
    """
    Clear the icon render cache and warned icons set.

    Useful for testing or when icons are modified during development.

    Thread-safe: Protected by lock.

    """
    _icon_render_cache.clear()
    with _warned_lock:
        _warned_icons.clear()
    icon_resolver.clear_cache()
