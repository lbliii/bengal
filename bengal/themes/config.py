"""
Theme configuration models and YAML loader.

Provides dataclass models for theme configuration, loaded from theme.yaml files
in theme directories. Supports nested configuration for features, appearance,
and icons with validation.

Models:
    FeatureFlags: Category-organized boolean feature toggles
    AppearanceConfig: Theme mode and palette selection
    IconConfig: Icon library and semantic aliases
    ThemeConfig: Root configuration combining all settings

Architecture:
    Configuration models are passive dataclasses with factory methods for
    loading from dictionaries or YAML files. Validation occurs in __post_init__
    for immediate feedback on invalid values.

Example:
    >>> config = ThemeConfig.load(Path("themes/default"))
    >>> config.name
    'default'
    >>> config.features.has_feature("navigation.toc")
    True
    >>> config.appearance.default_mode
    'system'

Related:
    bengal/themes/tokens.py: Design tokens used with theme config
    bengal/themes/default/theme.yaml: Example theme configuration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bengal.errors import BengalConfigError
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureFlags:
    """
    Feature flags organized by category.

    Features are grouped into categories (navigation, content, search, etc.)
    with boolean toggles for each feature. Use dotted notation to query
    features (e.g., "navigation.toc").

    Attributes:
        navigation: Navigation features (toc, breadcrumbs, prev_next, etc.)
        content: Content features (code_copy, syntax_highlight, etc.)
        search: Search features (enabled, keyboard_shortcuts, etc.)
        header: Header features (logo, theme_toggle, etc.)
        footer: Footer features (copyright, social_links, etc.)
        accessibility: Accessibility features (skip_links, focus_visible, etc.)

    Example:
        >>> flags = FeatureFlags(navigation={"toc": True, "breadcrumbs": False})
        >>> flags.has_feature("navigation.toc")
        True
        >>> flags.get_enabled_features()
        ['navigation.toc']
    """

    navigation: dict[str, bool] = field(default_factory=dict)
    content: dict[str, bool] = field(default_factory=dict)
    search: dict[str, bool] = field(default_factory=dict)
    header: dict[str, bool] = field(default_factory=dict)
    footer: dict[str, bool] = field(default_factory=dict)
    accessibility: dict[str, bool] = field(default_factory=dict)

    def get_enabled_features(self) -> list[str]:
        """
        Get list of all enabled feature keys in dotted notation.

        Returns:
            List of feature keys like ["navigation.toc", "content.code.copy"]
        """
        enabled: list[str] = []
        for category, features in [
            ("navigation", self.navigation),
            ("content", self.content),
            ("search", self.search),
            ("header", self.header),
            ("footer", self.footer),
            ("accessibility", self.accessibility),
        ]:
            for feature_name, enabled_flag in features.items():
                if enabled_flag:
                    enabled.append(f"{category}.{feature_name}")
        return enabled

    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature: Feature key in dotted notation (e.g., "navigation.toc")

        Returns:
            True if feature is enabled
        """
        if "." not in feature:
            return False
        category, feature_name = feature.split(".", 1)
        category_dict = getattr(self, category, {})
        if isinstance(category_dict, dict):
            return bool(category_dict.get(feature_name, False))
        return False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureFlags:
        """
        Create FeatureFlags from dictionary.

        Args:
            data: Dictionary with feature flags organized by category

        Returns:
            FeatureFlags instance
        """
        return cls(
            navigation=data.get("navigation", {}),
            content=data.get("content", {}),
            search=data.get("search", {}),
            header=data.get("header", {}),
            footer=data.get("footer", {}),
            accessibility=data.get("accessibility", {}),
        )


@dataclass
class AppearanceConfig:
    """
    Appearance configuration for theme mode and color palette.

    Controls the default visual appearance including light/dark mode preference
    and optional color palette variant. Validates mode against allowed values.

    Attributes:
        default_mode: Theme mode preference ("light", "dark", or "system")
        default_palette: Optional palette variant name (e.g., "blue-bengal")

    Raises:
        BengalConfigError: If default_mode is not one of: light, dark, system
    """

    default_mode: str = "system"
    default_palette: str = ""

    def __post_init__(self) -> None:
        """Validate appearance configuration."""
        valid_modes = {"light", "dark", "system"}
        if self.default_mode not in valid_modes:
            raise BengalConfigError(
                f"Invalid default_mode '{self.default_mode}'. "
                f"Must be one of: {', '.join(valid_modes)}",
                suggestion=f"Set default_mode to one of: {', '.join(valid_modes)}",
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppearanceConfig:
        """
        Create AppearanceConfig from dictionary.

        Args:
            data: Dictionary with appearance settings

        Returns:
            AppearanceConfig instance
        """
        return cls(
            default_mode=data.get("default_mode", "system"),
            default_palette=data.get("default_palette", ""),
        )


@dataclass
class IconConfig:
    """
    Icon library configuration with semantic aliases.

    Controls which icon library is used (default: Phosphor) and provides
    semantic name mappings for consistent icon usage across the theme.

    Attributes:
        library: Icon library name (e.g., "phosphor", "heroicons")
        aliases: Semantic-to-icon name mappings (e.g., {"search": "magnifying-glass"})
        defaults: Default icons for common UI elements (e.g., {"external_link": "arrow-up-right"})

    Example:
        >>> icons = IconConfig(library="phosphor", aliases={"search": "magnifying-glass"})
        >>> icons.library
        'phosphor'
    """

    library: str = "phosphor"
    aliases: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IconConfig:
        """
        Create IconConfig from dictionary.

        Args:
            data: Dictionary with icon settings

        Returns:
            IconConfig instance
        """
        return cls(
            library=data.get("library", "phosphor"),
            aliases=data.get("aliases", {}),
            defaults=data.get("defaults", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert IconConfig to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "library": self.library,
            "aliases": self.aliases,
            "defaults": self.defaults,
        }


@dataclass
class ThemeConfig:
    """
    Complete theme configuration loaded from theme.yaml.

    Consolidates all theme settings into a single configuration object that
    can be loaded from YAML files and serialized back for export.

    Attributes:
        name: Theme identifier (e.g., "default", "docs-theme")
        version: Semantic version string (e.g., "1.0.0")
        parent: Optional parent theme name for inheritance
        features: Feature flags organized by category
        appearance: Theme mode and palette settings
        icons: Icon library and alias configuration

    Example:
        >>> config = ThemeConfig.load(Path("themes/default"))
        >>> config.name
        'default'
        >>> config.features.has_feature("navigation.toc")
        True

    See Also:
        FeatureFlags: Feature toggle configuration
        AppearanceConfig: Visual appearance settings
        IconConfig: Icon library settings
    """

    name: str = "default"
    version: str = "1.0.0"
    parent: str | None = None
    features: FeatureFlags = field(default_factory=FeatureFlags)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)
    icons: IconConfig = field(default_factory=IconConfig)

    @classmethod
    def load(cls, theme_path: Path) -> ThemeConfig:
        """
        Load theme configuration from theme.yaml file.

        Args:
            theme_path: Path to theme directory (will look for theme.yaml)

        Returns:
            ThemeConfig instance loaded from YAML

        Raises:
            FileNotFoundError: If theme.yaml doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If configuration is invalid
        """
        yaml_path = theme_path / "theme.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Theme config not found: {yaml_path}")

        try:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise BengalConfigError(
                f"Invalid YAML in {yaml_path}: {e}",
                file_path=yaml_path,
                suggestion="Check YAML syntax and indentation",
                original_error=e,
            ) from e

        # Extract top-level fields
        name = data.get("name", "default")
        version = data.get("version", "1.0.0")
        parent = data.get("parent")

        # Load nested configurations
        features = FeatureFlags.from_dict(data.get("features", {}))
        appearance = AppearanceConfig.from_dict(data.get("appearance", {}))
        icons = IconConfig.from_dict(data.get("icons", {}))

        return cls(
            name=name,
            version=version,
            parent=parent,
            features=features,
            appearance=appearance,
            icons=icons,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert ThemeConfig to dictionary for serialization.

        Returns:
            Dictionary representation suitable for YAML export
        """
        return {
            "name": self.name,
            "version": self.version,
            "parent": self.parent,
            "features": {
                "navigation": self.features.navigation,
                "content": self.features.content,
                "search": self.features.search,
                "header": self.features.header,
                "footer": self.features.footer,
                "accessibility": self.features.accessibility,
            },
            "appearance": {
                "default_mode": self.appearance.default_mode,
                "default_palette": self.appearance.default_palette,
            },
            "icons": {
                "library": self.icons.library,
                "aliases": self.icons.aliases,
                "defaults": self.icons.defaults,
            },
        }
