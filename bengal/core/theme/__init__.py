"""
Theme system for Bengal SSG.

Provides theme configuration, discovery, and inheritance chain resolution.
Themes define templates, assets, and visual styling for sites.

Public API:
    Theme: Configuration object accessible as site.theme in templates
    ThemePackage: Installed theme metadata and resource access
    get_theme_package: Get ThemePackage by name
    get_installed_themes: List all available themes
    clear_theme_cache: Clear theme discovery cache
    resolve_theme_chain: Build inheritance chain for template lookup
    iter_theme_asset_dirs: Iterate asset directories in theme chain

Package Structure:
    config.py: Theme dataclass with feature flags and appearance
    registry.py: Theme discovery via entry points and filesystem
    resolution.py: Theme inheritance chain resolution

Architecture:
    Theme Configuration: Theme class holds settings (features, appearance).
        Accessible in templates as site.theme.

    Theme Discovery: ThemePackage represents an installed theme. Found via
        entry points (bengal.themes) or filesystem (themes/ directory).

    Theme Resolution: Themes can extend other themes. resolve_theme_chain()
        builds the inheritance chain for template/asset lookup order.

Example:
    from bengal.core.theme import Theme, resolve_theme_chain

    theme = Theme.from_config(site_config, root_path=site.root_path)
    if theme.has_feature('navigation.toc'):
        enable_toc()

    chain = resolve_theme_chain('docs', site.root_path)
    # Returns: ['docs', 'default'] if docs extends default

Related Packages:
    bengal.rendering.template_engine: Uses theme chains for template loading
    bengal.themes: Bundled themes (default, docs)
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
    _read_theme_extends,
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
    "_read_theme_extends",  # Internal helper (used by CLI)
]
