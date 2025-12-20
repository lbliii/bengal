"""
Theme system for Bengal SSG.

Provides theme configuration, discovery, and inheritance chain resolution.

Components:
    - Theme: Configuration object accessible as site.theme in templates
    - ThemePackage: Installed theme metadata and resource access
    - Theme resolution: Inheritance chain building for template/asset discovery

Architecture:
    Theme configuration (Theme class) is a core model that holds theme settings.
    Theme discovery (ThemePackage, registry) finds installed themes via entry points.
    Theme resolution builds inheritance chains for template lookup.

Related:
    - bengal/rendering/template_engine/: Uses theme chains for template loading
    - bengal/themes/: Bundled themes
    - utils/theme_registry.py: Original location (deprecated)
    - utils/theme_resolution.py: Original location (deprecated)
"""

from __future__ import annotations

from bengal.core.theme.config import Theme
from bengal.core.theme.registry import (
    ThemePackage,
    clear_theme_cache,
    get_installed_themes,
    get_theme_package,
)
from bengal.core.theme.resolution import (
    iter_theme_asset_dirs,
    resolve_theme_chain,
)

__all__ = [
    # Theme configuration
    "Theme",
    # Theme discovery
    "ThemePackage",
    "get_installed_themes",
    "get_theme_package",
    "clear_theme_cache",
    # Theme resolution
    "resolve_theme_chain",
    "iter_theme_asset_dirs",
]
