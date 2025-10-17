"""
Theme configuration object for Bengal SSG.

Provides theme-related configuration accessible in templates as `site.theme`.
"""

from dataclasses import dataclass
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
        config: Additional theme-specific configuration from [theme] section
    """

    name: str = "default"
    default_appearance: str = "system"
    default_palette: str = ""
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

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Theme":
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
                config={},
            )

        # Modern config: [theme] is a dict with name, appearance, palette
        if not isinstance(theme_section, dict):
            theme_section = {}

        theme_name = theme_section.get("name", "default")
        default_appearance = theme_section.get("default_appearance", "system")
        default_palette = theme_section.get("default_palette", "")

        # Pass through any additional theme config (excluding known keys)
        theme_config = {
            k: v
            for k, v in theme_section.items()
            if k not in ("name", "default_appearance", "default_palette")
        }

        return cls(
            name=theme_name,
            default_appearance=default_appearance,
            default_palette=default_palette,
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
            "config": self.config or {},
        }
