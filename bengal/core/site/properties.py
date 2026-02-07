"""
Site properties mixin for config accessor properties.

Provides properties for accessing site configuration values like title,
description, baseurl, author, and various config section accessors.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.protocols.core import SiteLike
from bengal.core.utils.config import get_config_section, get_site_value

if TYPE_CHECKING:
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.core.theme import Theme


class SitePropertiesMixin:
    """
    Mixin providing config accessor properties for Site.

    This mixin provides convenient access to configuration values stored in
    the site's config dictionary, with proper fallbacks and type handling.
    """

    # These attributes are defined on the Site dataclass
    config: Config | dict[str, Any]
    root_path: Path
    _paths: BengalPaths | None
    _theme_obj: Theme | None
    _query_registry: QueryIndexRegistry | None
    _config_hash: str | None

    @property
    def paths(self) -> BengalPaths:
        """
        Access to .bengal directory paths.

        Provides centralized access to all paths within the Bengal state directory.
        Use this instead of hardcoding ".bengal" strings throughout the codebase.

        Returns:
            BengalPaths instance with all state directory paths

        Examples:
            site.paths.build_cache      # .bengal/cache.json
            site.paths.page_cache       # .bengal/page_metadata.json
            site.paths.templates_dir    # .bengal/templates/
            site.paths.ensure_dirs()    # Create all necessary directories
        """
        if self._paths is None:
            from bengal.cache.paths import BengalPaths

            self._paths = BengalPaths(self.root_path)
        return self._paths

    @property
    def title(self) -> str | None:
        """
        Get site title from configuration.

        Returns:
            Site title string from config, or None if not configured

        Examples:
            site.title  # Returns "My Blog" or None
        """
        return get_site_value(self.config, "title")

    @property
    def description(self) -> str | None:
        """
        Get site description from configuration.

        Respects runtime overrides set on the Site instance while falling back
        to canonical config locations.
        """
        if getattr(self, "_description_override", None) is not None:
            return self._description_override

        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "get", lambda k: None)("description")

        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and "description" in site_section:
            return site_section.get("description")

        return self.config.get("description")

    @description.setter
    def description(self, value: str | None) -> None:
        """Allow runtime override of site description for generated outputs."""
        self._description_override = value

    @property
    def baseurl(self) -> str | None:
        """
        Get site baseurl from configuration.

        Baseurl is prepended to all page URLs. Can be empty, path-only (e.g., "/blog"),
        or absolute (e.g., "https://example.com").

        Priority order:
        1. Flat config["baseurl"] (allows runtime overrides, e.g., dev server clearing)
        2. Nested config.site.baseurl or config["site"]["baseurl"]

        Returns:
            Base URL string from config, or None if not configured

        Examples:
            site.baseurl  # Returns "/blog" or "https://example.com" or None
        """
        # Check flat baseurl first (allows runtime overrides like dev server clearing)
        flat_baseurl = self.config.get("baseurl")
        if flat_baseurl is not None:
            return flat_baseurl

        # Fall back to nested site.baseurl
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "baseurl", None)
        return self.config.get("site", {}).get("baseurl")

    @property
    def content_dir(self) -> Path:
        """
        Get path to the content directory.

        Returns the configured content directory or defaults to root_path/content.

        Returns:
            Path to the content directory
        """
        content_config = self.config.get("content", {})
        if isinstance(content_config, dict):
            dir_name = content_config.get("dir", "content")
        else:
            dir_name = getattr(content_config, "dir", "content") or "content"
        return self.root_path / dir_name

    @property
    def author(self) -> str | None:
        """
        Get site author from configuration.

        Returns:
            Author name string from config, or None if not configured

        Examples:
            site.author  # Returns "Jane Doe" or None
        """
        return get_site_value(self.config, "author")

    @property
    def favicon(self) -> str | None:
        """
        Get favicon path from site config.

        Returns:
            Favicon path string from config, or None if not configured
        """
        return get_site_value(self.config, "favicon")

    @property
    def logo_image(self) -> str | None:
        """
        Get logo image path from site config.

        Returns:
            Logo image path string from config, or None if not configured
        """
        # Support both Config and dict access
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
        """
        Get logo text from site config.

        Returns:
            Logo text string from config, or None if not configured
        """
        # Support both Config and dict access
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
        """
        Site-level custom parameters from [params] config section.

        Provides access to arbitrary site-wide configuration values
        that can be used in templates.

        Returns:
            Dict of custom parameters (empty dict if not configured)

        Examples:
            # In bengal.toml:
            # [params]
            # repo_url = "https://github.com/org/repo"
            # author = "Jane Doe"

            # In templates:
            # {{ site.params.repo_url }}
            # {{ site.params.author }}
        """
        return self.config.get("params", {})

    @property
    def logo(self) -> str:
        """
        Logo URL from config (checks multiple locations).

        Checks 'logo_image' at root level and under 'site' section
        for flexibility in configuration.

        Returns:
            Logo URL string or empty string if not configured

        Examples:
            site.logo  # Returns "/assets/logo.png" or ""
        """
        cfg = self.config
        return cfg.get("logo_image", "") or cfg.get("site", {}).get("logo_image", "") or ""

    @property
    def config_hash(self) -> str:
        """
        Get deterministic hash of the resolved configuration.

        Used for automatic cache invalidation when configuration changes.
        The hash captures the effective config state including:
        - Base config from files
        - Environment variable overrides
        - Build profile settings

        Returns:
            16-character hex string (truncated SHA-256)
        """
        if self._config_hash is None:
            self._compute_config_hash()
        # After _compute_config_hash(), _config_hash is guaranteed to be set
        assert self._config_hash is not None, "config_hash should be computed"
        return self._config_hash

    def _compute_config_hash(self) -> None:
        """
        Compute and cache the configuration hash.

        Calculates SHA-256 hash of resolved configuration (including env overrides
        and build profiles) and stores it in `_config_hash`. Used for automatic
        cache invalidation when configuration changes.

        Called during __post_init__ to ensure hash is available immediately.
        Subsequent calls use cached value unless config changes.

        See Also:
            bengal.config.hash.compute_config_hash: Hash computation implementation
        """
        from bengal.config.hash import compute_config_hash

        self._config_hash = compute_config_hash(self.config)
        emit_diagnostic(
            self,
            "debug",
            "config_hash_computed",
            hash=self._config_hash[:8] if self._config_hash else "none",
        )

    @property
    def theme_config(self) -> Theme:
        """
        Get theme configuration object.

        Available in templates as `site.theme_config` for accessing theme settings:
        - site.theme_config.name: Theme name
        - site.theme_config.default_appearance: Default light/dark/system mode
        - site.theme_config.default_palette: Default color palette
        - site.theme_config.config: Additional theme-specific config

        Returns:
            Theme configuration object
        """
        if self._theme_obj is None:
            from bengal.core.theme import Theme

            config_dict: dict[str, Any]
            if hasattr(self.config, "raw"):
                config_dict = self.config.raw
            elif isinstance(self.config, dict):
                config_dict = self.config
            else:
                config_dict = {}
            self._theme_obj = Theme.from_config(
                config_dict,
                root_path=self.root_path,
                diagnostics_site=self,
            )
        return self._theme_obj

    @property
    def indexes(self) -> QueryIndexRegistry:
        """
        Access to query indexes for O(1) page lookups.

        Provides pre-computed indexes for common page queries:
            site.indexes.section.get('blog')        # All blog posts
            site.indexes.author.get('Jane Smith')   # Posts by Jane
            site.indexes.category.get('tutorial')   # Tutorial pages
            site.indexes.date_range.get('2024')     # 2024 posts

        Indexes are built during the build phase and provide O(1) lookups
        instead of O(n) filtering. This makes templates scale to large sites.

        Returns:
            QueryIndexRegistry instance

        Example:
            {% set blog_posts = site.indexes.section.get('blog') | resolve_pages %}
            {% for post in blog_posts %}
                <h2>{{ post.title }}</h2>
            {% endfor %}
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
        """
        Get the assets configuration section.

        Provides safe access to assets configuration with empty dict fallback.
        Reduces repeated ``site.config.get("assets", {})`` pattern.

        Returns:
            Assets configuration dict (empty dict if not configured)

        Example:
            pipeline_enabled = site.assets_config.get("pipeline", False)
        """
        return get_config_section(self.config, "assets")

    @property
    def build_config(self) -> dict[str, Any]:
        """
        Get the build configuration section.

        Provides safe access to build configuration with empty dict fallback.
        Reduces repeated ``site.config.get("build", {})`` pattern.

        Returns:
            Build configuration dict (empty dict if not configured)

        Example:
            parallel = site.build_config.get("parallel", True)
        """
        return get_config_section(self.config, "build")

    @property
    def i18n_config(self) -> dict[str, Any]:
        """
        Get the internationalization configuration section.

        Provides safe access to i18n configuration with empty dict fallback.
        Reduces repeated ``site.config.get("i18n", {})`` pattern.

        Returns:
            i18n configuration dict (empty dict if not configured)

        Example:
            default_lang = site.i18n_config.get("default_language", "en")
        """
        return get_config_section(self.config, "i18n")

    @property
    def menu_config(self) -> dict[str, Any]:
        """
        Get the menu configuration section.

        Provides safe access to menu configuration with empty dict fallback.
        Reduces repeated ``site.config.get("menu", {})`` pattern.

        Returns:
            Menu configuration dict (empty dict if not configured)

        Example:
            main_menu = site.menu_config.get("main", [])
        """
        return get_config_section(self.config, "menu")

    @property
    def content_config(self) -> dict[str, Any]:
        """
        Get the content configuration section.

        Provides safe access to content configuration with empty dict fallback.
        Reduces repeated ``site.config.get("content", {})`` pattern.

        Returns:
            Content configuration dict (empty dict if not configured)

        Example:
            content_dir = site.content_config.get("dir", "content")
        """
        return get_config_section(self.config, "content")

    @property
    def output_config(self) -> dict[str, Any]:
        """
        Get the output configuration section.

        Provides safe access to output configuration with empty dict fallback.
        Reduces repeated ``site.config.get("output", {})`` pattern.

        Returns:
            Output configuration dict (empty dict if not configured)

        Example:
            output_dir = site.output_config.get("dir", "public")
        """
        return get_config_section(self.config, "output")
