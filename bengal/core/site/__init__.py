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
discovery.py: SiteDiscoveryMixin (content/asset discovery)
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

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Self, cast

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
from bengal.protocols.core import SiteLike

# Import mixins
from .config_normalized import SiteNormalizedConfigMixin
from .discovery import SiteDiscoveryMixin
from .factory import for_testing, from_config
from .properties import SitePropertiesMixin
from .versioning import SiteVersioningMixin

if TYPE_CHECKING:
    from bengal.assets.manifest import AssetManifest
    from bengal.cache.paths import BengalPaths
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.config.accessor import Config
    from bengal.core.cascade_snapshot import CascadeSnapshot
    from bengal.core.page_cache import PageCacheManager
    from bengal.orchestration.build_state import BuildState
    from bengal.parsing.base import BaseMarkdownParser
    from bengal.utils.primitives.dotdict import DotDict


# Thread-safe output lock for parallel processing.
_print_lock = Lock()


@dataclass
class Site(
    SitePropertiesMixin,
    SiteNormalizedConfigMixin,
    SiteVersioningMixin,
    SiteDiscoveryMixin,
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
    data: DotDict = field(default_factory=dict)
    # Runtime flag: True when running in dev server mode (not persisted to config).
    dev_mode: bool = False

    # Versioning configuration (loaded from config during __post_init__)
    version_config: VersionConfig = field(default_factory=VersionConfig)
    # Current version context for rendering (set per page during rendering)
    current_version: Version | None = None

    # Page cache manager (lazy caches over self.pages, extracted to PageCacheManager)
    _page_cache: PageCacheManager | None = field(default=None, repr=False, init=False)
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
        icon_resolver.initialize(cast(SiteLike, self))

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

        # Initialize page cache manager (lazy caches over self.pages)
        from bengal.core.page_cache import PageCacheManager

        self._page_cache = PageCacheManager(lambda: self.pages)

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

    # =========================================================================
    # HELPERS
    # =========================================================================

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
                    owner_info = (
                        f" ({claim.owner}, priority {claim.priority})" if claim else ""
                    )

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
    # CASCADE (inlined from SiteCascadeMixin)
    # =========================================================================

    @property
    def cascade(self) -> CascadeSnapshot:
        """
        Get the immutable cascade snapshot for this build.

        Resolution order:
            1. BuildState.cascade_snapshot (during builds — structurally fresh)
            2. Local _cascade_snapshot (outside builds — tests, CLI)
            3. Empty snapshot (graceful fallback)

        The cascade snapshot provides thread-safe access to cascade metadata
        without locks. It is computed once at build start and can be safely
        accessed from multiple render threads in free-threaded Python.

        Returns:
            CascadeSnapshot instance (empty if not yet built)

        Example:
            >>> page_type = site.cascade.resolve("docs/guide", "type")
            >>> all_cascade = site.cascade.resolve_all("docs/guide")
        """
        # During builds: delegate to BuildState (structurally fresh each build)
        if self._current_build_state is not None:
            snapshot = self._current_build_state.cascade_snapshot
            if snapshot is not None:
                return snapshot

        # Outside builds (tests, CLI): use local fallback
        if self._cascade_snapshot is not None:
            return self._cascade_snapshot

        # Return empty snapshot for graceful fallback
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

        # Store on BuildState if available (primary path during builds)
        if self._current_build_state is not None:
            self._current_build_state.cascade_snapshot = snapshot

        # Always store locally for non-build access (tests, CLI)
        self._cascade_snapshot = snapshot

    # =========================================================================
    # PAGE CACHES (delegated to PageCacheManager)
    # =========================================================================

    @property
    def regular_pages(self) -> list[Page]:
        """Regular content pages (excludes generated taxonomy/archive pages)."""
        return self._page_cache.regular_pages

    @property
    def generated_pages(self) -> list[Page]:
        """Generated pages (taxonomy, archive, pagination)."""
        return self._page_cache.generated_pages

    @property
    def listable_pages(self) -> list[Page]:
        """Pages eligible for public listings (excludes hidden/draft)."""
        return self._page_cache.listable_pages

    def get_page_path_map(self) -> dict[str, Page]:
        """Cached string-keyed page lookup map for O(1) resolution."""
        return self._page_cache.get_page_path_map()

    @property
    def page_by_source_path(self) -> dict[Path, Page]:
        """O(1) page lookup by source Path (shared across orchestrators)."""
        return self._page_cache.page_by_source_path

    def invalidate_page_caches(self) -> None:
        """Clear all page caches. Call after adding/removing pages."""
        self._page_cache.invalidate()

    def invalidate_regular_pages_cache(self) -> None:
        """Clear only the regular_pages cache."""
        self._page_cache.invalidate_regular()

    # =========================================================================
    # LIFECYCLE (inlined from SiteLifecycleMixin)
    # =========================================================================

    def prepare_for_rebuild(self) -> None:
        """
        Reset content and derived-content state for a warm rebuild.

        Called by BuildTrigger before each warm build to ensure clean state
        while preserving config, theme, paths, and other immutable state that
        is expensive to recompute.

        What IS reset here (content and derived structures):
            - pages, sections, assets (rediscovered every build)
            - taxonomies, menus, xref_index (rebuilt from content)
            - page caches (regular_pages, generated_pages, etc.)
            - content registry and URL registry
            - _cascade_snapshot fallback (primary is on BuildState)
            - _affected_tags, _page_lookup_maps (legacy fallback fields)

        What is handled by BuildState (structurally fresh each build):
            - cascade_snapshot (primary — site.cascade delegates to BuildState)
            - features_detected, discovery_timing_ms
            - template caches (theme_chain, template_dirs, template_metadata)
            - asset_manifest_previous, asset_manifest_fallbacks
            - current_language, current_version (render context)

        What is NOT reset (immutable/persistent across builds):
            - root_path, config, theme, output_dir (configuration)
            - _theme_obj, _paths, _config_hash (derived config)
            - version_config (versioning setup)
            - data (data/ directory — reloaded during discovery if changed)
            - dev_mode (runtime flag)
            - build_time (overwritten at build start)

        Example:
            # Dev server warm rebuild:
            site.prepare_for_rebuild()
            site.build(options)

        See Also:
            bengal/server/build_trigger.py: Where this is called
            bengal/orchestration/build_state.py: Per-build ephemeral state
            bengal/core/site/cascade.py: Cascade bridge to BuildState
        """
        # =================================================================
        # Content (rediscovered every build)
        # =================================================================
        self.pages = []
        self.sections = []
        self.assets = []

        # =================================================================
        # Derived content (rebuilt from content every build)
        # =================================================================
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        self.xref_index = {}

        # =================================================================
        # Cascade snapshot — local fallback
        #
        # The primary cascade path now goes through BuildState (structurally
        # fresh each build). This reset is a safety net for the local
        # fallback path used by tests and CLI health checks.
        # =================================================================
        self._cascade_snapshot = None

        # =================================================================
        # Page caches (must be invalidated when pages change)
        # =================================================================
        if hasattr(self, "invalidate_page_caches"):
            self.invalidate_page_caches()
        if hasattr(self, "invalidate_regular_pages_cache"):
            self.invalidate_regular_pages_cache()

        # =================================================================
        # Content registry (unfreezes and clears for re-discovery)
        # =================================================================
        if hasattr(self, "registry"):
            self.registry.clear()

        # URL registry (fresh registry for new build)
        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        if hasattr(self, "registry"):
            self.registry.url_ownership = self.url_registry

        # =================================================================
        # Legacy per-build fields (primary path is now BuildState)
        #
        # These are kept as safety nets for code paths that haven't
        # been migrated to use BuildState yet.
        # =================================================================
        self._affected_tags = set()
        self._page_lookup_maps = None

    # =========================================================================
    # OPERATIONS (inlined from SiteOperationsMixin)
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

        Most per-build state (cascade, template caches, features_detected,
        discovery timing) now lives on BuildState which is structurally fresh
        each build. This method only needs to reset content, derived structures,
        registries, and legacy fields.

        Persistence contract:
        - Persist: root_path, config, theme, output_dir, build_time, dev_mode
        - Clear: pages, sections, assets (content)
        - Clear derived: taxonomies, menu, xref_index
        - Clear caches: page caches
        - Clear registries: content registry, URL registry
        - Handled by BuildState: cascade, template caches, features, discovery timing
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
        from bengal.core.url_ownership import URLRegistry

        self.url_registry = URLRegistry()
        self.registry.url_ownership = self.url_registry

        # Reset query registry (clear cached_property)
        self.__dict__.pop("indexes", None)

        # Reset theme if needed (will be reloaded on first access)
        self._theme_obj = None

        # Legacy per-build fields (primary path is now BuildState).
        # These may not exist as dataclass fields, so guard with hasattr.
        self._page_lookup_maps = None
        self._bengal_theme_chain_cache = None
        self._bengal_template_dirs_cache = None
        self._bengal_template_metadata_cache = None
        self._discovery_breakdown_ms = None
        if hasattr(self, "_asset_manifest_fallbacks_global"):
            self._asset_manifest_fallbacks_global.clear()
        if hasattr(self, "features_detected"):
            self.features_detected.clear()

        # Clear Kida adapter's asset manifest cache (used for fingerprint resolution)
        if hasattr(self, "_kida_asset_manifest_cache"):
            delattr(self, "_kida_asset_manifest_cache")

        # Clear thread-local rendering caches
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        # Clear thread-local asset manifest context
        from bengal.rendering.assets import reset_asset_manifest

        reset_asset_manifest()

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


__all__ = [
    "Site",
]
