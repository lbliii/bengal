"""
Unified icon resolution for all Bengal icon consumers.

This module provides centralized icon loading with theme-aware resolution.
All icon loading (template functions, plugins, directives) should use this module.

Resolution Order (first match wins):
    1. site/themes/{theme}/assets/icons/{name}.svg   ← Site overrides (highest)
    2. bengal/themes/{theme}/assets/icons/{name}.svg ← Theme's custom icons
    3. bengal/themes/{parent}/assets/icons/{name}.svg ← Parent theme (if extended)
    4. bengal/themes/default/assets/icons/{name}.svg ← Bengal defaults (lowest)

Usage:
    >>> from bengal.icons import resolver
    >>> resolver.initialize(site)
    >>> svg_content = resolver.load_icon("warning")
    >>> paths = resolver.get_search_paths()  # For error messages
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

__all__ = [
    "initialize",
    "load_icon",
    "get_search_paths",
    "get_available_icons",
    "clear_cache",
]

# Module-level state (set during Site initialization)
_search_paths: list[Path] = []
_icon_cache: dict[str, str] = {}
_not_found_cache: set[str] = set()  # Avoid repeated disk checks
_initialized: bool = False


def initialize(site: Site, preload: bool = False) -> None:
    """
    Initialize icon resolver with Site context.

    Called once during Site initialization, before any rendering.
    Sets up search paths based on theme configuration.

    Args:
        site: Site instance for theme resolution
        preload: If True, eagerly load all icons (production mode)
    """
    global _search_paths, _initialized
    _search_paths = _get_icon_search_paths(site)
    _icon_cache.clear()
    _not_found_cache.clear()
    _initialized = True

    if preload:
        _preload_all_icons()


def _get_icon_search_paths(site: Site) -> list[Path]:
    """
    Get ordered list of icon directories to search.

    Returns directories from highest to lowest priority:
    1. Site theme icons (site/themes/{theme}/assets/icons)
    2. Theme icons with inheritance chain
    3. Default theme icons (if extend_defaults=True)
    """
    paths: list[Path] = []

    # Get theme asset chain (handles inheritance)
    # Returns paths from parent → child, we want child → parent for lookup
    for assets_dir in reversed(site._get_theme_assets_chain()):
        icons_dir = assets_dir / "icons"
        if icons_dir.exists() and icons_dir not in paths:
            paths.append(icons_dir)

    # Add default theme if extending (default behavior)
    extend_defaults = True
    if hasattr(site, "theme_config") and site.theme_config is not None:
        icons_config = getattr(site.theme_config, "icons", None)
        if icons_config is not None:
            extend_defaults = getattr(icons_config, "extend_defaults", True)

    if extend_defaults:
        import bengal

        default_icons = (
            Path(bengal.__file__).parent / "themes" / "default" / "assets" / "icons"
        )
        if default_icons.exists() and default_icons not in paths:
            paths.append(default_icons)

    return paths


def _get_fallback_path() -> Path:
    """Get fallback icon path when resolver not initialized."""
    import bengal

    return Path(bengal.__file__).parent / "themes" / "default" / "assets" / "icons"


def load_icon(name: str) -> str | None:
    """
    Load icon from first matching path in search chain.

    Uses caching to avoid repeated disk I/O:
    - Found icons cached by content
    - Not-found icons cached to skip repeated searches

    Args:
        name: Icon name (without .svg extension)

    Returns:
        SVG content string, or None if not found
    """
    if name in _icon_cache:
        return _icon_cache[name]

    if name in _not_found_cache:
        return None

    # Use search paths if initialized, otherwise fallback to default
    search_paths = _search_paths if _initialized else [_get_fallback_path()]

    for icons_dir in search_paths:
        icon_path = icons_dir / f"{name}.svg"
        if icon_path.exists():
            try:
                content = icon_path.read_text(encoding="utf-8")
                _icon_cache[name] = content
                return content
            except OSError:
                continue

    _not_found_cache.add(name)
    return None


def get_search_paths() -> list[Path]:
    """
    Get current search paths (for error messages).

    Returns:
        Copy of the current search paths list
    """
    if _initialized:
        return _search_paths.copy()
    return [_get_fallback_path()]


def get_available_icons() -> list[str]:
    """
    Get list of all available icon names across search paths.

    Returns icon names in priority order (higher priority first).
    Duplicates are included only once (first occurrence wins).

    Returns:
        List of icon names (without .svg extension)
    """
    seen: set[str] = set()
    icons: list[str] = []

    search_paths = _search_paths if _initialized else [_get_fallback_path()]

    for icons_dir in search_paths:
        if icons_dir.exists():
            for icon_path in sorted(icons_dir.glob("*.svg")):
                name = icon_path.stem
                if name not in seen:
                    icons.append(name)
                    seen.add(name)

    return icons


def clear_cache() -> None:
    """
    Clear icon cache (for dev server hot reload).

    Call this when theme assets change to reload modified icons.
    """
    _icon_cache.clear()
    _not_found_cache.clear()


def _preload_all_icons() -> None:
    """
    Preload all icons from search paths (production optimization).

    Scans all icon directories and loads SVG content into cache.
    First match wins for duplicate icon names.
    """
    seen: set[str] = set()
    for icons_dir in _search_paths:
        if not icons_dir.exists():
            continue
        for icon_path in icons_dir.glob("*.svg"):
            name = icon_path.stem
            if name not in seen:  # First match wins
                try:
                    _icon_cache[name] = icon_path.read_text(encoding="utf-8")
                    seen.add(name)
                except OSError:
                    pass


def is_initialized() -> bool:
    """Check if resolver has been initialized with a Site."""
    return _initialized

