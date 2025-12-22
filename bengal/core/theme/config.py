"""
Theme configuration object for Bengal SSG.

Provides theme-related configuration accessible in templates as `site.theme`.
Includes feature flags system for declarative theme customization.

Public API:
    Theme: Theme configuration dataclass with feature flags and appearance

Key Concepts:
    Feature Flags: Declarative toggles for theme behavior. Users enable
        features via config rather than editing templates:

        [theme]
        features = ["navigation.toc", "content.code.copy"]

    Appearance Modes: Control default color scheme:
        - "light": Light mode by default
        - "dark": Dark mode by default
        - "system": Follow user's system preference

    Color Palettes: Named color schemes for theming. The default_palette
        field specifies which palette to use initially.

Usage:
    # In templates:
    {% if site.theme.has_feature('navigation.toc') %}
      {{ render_toc(page) }}
    {% endif %}

    # Programmatic access:
    theme = Theme.from_config(site_config, root_path=site.root_path)
    if theme.has_feature("content.code.copy"):
        enable_code_copy()

Related Packages:
    bengal.core.theme.registry: Installed theme discovery via entry points
    bengal.core.theme.resolution: Theme inheritance chain resolution
    bengal.themes.config: ThemeConfig for theme.yaml loading
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.errors import BengalConfigError


@dataclass
class Theme:
    """
    Theme configuration object.

    Available in templates as `site.theme` for theme developers to access
    theme-related settings.

    Attributes:
        name: Theme name (e.g., "default", "my-custom-theme")
        default_appearance: Default appearance mode ("light", "dark", "system")
        default_palette: Default color palette key (empty string for default)
        features: List of enabled feature flags (e.g., ["navigation.toc", "content.code.copy"])
        config: Additional theme-specific configuration from [theme] section

    Feature Flags:
        Features are declarative toggles for theme behavior. Users enable/disable
        features via config rather than editing templates.

        Example:
            [theme]
            features = ["navigation.toc", "content.code.copy"]

        Templates check features via:
            {% if 'navigation.toc' in site.theme_config.features %}
    """

    name: str = "default"
    default_appearance: str = "system"
    default_palette: str = ""
    features: list[str] = field(default_factory=list)
    config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate theme configuration."""
        # Validate appearance
        valid_appearances = {"light", "dark", "system"}
        if self.default_appearance not in valid_appearances:
            raise BengalConfigError(
                f"Invalid default_appearance '{self.default_appearance}'. "
                f"Must be one of: {', '.join(valid_appearances)}",
                suggestion=f"Set default_appearance to one of: {', '.join(valid_appearances)}",
            )

        # Ensure config is a dict
        if self.config is None:
            self.config = {}

        # Normalize features to list
        if self.features is None:
            self.features = []

    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature: Feature key (e.g., "navigation.toc", "content.code.copy")

        Returns:
            True if the feature is in the enabled features list

        Example:
            >>> theme = Theme(features=["navigation.toc"])
            >>> theme.has_feature("navigation.toc")
            True
            >>> theme.has_feature("navigation.tabs")
            False
        """
        return feature in self.features

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        root_path: Path | None = None,
        diagnostics_site: Any | None = None,
    ) -> Theme:
        """
        Create Theme object from configuration dictionary.

        Attempts to load theme.yaml first, then falls back to config dict.
        This allows themes to define their configuration in theme.yaml while
        still supporting site-level overrides in bengal.toml.

        Args:
            config: Full site configuration dictionary
            root_path: Optional root path for theme discovery

        Returns:
            Theme object with values from config or theme.yaml
        """
        # Get [theme] section
        theme_section = config.get("theme", {})

        # Handle config where theme was a string
        if isinstance(theme_section, str):
            theme_name = theme_section
        else:
            # Modern config: [theme] is a dict
            if not isinstance(theme_section, dict):
                theme_section = {}
            theme_name = theme_section.get("name", "default")

        # Try loading theme.yaml first (if root_path provided)
        theme_config_obj = None
        if root_path:
            try:
                from bengal.themes.config import ThemeConfig

                # Try site themes first, then bundled themes
                site_theme_path = root_path / "themes" / theme_name
                bundled_theme_path = Path(__file__).parent.parent.parent / "themes" / theme_name

                theme_path = None
                if site_theme_path.exists():
                    theme_path = site_theme_path
                elif bundled_theme_path.exists():
                    theme_path = bundled_theme_path

                if theme_path:
                    try:
                        theme_config_obj = ThemeConfig.load(theme_path)
                        emit_diagnostic(
                            diagnostics_site,
                            "debug",
                            "theme_yaml_loaded",
                            theme=theme_name,
                            path=str(theme_path),
                        )
                    except FileNotFoundError:
                        # theme.yaml doesn't exist, fall back to config
                        pass
                    except Exception as e:
                        emit_diagnostic(
                            diagnostics_site,
                            "warning",
                            "theme_yaml_load_failed",
                            theme=theme_name,
                            error=str(e),
                        )
            except ImportError:
                # ThemeConfig not available (shouldn't happen, but graceful degradation)
                pass

        # If theme.yaml loaded successfully, use it
        if theme_config_obj:
            # Merge site config overrides (site config takes precedence)
            features = theme_config_obj.features.get_enabled_features()
            if isinstance(theme_section, dict):
                # Site config can override features
                site_features = theme_section.get("features", [])
                if site_features:
                    features = site_features

            return cls(
                name=theme_config_obj.name,
                default_appearance=theme_config_obj.appearance.default_mode,
                default_palette=theme_config_obj.appearance.default_palette,
                features=features,
                config={
                    "version": theme_config_obj.version,
                    "parent": theme_config_obj.parent,
                    "icons": theme_config_obj.icons.to_dict(),
                },
            )

        # Fall back to config dict (when theme.yaml doesn't exist)
        if isinstance(theme_section, str):
            return cls(
                name=theme_section,
                default_appearance="system",
                default_palette="",
                features=[],
                config={},
            )

        default_appearance = theme_section.get("default_appearance", "system")
        default_palette = theme_section.get("default_palette", "")
        features = theme_section.get("features", [])

        # Ensure features is a list
        if not isinstance(features, list):
            features = []

        # Pass through any additional theme config (excluding known keys)
        theme_config = {
            k: v
            for k, v in theme_section.items()
            if k not in ("name", "default_appearance", "default_palette", "features")
        }

        return cls(
            name=theme_name,
            default_appearance=default_appearance,
            default_palette=default_palette,
            features=features,
            config=theme_config,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert theme to dictionary for template access.

        Returns:
            Dictionary representation of theme
        """
        return {
            "name": self.name,
            "default_appearance": self.default_appearance,
            "default_palette": self.default_palette,
            "features": self.features,
            "config": self.config or {},
        }
