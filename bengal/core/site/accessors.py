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
    from bengal.services.config import ConfigService


class SiteAccessorsMixin:
    """
    Mixin providing config accessor properties for Site.

    Expects from host class:
        config_service: ConfigService (property)
        _theme_obj: Theme | None
        _description_override: str | None
    """

    config_service: ConfigService
    _theme_obj: Theme | None
    _description_override: str | None

    @property
    def paths(self) -> BengalPaths:
        """Access to .bengal directory paths.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.paths

    @property
    def title(self) -> str | None:
        """Get site title from configuration.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.title

    @property
    def description(self) -> str | None:
        """Get site description, respecting runtime overrides.

        Cost: O(1) — attribute read, optional override check.
        """
        if self._description_override is not None:
            return self._description_override
        return self.config_service.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Allow runtime override of site description for generated outputs."""
        self._description_override = value

    @property
    def baseurl(self) -> str | None:
        """Get site baseurl from configuration.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.baseurl

    @property
    def content_dir(self) -> Path:
        """Get path to the content directory.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.content_dir

    @property
    def author(self) -> str | None:
        """Get site author from configuration.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.author

    @property
    def favicon(self) -> str | None:
        """Get favicon path from site config.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.favicon

    @property
    def logo_image(self) -> str | None:
        """Get logo image path from site config.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.logo_image

    @property
    def logo_text(self) -> str | None:
        """Get logo text from site config.

        Cost: O(1) — direct attribute read.
        """
        return self.config_service.logo_text

    @property
    def params(self) -> dict[str, Any]:
        """Site-level custom parameters from [params] config section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.params

    @property
    def logo(self) -> str:
        """Logo URL from config (checks multiple locations).

        Cost: O(1) — config lookups, returns cached value.
        """
        return self.config_service.logo

    @property
    def config_hash(self) -> str:
        """Get deterministic hash of the resolved configuration.

        Cost: O(1) cached — computed once at config load, then cached.
        """
        return self.config_service.config_hash

    @property
    def theme_config(self) -> Theme:
        """Get theme configuration object.

        Cost: O(1) — attribute read, optional override check.
        """
        if self._theme_obj is not None:
            return self._theme_obj
        return self.config_service.theme_config

    @property
    def assets_config(self) -> dict[str, Any]:
        """Get the assets configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.assets_config

    @property
    def build_config(self) -> dict[str, Any]:
        """Get the build configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.build_config

    @property
    def i18n_config(self) -> dict[str, Any]:
        """Get the internationalization configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.i18n_config

    @property
    def menu_config(self) -> dict[str, Any]:
        """Get the menu configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.menu_config

    @property
    def content_config(self) -> dict[str, Any]:
        """Get the content configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.content_config

    @property
    def output_config(self) -> dict[str, Any]:
        """Get the output configuration section.

        Cost: O(1) — returns cached dict reference.
        """
        return self.config_service.output_config
