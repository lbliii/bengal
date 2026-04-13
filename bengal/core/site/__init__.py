"""
Site package for Bengal SSG.

Provides the Site class—the central container for all content (pages,
sections, assets) and coordinator of the build process.

Public API:
Site: Main site dataclass with discovery, build, and serve capabilities

Creation:
Site.from_config(path): Load from bengal.toml (recommended)
Site.for_testing(): Minimal instance for unit tests
Site(root_path, config): Direct instantiation (advanced)

Package Structure:
factory.py: Factory functions (from_config, for_testing)
versioning.py: VersionService (version support, composed)

Key Features:
Build Coordination: site.build() orchestrates full build pipeline
Dev Server: site.serve() starts live-reload development server
Content Discovery: site.discover_content() finds pages/sections/assets
Theme Resolution: site.theme_config provides theme configuration
Query Interface: site.pages, site.sections, site.taxonomies

Example:
    from bengal.core import Site

    site = Site.from_config(Path('/path/to/site'))
    site.build(parallel=True, incremental=True)

Related Packages:
bengal.orchestration.build: Build orchestration
bengal.rendering.template_engine: Template rendering
bengal.cache.build_cache: Build state persistence

"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Self, cast

from bengal.config.utils import unwrap_config
from bengal.core.diagnostics import DiagnosticsSink
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.registry import ContentRegistry
from bengal.core.theme import Theme
from bengal.core.url_ownership import URLRegistry
from bengal.core.version import Version, VersionConfig
from bengal.icons import resolver as icon_resolver
from bengal.services.config import ConfigService

from .factory import for_testing, from_config
from .versioning import VersionService

if TYPE_CHECKING:
    from datetime import datetime

    from bengal.assets.manifest import AssetManifest
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.core.asset import Asset
    from bengal.core.cascade_snapshot import CascadeSnapshot
    from bengal.core.menu import MenuBuilder, MenuItem
    from bengal.core.page_cache import PageCacheManager
    from bengal.orchestration.build.inputs import BuildInput
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats.models import BuildStats
    from bengal.parsing.base import BaseMarkdownParser
    from bengal.protocols.core import PageLike, SectionLike, SiteLike
    from bengal.utils.primitives.dotdict import DotDict


# Thread-safe output lock for parallel processing.
_print_lock = Lock()


@dataclass
class Site:
    """
    Represents the entire website and orchestrates the build process.

    Creation:
        Recommended: Site.from_config(root_path)
            - Loads configuration from bengal.toml
            - Applies all settings automatically
            - Use for production builds and CLI

        Direct instantiation: Site(root_path=path, config=config)
            - For unit testing with controlled state
            - For programmatic config manipulation
            - Advanced use case only

    Attributes:
        root_path: Root directory of the site
        config: Site configuration dictionary (from bengal.toml or explicit)
        pages: All pages in the site
        sections: All sections in the site
        assets: All assets in the site
        theme: Theme name or path
        output_dir: Output directory for built site
        build_time: Timestamp of the last build
        taxonomies: Collected taxonomies (tags, categories, etc.)

    Examples:
        # Production/CLI (recommended):
        site = Site.from_config(Path('/path/to/site'))

        # Unit testing:
        site = Site(root_path=Path('/test'), config={})
        site.pages = [test_page1, test_page2]

        # Programmatic config:
        from bengal.config import UnifiedConfigLoader
        loader = UnifiedConfigLoader()
        config = loader.load(path)
        # Note: config is now a Config object, use config.raw for dict access
        site = Site(root_path=path, config=config)

    """

    root_path: Path
    config: Config | dict[str, Any] = field(default_factory=dict)
    pages: list[PageLike] = field(default_factory=list)
    sections: list[SectionLike] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    theme: str | None = None
    output_dir: Path = field(default_factory=lambda: Path("public"))
    build_time: datetime | None = None
    taxonomies: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Cross-reference index for internal linking (built during rendering)
    xref_index: dict[str, Any] = field(default_factory=dict)
    menu: dict[str, list[MenuItem]] = field(default_factory=dict)
    menu_builders: dict[str, MenuBuilder] = field(default_factory=dict)
    # Localized menus when i18n is enabled: {lang: {menu_name: [MenuItem]}}.
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)
    # Current language context for rendering (set per page during rendering).
    current_language: str | None = None
    # Global data from data/ directory (YAML, JSON, TOML files).
    data: DotDict = field(default_factory=dict)
    # Runtime flag: True when running in dev server mode (not persisted to config).
    dev_mode: bool = False

    # Versioning configuration (loaded from config during __post_init__)
    version_config: VersionConfig = field(default_factory=VersionConfig)
    # Current version context for rendering (set per page during rendering)
    current_version: Version | None = None

    # Version service (composed, replaces SiteVersioningMixin)
    _version_service: VersionService | None = field(default=None, repr=False, init=False)

    # Page cache manager (lazy caches over self.pages, extracted to PageCacheManager)
    _page_cache: PageCacheManager = field(default=None, repr=False, init=False)  # type: ignore[assignment]  # set in __post_init__
    _theme_obj: Theme | None = field(default=None, repr=False, init=False)
    _query_registry: QueryIndexRegistry | None = field(default=None, repr=False, init=False)

    # URL ownership registry for claim-time enforcement
    # See: plan/drafted/plan-url-ownership-architecture.md
    url_registry: URLRegistry = field(default_factory=URLRegistry, init=False)

    # Content registry for O(1) page/section lookups
    _registry: ContentRegistry | None = field(default=None, repr=False, init=False)

    # Current build state (set during build, None outside build context)
    _current_build_state: BuildState | None = field(default=None, repr=False, init=False)

    # Config hash for cache invalidation (computed on init)
    _config_hash: str | None = field(default=None, repr=False, init=False)

    # BengalPaths instance for centralized .bengal directory access
    _paths: BengalPaths | None = field(default=None, repr=False, init=False)
    # Optional runtime override for site description (used by postprocessors)
    _description_override: str | None = field(default=None, repr=False, init=False)

    # Immutable config service (constructed in __post_init__, thread-safe)
    _config_service: ConfigService | None = field(default=None, repr=False, init=False)

    # Shared link registry built after rendering (consumed by all link validators)
    link_registry: Any | None = field(default=None, repr=False, init=False)

    # Dynamic runtime attributes (set by various orchestrators)
    # Diagnostics sink for core-model events (set by BuildOrchestrator)
    diagnostics: DiagnosticsSink | None = field(default=None, repr=False, init=False)
    # Menu metadata for dev server menu items (set by MenuOrchestrator)
    _dev_menu_metadata: dict[str, Any] | None = field(default=None, repr=False, init=False)
    # Page lookup maps for efficient page resolution (set by template functions)
    _page_lookup_maps: dict[str, dict[str, PageLike]] | None = field(
        default=None, repr=False, init=False
    )
    # Last build stats for health check access (set by finalization phase)
    _last_build_stats: dict[str, Any] | None = field(default=None, repr=False, init=False)
    # Template parser cache (set by get_page template function)
    _template_parser: BaseMarkdownParser | None = field(default=None, repr=False, init=False)

    # =========================================================================
    # RUNTIME CACHES — LEGACY FALLBACK FIELDS
    #
    # Primary path for these caches is now BuildState (structurally fresh
    # each build). These Site fields exist as fallback for code paths
    # that run outside of builds (tests, CLI health checks, etc.).
    #
    # Template caches (theme_chain, template_dirs, template_metadata) and
    # discovery state (features_detected, discovery_timing_ms) have been
    # moved to BuildState. Consumers check BuildState first, falling back
    # to these fields via getattr.
    # =========================================================================

    # --- Asset Manifest State ---
    # Previous manifest for incremental asset comparison (set by AssetOrchestrator)
    _asset_manifest_previous: AssetManifest | None = field(default=None, repr=False, init=False)

    # Thread-safe set of fallback warnings to avoid duplicate warnings
    _asset_manifest_fallbacks_global: set[str] = field(default_factory=set, repr=False, init=False)

    # Lock for thread-safe fallback set access (initialized in __post_init__)
    _asset_manifest_fallbacks_lock: Lock | None = field(default=None, repr=False, init=False)

    # Shared lock for lazy-property initialization (double-checked locking pattern)
    _init_lock: Lock = field(default_factory=Lock, repr=False, init=False)

    # --- Legacy Template Environment Caches (primary: BuildState) ---
    _bengal_theme_chain_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _bengal_template_dirs_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)
    _bengal_template_metadata_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )

    # --- Legacy Discovery State (primary: BuildState) ---
    _discovery_breakdown_ms: dict[str, float] | None = field(default=None, repr=False, init=False)
    features_detected: set[str] = field(default_factory=set, repr=False, init=False)

    # --- Cascade Snapshot (primary: BuildState, bridge: site.cascade property) ---
    _cascade_snapshot: CascadeSnapshot | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        # Ensure root_path is always absolute to eliminate CWD-dependent behavior.
        if not self.root_path.is_absolute():
            self.root_path = self.root_path.resolve()

        # Access theme name from config (Config supports dict-like access via get())
        # Priority order for theme name:
        # 1. [site] section with theme key: config["site"]["theme"] (TOML format)
        # 2. Top-level theme string: config["theme"] = "mytheme" (legacy)
        # 3. Default to "default"
        # Note: [theme] section contains theme SETTINGS (appearance, palette),
        #       NOT the theme name to use.
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("theme"):
            self.theme = site_section.get("theme")
        elif hasattr(site_section, "theme") and site_section.theme:
            # ConfigSection access
            self.theme = site_section.theme
        else:
            # Legacy: top-level theme as string
            theme_value = self.config.get("theme")
            if isinstance(theme_value, str):
                self.theme = theme_value
            elif (isinstance(theme_value, dict) and theme_value.get("name")) or (
                hasattr(theme_value, "get") and theme_value.get("name")
            ):
                self.theme = str(theme_value.get("name"))
            elif hasattr(theme_value, "name") and theme_value.name:
                self.theme = str(theme_value.name)
            else:
                self.theme = "default"

        # Theme.from_config expects a dict; unwrap_config handles Config, dict, etc.
        config_dict = unwrap_config(self.config)
        self._theme_obj = Theme.from_config(
            config_dict,
            root_path=self.root_path,
            diagnostics_site=self,
        )

        # Initialize theme-aware icon resolver for all icon consumers
        # (template functions, inline icon plugin, directives)
        icon_resolver.initialize(cast("SiteLike", self))

        # Access output_dir from build section (supports both Config and dict)
        output_dir_str: str | None = None
        if hasattr(self.config, "build"):
            build_attr = self.config.build
            output_dir_str = getattr(build_attr, "output_dir", "public")
        else:
            build_section = self.config.get("build", {})
            if isinstance(build_section, dict):
                output_dir_str = build_section.get("output_dir", "public")
            else:
                # Fallback to flat access for backward compatibility
                output_dir_str = self.config.get("output_dir", "public")

        if output_dir_str:
            self.output_dir = Path(output_dir_str)

        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir

        self.data = self._load_data_directory()
        self._compute_config_hash()

        # Construct immutable ConfigService (thread-safe accessor for all config properties)
        self._config_service = ConfigService.from_config(self.config, self.root_path)

        # Initialize page cache manager (lazy caches over self.pages)
        from bengal.core.page_cache import PageCacheManager

        self._page_cache = PageCacheManager(lambda: self.pages)

        # Initialize versioning configuration
        # VersionConfig.from_config expects a dict; config_dict already computed above
        self.version_config = VersionConfig.from_config(config_dict)
        self._version_service = VersionService(self.version_config)
        if self.version_config.enabled:
            emit_diagnostic(
                self,
                "debug",
                "versioning_enabled",
                versions=[v.id for v in self.version_config.versions],
                latest=self.version_config.latest_version.id
                if self.version_config.latest_version
                else None,
            )

        # Initialize thread-safe lock for asset manifest fallback tracking
        if self._asset_manifest_fallbacks_lock is None:
            self._asset_manifest_fallbacks_lock = Lock()

        # Initialize URL registry for claim-time ownership enforcement
        if not hasattr(self, "url_registry") or self.url_registry is None:
            self.url_registry = URLRegistry()

        # Initialize content registry for O(1) lookups
        if self._registry is None:
            self._registry = ContentRegistry()
            self._registry.set_root_path(self.root_path)
            # Share URL registry with content registry
            self._registry.url_ownership = self.url_registry

    # =========================================================================
    # REGISTRY ACCESS
    # =========================================================================

    @property
    def config_service(self) -> ConfigService:
        """
        Immutable configuration service for thread-safe config access.

        Provides config-derived properties (title, baseurl, author, etc.)
        via a frozen dataclass that requires no locks during parallel rendering.
        """
        if self._config_service is None:
            with self._init_lock:
                if self._config_service is None:
                    self._config_service = ConfigService.from_config(self.config, self.root_path)
        return self._config_service

    # =========================================================================
    # CASCADE SNAPSHOT (inlined from SiteCascadeMixin)
    # =========================================================================

    @property
    def cascade(self) -> CascadeSnapshot:
        """
        Get the immutable cascade snapshot for this build.

        Resolution order:
            1. BuildState.cascade_snapshot (during builds — structurally fresh)
            2. Local _cascade_snapshot (outside builds — tests, CLI)
            3. Empty snapshot (graceful fallback)

        Returns:
            CascadeSnapshot instance (empty if not yet built)
        """
        if self._current_build_state is not None:
            snapshot = self._current_build_state.cascade_snapshot
            if snapshot is not None:
                return snapshot

        if self._cascade_snapshot is not None:
            return self._cascade_snapshot

        from bengal.core.cascade_snapshot import CascadeSnapshot

        return CascadeSnapshot.empty()

    def build_cascade_snapshot(self) -> None:
        """
        Build the immutable cascade snapshot from all sections.

        Delegates to bengal.core.cascade_snapshot.build_cascade_from_content()
        and stores the result on BuildState (primary) and _cascade_snapshot (fallback).
        """
        from bengal.core.cascade_snapshot import build_cascade_from_content

        snapshot = build_cascade_from_content(self.root_path, self.sections, self.pages)
        snapshot = dataclasses.replace(snapshot)  # New id for cache invalidation

        if self._current_build_state is not None:
            self._current_build_state.cascade_snapshot = snapshot

        self._cascade_snapshot = snapshot

    # =========================================================================
    # CONFIG ACCESSORS (inlined from SiteAccessorsMixin)
    # =========================================================================

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
        """Get site description, respecting runtime overrides."""
        if self._description_override is not None:
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

    @property
    def theme_config(self) -> Theme:
        """Get theme configuration object."""
        if self._theme_obj is not None:
            return self._theme_obj
        return self.config_service.theme_config

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

    # =========================================================================
    # NORMALIZED CONFIG (inlined from SiteNormalizedConfigMixin)
    # =========================================================================

    @property
    def build_badge(self) -> dict[str, Any]:
        """
        Get normalized build badge configuration.

        Handles all supported formats:
        - None/False: disabled
        - True: enabled with defaults
        - dict: enabled with custom settings
        """
        _defaults = {
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }
        value = self.config.get("build_badge")

        if value is None or value is False:
            return {"enabled": False, **_defaults}
        if value is True:
            return {"enabled": True, **_defaults}
        if isinstance(value, dict):
            return {
                "enabled": bool(value.get("enabled", True)),
                "dir_name": str(value.get("dir_name", _defaults["dir_name"])),
                "label": str(value.get("label", _defaults["label"])),
                "label_color": str(value.get("label_color", _defaults["label_color"])),
                "message_color": str(value.get("message_color", _defaults["message_color"])),
            }
        return {"enabled": False, **_defaults}

    @property
    def document_application(self) -> dict[str, Any]:
        """
        Get normalized document application configuration.

        Enables modern browser-native features: View Transitions API,
        Speculation Rules, native dialogs, CSS state machines.
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["document_application"]
        value = self.config.get("document_application", {})

        if not isinstance(value, dict):
            return {
                "enabled": False,
                "navigation": dict(defaults["navigation"]),
                "speculation": dict(defaults["speculation"]),
                "interactivity": dict(defaults["interactivity"]),
                "features": {},
            }

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

        Provides Wikipedia-style hover cards for internal links.
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["link_previews"]
        value = self.config.get("link_previews", {})

        if not isinstance(value, dict):
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
                    "include_selectors": defaults["include_selectors"],
                    "exclude_selectors": defaults["exclude_selectors"],
                    "allowed_hosts": defaults["allowed_hosts"],
                    "allowed_schemes": defaults["allowed_schemes"],
                    "host_failure_threshold": defaults["host_failure_threshold"],
                    "show_dead_links": defaults["show_dead_links"],
                }
            return dict(defaults)

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
            "allowed_hosts": value.get("allowed_hosts", defaults["allowed_hosts"]),
            "allowed_schemes": value.get("allowed_schemes", defaults["allowed_schemes"]),
            "host_failure_threshold": value.get(
                "host_failure_threshold", defaults["host_failure_threshold"]
            ),
            "show_dead_links": value.get("show_dead_links", defaults["show_dead_links"]),
        }

    def _compute_config_hash(self) -> None:
        """Compute and cache the configuration hash (backward compat)."""
        from bengal.config.hash import compute_config_hash

        self._config_hash = compute_config_hash(self.config)
        emit_diagnostic(
            self,
            "debug",
            "config_hash_computed",
            hash=self._config_hash[:8] if self._config_hash else "none",
        )

    @property
    def indexes(self) -> QueryIndexRegistry:
        """Access to query indexes for O(1) page lookups."""
        if self._query_registry is None:
            with self._init_lock:
                if self._query_registry is None:
                    from bengal.cache.query_index_registry import QueryIndexRegistry

                    self._query_registry = QueryIndexRegistry(
                        cast("SiteLike", self), self.paths.indexes_dir
                    )
        return self._query_registry

    @property
    def registry(self) -> ContentRegistry:
        """
        Content registry for O(1) page/section lookups.

        Provides centralized access to content lookups without scanning
        hierarchies. Initialized lazily on first access.

        Returns:
            ContentRegistry instance

        Example:
            page = site.registry.get_page(path)
            section = site.registry.get_section_by_url("/api/")
        """
        if self._registry is None:
            with self._init_lock:
                if self._registry is None:
                    _reg = ContentRegistry()
                    _reg.set_root_path(self.root_path)
                    _reg.url_ownership = self.url_registry
                    self._registry = _reg
        return self._registry

    # =========================================================================
    # FACTORY METHODS (module-level functions attached as classmethods)
    # =========================================================================

    @classmethod
    def from_config(
        cls,
        root_path: Path,
        config_path: Path | None = None,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Self:
        """
        Create a Site instance from configuration.

        This is the PREFERRED way to create a Site - it loads configuration
        from config/ directory or single config file and applies all settings.

        Args:
            root_path: Root directory of the site (Path object)
            config_path: Optional explicit path to config file (Path object)
            environment: Environment name (e.g., 'production', 'local')
            profile: Profile name (e.g., 'writer', 'dev')

        Returns:
            Configured Site instance with all settings loaded

        Examples:
            site = Site.from_config(Path('/path/to/site'))
            site = Site.from_config(Path('/path'), environment='production')

        For Testing:
            Use Site.for_testing() instead for test scenarios.
        """
        return from_config(cls, root_path, config_path, environment, profile)

    @classmethod
    def for_testing(
        cls, root_path: Path | None = None, config: dict[str, Any] | None = None
    ) -> Self:
        """
        Create a Site instance for testing without requiring a config file.

        Args:
            root_path: Root directory of the test site (defaults to current dir)
            config: Configuration dictionary (defaults to minimal config)

        Returns:
            Configured Site instance ready for testing

        Example:
            site = Site.for_testing()
            site = Site.for_testing(config={'site': {'title': 'Test'}})
        """
        return for_testing(cls, root_path, config)

    # =========================================================================
    # VERSIONING (delegated to VersionService)
    # =========================================================================

    @property
    def versioning_enabled(self) -> bool:
        """Whether versioned documentation is enabled."""
        return self._version_service.versioning_enabled if self._version_service else False

    @property
    def versions(self) -> list[dict[str, Any]]:
        """Available documentation versions."""
        return self._version_service.versions if self._version_service else []

    @property
    def latest_version(self) -> dict[str, Any] | None:
        """Latest documentation version."""
        return self._version_service.latest_version if self._version_service else None

    def get_version(self, version_id: str) -> Version | None:
        """Get version by ID or alias."""
        return self._version_service.get_version(version_id) if self._version_service else None

    def invalidate_version_caches(self) -> None:
        """Clear cached version data."""
        if self._version_service:
            self._version_service.invalidate_caches()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def get_version_target_url(
        self, page: PageLike | None, target_version: dict[str, Any] | None
    ) -> str:
        """
        Get the best URL for a page in the target version.

        Computes a fallback cascade at build time:
        1. If exact equivalent page exists → return that URL
        2. If section index exists → return section index URL
        3. Otherwise → return version root URL

        This is engine-agnostic and works with any template engine (Jinja2,
        Mako, or any BYORenderer).

        Args:
            page: Current page object (may be None for edge cases)
            target_version: Target version dict with 'id', 'url_prefix', 'latest' keys

        Returns:
            Best URL to navigate to (guaranteed to exist, never 404)

        Example (Jinja2):
            {% for v in versions %}
            <option data-target="{{ site.get_version_target_url(page, v) }}">
              {{ v.label }}
            </option>
            {% endfor %}

        Example (Mako):
            % for v in versions:
            <option data-target="${site.get_version_target_url(page, v)}">
              ${v['label']}
            </option>
            % endfor
        """
        # Delegate to core logic (engine-agnostic pure Python)
        from bengal.rendering.template_functions.version_url import (
            get_version_target_url as _get_version_target_url,
        )

        return _get_version_target_url(page, target_version, cast("SiteLike", self))

    def __repr__(self) -> str:
        pages = len(self.pages)
        sections = len(self.sections)
        assets = len(self.assets)
        return f"Site(pages={pages}, sections={sections}, assets={assets})"

    # =========================================================================
    # VALIDATION (inlined from SiteValidationMixin)
    # =========================================================================

    def validate_no_url_collisions(self, *, strict: bool = False) -> list[str]:
        """
        Detect when multiple pages output to the same URL.

        This method catches URL collisions early during the build process,
        preventing silent overwrites that cause broken navigation.

        Uses URLRegistry if available for enhanced ownership context, otherwise
        falls back to page iteration if URLRegistry is not available.

        Args:
            strict: If True, raise ValueError on collision instead of warning.
                   Set to True when site config has strict_mode=True.

        Returns:
            List of collision warning messages (empty if no collisions)

        Raises:
            ValueError: If strict=True and collisions are detected

        Example:
            >>> collisions = site.validate_no_url_collisions()
            >>> if collisions:
            ...     for msg in collisions:
            ...         print(f"Warning: {msg}")

        Note:
            This is a proactive check during Phase 12 (Update Pages List) that
            catches issues before they cause broken navigation.

        See Also:
            - bengal/health/validators/url_collisions.py: Health check validator
        """
        collisions: list[str] = []

        # Use registry if available (provides ownership context)
        if hasattr(self, "url_registry") and self.url_registry:
            # Check for duplicate URLs in pages (registry tracks all claims, including non-page)
            urls_seen: dict[str, str] = {}  # url -> source description

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    # Get ownership context from registry
                    claim = self.url_registry.get_claim(url)
                    owner_info = f" ({claim.owner}, priority {claim.priority})" if claim else ""

                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}{owner_info}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    # Emit diagnostic for orchestrators to surface
                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source
        else:
            # Fallback: iterate pages
            urls_seen = {}  # url -> source description

            for page in self.pages:
                url = page._path
                source = str(getattr(page, "source_path", page.title))

                if url in urls_seen:
                    msg = (
                        f"URL collision detected: {url}\n"
                        f"  Already claimed by: {urls_seen[url]}\n"
                        f"  Also claimed by: {source}\n"
                        f"Tip: Check for duplicate slugs or conflicting autodoc output"
                    )
                    collisions.append(msg)

                    # Emit diagnostic for orchestrators to surface
                    emit_diagnostic(
                        self,
                        "warning",
                        "url_collision",
                        url=url,
                        first_source=urls_seen[url],
                        second_source=source,
                    )
                else:
                    urls_seen[url] = source

        if collisions and strict:
            from bengal.errors import BengalContentError, ErrorCode

            raise BengalContentError(
                "URL collisions detected (strict mode):\n\n" + "\n\n".join(collisions),
                code=ErrorCode.D005,
                suggestion=(
                    "Check for duplicate slugs, conflicting autodoc output, "
                    "or use different URLs for conflicting pages"
                ),
            )

        return collisions

    # =========================================================================
    # DATA LOADING (inlined from SiteDataMixin)
    # =========================================================================

    def _load_data_directory(self) -> DotDict:
        """
        Load all data files from the data/ directory into site.data.

        Delegates file scanning to bengal.services.data.scan_data_directory(),
        then wraps the result in DotDict for template dot-access compatibility.

        Example:
            data/resume.yaml -> site.data.resume
            data/team/members.json -> site.data.team.members

        Returns:
            DotDict with loaded data accessible via dot notation
        """
        from bengal.services.data import scan_data_directory
        from bengal.utils.primitives.dotdict import DotDict, wrap_data

        data, _source_files = scan_data_directory(self.root_path)
        if not data:
            return DotDict()

        return wrap_data(data)

    # =========================================================================
    # SECTION REGISTRY (inlined from SiteSectionRegistryMixin)
    # =========================================================================

    def get_section_by_path(self, path: Path | str) -> SectionLike | None:
        """
        Look up a section by its path (O(1) operation).

        Args:
            path: Section path (absolute, relative to content/, or relative to root)

        Returns:
            Section object if found, None otherwise
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

        section = self.registry.get_section(path)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_registry",
                path=str(path),
                registry_size=self.registry.section_count,
            )

        return section

    def get_section_by_url(self, url: str) -> SectionLike | None:
        """
        Look up a section by its relative URL (O(1) operation).

        Args:
            url: Section relative URL (e.g., "/api/", "/api/core/")

        Returns:
            Section object if found, None otherwise
        """
        section = self.registry.get_section_by_url(url)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_url_registry",
                url=url,
                registry_size=self.registry.section_count,
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registry for path-based and URL-based lookups.

        Populates ContentRegistry with all sections (recursive).
        Must be called after discover_content().
        """
        start = time.time()

        self.registry._sections_by_path.clear()
        self.registry._sections_by_url.clear()

        for section in self.sections:
            self.registry.register_sections_recursive(section)

        self.registry.increment_epoch()

        elapsed_ms = (time.time() - start) * 1000

        emit_diagnostic(
            self,
            "debug",
            "section_registry_built",
            sections=self.registry.section_count,
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / self.registry.section_count):.2f}"
            if self.registry.section_count
            else "0",
        )

    # =========================================================================
    # CONTENT & ASSET DISCOVERY (inlined from SiteDiscoveryMixin)
    # =========================================================================

    def discover_content(self, content_dir: Path | None = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Scans the content directory recursively, creating Page and Section
        objects for all markdown files and organizing them into a hierarchy.

        Args:
            content_dir: Content directory path (defaults to root_path/content)
        """
        if content_dir is None:
            content_dir = self.root_path / "content"

        if not content_dir.exists():
            build_cfg = self.config.get("build", {}) if isinstance(self.config, dict) else {}
            if build_cfg.get("strict_mode", False):
                from bengal.errors import BengalConfigError, ErrorCode

                raise BengalConfigError(
                    f"Content directory not found: {content_dir}\n"
                    f"Strict mode is enabled — missing content directory is an error.",
                    code=ErrorCode.C003,
                    suggestion=f"Create the directory at '{content_dir}', or check "
                    f"'build.content_dir' in your config",
                )
            emit_diagnostic(self, "warning", "content_dir_not_found", path=str(content_dir))
            import warnings

            warnings.warn(
                f"Content directory not found: {content_dir} — "
                f"site will have zero pages. Check 'build.content_dir' in your config.",
                stacklevel=2,
            )
            return

        from bengal.collections import load_collections
        from bengal.content.discovery.content_discovery import ContentDiscovery

        collections = load_collections(self.root_path)

        build_config = self.config.get("build", {}) if isinstance(self.config, dict) else {}
        strict_validation = build_config.get("strict_collections", False)

        discovery = ContentDiscovery(
            content_dir,
            site=self,
            collections=collections,
            strict_validation=strict_validation,
        )
        self.sections, self.pages = discovery.discover()

        # MUST come before _setup_page_references (registry needed for lookups)
        self.register_sections()
        self._setup_page_references()
        self._validate_page_section_references()
        self._apply_cascades()
        # Set output paths for all pages immediately after discovery
        self._set_output_paths()
        # Detect features for CSS optimization (mermaid, data_tables, etc.)
        self._detect_features()

    def _set_output_paths(self) -> None:
        """
        Set output paths for all discovered pages.

        This must be called after discovery and cascade application but before
        any code tries to access page.href (which depends on output_path).
        """
        from bengal.utils.paths.url_strategy import URLStrategy

        for page in self.pages:
            # Skip if already set (e.g., generated pages)
            if page.output_path:
                continue

            # Compute output path using centralized strategy for regular pages
            page.output_path = URLStrategy.compute_regular_page_output_path(
                page, cast("SiteLike", self)
            )

            # Claim URL in registry for ownership enforcement
            # Priority 100 = user content (highest priority)
            if hasattr(self, "url_registry") and self.url_registry:
                try:
                    url = URLStrategy.url_from_output_path(page.output_path, cast("SiteLike", self))
                    source = str(getattr(page, "source_path", page.title))
                    version = getattr(page, "version", None)
                    lang = getattr(page, "lang", None)
                    self.url_registry.claim(
                        url=url,
                        owner="content",
                        source=source,
                        priority=100,  # User content always wins
                        version=version,
                        lang=lang,
                    )
                except Exception:
                    # Don't fail discovery on registry errors (graceful degradation)
                    pass

    def _detect_features(self) -> None:
        """
        Detect CSS-requiring features in page content.

        Scans page content for features like mermaid diagrams, data tables,
        and graph visualizations. Populates site.features_detected for use
        by the CSSOptimizer during asset processing.
        """
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        for page in self.pages:
            # Detect features in page content
            features = detector.detect_features_in_page(page)
            # Prefer BuildState (fresh each build), fall back to Site field
            _bs = getattr(self, "_current_build_state", None)
            target = _bs.features_detected if _bs is not None else self.features_detected
            target.update(features)

        # Also check config for explicitly enabled features
        config = self.config
        _bs = getattr(self, "_current_build_state", None)
        target = _bs.features_detected if _bs is not None else self.features_detected

        # Search enabled?
        if config.get("search", {}).get("enabled", False):
            target.add("search")

        # Graph enabled?
        if config.get("graph", {}).get("enabled", False):
            target.add("graph")

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Scans both theme assets (from theme inheritance chain) and site assets
        (from assets/ directory). Theme assets are discovered first (lower priority),
        then site assets (higher priority, can override theme assets).

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.content.discovery.asset_discovery import AssetDiscovery
        from bengal.services.theme import get_theme_assets_chain

        self.assets = []

        # Theme assets first (lower priority), then site assets (higher priority)
        if self.theme:
            for theme_dir in get_theme_assets_chain(self.root_path, self.theme):
                if theme_dir and theme_dir.exists():
                    theme_discovery = AssetDiscovery(theme_dir)
                    self.assets.extend(theme_discovery.discover())

        # Theme library provider assets (between theme and site priority)
        self._discover_provider_assets()

        if assets_dir is None:
            assets_dir = self.root_path / "assets"

        if assets_dir.exists():
            emit_diagnostic(self, "debug", "discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            emit_diagnostic(self, "warning", "assets_dir_not_found", path=str(assets_dir))

        # Deduplicate by output path: later entries override earlier (site > child theme > parents)
        if self.assets:
            dedup: dict[str, Asset] = {}
            order: list[str] = []
            for asset in self.assets:
                key = str(asset.output_path) if asset.output_path else str(asset.source_path.name)
                if key in dedup:
                    dedup[key] = asset
                else:
                    dedup[key] = asset
                    order.append(key)
            self.assets = [dedup[k] for k in order]

    def _discover_provider_assets(self) -> None:
        """Discover assets from theme library providers.

        Provider assets are namespaced under their package prefix so they
        don't collide with theme-owned assets. For example, chirp_ui assets
        appear as chirp_ui/chirpui.css in the output.
        """
        from bengal.content.discovery.asset_discovery import AssetDiscovery
        from bengal.core.theme.providers import get_provider_asset_dirs, resolve_theme_providers
        from bengal.core.theme.resolution import resolve_theme_chain

        if not self.theme:
            return

        theme_chain = resolve_theme_chain(self.root_path, self.theme)
        providers = resolve_theme_providers(self.root_path, theme_chain)
        if not providers:
            return

        for prefix, asset_root in get_provider_asset_dirs(providers):
            discovery = AssetDiscovery(asset_root)
            for asset in discovery.discover():
                # Namespace the output path under the provider prefix
                if asset.output_path:
                    from pathlib import Path as _Path

                    asset.output_path = _Path(prefix) / asset.output_path
                self.assets.append(asset)

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        Sets _site and _section references on all pages to enable navigation
        properties. Must be called after content discovery and section registry
        building, but before cascade application.
        """
        # Set site reference on all pages (including top-level pages not in sections)
        for page in self.pages:
            page._site = self

        for section in self.sections:
            # Set site reference on section
            section._site = self

            # Set section reference on the section's index page (if it has one)
            if section.index_page:
                section.index_page._section = section

            # Set section reference on all pages in this section
            for page in section.pages:
                page._section = section

            # Recursively set for subsections
            self._setup_section_references(section)

    def _setup_section_references(self, section: SectionLike) -> None:
        """
        Recursively set up references for a section and its subsections.

        Args:
            section: Section to set up references for (processes its subsections)
        """
        for subsection in section.subsections:
            subsection._site = self

            # Set section reference on the subsection's index page (if it has one)
            if subsection.index_page:
                subsection.index_page._section = subsection

            # Set section reference on pages in subsection
            for page in subsection.pages:
                page._section = subsection

            # Recurse into deeper subsections
            self._setup_section_references(subsection)

    def _validate_page_section_references(self) -> None:
        """
        Validate that pages in sections have correct _section references.

        Logs warnings for pages that are in a section's pages list but have
        _section = None, which would cause navigation to fall back to flat mode.
        """
        pages_without_section: list[tuple[PageLike, SectionLike]] = []

        for section in self.sections:
            pages_without_section.extend(
                (page, section) for page in section.pages if page._section is None
            )
            # Check subsections recursively
            self._validate_subsection_references(section, pages_without_section)

        if pages_without_section:
            # Log warning with samples (limit to 5 to avoid log spam)
            sample_pages = [(str(p.source_path), s.name) for p, s in pages_without_section[:5]]
            emit_diagnostic(
                self,
                "warning",
                "pages_missing_section_reference",
                count=len(pages_without_section),
                samples=sample_pages,
                note="These pages are in sections but have _section=None, navigation may be flat",
            )

    def _validate_subsection_references(
        self, section: SectionLike, pages_without_section: list[tuple[PageLike, SectionLike]]
    ) -> None:
        """
        Recursively validate page-section references in subsections.

        Args:
            section: Section to check subsections of
            pages_without_section: List to append (page, expected_section) tuples to
        """
        for subsection in section.subsections:
            pages_without_section.extend(
                (page, subsection) for page in subsection.pages if page._section is None
            )
            # Recurse into deeper subsections
            self._validate_subsection_references(subsection, pages_without_section)

    def _apply_cascades(self) -> None:
        """
        Build cascade snapshot for view-based resolution.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages. This allows setting common metadata (like type, version, or
        visibility) at the section level rather than repeating it on every page.
        """
        # Build immutable cascade snapshot with pre-merged data for O(1) resolution
        # Page.metadata property returns CascadeView using this snapshot
        self.build_cascade_snapshot()

    # =========================================================================
    # LIFECYCLE (inlined from SiteLifecycleMixin)
    # =========================================================================

    def prepare_for_rebuild(self) -> None:
        """
        Reset content and derived-content state for a warm rebuild.

        Called by BuildTrigger before each warm build to ensure clean state
        while preserving config, theme, paths, and other immutable state.
        """
        self.pages = []
        self.sections = []
        self.assets = []

        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        self.xref_index = {}

        self._cascade_snapshot = None

        self.invalidate_page_caches()
        self.invalidate_regular_pages_cache()
        self.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        self._page_lookup_maps = None

    def build(
        self,
        options: BuildOptions | BuildInput,
    ) -> BuildStats:
        """
        Build the entire site. Delegates to BuildOrchestrator.

        Args:
            options: BuildOptions or BuildInput with all build configuration.

        Returns:
            BuildStats object with build statistics
        """
        from bengal.orchestration import BuildOrchestrator

        orchestrator = BuildOrchestrator(self)
        return orchestrator.build(options)

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        version_scope: str | None = None,
    ) -> None:
        """
        Start a development server.

        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
            auto_port: Whether to automatically find an available port
            open_browser: Whether to automatically open the browser
            version_scope: Focus rebuilds on a single version
        """
        from bengal.server.dev_server import DevServer

        server = DevServer(
            self,
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            version_scope=version_scope,
        )
        server.start()

    def clean(self) -> None:
        """
        Clean the output directory by removing all generated files.
        """
        if self.output_dir.exists():
            emit_diagnostic(self, "debug", "cleaning_output_dir", path=str(self.output_dir))
            self._rmtree_robust(self.output_dir)
            emit_diagnostic(self, "debug", "output_dir_cleaned", path=str(self.output_dir))
        else:
            emit_diagnostic(self, "debug", "output_dir_does_not_exist", path=str(self.output_dir))

    @staticmethod
    def _rmtree_robust(path: Path, max_retries: int = 3) -> None:
        """Remove directory tree with retry logic for transient filesystem errors."""
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(path, max_retries=max_retries, caller="site")

    def reset_ephemeral_state(self) -> None:
        """
        Clear ephemeral/derived state that should not persist between builds.

        For long-lived Site instances (e.g., dev server) to avoid stale
        object references across rebuilds.
        """
        emit_diagnostic(self, "debug", "site_reset_ephemeral_state", site_root=str(self.root_path))

        self.pages = []
        self.sections = []
        self.assets = []

        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}

        self.xref_index = {}

        self.invalidate_page_caches()
        self.registry.clear()

        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        self.__dict__.pop("indexes", None)

        self._theme_obj = None
        self._page_lookup_maps = None
        self._bengal_theme_chain_cache = None
        self._bengal_template_dirs_cache = None
        self._bengal_template_metadata_cache = None
        self._discovery_breakdown_ms = None
        self._asset_manifest_fallbacks_global.clear()
        self.features_detected.clear()

        if hasattr(self, "_kida_asset_manifest_cache"):
            delattr(self, "_kida_asset_manifest_cache")

        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        from bengal.rendering.assets import reset_asset_manifest

        reset_asset_manifest()

    @property
    def build_state(self) -> BuildState | None:
        """Current build state (None outside build context)."""
        return self._current_build_state

    def set_build_state(self, state: BuildState | None) -> None:
        """Set current build state (called by BuildOrchestrator)."""
        self._current_build_state = state

    # =========================================================================
    # PAGE CACHES (delegated to PageCacheManager)
    # =========================================================================

    @property
    def regular_pages(self) -> list[PageLike]:
        """Regular content pages (excludes generated taxonomy/archive pages)."""
        return self._page_cache.regular_pages

    @property
    def generated_pages(self) -> list[PageLike]:
        """Generated pages (taxonomy, archive, pagination)."""
        return self._page_cache.generated_pages

    @property
    def listable_pages(self) -> list[PageLike]:
        """Pages eligible for public listings (excludes hidden/draft)."""
        return self._page_cache.listable_pages

    def get_page_path_map(self) -> dict[str, PageLike]:
        """Cached string-keyed page lookup map for O(1) resolution."""
        return self._page_cache.get_page_path_map()

    @property
    def page_by_source_path(self) -> dict[Path, PageLike]:
        """O(1) page lookup by source Path (shared across orchestrators)."""
        return self._page_cache.page_by_source_path

    @property
    def root_section(self) -> SectionLike:
        """Root section of the content tree (first parentless section)."""
        for section in self.sections:
            if section.parent is None:
                return section
        # Fallback: find sections that aren't children of other sections
        child_ids = {id(sub) for s in self.sections for sub in s.subsections}
        for section in self.sections:
            if id(section) not in child_ids:
                return section
        msg = "No root section found — site has no sections"
        raise ValueError(msg)

    def invalidate_page_caches(self) -> None:
        """Clear all page caches. Call after adding/removing pages."""
        self._page_cache.invalidate()

    def invalidate_regular_pages_cache(self) -> None:
        """Clear only the regular_pages cache."""
        self._page_cache.invalidate_regular()


__all__ = [
    "Site",
]
