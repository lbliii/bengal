"""
Config accessor mixin for Site.

Thin property delegates to ConfigService for thread-safe config access.
All properties are read-only wrappers that forward to the immutable
ConfigService instance constructed during __post_init__.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.paths import BengalPaths
    from bengal.core.theme import Theme


class SiteAccessorsMixin:
    """
    Mixin providing config accessor properties for Site.

    Expects from host class:
        _config_service: ConfigService | None
        _theme_obj: Theme | None
        config_service: ConfigService (property)
    """

    _description_override: str | None

    @property
    def paths(self) -> BengalPaths:
        """Access to .bengal directory paths."""
        return self.config_service.paths  # type: ignore[attr-defined]

    @property
    def title(self) -> str | None:
        """Get site title from configuration."""
        return self.config_service.title  # type: ignore[attr-defined]

    @property
    def description(self) -> str | None:
        """Get site description, respecting runtime overrides."""
        if self._description_override is not None:
            return self._description_override
        return self.config_service.description  # type: ignore[attr-defined]

    @description.setter
    def description(self, value: str | None) -> None:
        """Allow runtime override of site description for generated outputs."""
        self._description_override = value

    @property
    def baseurl(self) -> str | None:
        """Get site baseurl from configuration."""
        return self.config_service.baseurl  # type: ignore[attr-defined]

    @property
    def content_dir(self) -> Path:
        """Get path to the content directory."""
        return self.config_service.content_dir  # type: ignore[attr-defined]

    @property
    def author(self) -> str | None:
        """Get site author from configuration."""
        return self.config_service.author  # type: ignore[attr-defined]

    @property
    def favicon(self) -> str | None:
        """Get favicon path from site config."""
        return self.config_service.favicon  # type: ignore[attr-defined]

    @property
    def logo_image(self) -> str | None:
        """Get logo image path from site config."""
        return self.config_service.logo_image  # type: ignore[attr-defined]

    @property
    def logo_text(self) -> str | None:
        """Get logo text from site config."""
        return self.config_service.logo_text  # type: ignore[attr-defined]

    @property
    def params(self) -> dict[str, Any]:
        """Site-level custom parameters from [params] config section."""
        return self.config_service.params  # type: ignore[attr-defined]

    @property
    def logo(self) -> str:
        """Logo URL from config (checks multiple locations)."""
        return self.config_service.logo  # type: ignore[attr-defined]

    @property
    def config_hash(self) -> str:
        """Get deterministic hash of the resolved configuration."""
        return self.config_service.config_hash  # type: ignore[attr-defined]

    @property
    def theme_config(self) -> Theme:
        """Get theme configuration object."""
        if self._theme_obj is not None:  # type: ignore[attr-defined]
            return self._theme_obj  # type: ignore[attr-defined]
        return self.config_service.theme_config  # type: ignore[attr-defined]

    @property
    def assets_config(self) -> dict[str, Any]:
        """Get the assets configuration section."""
        return self.config_service.assets_config  # type: ignore[attr-defined]

    @property
    def build_config(self) -> dict[str, Any]:
        """Get the build configuration section."""
        return self.config_service.build_config  # type: ignore[attr-defined]

    @property
    def i18n_config(self) -> dict[str, Any]:
        """Get the internationalization configuration section."""
        return self.config_service.i18n_config  # type: ignore[attr-defined]

    @property
    def menu_config(self) -> dict[str, Any]:
        """Get the menu configuration section."""
        return self.config_service.menu_config  # type: ignore[attr-defined]

    @property
    def content_config(self) -> dict[str, Any]:
        """Get the content configuration section."""
        return self.config_service.content_config  # type: ignore[attr-defined]

    @property
    def output_config(self) -> dict[str, Any]:
        """Get the output configuration section."""
        return self.config_service.output_config  # type: ignore[attr-defined]
