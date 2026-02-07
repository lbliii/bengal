"""
Site properties mixin — thin wrappers over ConfigService.

All config-derived properties now delegate to the immutable ConfigService
instance (self._config_service / self.config_service). This mixin remains
on Site for backward compatibility but contains no logic of its own.

The `indexes` property stays here because it requires `cast(SiteLike, self)`.
The `description` setter stays here for runtime mutation support.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.protocols.core import SiteLike

if TYPE_CHECKING:
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.core.theme import Theme
    from bengal.services.config import ConfigService


class SitePropertiesMixin:
    """
    Mixin providing config accessor properties for Site.

    All properties delegate to the immutable ConfigService instance,
    except `indexes` (requires SiteLike) and `description` setter
    (runtime mutation).
    """

    # These attributes are defined on the Site dataclass
    config: Config | dict[str, Any]
    root_path: Path
    _paths: BengalPaths | None
    _theme_obj: Theme | None
    _query_registry: QueryIndexRegistry | None
    _config_hash: str | None
    _config_service: ConfigService | None

    @property
    def paths(self) -> BengalPaths:
        """Access to .bengal directory paths."""
        return self.config_service.paths

    @property
    def title(self) -> str | None:
        """Get site title from configuration."""
        return self.config_service.title

    @property
    def description(self) -> str | None:
        """
        Get site description from configuration.

        Respects runtime overrides set on the Site instance while falling back
        to canonical config locations.
        """
        if getattr(self, "_description_override", None) is not None:
            return self._description_override
        return self.config_service.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Allow runtime override of site description for generated outputs."""
        self._description_override = value

    @property
    def baseurl(self) -> str | None:
        """Get site baseurl from configuration."""
        return self.config_service.baseurl

    @property
    def content_dir(self) -> Path:
        """Get path to the content directory."""
        return self.config_service.content_dir

    @property
    def author(self) -> str | None:
        """Get site author from configuration."""
        return self.config_service.author

    @property
    def favicon(self) -> str | None:
        """Get favicon path from site config."""
        return self.config_service.favicon

    @property
    def logo_image(self) -> str | None:
        """Get logo image path from site config."""
        return self.config_service.logo_image

    @property
    def logo_text(self) -> str | None:
        """Get logo text from site config."""
        return self.config_service.logo_text

    @property
    def params(self) -> dict[str, Any]:
        """Site-level custom parameters from [params] config section."""
        return self.config_service.params

    @property
    def logo(self) -> str:
        """Logo URL from config (checks multiple locations)."""
        return self.config_service.logo

    @property
    def config_hash(self) -> str:
        """Get deterministic hash of the resolved configuration."""
        return self.config_service.config_hash

    def _compute_config_hash(self) -> None:
        """
        Compute and cache the configuration hash.

        Kept for backward compatibility. The hash is now computed
        eagerly by ConfigService at construction time.
        """
        from bengal.config.hash import compute_config_hash
        from bengal.core.diagnostics import emit as emit_diagnostic

        self._config_hash = compute_config_hash(self.config)
        emit_diagnostic(
            self,
            "debug",
            "config_hash_computed",
            hash=self._config_hash[:8] if self._config_hash else "none",
        )

    @property
    def theme_config(self) -> Theme:
        """Get theme configuration object."""
        # Prefer the locally-constructed Theme (which has diagnostics_site=self)
        # ConfigService's Theme doesn't pass diagnostics_site
        if self._theme_obj is not None:
            return self._theme_obj
        return self.config_service.theme_config

    @property
    def indexes(self) -> QueryIndexRegistry:
        """
        Access to query indexes for O(1) page lookups.

        This property stays on the mixin because it requires `cast(SiteLike, self)`.
        """
        if self._query_registry is None:
            from bengal.cache.query_index_registry import QueryIndexRegistry

            self._query_registry = QueryIndexRegistry(
                cast(SiteLike, self), self.paths.indexes_dir
            )
        return self._query_registry

    # =========================================================================
    # CONFIG SECTION ACCESSORS
    # =========================================================================

    @property
    def assets_config(self) -> dict[str, Any]:
        """Get the assets configuration section."""
        return self.config_service.assets_config

    @property
    def build_config(self) -> dict[str, Any]:
        """Get the build configuration section."""
        return self.config_service.build_config

    @property
    def i18n_config(self) -> dict[str, Any]:
        """Get the internationalization configuration section."""
        return self.config_service.i18n_config

    @property
    def menu_config(self) -> dict[str, Any]:
        """Get the menu configuration section."""
        return self.config_service.menu_config

    @property
    def content_config(self) -> dict[str, Any]:
        """Get the content configuration section."""
        return self.config_service.content_config

    @property
    def output_config(self) -> dict[str, Any]:
        """Get the output configuration section."""
        return self.config_service.output_config
