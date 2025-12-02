"""
Theme configuration object for Bengal SSG.

Provides theme-related configuration accessible in templates as `site.theme`.
Includes feature flags system for declarative theme customization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

    def __post_init__(self):
        """Validate theme configuration."""
        # Validate appearance
        valid_appearances = {"light", "dark", "system"}
        if self.default_appearance not in valid_appearances:
            raise ValueError(
                f"Invalid default_appearance '{self.default_appearance}'. "
                f"Must be one of: {', '.join(valid_appearances)}"
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
    def from_config(cls, config: dict[str, Any]) -> Theme:
        """
        Create Theme object from configuration dictionary.

        Args:
            config: Full site configuration dictionary

        Returns:
            Theme object with values from config
        """
        # Get [theme] section
        theme_section = config.get("theme", {})

        # Handle legacy config where theme was a string
        if isinstance(theme_section, str):
            return cls(
                name=theme_section,
                default_appearance="system",
                default_palette="",
                features=[],
                config={},
            )

        # Modern config: [theme] is a dict with name, appearance, palette, features
        if not isinstance(theme_section, dict):
            theme_section = {}

        theme_name = theme_section.get("name", "default")
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
