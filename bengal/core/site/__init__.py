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
properties.py: SitePropertiesMixin (config accessors)
config_normalized.py: SiteNormalizedConfigMixin (normalized config)
versioning.py: SiteVersioningMixin (version support)
caches.py: SiteCachesMixin (page cache management)
discovery.py: SiteDiscoveryMixin (content/asset discovery)
cascade.py: SiteCascadeMixin (cascade metadata)
lifecycle.py: SiteLifecycleMixin (warm rebuild state reset)
operations.py: SiteOperationsMixin (build/serve/clean)
section_registry.py: SiteSectionRegistryMixin (section lookups)
validation.py: SiteValidationMixin (URL validation)
helpers.py: SiteHelpersMixin (ergonomic methods)
data_loading.py: SiteDataMixin (data directory loading)
factory.py: Factory functions (from_config, for_testing)

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

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Self

from bengal.core.asset import Asset
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.page import Page
from bengal.core.registry import ContentRegistry
from bengal.core.section import Section
from bengal.core.theme import Theme
from bengal.core.url_ownership import URLRegistry
from bengal.core.version import Version, VersionConfig
from bengal.icons import resolver as icon_resolver

# Import mixins
from .caches import SiteCachesMixin
from .cascade import SiteCascadeMixin
from .config_normalized import SiteNormalizedConfigMixin
from .data_loading import SiteDataMixin
from .discovery import SiteDiscoveryMixin
from .factory import for_testing, from_config
from .helpers import SiteHelpersMixin
from .lifecycle import SiteLifecycleMixin
from .operations import SiteOperationsMixin
from .properties import SitePropertiesMixin
from .section_registry import SiteSectionRegistryMixin
from .validation import SiteValidationMixin
from .versioning import SiteVersioningMixin

if TYPE_CHECKING:
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.orchestration.build_state import BuildState
    from bengal.utils.primitives.dotdict import DotDict


# Thread-safe output lock for parallel processing.
_print_lock = Lock()


@dataclass
class Site(
    SitePropertiesMixin,
    SiteNormalizedConfigMixin,
    SiteVersioningMixin,
    SiteCachesMixin,
    SiteDiscoveryMixin,
    SiteCascadeMixin,
    SiteLifecycleMixin,
    SiteOperationsMixin,
    SiteSectionRegistryMixin,
    SiteValidationMixin,
    SiteHelpersMixin,
    SiteDataMixin,
):
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
    pages: list[Page] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
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
    data: Any = field(default_factory=dict)
    # Runtime flag: True when running in dev server mode (not persisted to config).
    dev_mode: bool = False

    # Versioning configuration (loaded from config during __post_init__)
    version_config: VersionConfig = field(default_factory=VersionConfig)
    # Current version context for rendering (set per page during rendering)
    current_version: Version | None = None

    # Private caches for expensive properties (invalidated when pages change)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _generated_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _listable_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    # Page path map cache for O(1) page resolution (used by resolve_pages template function)
    _page_path_map: dict[str, Page] | None = field(default=None, repr=False, init=False)
    _page_path_map_version: int = field(default=-1, repr=False, init=False)
    # Page source path lookup cache for O(1) page resolution (shared by orchestrators)
    _page_by_source_path_cache: dict[Path, Page] | None = field(
        default=None, repr=False, init=False
    )
    _theme_obj: Theme | None = field(default=None, repr=False, init=False)
    _query_registry: Any = field(default=None, repr=False, init=False)

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

    # Dynamic runtime attributes (set by various orchestrators)
    # Menu metadata for dev server menu items (set by MenuOrchestrator)
    _dev_menu_metadata: dict[str, Any] | None = field(default=None, repr=False, init=False)
    # Affected tags during incremental builds (set by TaxonomyOrchestrator)
    _affected_tags: set[str] = field(default_factory=set, repr=False, init=False)
    # Page lookup maps for efficient page resolution (set by template functions)
    _page_lookup_maps: dict[str, dict[str, Page]] | None = field(
        default=None, repr=False, init=False
    )
    # Last build stats for health check access (set by finalization phase)
    _last_build_stats: dict[str, Any] | None = field(default=None, repr=False, init=False)
    # Template parser cache (set by get_page template function)
    _template_parser: Any = field(default=None, repr=False, init=False)

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
    _asset_manifest_previous: Any = field(default=None, repr=False, init=False)

    # Thread-safe set of fallback warnings to avoid duplicate warnings
    _asset_manifest_fallbacks_global: set[str] = field(default_factory=set, repr=False, init=False)

    # Lock for thread-safe fallback set access (initialized in __post_init__)
    _asset_manifest_fallbacks_lock: Any = field(default=None, repr=False, init=False)

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
    _cascade_snapshot: Any = field(default=None, repr=False, init=False)

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

        # Theme.from_config expects a dict; use .raw if available (Config object)
        # else use directly (plain dict)
        config_dict: dict[str, Any]
        if hasattr(self.config, "raw"):
            config_dict = self.config.raw  # type: ignore[union-attr]
        elif isinstance(self.config, dict):
            config_dict = self.config
        else:
            config_dict = {}
        self._theme_obj = Theme.from_config(
            config_dict,
            root_path=self.root_path,
            diagnostics_site=self,
        )

        # Initialize theme-aware icon resolver for all icon consumers
        # (template functions, inline icon plugin, directives)
        icon_resolver.initialize(self)

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

        # Initialize versioning configuration
        # VersionConfig.from_config expects a dict; config_dict already computed above
        self.version_config = VersionConfig.from_config(config_dict)
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
            self._registry = ContentRegistry()
            self._registry.set_root_path(self.root_path)
            self._registry.url_ownership = self.url_registry
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


__all__ = [
    "Site",
]
