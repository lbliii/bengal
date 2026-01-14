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
Theme Integration: Resolves theme chains for template/asset lookup
Query Interfaces: Provides taxonomy, menu, and page query APIs

Mixin Architecture:
Site is composed of focused mixins for separation of concerns:
- SitePropertiesMixin: Config property accessors
- PageCachesMixin: Cached page lists
- SiteFactoriesMixin: Factory methods (from_config, for_testing)
- ContentDiscoveryMixin: Content/asset discovery
- ThemeIntegrationMixin: Theme resolution
- DataLoadingMixin: data/ directory loading
- SectionRegistryMixin: O(1) section lookups

Caching Strategy:
Expensive computations (page lists, section lookups) are cached and
invalidated when content changes via invalidate_page_caches().

Related Packages:
bengal.orchestration.build: Build phase orchestration
bengal.rendering.template_engine: Template rendering with Site context
bengal.cache.build_cache: Build state persistence

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from bengal.core.asset import Asset
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.page import Page
from bengal.core.registry import ContentRegistry
from bengal.core.section import Section
from bengal.core.site.data import DataLoadingMixin
from bengal.core.site.discovery import ContentDiscoveryMixin
from bengal.core.site.factories import SiteFactoriesMixin
from bengal.core.site.page_caches import PageCachesMixin
from bengal.core.site.properties import SitePropertiesMixin
from bengal.core.site.section_registry import SectionRegistryMixin
from bengal.core.site.theme import ThemeIntegrationMixin
from bengal.core.theme import Theme
from bengal.core.url_ownership import URLRegistry
from bengal.core.version import Version, VersionConfig
from bengal.icons import resolver as icon_resolver

if TYPE_CHECKING:
    from bengal.config.accessor import Config
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_state import BuildState
    from bengal.orchestration.stats import BuildStats


# Thread-safe output lock for parallel processing.
_print_lock = Lock()


@dataclass
class Site(
    SitePropertiesMixin,
    PageCachesMixin,
    SiteFactoriesMixin,
    ThemeIntegrationMixin,  # Must come before ContentDiscoveryMixin for _get_theme_assets_chain
    ContentDiscoveryMixin,
    DataLoadingMixin,
    SectionRegistryMixin,
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
    _paths: Any = field(default=None, repr=False, init=False)
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
            elif (
                isinstance(theme_value, dict)
                and theme_value.get("name")
                or hasattr(theme_value, "get")
                and theme_value.get("name")
            ):
                self.theme = str(theme_value.get("name"))
            elif hasattr(theme_value, "name") and theme_value.name:
                self.theme = str(theme_value.name)
            else:
                self.theme = "default"

        # Theme.from_config expects a dict; use .raw if available (Config object) else use directly (plain dict)
        config_dict = self.config.raw if hasattr(self.config, "raw") else self.config
        self._theme_obj = Theme.from_config(
            config_dict,
            root_path=self.root_path,
            diagnostics_site=self,
        )

        # Initialize theme-aware icon resolver for all icon consumers
        # (template functions, inline icon plugin, directives)
        icon_resolver.initialize(self)

        # Access output_dir from build section (supports both Config and dict)
        if hasattr(self.config, "build"):
            output_dir_str = self.config.build.output_dir
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
        if hasattr(self, "xref_index"):
            from contextlib import suppress

            with suppress(Exception):
                self.xref_index: dict[str, Any] = {}

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
        return [
            p
            for p in self.pages
            if getattr(p, "_section", None) and p._section.name == section_name
        ]

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

        return _get_version_target_url(page, target_version, self)

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
            urls_seen: dict[str, str] = {}  # url -> source description

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
                suggestion="Check for duplicate slugs, conflicting autodoc output, or use different URLs for conflicting pages",
            )

        return collisions
