"""
Theme configuration models and YAML loader.

Provides ThemeConfig dataclass with nested configuration models for features,
appearance, and icons. Supports loading from theme.yaml files with validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bengal.utils.exceptions import BengalConfigError
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureFlags:
    """
    Feature flags configuration.

    Features are organized by category (navigation, content, etc.) and can be
    enabled/disabled individually. Each feature can have a description for
    documentation purposes.
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
    Appearance configuration (theme mode and palette).

    Controls default appearance mode (light/dark/system) and color palette.
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
    Icon configuration (library and aliases).

    Controls which icon library is used and provides semantic name aliases
    for icon names (e.g., "search" -> "magnifying-glass").
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

    Consolidates all theme settings (features, appearance, icons) into a
    single configuration object that can be loaded from YAML.
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
