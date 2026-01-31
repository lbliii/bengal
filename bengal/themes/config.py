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

from bengal.errors import BengalConfigError, ErrorCode, record_error
from bengal.themes.tokens import PALETTE_VARIANTS
from bengal.themes.utils import validate_enum_field
from bengal.utils.observability.logger import get_logger

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
    and optional color palette variant. Validates mode and palette against allowed values.

    Attributes:
        default_mode: Theme mode preference ("light", "dark", or "system")
        default_palette: Optional palette variant name (e.g., "blue-bengal", "snow-lynx").
            Must be one of the valid palette names from PALETTE_VARIANTS or empty string.

    Raises:
        BengalConfigError: If default_mode is not one of: light, dark, system
        BengalConfigError: If default_palette is not a valid palette variant name

    """

    default_mode: str = "system"
    default_palette: str = ""

    def __post_init__(self) -> None:
        """Validate appearance configuration."""
        # Validate mode
        validate_enum_field("default_mode", self.default_mode, {"light", "dark", "system"})

        # Validate palette - derive valid names from PALETTE_VARIANTS (single source of truth)
        # Empty string is also valid (means no palette override)
        valid_palettes = {"", *PALETTE_VARIANTS.keys()}
        validate_enum_field("default_palette", self.default_palette, valid_palettes)

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
        extend_defaults: Whether to fall through to Bengal's default icons (Phosphor)
            when an icon is not found in the theme. Defaults to True.

    Example:
            >>> icons = IconConfig(library="phosphor", aliases={"search": "magnifying-glass"})
            >>> icons.library
            'phosphor'

            >>> # Disable fallback to default icons
            >>> icons = IconConfig(extend_defaults=False)

    """

    library: str = "phosphor"
    aliases: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    extend_defaults: bool = True

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
            extend_defaults=data.get("extend_defaults", True),
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
            "extend_defaults": self.extend_defaults,
        }


@dataclass
class HeaderConfig:
    """
    Header layout and behavior configuration.

    Controls the site header appearance including navigation position,
    sticky behavior, and auto-hide functionality.

    Attributes:
        nav_position: Navigation link alignment ("left" or "center").
            - "left": Nav links appear after the logo (default)
            - "center": Nav links are centered in the header
        sticky: Whether the header stays fixed at the top on scroll.
            Defaults to True.
        autohide: Whether the header hides on scroll down and reappears
            on scroll up. Only applies when sticky is True.

    Example:
        >>> header = HeaderConfig(nav_position="center", sticky=True)
        >>> header.nav_position
        'center'
    """

    nav_position: str = "left"
    sticky: bool = True
    autohide: bool = False

    def __post_init__(self) -> None:
        """Validate header configuration."""
        validate_enum_field("nav_position", self.nav_position, {"left", "center"})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HeaderConfig:
        """
        Create HeaderConfig from dictionary.

        Args:
            data: Dictionary with header settings

        Returns:
            HeaderConfig instance
        """
        return cls(
            nav_position=data.get("nav_position", "left"),
            sticky=data.get("sticky", True),
            autohide=data.get("autohide", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert HeaderConfig to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "nav_position": self.nav_position,
            "sticky": self.sticky,
            "autohide": self.autohide,
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
    header: HeaderConfig = field(default_factory=HeaderConfig)

    @classmethod
    def load(cls, theme_path: Path) -> ThemeConfig:
        """
        Load theme configuration from theme.yaml file.

        Args:
            theme_path: Path to theme directory (will look for theme.yaml)

        Returns:
            ThemeConfig instance loaded from YAML

        Raises:
            BengalConfigError: If theme.yaml doesn't exist (code=C005) or
                if YAML is invalid (code=C001)
        """
        yaml_path = theme_path / "theme.yaml"
        if not yaml_path.exists():
            error = BengalConfigError(
                f"Theme config not found: {yaml_path}",
                code=ErrorCode.C005,
                file_path=yaml_path,
                suggestion="Ensure theme directory contains theme.yaml. "
                "Run 'bengal theme new <name>' to create a new theme.",
            )
            record_error(error, file_path=str(yaml_path))
            raise error

        try:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            error = BengalConfigError(
                f"Invalid YAML in {yaml_path}: {e}",
                code=ErrorCode.C001,
                file_path=yaml_path,
                suggestion="Check YAML syntax and indentation",
                original_error=e,
            )
            record_error(error, file_path=str(yaml_path))
            raise error from e

        # Extract top-level fields
        name = data.get("name", "default")
        version = data.get("version", "1.0.0")
        parent = data.get("parent")

        # Load nested configurations
        features = FeatureFlags.from_dict(data.get("features", {}))
        appearance = AppearanceConfig.from_dict(data.get("appearance", {}))
        icons = IconConfig.from_dict(data.get("icons", {}))

        # Header config can come from top-level 'header' or from 'features.header'
        # Top-level 'header' takes precedence for layout settings
        header_data = data.get("header", {})
        features_header = data.get("features", {}).get("header", {})

        # Merge: features.header provides defaults, top-level header overrides
        merged_header = {**features_header, **header_data}

        # Warn about unknown keys in header config - these might be misplaced
        # feature flags that won't take effect as layout settings
        valid_header_keys = {"nav_position", "sticky", "autohide"}
        unknown_keys = set(merged_header.keys()) - valid_header_keys
        if unknown_keys:
            logger.warning(
                "theme_config_unknown_header_keys",
                unknown_keys=sorted(unknown_keys),
                valid_keys=sorted(valid_header_keys),
                hint="These may be feature flags that belong in 'features.header' "
                "rather than layout settings in 'header'",
            )

        header = HeaderConfig.from_dict(merged_header)

        return cls(
            name=name,
            version=version,
            parent=parent,
            features=features,
            appearance=appearance,
            icons=icons,
            header=header,
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
            "header": self.header.to_dict(),
        }
