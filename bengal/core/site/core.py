"""
Core Site dataclass for Bengal SSG.

Provides the Site class—the central container coordinating pages, sections,
assets, themes, and the build process. Site is the primary entry point for
building and serving Bengal sites.

Public API:
Site: Central container with build(), serve(), and clean() methods

Key Responsibilities:
Content Organization: Manages pages, sections, and assets in hierarchy
Build Coordination: site.build() orchestrates full build pipeline
Dev Server: site.serve() provides live-reload development server
Theme Integration: Uses bengal.services.theme for theme resolution
Query Interfaces: Provides taxonomy, menu, and page query APIs

Architecture (RFC: Aggressive Cleanup):
All mixin functionality is now inlined directly into Site:
- Properties: Config accessors (title, baseurl, author, etc.)
- Page Caches: Cached page lists (regular_pages, generated_pages, etc.)
- Content Discovery: discover_content(), discover_assets()
- Data Loading: _load_data_directory()
- Section Registry: O(1) section lookups via registry

Factory Methods:
Site.from_config() and Site.for_testing() are module-level functions
re-exported as classmethods for backward compatibility.

Related Services (RFC: Snapshot-Enabled v2):
- bengal.services.theme: Pure functions for theme resolution
- bengal.services.query: Pure functions for content queries
- bengal.services.data: Pure functions for data loading

Caching Strategy:
Expensive computations (page lists, section lookups) are cached and
invalidated when content changes via invalidate_page_caches().

Related Packages:
bengal.orchestration.build: Build phase orchestration
bengal.rendering.template_engine: Template rendering with Site context
bengal.cache.build_cache: Build state persistence

"""

from __future__ import annotations

import time
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

if TYPE_CHECKING:
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats import BuildStats
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
    # RUNTIME CACHES (Phase B: Formalized from dynamic injection)
    # =========================================================================

    # --- Asset Manifest State ---
    # Previous manifest for incremental asset comparison (set by AssetOrchestrator)
    _asset_manifest_previous: Any = field(default=None, repr=False, init=False)

    # Thread-safe set of fallback warnings to avoid duplicate warnings
    _asset_manifest_fallbacks_global: set[str] = field(default_factory=set, repr=False, init=False)

    # Lock for thread-safe fallback set access (initialized in __post_init__)
    _asset_manifest_fallbacks_lock: Any = field(default=None, repr=False, init=False)

    # --- Template Environment Caches ---
    # Theme chain cache for template resolution
    _bengal_theme_chain_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)

    # Template directories cache
    _bengal_template_dirs_cache: dict[str, Any] | None = field(default=None, repr=False, init=False)

    # Template metadata cache
    _bengal_template_metadata_cache: dict[str, Any] | None = field(
        default=None, repr=False, init=False
    )

    # --- Discovery State ---
    # Discovery timing breakdown (set by ContentOrchestrator)
    _discovery_breakdown_ms: dict[str, float] | None = field(default=None, repr=False, init=False)

    # Features detected during content discovery (mermaid, graph, data_tables, etc.)
    # Used by CSSOptimizer to include only CSS for features actually in use.
    features_detected: set[str] = field(default_factory=set, repr=False, init=False)

    # --- Cascade Snapshot ---
    # Immutable cascade data computed once per build for thread-safe access.
    # See: bengal/core/cascade_snapshot.py
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
    # FACTORY METHODS (module-level functions re-exported as classmethods)
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

        Config Loading (Priority):
            1. config/ directory (if exists) - Environment-aware, profile-native
            2. bengal.yaml / bengal.toml (single file) - Traditional
            3. Auto-detect environment from platform (Netlify, Vercel, GitHub Actions)

        Directory Structure (Recommended):
            config/
            ├── _default/          # Base config
            │   ├── site.yaml
            │   ├── build.yaml
            │   └── features.yaml
            ├── environments/      # Environment overrides
            │   ├── local.yaml
            │   ├── preview.yaml
            │   └── production.yaml
            └── profiles/          # Build profiles
                ├── writer.yaml
                ├── theme-dev.yaml
                └── dev.yaml

        Important Config Sections:
            - [site]: title, baseurl, author, etc.
            - [build]: parallel, max_workers, incremental, etc.
            - [markdown]: parser selection ('patitas' is default)
            - [features]: rss, sitemap, search, json, etc.
            - [taxonomies]: tags, categories, series

        Args:
            root_path: Root directory of the site (Path object)
            config_path: Optional explicit path to config file (Path object)
                        Only used for single-file configs, ignored if config/ exists
            environment: Environment name (e.g., 'production', 'local')
                        Auto-detected if not specified (Netlify, Vercel, GitHub)
            profile: Profile name (e.g., 'writer', 'dev')
                        Optional, only applies if config/ directory exists

        Returns:
            Configured Site instance with all settings loaded

        Examples:
            # Auto-detect config (prefers config/ directory)
            site = Site.from_config(Path('/path/to/site'))

            # Explicit environment
            site = Site.from_config(
                Path('/path/to/site'),
                environment='production'
            )

            # With profile
            site = Site.from_config(
                Path('/path/to/site'),
                environment='local',
                profile='dev'
            )

        For Testing:
            If you need a Site for testing, use Site.for_testing() instead.
            It creates a minimal Site without requiring a config file.

        See Also:
            - Site() - Direct constructor for advanced use cases
            - Site.for_testing() - Factory for test sites
        """
        from bengal.config.unified_loader import UnifiedConfigLoader

        loader = UnifiedConfigLoader()
        config = loader.load(root_path, environment=environment, profile=profile)

        return cls(root_path=root_path, config=config)

    @classmethod
    def for_testing(
        cls, root_path: Path | None = None, config: dict[str, Any] | None = None
    ) -> Self:
        """
        Create a Site instance for testing without requiring a config file.

        This is a convenience factory for unit tests and integration tests
        that need a Site object with custom configuration.

        Args:
            root_path: Root directory of the test site (defaults to current dir)
            config: Configuration dictionary (defaults to minimal config)

        Returns:
            Configured Site instance ready for testing

        Example:
            # Minimal test site
            site = Site.for_testing()

            # Test site with custom root path
            site = Site.for_testing(Path('/tmp/test_site'))

            # Test site with custom config
            config = {'site': {'title': 'My Test Site'}}
            site = Site.for_testing(config=config)

        Note:
            This bypasses config file loading, so you control all settings.
            Perfect for unit tests that need predictable behavior.
        """
        if root_path is None:
            root_path = Path(".")

        if config is None:
            config = {
                "site": {"title": "Test Site"},
                "build": {"output_dir": "public"},
            }

        return cls(root_path=root_path, config=config)

    # =========================================================================
    # CORE METHODS
    # =========================================================================

    def build(
        self,
        options: BuildOptions,
    ) -> BuildStats:
        """
        Build the entire site.

        Delegates to BuildOrchestrator for actual build process.

        Args:
            options: BuildOptions dataclass with all build configuration.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(strict=True)
            >>> stats = site.build(options)
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
            auto_port: Whether to automatically find an available port if the specified one is
                       in use
            open_browser: Whether to automatically open the browser
            version_scope: Focus rebuilds on a single version (e.g., "v2", "latest").
                If None, all versions are rebuilt on changes.
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

        Useful for starting fresh or troubleshooting build issues.

        Example:
            >>> site = Site.from_config(Path('/path/to/site'))
            >>> site.clean()  # Remove all files in public/
            >>> site.build()  # Rebuild from scratch
        """
        if self.output_dir.exists():
            # Use debug level to avoid noise in clean command output
            emit_diagnostic(self, "debug", "cleaning_output_dir", path=str(self.output_dir))
            self._rmtree_robust(self.output_dir)
            emit_diagnostic(self, "debug", "output_dir_cleaned", path=str(self.output_dir))
        else:
            emit_diagnostic(self, "debug", "output_dir_does_not_exist", path=str(self.output_dir))

    @staticmethod
    def _rmtree_robust(path: Path, max_retries: int = 3) -> None:
        """
        Remove directory tree with retry logic for transient filesystem errors.

        Delegates to bengal.utils.file_io.rmtree_robust for the actual
        implementation.

        Args:
            path: Directory to remove
            max_retries: Number of retry attempts (default 3)

        Raises:
            OSError: If deletion fails after all retries
        """
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(path, max_retries=max_retries, caller="site")

    def reset_ephemeral_state(self) -> None:
        """
        Clear ephemeral/derived state that should not persist between builds.

        This method is intended for long-lived Site instances (e.g., dev server)
        to avoid stale object references across rebuilds.

        Persistence contract:
        - Persist: root_path, config, theme, output_dir, build_time
        - Clear: pages, sections, assets
        - Clear derived: taxonomies, menu, menu_builders, xref_index (if present)
        - Clear caches: cached page lists
        """
        emit_diagnostic(self, "debug", "site_reset_ephemeral_state", site_root=str(self.root_path))

        # Content to be rediscovered
        self.pages = []
        self.sections = []
        self.assets = []

        # Derived structures (contain object references)
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}

        # Indices (rebuilt from pages)
        self.xref_index = {}

        # Cached properties
        self.invalidate_page_caches()

        # Clear content registry (includes section registries and URL ownership)
        self.registry.clear()

        # Reset URL registry and reconnect with content registry
        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        # Reset query registry (clear cached_property)
        self.__dict__.pop("indexes", None)

        # Reset lookup maps
        self._page_lookup_maps = None

        # Reset theme if needed (will be reloaded on first access)
        self._theme_obj = None

        # Runtime caches (Phase B fields)
        self._bengal_theme_chain_cache = None
        self._bengal_template_dirs_cache = None
        self._bengal_template_metadata_cache = None
        self._discovery_breakdown_ms = None
        self._asset_manifest_fallbacks_global.clear()

        # Clear Kida adapter's asset manifest cache (used for fingerprint resolution)
        if hasattr(self, "_kida_asset_manifest_cache"):
            delattr(self, "_kida_asset_manifest_cache")

        # CSS optimization state
        self.features_detected.clear()

        # Clear thread-local rendering caches (Phase B formalization)
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        # Clear thread-local asset manifest context (RFC: rfc-global-build-state-dependencies)
        from bengal.rendering.assets import reset_asset_manifest

        reset_asset_manifest()

    # =========================================================================
    # ERGONOMIC HELPER METHODS (for theme developers)
    # =========================================================================

    def get_section_by_name(self, name: str) -> Section | None:
        """
        Get a section by its name.

        Searches top-level sections for a matching name. Returns the first
        match or None if not found.

        Args:
            name: Section name to find (e.g., 'blog', 'docs', 'api')

        Returns:
            Section if found, None otherwise

        Example:
            {% set blog = site.get_section_by_name('blog') %}
            {% if blog %}
              {{ blog.title }} has {{ blog.pages | length }} posts
            {% endif %}
        """
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def pages_by_section(self, section_name: str) -> list[Page]:
        """
        Get all pages belonging to a section by name.

        Filters site.pages to return only pages whose section matches
        the given name. Useful for archive and taxonomy templates.

        Args:
            section_name: Section name to filter by (e.g., 'blog', 'docs')

        Returns:
            List of pages in that section (empty list if section not found)

        Example:
            {% set blog_posts = site.pages_by_section('blog') %}
            {% for post in blog_posts %}
              <article>{{ post.title }}</article>
            {% endfor %}
        """
        result: list[Page] = []
        for p in self.pages:
            section = getattr(p, "_section", None)
            if section is not None and section.name == section_name:
                result.append(p)
        return result

    def get_version_target_url(
        self, page: Page | None, target_version: dict[str, Any] | None
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

        return _get_version_target_url(page, target_version, self)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        pages = len(self.pages)
        sections = len(self.sections)
        assets = len(self.assets)
        return f"Site(pages={pages}, sections={sections}, assets={assets})"

    # =========================================================================
    # BUILD STATE ACCESS
    # =========================================================================

    @property
    def build_state(self) -> BuildState | None:
        """
        Current build state (None outside build context).

        Returns:
            BuildState during build execution, None otherwise

        Example:
            if site.build_state:
                lock = site.build_state.get_lock("asset_write")
        """
        return self._current_build_state

    def set_build_state(self, state: BuildState | None) -> None:
        """
        Set current build state (called by BuildOrchestrator).

        Args:
            state: BuildState to set, or None to clear

        Note:
            This is called internally by BuildOrchestrator at build start/end.
            Do not call directly unless implementing custom build coordination.
        """
        self._current_build_state = state

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
    # VALIDATION METHODS
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
    # SITE PROPERTIES (inlined from SitePropertiesMixin)
    # =========================================================================

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
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "title", None)
        return self.config.get("site", {}).get("title") or self.config.get("title")

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
        # Support both Config and dict access
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "author", None)
        return self.config.get("site", {}).get("author") or self.config.get("author")

    @property
    def favicon(self) -> str | None:
        """
        Get favicon path from site config.

        Returns:
            Favicon path string from config, or None if not configured
        """
        # Support both Config and dict access
        site_attr = getattr(self.config, "site", None)
        if site_attr is not None:
            return getattr(site_attr, "get", lambda k: None)("favicon")
        return self.config.get("site", {}).get("favicon")

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
        build_attr = getattr(self.config, "build", None)
        if build_attr is not None:
            # ConfigSection - access raw dict
            data_attr = getattr(build_attr, "_data", None)
            return dict(data_attr) if data_attr is not None else {}
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
            {% if site.document_application.enabled %}
            {% if site.document_application.navigation.view_transitions %}
                <meta name="view-transition" content="same-origin">
            {% endif %}
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

        Cross-site previews can be enabled for trusted hosts via allowed_hosts.
        See: plan/rfc-cross-site-xref-link-previews.md

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
                    # Cross-site preview defaults
                    "allowed_hosts": defaults["allowed_hosts"],
                    "allowed_schemes": defaults["allowed_schemes"],
                    "host_failure_threshold": defaults["host_failure_threshold"],
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
            # Cross-site preview configuration (RFC: Cross-Site Link Previews)
            "allowed_hosts": value.get("allowed_hosts", defaults["allowed_hosts"]),
            "allowed_schemes": value.get("allowed_schemes", defaults["allowed_schemes"]),
            "host_failure_threshold": value.get(
                "host_failure_threshold", defaults["host_failure_threshold"]
            ),
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

    # =========================================================================
    # PAGE CACHES (inlined from PageCachesMixin)
    # =========================================================================

    @property
    def regular_pages(self) -> list[Page]:
        """
        Get only regular content pages (excludes generated taxonomy/archive pages).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of regular Page objects (excludes tag pages, archive pages, etc.)

        Example:
            {% for page in site.regular_pages %}
                <article>{{ page.title }}</article>
            {% endfor %}
        """
        if self._regular_pages_cache is not None:
            return self._regular_pages_cache

        self._regular_pages_cache = [p for p in self.pages if not p.metadata.get("_generated")]
        return self._regular_pages_cache

    @property
    def generated_pages(self) -> list[Page]:
        """
        Get only generated pages (taxonomy, archive, pagination pages).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of generated Page objects (tag pages, archive pages, pagination, etc.)

        Example:
            # Check if any tag pages need rebuilding
            for page in site.generated_pages:
                if page.metadata.get("type") == "tag":
                    # ... process tag page
        """
        if self._generated_pages_cache is not None:
            return self._generated_pages_cache

        self._generated_pages_cache = [p for p in self.pages if p.metadata.get("_generated")]
        return self._generated_pages_cache

    @property
    def listable_pages(self) -> list[Page]:
        """
        Get pages that should appear in listings (excludes hidden pages).

        This property respects the visibility system:
        - Excludes pages with `hidden: true`
        - Excludes pages with `visibility.listings: false`
        - Excludes draft pages

        Use this for:
        - "Recent posts" sections
        - Archive pages
        - Category/tag listings
        - Any public-facing page list

        Use `site.pages` when you need ALL pages including hidden ones
        (e.g., for sitemap generation where you filter separately).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of Page objects that should appear in public listings

        Example:
            {% set posts = site.listable_pages | where('section', 'blog') %}
            {% for post in posts | sort_by('date', reverse=true) | limit(5) %}
                <article>{{ post.title }}</article>
            {% endfor %}
        """
        if self._listable_pages_cache is not None:
            return self._listable_pages_cache

        self._listable_pages_cache = [p for p in self.pages if p.in_listings]
        return self._listable_pages_cache

    def get_page_path_map(self) -> dict[str, Page]:
        """
        Get cached page path lookup map for O(1) page resolution.

        Cache is automatically invalidated when page count changes,
        covering add/remove operations in dev server.

        Returns:
            Dictionary mapping source_path strings to Page objects

        Example:
            page_map = site.get_page_path_map()
            page = page_map.get("content/posts/my-post.md")
        """
        current_version = len(self.pages)
        if self._page_path_map is None or self._page_path_map_version != current_version:
            self._page_path_map = {str(p.source_path): p for p in self.pages}
            self._page_path_map_version = current_version
        return self._page_path_map

    @property
    def page_by_source_path(self) -> dict[Path, Page]:
        """
        O(1) page lookup by source path (site-level cache).

        Provides centralized page lookup cache shared across all consumers
        (CascadeTracker, RebuildFilter, ContentOrchestrator). Built lazily
        on first access, invalidated when pages change.

        Returns:
            Dictionary mapping source Path to Page objects

        Performance:
            - First access: O(P) to build cache
            - Subsequent access: O(1)
            - Replaces 3 separate O(P) builds with 1 shared build

        Example:
            page = site.page_by_source_path.get(source_path)

        See Also:
            get_page_path_map(): String-based path map (for template functions)
            invalidate_page_caches(): Clears this cache
        """
        if self._page_by_source_path_cache is None:
            self._page_by_source_path_cache = {p.source_path: p for p in self.pages}
        return self._page_by_source_path_cache

    def invalidate_page_caches(self) -> None:
        """
        Invalidate cached page lists when pages are modified.

        Call this after:
        - Adding/removing pages
        - Modifying page metadata (especially _generated flag or visibility)
        - Any operation that changes the pages list

        This ensures cached properties (regular_pages, generated_pages, listable_pages,
        page_path_map, page_by_source_path) will recompute on next access.
        """
        self._regular_pages_cache = None
        self._generated_pages_cache = None
        self._listable_pages_cache = None
        self._page_path_map = None
        self._page_path_map_version = -1
        self._page_by_source_path_cache = None

    def invalidate_regular_pages_cache(self) -> None:
        """
        Invalidate the regular_pages cache.

        Call this after modifying the pages list or page metadata that affects
        the _generated flag. More specific than invalidate_page_caches() if you
        only need to invalidate regular_pages.

        See Also:
            invalidate_page_caches(): Invalidate all page caches at once
        """
        self._regular_pages_cache = None

    # =========================================================================
    # DATA LOADING (inlined from DataLoadingMixin)
    # =========================================================================

    def _load_data_directory(self) -> DotDict:
        """
        Load all data files from the data/ directory into site.data.

        Supports YAML, JSON, and TOML files. Files are loaded into a nested
        structure based on their path in the data/ directory.

        Example:
            data/resume.yaml → site.data.resume
            data/team/members.json → site.data.team.members

        Returns:
            DotDict with loaded data accessible via dot notation
        """
        from bengal.utils.io.file_io import load_data_file
        from bengal.utils.primitives.dotdict import DotDict, wrap_data

        data_dir = self.root_path / "data"

        if not data_dir.exists():
            emit_diagnostic(self, "debug", "data_directory_not_found", path=str(data_dir))
            return DotDict()

        emit_diagnostic(self, "debug", "loading_data_directory", path=str(data_dir))

        data: dict[str, Any] = {}
        supported_extensions = [".json", ".yaml", ".yml", ".toml"]

        for file_path in data_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix not in supported_extensions:
                continue

            relative = file_path.relative_to(data_dir)
            parts = list(relative.with_suffix("").parts)

            try:
                content = load_data_file(
                    file_path, on_error="return_empty", caller="site_data_loader"
                )

                current = data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current[parts[-1]] = content

                if parts[-1] == "tracks" and isinstance(content, dict):
                    self._validate_tracks_structure(content)

                emit_diagnostic(
                    self,
                    "debug",
                    "data_file_loaded",
                    file=str(relative),
                    key=".".join(parts),
                    size=len(str(content)) if content else 0,
                )

            except Exception as e:
                emit_diagnostic(
                    self,
                    "warning",
                    "data_file_load_failed",
                    file=str(relative),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        wrapped_data: DotDict = wrap_data(data)

        if data:
            emit_diagnostic(
                self,
                "debug",
                "data_directory_loaded",
                files_loaded=len(list(data_dir.rglob("*.*"))),
                top_level_keys=list(data.keys()) if isinstance(data, dict) else [],
            )

        return wrapped_data

    def _validate_tracks_structure(self, tracks_data: dict[str, Any]) -> None:
        """Validate tracks.yaml structure during data loading."""
        if not isinstance(tracks_data, dict):
            emit_diagnostic(
                self,
                "warning",
                "tracks.yaml root must be a dictionary",
                event="tracks_invalid_structure",
            )
            return

        for track_id, track in tracks_data.items():
            if not isinstance(track, dict):
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' must be a dictionary",
                    event="track_invalid_structure",
                    track_id=track_id,
                )
                continue

            if "items" not in track:
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' is missing required 'items' field",
                    event="track_missing_items",
                    track_id=track_id,
                )
                continue

            if not isinstance(track["items"], list):
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' has 'items' field that is not a list",
                    event="track_items_not_list",
                    track_id=track_id,
                )
                continue

            if len(track["items"]) == 0:
                emit_diagnostic(
                    self,
                    "debug",
                    f"Track '{track_id}' has no items",
                    event="track_empty_items",
                    track_id=track_id,
                )

    # =========================================================================
    # SECTION REGISTRY (inlined from SectionRegistryMixin)
    # =========================================================================

    def get_section_by_path(self, path: Path | str) -> Section | None:
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

    def get_section_by_url(self, url: str) -> Section | None:
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
    # CONTENT DISCOVERY (inlined from ContentDiscoveryMixin)
    # =========================================================================

    def discover_content(self, content_dir: Path | None = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.

        Scans the content directory recursively, creating Page and Section
        objects for all markdown files and organizing them into a hierarchy.

        Args:
            content_dir: Content directory path (defaults to root_path/content)

        Example:
            >>> site = Site.from_config(Path('/path/to/site'))
            >>> site.discover_content()
            >>> print(f"Found {len(site.pages)} pages in {len(site.sections)} sections")
        """
        if content_dir is None:
            content_dir = self.root_path / "content"

        if not content_dir.exists():
            emit_diagnostic(self, "warning", "content_dir_not_found", path=str(content_dir))
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
            page.output_path = URLStrategy.compute_regular_page_output_path(page, self)

            # Claim URL in registry for ownership enforcement
            # Priority 100 = user content (highest priority)
            if hasattr(self, "url_registry") and self.url_registry:
                try:
                    url = URLStrategy.url_from_output_path(page.output_path, self)
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
                    # Registry errors will be caught during validation phase
                    pass

    def _detect_features(self) -> None:
        """
        Detect CSS-requiring features in page content.

        Scans page content for features like mermaid diagrams, data tables,
        and graph visualizations. Populates site.features_detected for use
        by the CSSOptimizer during asset processing.

        See Also:
            bengal/orchestration/css_optimizer.py: Consumes detected features
            plan/drafted/rfc-css-tree-shaking.md: Design rationale
        """
        from bengal.core.page.proxy import PageProxy
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        for page in self.pages:
            # Skip PageProxy objects (they may not have content loaded)
            if isinstance(page, PageProxy):
                continue

            # Detect features in page content
            features = detector.detect_features_in_page(page)
            self.features_detected.update(features)

        # Also check config for explicitly enabled features
        config = self.config

        # Search enabled?
        if config.get("search", {}).get("enabled", False):
            self.features_detected.add("search")

        # Graph enabled?
        if config.get("graph", {}).get("enabled", False):
            self.features_detected.add("graph")

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Scans both theme assets (from theme inheritance chain) and site assets
        (from assets/ directory). Theme assets are discovered first (lower priority),
        then site assets (higher priority, can override theme assets). Assets are
        deduplicated by output path with site assets taking precedence.

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets).
                       If None, uses site root_path / "assets"

        Process:
            1. Discover theme assets from inheritance chain (child → parent → default)
            2. Discover site assets from assets_dir
            3. Deduplicate by output path (site assets override theme assets)

        Examples:
            site.discover_assets()  # Discovers from root_path/assets
            site.discover_assets(Path('/custom/assets'))  # Custom assets directory
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

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        Sets _site and _section references on all pages to enable navigation
        properties. Must be called after content discovery and section registry
        building, but before cascade application.

        Process:
            1. Set _site reference on all pages (including top-level pages)
            2. Set _site reference on all sections
            3. Set _section reference on section index pages
            4. Set _section reference on pages based on their location
            5. Recursively process subsections

        Build Ordering Invariant:
            This method must be called after register_sections() to ensure
            the section registry is populated for virtual section URL lookups.

        Called By:
            discover_content() - Automatically called after content discovery

        See Also:
            _setup_section_references(): Sets up section parent-child relationships
            plan/active/rfc-page-section-reference-contract.md
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

    def _setup_section_references(self, section: Section) -> None:
        """
        Recursively set up references for a section and its subsections.

        Sets _site reference on subsections, _section reference on index pages,
        and _section reference on pages within subsections. Recursively
        processes all nested subsections.

        Args:
            section: Section to set up references for (processes its subsections)

        Called By:
            _setup_page_references() - Called for each top-level section

        See Also:
            _setup_page_references(): Main entry point for reference setup
            plan/active/rfc-page-section-reference-contract.md
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

        This validation catches bugs like the virtual section path=None issue
        described in plan/active/rfc-page-section-reference-contract.md.

        Called By:
            discover_content() - After _setup_page_references()
        """
        pages_without_section: list[tuple[Page, Section]] = []

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
        self, section: Section, pages_without_section: list[tuple[Page, Section]]
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
        Apply cascading metadata from sections to their child pages and subsections.

        Section _index.md files can define metadata that automatically applies to all
        descendant pages. This allows setting common metadata (like type, version, or
        visibility) at the section level rather than repeating it on every page.

        Cascade metadata is defined in a section's _index.md frontmatter:

        Example:
            ---
            title: "Products"
            cascade:
              type: "product"
              version: "2.0"
              show_price: true
            ---

        All pages under this section will inherit these values unless they
        define their own values (page values take precedence over cascaded values).

        Implementation:
            1. Build immutable CascadeSnapshot for thread-safe resolution
            2. Apply cascade values to page.metadata for backward compatibility
        """
        # Build immutable cascade snapshot for thread-safe resolution
        self.build_cascade_snapshot()

        # Apply cascade values to page.metadata for backward compatibility
        # This ensures templates using page.metadata.get('cascaded_key') still work
        self._apply_cascade_to_pages()

    def _apply_cascade_to_pages(self) -> None:
        """
        Apply cascade values from snapshot to page.metadata.

        For each page, resolves all cascade values from the snapshot and applies
        them to page.metadata. Page-level values take precedence over cascades.
        """

        content_dir = self.root_path / "content"

        for section in self.sections:
            self._apply_cascade_to_section_pages(section, content_dir)

    def _apply_cascade_to_section_pages(self, section: Section, content_dir: Path) -> None:
        """
        Apply cascade values to pages in a section and its subsections.

        Args:
            section: Section to process
            content_dir: Content directory for relative path computation
        """
        from bengal.core.page.proxy import PageProxy

        # Compute section path for cascade lookup
        if section.path is None:
            section_path = ""
        else:
            try:
                section_path = str(section.path.relative_to(content_dir))
            except ValueError:
                section_path = str(section.path)

        # Get all cascade values for this section
        cascade = self.cascade.resolve_all(section_path)

        if cascade:
            for page in section.pages:
                # Skip PageProxy objects - they resolve cascade at access time
                if isinstance(page, PageProxy):
                    continue

                # Skip index pages - they define cascade, don't receive it
                if page.source_path.stem in ("_index", "index"):
                    continue

                # Apply cascade values (page values take precedence)
                for key, value in cascade.items():
                    if key not in page.metadata:
                        page.metadata[key] = value

        # Recurse into subsections
        for subsection in section.subsections:
            self._apply_cascade_to_section_pages(subsection, content_dir)

    # =========================================================================
    # CASCADE SNAPSHOT (immutable cascade data for thread-safe access)
    # =========================================================================

    @property
    def cascade(self) -> Any:
        """
        Get the immutable cascade snapshot for this build.

        The cascade snapshot provides thread-safe access to cascade metadata
        without locks. It is computed once at build start and can be safely
        accessed from multiple render threads in free-threaded Python.

        If accessed before build_cascade_snapshot() is called, returns an
        empty snapshot for graceful fallback (no cascade values will resolve).

        Returns:
            CascadeSnapshot instance (empty if not yet built)

        Example:
            >>> page_type = site.cascade.resolve("docs/guide", "type")
            >>> all_cascade = site.cascade.resolve_all("docs/guide")
        """
        if self._cascade_snapshot is None:
            # Return empty snapshot instead of raising to allow graceful fallback
            from bengal.core.cascade_snapshot import CascadeSnapshot

            return CascadeSnapshot.empty()
        return self._cascade_snapshot

    def build_cascade_snapshot(self) -> None:
        """
        Build the immutable cascade snapshot from all sections.

        This scans all sections and extracts cascade metadata from their
        index pages (_index.md). The resulting snapshot is frozen and can
        be safely shared across threads.

        Also extracts root-level cascade from pages not in any section
        (like content/index.md) and applies it site-wide.

        Called automatically by _apply_cascades() during discovery.
        Can also be called manually to refresh the snapshot after
        incremental changes to _index.md files.

        Example:
            >>> site.build_cascade_snapshot()
            >>> print(f"Cascade data for {len(site.cascade)} sections")
        """
        from bengal.core.cascade_snapshot import CascadeSnapshot

        # Gather all sections including subsections
        all_sections = self._collect_all_sections()

        # Compute content directory
        content_dir = self.root_path / "content"

        # Collect root-level cascade from pages not in any section
        # This handles content/index.md with cascade that applies site-wide
        pages_in_sections: set[Page] = set()
        for section in all_sections:
            pages_in_sections.update(section.get_all_pages(recursive=True))

        root_cascade: dict[str, Any] = {}
        for page in self.pages:
            if page not in pages_in_sections and "cascade" in page.metadata:
                root_cascade.update(page.metadata["cascade"])

        # Build and store immutable snapshot
        self._cascade_snapshot = CascadeSnapshot.build(
            content_dir, all_sections, root_cascade=root_cascade
        )

    def _collect_all_sections(self) -> list[Section]:
        """
        Collect all sections including nested subsections.

        Returns:
            Flat list of all Section objects in the site.
        """
        all_sections: list[Section] = []

        def collect_recursive(sections: list[Section]) -> None:
            for section in sections:
                all_sections.append(section)
                if section.subsections:
                    collect_recursive(section.subsections)

        collect_recursive(self.sections)
        return all_sections
