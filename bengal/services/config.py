"""
Immutable configuration service for Site.

Replaces SitePropertiesMixin with a frozen dataclass that provides
thread-safe, lock-free access to all configuration-derived values.

ConfigService is constructed once from (config, root_path) and shared
across threads during parallel rendering. Because it is frozen, no
synchronization is needed.

Classes:
    ConfigService: Frozen dataclass providing config accessor properties.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.utils.config import get_config_section, get_site_value

if TYPE_CHECKING:
    from bengal.cache.paths import BengalPaths
    from bengal.config.accessor import Config
    from bengal.core.theme import Theme


@dataclass(frozen=True, slots=True)
class ConfigService:
    """
    Immutable configuration service providing config accessor properties.

    Constructed once from (config, root_path) at Site initialization.
    Thread-safe by immutability — no locks needed.

    Attributes:
        config: Site configuration dictionary or Config object
        root_path: Root directory of the site
        paths: BengalPaths instance for .bengal directory paths
        config_hash: Deterministic hash of resolved configuration
        theme_obj: Pre-computed Theme object (constructed eagerly)

    Example:
        >>> svc = ConfigService.from_config(config, root_path)
        >>> svc.title       # "My Blog"
        >>> svc.baseurl     # "/blog"
        >>> svc.paths       # BengalPaths(root_path)
        >>> svc.config_hash # "a1b2c3d4e5f6g7h8"
    """

    config: Config | dict[str, Any]
    root_path: Path
    paths: BengalPaths
    config_hash: str
    theme_obj: Theme | None = None

    @classmethod
    def from_config(cls, config: Config | dict[str, Any], root_path: Path) -> ConfigService:
        """
        Construct ConfigService from config and root_path.

        Eagerly computes paths and config_hash at construction time
        so all derived values are available without lazy initialization.

        Args:
            config: Site configuration dictionary or Config object
            root_path: Root directory of the site

        Returns:
            Frozen ConfigService instance
        """
        from bengal.cache.paths import BengalPaths
        from bengal.config.hash import compute_config_hash
        from bengal.core.theme import Theme

        paths = BengalPaths(root_path)
        config_hash = compute_config_hash(config)

        # Eagerly compute theme
        config_dict: dict[str, Any]
        if hasattr(config, "raw"):
            config_dict = config.raw
        elif isinstance(config, dict):
            config_dict = config
        else:
            config_dict = {}
        theme = Theme.from_config(config_dict, root_path=root_path)

        return cls(
            config=config,
            root_path=root_path,
            paths=paths,
            config_hash=config_hash,
            theme_obj=theme,
        )

    # =========================================================================
    # PURE CONFIG ACCESSORS
    # =========================================================================

    @property
    def title(self) -> str | None:
        """Get site title from configuration."""
        return get_site_value(self.config, "title")

    @property
    def description(self) -> str | None:
        """
        Get site description from configuration.

        Note: Runtime overrides (via Site.description setter) are handled
        by Site itself, which checks its _description_override before
        delegating to this property.
        """
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "get", lambda k: None)("description")

        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and "description" in site_section:
            return site_section.get("description")

        return self.config.get("description")

    @property
    def baseurl(self) -> str | None:
        """
        Get site baseurl from configuration.

        Priority order:
        1. Flat config["baseurl"] (allows runtime overrides)
        2. Nested config.site.baseurl or config["site"]["baseurl"]
        """
        flat_baseurl = self.config.get("baseurl")
        if flat_baseurl is not None:
            return flat_baseurl

        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "baseurl", None)
        return self.config.get("site", {}).get("baseurl")

    @property
    def content_dir(self) -> Path:
        """Get path to the content directory."""
        content_config = self.config.get("content", {})
        if isinstance(content_config, dict):
            dir_name = content_config.get("dir", "content")
        else:
            dir_name = getattr(content_config, "dir", "content") or "content"
        return self.root_path / dir_name

    @property
    def author(self) -> str | None:
        """Get site author from configuration."""
        return get_site_value(self.config, "author")

    @property
    def favicon(self) -> str | None:
        """Get favicon path from site config."""
        return get_site_value(self.config, "favicon")

    @property
    def logo_image(self) -> str | None:
        """Get logo image path from site config."""
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            get_fn = getattr(site_attr, "get", lambda k: None)
            return get_fn("logo_image") or get_fn("logo")
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("logo_image") or site_section.get("logo")
        return self.config.get("logo_image") or self.config.get("logo")

    @property
    def logo_text(self) -> str | None:
        """Get logo text from site config."""
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            get_fn = getattr(site_attr, "get", lambda k: None)
            return get_fn("logo_text") or getattr(site_attr, "title", None)
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("logo_text") or site_section.get("title")
        return self.config.get("logo_text") or self.config.get("title")

    @property
    def params(self) -> dict[str, Any]:
        """Site-level custom parameters from [params] config section."""
        return self.config.get("params", {})

    @property
    def logo(self) -> str:
        """Logo URL from config (checks multiple locations)."""
        cfg = self.config
        return cfg.get("logo_image", "") or cfg.get("site", {}).get("logo_image", "") or ""

    @property
    def theme_config(self) -> Theme:
        """
        Get theme configuration object.

        Eagerly computed at construction time via from_config().
        """
        if self.theme_obj is None:
            from bengal.core.theme import Theme

            config_dict: dict[str, Any]
            if hasattr(self.config, "raw"):
                config_dict = self.config.raw
            elif isinstance(self.config, dict):
                config_dict = self.config
            else:
                config_dict = {}
            return Theme.from_config(config_dict, root_path=self.root_path)
        return self.theme_obj

    # =========================================================================
    # CONFIG SECTION ACCESSORS
    # =========================================================================

    @property
    def assets_config(self) -> dict[str, Any]:
        """Get the assets configuration section."""
        return get_config_section(self.config, "assets")

    @property
    def build_config(self) -> dict[str, Any]:
        """Get the build configuration section."""
        return get_config_section(self.config, "build")

    @property
    def i18n_config(self) -> dict[str, Any]:
        """Get the internationalization configuration section."""
        return get_config_section(self.config, "i18n")

    @property
    def menu_config(self) -> dict[str, Any]:
        """Get the menu configuration section."""
        return get_config_section(self.config, "menu")

    @property
    def content_config(self) -> dict[str, Any]:
        """Get the content configuration section."""
        return get_config_section(self.config, "content")

    @property
    def output_config(self) -> dict[str, Any]:
        """Get the output configuration section."""
        return get_config_section(self.config, "output")
