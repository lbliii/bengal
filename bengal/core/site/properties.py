"""
Site properties mixin.

Provides property accessors for site configuration values (title, baseurl, author)
and computed properties like theme_config and indexes.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.core.theme: Theme configuration
    - bengal.cache.query_index_registry: Query indexes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.core.theme import Theme
    from bengal.core.version import Version, VersionConfig


class SitePropertiesMixin:
    """
    Mixin providing property accessors for site configuration.

    Requires these attributes on the host class:
        - config: dict[str, Any]
        - root_path: Path
        - _theme_obj: Theme | None
        - _config_hash: str | None
        - _query_registry: Any
    """

    # Type hints for mixin attributes (provided by host class)
    config: dict[str, Any]
    root_path: Path
    _theme_obj: Theme | None
    _config_hash: str | None
    _query_registry: Any
    _paths: BengalPaths | None

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
        return self.config.get("title")

    @property
    def baseurl(self) -> str | None:
        """
        Get site baseurl from configuration.

        Baseurl is prepended to all page URLs. Can be empty, path-only (e.g., "/blog"),
        or absolute (e.g., "https://example.com").

        Returns:
            Base URL string from config, or None if not configured

        Examples:
            site.baseurl  # Returns "/blog" or "https://example.com" or None
        """
        return self.config.get("baseurl")

    @property
    def author(self) -> str | None:
        """
        Get site author from configuration.

        Returns:
            Author name string from config, or None if not configured

        Examples:
            site.author  # Returns "Jane Doe" or None
        """
        return self.config.get("author")

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

            self._theme_obj = Theme.from_config(
                self.config,
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

            self._query_registry = QueryIndexRegistry(self, self.paths.indexes_dir)
        return self._query_registry

    # =========================================================================
    # VERSIONING PROPERTIES
    # =========================================================================

    @property
    def versioning_enabled(self) -> bool:
        """
        Check if versioned documentation is enabled.

        Returns:
            True if versioning is configured and enabled
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        return version_config is not None and version_config.enabled

    @property
    def versions(self) -> list[dict[str, Any]]:
        """
        Get list of all versions for templates.

        Available in templates as `site.versions` for version selector rendering.
        Each version dict contains: id, label, latest, deprecated, url_prefix.

        Returns:
            List of version dictionaries for template use

        Example:
            {% for v in site.versions %}
                <option value="{{ v.url_prefix }}"
                        {% if v.id == site.current_version.id %}selected{% endif %}>
                    {{ v.label }}{% if v.latest %} (Latest){% endif %}
                </option>
            {% endfor %}
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            return []
        return [v.to_dict() for v in version_config.versions]

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """
        Get the latest version info for templates.

        Returns:
            Latest version dictionary or None if versioning disabled
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            return None
        latest = version_config.latest_version
        return latest.to_dict() if latest else None

    def get_version(self, version_id: str) -> Version | None:
        """
        Get a version by ID or alias.

        Args:
            version_id: Version ID (e.g., 'v2') or alias (e.g., 'latest')

        Returns:
            Version object or None if not found
        """
        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            return None
        return version_config.get_version_or_alias(version_id)
