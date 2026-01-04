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
        # Support both Config and dict access
        if hasattr(self.config, "site"):
            return self.config.site.title
        return self.config.get("site", {}).get("title") or self.config.get("title")

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
        # Support both Config and dict access
        if hasattr(self.config, "site"):
            return self.config.site.baseurl
        return self.config.get("site", {}).get("baseurl") or self.config.get("baseurl")

    @property
    def author(self) -> str | None:
        """
        Get site author from configuration.

        Returns:
            Author name string from config, or None if not configured

        Examples:
            site.author  # Returns "Jane Doe" or None
        """
        # Support both Config and dict access
        if hasattr(self.config, "site"):
            return self.config.site.author
        return self.config.get("site", {}).get("author") or self.config.get("author")

    @property
    def favicon(self) -> str | None:
        """
        Get favicon path from site config.

        Returns:
            Favicon path string from config, or None if not configured
        """
        # Support both Config and dict access
        if hasattr(self.config, "site"):
            return self.config.site.get("favicon")
        return self.config.get("site", {}).get("favicon")

    @property
    def logo_image(self) -> str | None:
        """
        Get logo image path from site config.

        Returns:
            Logo image path string from config, or None if not configured
        """
        # Support both Config and dict access
        if hasattr(self.config, "site"):
            return self.config.site.get("logo_image") or self.config.site.get("logo")
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
        if hasattr(self.config, "site"):
            return self.config.site.get("logo_text") or self.config.site.title
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
        value = self.config.get("assets")
        return dict(value) if isinstance(value, dict) else {}

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
        # Support both Config and dict access
        if hasattr(self.config, "build"):
            # ConfigSection - access raw dict
            return dict(self.config.build._data) if hasattr(self.config.build, "_data") else {}
        value = self.config.get("build")
        return dict(value) if isinstance(value, dict) else {}

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
        value = self.config.get("i18n")
        return dict(value) if isinstance(value, dict) else {}

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
        value = self.config.get("menu")
        return dict(value) if isinstance(value, dict) else {}

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
        value = self.config.get("content")
        return dict(value) if isinstance(value, dict) else {}

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
        value = self.config.get("output")
        return dict(value) if isinstance(value, dict) else {}

    # =========================================================================
    # VERSIONING PROPERTIES
    # =========================================================================

    # =========================================================================
    # NORMALIZED CONFIG ACCESSORS
    # =========================================================================
    # These properties normalize config values that support multiple formats
    # (bool, dict, None) into consistent dictionaries with all defaults applied.
    # Templates use these instead of manual .get() chains with fallbacks.

    @property
    def build_badge(self) -> dict[str, Any]:
        """
        Get normalized build badge configuration.

        Handles all supported formats:
        - None/False: disabled
        - True: enabled with defaults
        - dict: enabled with custom settings

        Returns:
            Normalized dict with keys: enabled, dir_name, label, label_color, message_color

        Example:
            {% if site.build_badge.enabled %}
                <span>{{ site.build_badge.label }}</span>
            {% endif %}
        """
        value = self.config.get("build_badge")

        if value is None or value is False:
            return {
                "enabled": False,
                "dir_name": "bengal",
                "label": "built in",
                "label_color": "#555",
                "message_color": "#4c1d95",
            }

        if value is True:
            return {
                "enabled": True,
                "dir_name": "bengal",
                "label": "built in",
                "label_color": "#555",
                "message_color": "#4c1d95",
            }

        if isinstance(value, dict):
            return {
                "enabled": bool(value.get("enabled", True)),
                "dir_name": str(value.get("dir_name", "bengal")),
                "label": str(value.get("label", "built in")),
                "label_color": str(value.get("label_color", "#555")),
                "message_color": str(value.get("message_color", "#4c1d95")),
            }

        # Unknown type: treat as disabled
        return {
            "enabled": False,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    @property
    def document_application(self) -> dict[str, Any]:
        """
        Get normalized document application configuration.

        Document Application enables modern browser-native features:
        - View Transitions API for smooth page transitions
        - Speculation Rules for prefetching/prerendering
        - Native <dialog>, popover, and CSS state machines

        Returns:
            Normalized dict with enabled flag and all sub-configs with defaults applied

        Example:
            {% if site.document_application.enabled and site.document_application.navigation.view_transitions %}
                <meta name="view-transition" content="same-origin">
            {% endif %}
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["document_application"]
        value = self.config.get("document_application", {})

        if not isinstance(value, dict):
            # If not a dict (e.g., False), return defaults with enabled=False
            result = {
                "enabled": False,
                "navigation": dict(defaults["navigation"]),
                "speculation": dict(defaults["speculation"]),
                "interactivity": dict(defaults["interactivity"]),
                "features": {},
            }
            return result

        # Merge with defaults
        navigation = value.get("navigation", {})
        speculation = value.get("speculation", {})
        interactivity = value.get("interactivity", {})

        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "navigation": {
                "view_transitions": navigation.get(
                    "view_transitions", defaults["navigation"]["view_transitions"]
                ),
                "transition_style": navigation.get(
                    "transition_style", defaults["navigation"]["transition_style"]
                ),
                "scroll_restoration": navigation.get(
                    "scroll_restoration", defaults["navigation"]["scroll_restoration"]
                ),
            },
            "speculation": {
                "enabled": speculation.get("enabled", defaults["speculation"]["enabled"]),
                "prerender": {
                    "eagerness": speculation.get("prerender", {}).get(
                        "eagerness", defaults["speculation"]["prerender"]["eagerness"]
                    ),
                    "patterns": speculation.get("prerender", {}).get(
                        "patterns", defaults["speculation"]["prerender"]["patterns"]
                    ),
                },
                "prefetch": {
                    "eagerness": speculation.get("prefetch", {}).get(
                        "eagerness", defaults["speculation"]["prefetch"]["eagerness"]
                    ),
                    "patterns": speculation.get("prefetch", {}).get(
                        "patterns", defaults["speculation"]["prefetch"]["patterns"]
                    ),
                },
                "auto_generate": speculation.get(
                    "auto_generate", defaults["speculation"]["auto_generate"]
                ),
                "exclude_patterns": speculation.get(
                    "exclude_patterns", defaults["speculation"]["exclude_patterns"]
                ),
            },
            "interactivity": {
                "tabs": interactivity.get("tabs", defaults["interactivity"]["tabs"]),
                "accordions": interactivity.get(
                    "accordions", defaults["interactivity"]["accordions"]
                ),
                "modals": interactivity.get("modals", defaults["interactivity"]["modals"]),
                "tooltips": interactivity.get("tooltips", defaults["interactivity"]["tooltips"]),
                "dropdowns": interactivity.get("dropdowns", defaults["interactivity"]["dropdowns"]),
                "code_copy": interactivity.get("code_copy", defaults["interactivity"]["code_copy"]),
            },
            # Feature flags with defaults (all enabled by default)
            "features": {
                "speculation_rules": True,
                "view_transitions_meta": True,
                **value.get("features", {}),
            },
        }

    @property
    def link_previews(self) -> dict[str, Any]:
        """
        Get normalized link previews configuration.

        Link Previews provide Wikipedia-style hover cards for internal links,
        showing page title, excerpt, reading time, and tags. Requires per-page
        JSON generation to be enabled.

        Returns:
            Normalized dict with enabled flag and all display options

        Example:
            {% if site.link_previews.enabled %}
                {# Include link preview script and config bridge #}
            {% endif %}
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["link_previews"]
        value = self.config.get("link_previews", {})

        if not isinstance(value, dict):
            # If not a dict (e.g., False), return defaults with enabled=False
            if value is False:
                return {
                    "enabled": False,
                    "hover_delay": defaults["hover_delay"],
                    "hide_delay": defaults["hide_delay"],
                    "show_section": defaults["show_section"],
                    "show_reading_time": defaults["show_reading_time"],
                    "show_word_count": defaults["show_word_count"],
                    "show_date": defaults["show_date"],
                    "show_tags": defaults["show_tags"],
                    "max_tags": defaults["max_tags"],
                    "exclude_selectors": defaults["exclude_selectors"],
                }
            # True or None: use defaults with enabled=True
            return dict(defaults)

        # Merge with defaults
        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "hover_delay": value.get("hover_delay", defaults["hover_delay"]),
            "hide_delay": value.get("hide_delay", defaults["hide_delay"]),
            "show_section": value.get("show_section", defaults["show_section"]),
            "show_reading_time": value.get("show_reading_time", defaults["show_reading_time"]),
            "show_word_count": value.get("show_word_count", defaults["show_word_count"]),
            "show_date": value.get("show_date", defaults["show_date"]),
            "show_tags": value.get("show_tags", defaults["show_tags"]),
            "max_tags": value.get("max_tags", defaults["max_tags"]),
            "include_selectors": value.get("include_selectors", defaults["include_selectors"]),
            "exclude_selectors": value.get("exclude_selectors", defaults["exclude_selectors"]),
        }

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
        Get list of all versions for templates (cached).

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

        Performance:
            Version dicts are cached on first access. For a 1000-page site with
            version selector in header, this eliminates ~1000 list creations.
        """
        # Return cached value if available
        cache_attr = "_versions_dict_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            return cached

        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            result: list[dict[str, Any]] = []
        else:
            result = [v.to_dict() for v in version_config.versions]

        # Cache the result
        object.__setattr__(self, cache_attr, result)
        return result

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """
        Get the latest version info for templates (cached).

        Returns:
            Latest version dictionary or None if versioning disabled

        Performance:
            Cached on first access to avoid repeated .to_dict() calls.
        """
        # Return cached value if available
        cache_attr = "_latest_version_dict_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            # None means "not cached yet", use sentinel for "cached None"
            return cached if cached != "_NO_LATEST_VERSION_" else None

        version_config: VersionConfig = getattr(self, "version_config", None)  # type: ignore[assignment]
        if not version_config or not version_config.enabled:
            result = None
        else:
            latest = version_config.latest_version
            result = latest.to_dict() if latest else None

        # Cache the result (use sentinel for None to distinguish from "not cached")
        object.__setattr__(
            self, cache_attr, result if result is not None else "_NO_LATEST_VERSION_"
        )
        return result

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

    def invalidate_version_caches(self) -> None:
        """
        Invalidate cached version dict lists.

        Call this when versioning configuration changes (e.g., during dev server reload).
        """
        for attr in ("_versions_dict_cache", "_latest_version_dict_cache"):
            if hasattr(self, attr):
                object.__delattr__(self, attr)
