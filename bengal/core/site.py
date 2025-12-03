"""
Site Object - Represents the entire website and orchestrates the build.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from bengal.core.asset import Asset
from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.theme import Theme
from bengal.utils.build_stats import BuildStats
from bengal.utils.dotdict import DotDict
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.utils.profile import BuildProfile

logger = get_logger(__name__)

# Thread-local storage for pipelines (reuse per thread, not per page!)
_thread_local = threading.local()


# Thread-safe output lock for parallel processing
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
        from bengal.config.loader import ConfigLoader
        loader = ConfigLoader(path)
        config = loader.load()
        config['custom_setting'] = 'value'
        site = Site(root_path=path, config=config)
    """

    root_path: Path
    config: dict[str, Any] = field(default_factory=dict)
    pages: list[Page] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    theme: str | None = None
    output_dir: Path = field(default_factory=lambda: Path("public"))
    build_time: datetime | None = None
    taxonomies: dict[str, dict[str, list[Page]]] = field(default_factory=dict)
    menu: dict[str, list[MenuItem]] = field(default_factory=dict)
    menu_builders: dict[str, MenuBuilder] = field(default_factory=dict)
    # Localized menus when i18n is enabled: {lang: {menu_name: [MenuItem]}}
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)
    # Current language context for rendering (set per page during rendering)
    current_language: str | None = None
    # Global data from data/ directory (YAML, JSON, TOML files)
    data: Any = field(default_factory=dict)

    # Private caches for expensive properties (invalidated when pages change)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _generated_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _theme_obj: Theme | None = field(default=None, repr=False, init=False)
    _query_registry: Any = field(default=None, repr=False, init=False)

    # Section registry for path-based lookups (O(1) section access by path)
    _section_registry: dict[Path, Section] = field(default_factory=dict, repr=False, init=False)

    # Config hash for cache invalidation (computed on init)
    _config_hash: str | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        # Ensure root_path is a Path object
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        # Get theme NAME from [theme] section
        theme_section = self.config.get("theme", {})
        if isinstance(theme_section, dict):
            self.theme = theme_section.get("name", "default")
        else:
            # Fallback for legacy config where theme was a string
            self.theme = theme_section if isinstance(theme_section, str) else "default"

        # Initialize Theme object
        self._theme_obj = Theme.from_config(self.config)

        if "output_dir" in self.config:
            self.output_dir = Path(self.config["output_dir"])

        # Make output_dir absolute relative to root_path
        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir

        # Load data from data/ directory
        self.data = self._load_data_directory()

        # Compute config hash for cache invalidation
        self._compute_config_hash()

    @property
    def title(self) -> str | None:
        """Get site title from config."""
        return self.config.get("title")

    @property
    def baseurl(self) -> str | None:
        """Get site baseurl from config."""
        return self.config.get("baseurl")

    @property
    def author(self) -> str | None:
        """Get site author from config."""
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
        return self._config_hash

    def _compute_config_hash(self) -> None:
        """
        Compute and cache the configuration hash.

        Called during __post_init__ to ensure hash is available immediately.
        """
        from bengal.config.hash import compute_config_hash

        self._config_hash = compute_config_hash(self.config)
        logger.debug(
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
            self._theme_obj = Theme.from_config(self.config)
        return self._theme_obj

    @property
    def indexes(self):
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

            cache_dir = self.root_path / ".bengal" / "indexes"
            self._query_registry = QueryIndexRegistry(self, cache_dir)
        return self._query_registry

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
        # Return cached value if available (O(1))
        if self._regular_pages_cache is not None:
            return self._regular_pages_cache

        # Compute and cache (O(n), only happens once)
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
        # Return cached value if available (O(1))
        if self._generated_pages_cache is not None:
            return self._generated_pages_cache

        # Compute and cache (O(n), only happens once)
        self._generated_pages_cache = [p for p in self.pages if p.metadata.get("_generated")]
        return self._generated_pages_cache

    def invalidate_page_caches(self) -> None:
        """
        Invalidate cached page lists when pages are modified.

        Call this after:
        - Adding/removing pages
        - Modifying page metadata (especially _generated flag)
        - Any operation that changes the pages list

        This ensures cached properties (regular_pages, generated_pages) will
        recompute on next access.
        """
        self._regular_pages_cache = None
        self._generated_pages_cache = None

    def invalidate_regular_pages_cache(self) -> None:
        """
        Invalidate the regular_pages cache.

        Call this after modifying the pages list or page metadata that affects
        the _generated flag.
        """
        self._regular_pages_cache = None

    @classmethod
    def from_config(
        cls,
        root_path: Path,
        config_path: Path | None = None,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Site:
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
            - [markdown]: parser selection ('mistune' recommended)
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
        config_dir = root_path / "config"

        # Check if config directory exists (new system)
        if config_dir.exists() and config_dir.is_dir():
            from bengal.config.directory_loader import ConfigDirectoryLoader

            loader = ConfigDirectoryLoader()
            config = loader.load(config_dir, environment=environment, profile=profile)
        else:
            # Fall back to single-file config (old system)
            from bengal.config.loader import ConfigLoader

            loader = ConfigLoader(root_path)
            config = loader.load(config_path)

        return cls(root_path=root_path, config=config)

    @classmethod
    def for_testing(cls, root_path: Path | None = None, config: dict | None = None) -> Site:
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
            logger.warning("content_dir_not_found", path=str(content_dir))
            return

        from bengal.collections import load_collections
        from bengal.discovery.content_discovery import ContentDiscovery

        # Load collection schemas from project root (if collections.py exists)
        collections = load_collections(self.root_path)

        # Check if strict validation is enabled (default: False for backward compatibility)
        build_config = self.config.get("build", {}) if isinstance(self.config, dict) else {}
        strict_validation = build_config.get("strict_collections", False)

        discovery = ContentDiscovery(
            content_dir,
            site=self,
            collections=collections,
            strict_validation=strict_validation,
        )
        self.sections, self.pages = discovery.discover()

        # Build section registry for path-based lookups (MUST come before _setup_page_references)
        self.register_sections()

        # Set up page references for navigation
        self._setup_page_references()

        # Apply cascading frontmatter from sections to pages
        self._apply_cascades()

    def discover_assets(self, assets_dir: Path | None = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.

        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.discovery.asset_discovery import AssetDiscovery

        self.assets = []

        # Discover theme assets first (lower priority), support inheritance chain
        if self.theme:
            for theme_dir in self._get_theme_assets_chain():
                if theme_dir and theme_dir.exists():
                    theme_discovery = AssetDiscovery(theme_dir)
                    self.assets.extend(theme_discovery.discover())

        # Discover site assets (higher priority, can override theme assets)
        if assets_dir is None:
            assets_dir = self.root_path / "assets"

        if assets_dir.exists():
            logger.debug("discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            # Only warn if we have no theme assets either
            logger.warning("assets_dir_not_found", path=str(assets_dir))

        # Deduplicate by relative output path with precedence: site > child theme > parents
        if self.assets:
            dedup: dict[str, Asset] = {}
            order: list[str] = []
            for asset in self.assets:
                key = str(asset.output_path) if asset.output_path else str(asset.source_path.name)
                # Keep the latest occurrence (later entries override earlier)
                if key in dedup:
                    dedup[key] = asset
                else:
                    dedup[key] = asset
                    order.append(key)
            self.assets = [dedup[k] for k in order]

    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).

        This method sets _site and _section references on all pages to enable
        navigation properties (next, prev, ancestors, etc.).
        """
        # Set site reference on all pages
        for page in self.pages:
            page._site = self

        # Set section references
        for section in self.sections:
            # Set site reference on section
            section._site = self

            # Set section reference on all pages in this section
            for page in section.pages:
                page._section = section

            # Recursively set for subsections
            self._setup_section_references(section)

    def _setup_section_references(self, section: Section) -> None:
        """
        Recursively set up references for a section and its subsections.

        Args:
            section: Section to set up references for
        """
        for subsection in section.subsections:
            subsection._site = self

            # Set section reference on pages in subsection
            for page in subsection.pages:
                page._section = subsection

            # Recurse into deeper subsections
            self._setup_section_references(subsection)

    def _apply_cascades(self) -> None:
        """
        Apply cascading metadata from sections to their child pages and subsections.

        This implements Hugo-style cascade functionality where section _index.md files
        can define metadata that automatically applies to all descendant pages.

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

        Delegates to CascadeEngine for the actual implementation.
        """
        from bengal.core.cascade_engine import CascadeEngine

        engine = CascadeEngine(self.pages, self.sections)
        engine.apply()

    def _get_theme_assets_dir(self) -> Path | None:
        """
        Get the assets directory for the current theme.

        Returns:
            Path to theme assets or None if not found
        """
        if not self.theme:
            return None

        # Check in site's themes directory first
        site_theme_dir = self.root_path / "themes" / self.theme / "assets"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.theme / "assets"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _get_theme_assets_chain(self) -> list[Path]:
        """
        Return list of theme asset dirs from parents to child (low → high priority).
        Site assets will still override these.
        """
        dirs: list[Path] = []
        try:
            from bengal.utils.theme_resolution import resolve_theme_chain

            chain = resolve_theme_chain(self.root_path, self.theme)
        except Exception:
            chain = [self.theme] if self.theme else []

        # Build list from parents to child
        for theme_name in reversed(chain):
            from bengal.utils.theme_resolution import iter_theme_asset_dirs

            # iter_theme_asset_dirs returns parent→child; we just consume one theme at a time
            for d in iter_theme_asset_dirs(self.root_path, [theme_name]):
                dirs.append(d)
        return dirs

    def build(
        self,
        parallel: bool = True,
        incremental: bool | None = None,
        verbose: bool = False,
        quiet: bool = False,
        profile: BuildProfile = None,
        memory_optimized: bool = False,
        strict: bool = False,
        full_output: bool = False,
        profile_templates: bool = False,
        use_pipeline: bool = False,
    ) -> BuildStats:
        """
        Build the entire site.

        Delegates to BuildOrchestrator for actual build process, or uses
        the reactive dataflow pipeline if use_pipeline is True.

        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            quiet: Whether to suppress progress output (minimal output mode)
            profile: Build profile (writer, theme-dev, or dev)
            memory_optimized: Use streaming build for memory efficiency (best for 5K+ pages)
            strict: Whether to fail on warnings
            full_output: Show full traditional output instead of live progress
            profile_templates: Enable template profiling for performance analysis
            use_pipeline: Use reactive dataflow pipeline (experimental)

        Returns:
            BuildStats object with build statistics
        """
        if use_pipeline:
            return self._build_with_pipeline(parallel=parallel, verbose=verbose)

        from bengal.orchestration import BuildOrchestrator

        orchestrator = BuildOrchestrator(self)
        return orchestrator.build(
            parallel=parallel,
            incremental=incremental,
            verbose=verbose,
            quiet=quiet,
            profile=profile,
            memory_optimized=memory_optimized,
            strict=strict,
            full_output=full_output,
            profile_templates=profile_templates,
        )

    def _build_with_pipeline(
        self,
        parallel: bool = True,
        verbose: bool = False,
    ) -> BuildStats:
        """
        Build site using the reactive dataflow pipeline for rendering.

        This hybrid approach:
        1. Uses orchestrators for discovery, taxonomies, menus (complex logic)
        2. Uses pipeline for parallel rendering (where it shines)
        3. Uses orchestrators for postprocessing (sitemap, RSS, etc.)

        Args:
            parallel: Whether to use parallel processing
            verbose: Whether to show detailed build information

        Returns:
            BuildStats object with build statistics
        """
        import shutil
        import time

        from bengal.orchestration import (
            AssetOrchestrator,
            ContentOrchestrator,
            MenuOrchestrator,
            PostprocessOrchestrator,
            TaxonomyOrchestrator,
        )
        from bengal.orchestration.section import SectionOrchestrator
        from bengal.pipeline import create_simple_pipeline

        logger.info("pipeline_build_starting", parallel=parallel)
        start_time = time.time()

        # Phase 0a: Static files (copy FIRST, before everything else)
        # Static files are copied verbatim to output root, allowing raw HTML
        # pages to access theme assets via /assets/css/style.css
        from bengal.orchestration.static import StaticOrchestrator

        static_start = time.time()
        static = StaticOrchestrator(self)
        static_count = static.copy()
        static_time_ms = (time.time() - static_start) * 1000
        if static_count > 0:
            logger.debug(
                "static_phase_complete", files=static_count, time_ms=f"{static_time_ms:.1f}"
            )

        # Phase 0b: Font Processing (generate fonts.css if fonts configured)
        if "fonts" in self.config:
            try:
                from bengal.fonts import FontHelper

                assets_dir = self.root_path / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)

                font_helper = FontHelper(self.config["fonts"])
                css_path = font_helper.process(assets_dir)

                # Copy fonts.css to output directory
                if css_path and css_path.exists():
                    output_assets = self.output_dir / "assets"
                    output_assets.mkdir(parents=True, exist_ok=True)
                    output_css = output_assets / "fonts.css"
                    if (
                        not output_css.exists()
                        or css_path.stat().st_mtime > output_css.stat().st_mtime
                    ):
                        shutil.copy2(css_path, output_css)
            except Exception as e:
                logger.warning("fonts_processing_failed", error=str(e))

        # Phase 1: Discovery (use existing orchestrators - they handle all the edge cases)
        discovery_start = time.time()
        content = ContentOrchestrator(self)
        content.discover_content()
        content.discover_assets()
        discovery_time_ms = (time.time() - discovery_start) * 1000

        # Phase 2: Sections (finalize hierarchy, create missing index pages)
        sections = SectionOrchestrator(self)
        sections.finalize_sections()

        # Phase 3: Taxonomies (collects tags and generates tag pages)
        taxonomy_start = time.time()
        taxonomy = TaxonomyOrchestrator(self, parallel=parallel)
        taxonomy.collect_and_generate(parallel=parallel)
        taxonomy_time_ms = (time.time() - taxonomy_start) * 1000

        # Phase 4: Menus
        menu = MenuOrchestrator(self)
        menu.build()

        # Phase 5: Assets (copy/process BEFORE rendering so asset_url() works)
        assets_start = time.time()
        assets = AssetOrchestrator(self)
        assets.process(self.assets, parallel=parallel, progress_manager=None)
        assets_time_ms = (time.time() - assets_start) * 1000

        # Phase 6: Render ALL pages using pipeline (including generated pages)
        rendering_start = time.time()
        pipeline = create_simple_pipeline(self, pages=list(self.pages))
        result = pipeline.run()
        rendering_time_ms = (time.time() - rendering_start) * 1000

        # Phase 7: Postprocessing (sitemap, RSS, JSON, llms.txt)
        postprocess_start = time.time()
        postprocess = PostprocessOrchestrator(self)
        postprocess.run(parallel=parallel, incremental=False)
        postprocess_time_ms = (time.time() - postprocess_start) * 1000

        elapsed = time.time() - start_time

        # Count page types
        regular_count = len(self.regular_pages)
        generated_count = len(self.generated_pages)

        # Count sections
        section_count = len(self.sections) if hasattr(self, "sections") else 0

        # Count assets
        asset_count = len(self.assets) if hasattr(self, "assets") else 0

        # Count taxonomies (sum of all terms across all taxonomy types)
        taxonomies_count = (
            sum(len(terms) for terms in self.taxonomies.values())
            if hasattr(self, "taxonomies") and self.taxonomies
            else 0
        )

        logger.info(
            "pipeline_build_complete",
            total_pages=result.items_processed,
            regular_pages=regular_count,
            generated_pages=generated_count,
            elapsed_seconds=round(elapsed, 2),
            success=result.success,
            errors=len(result.errors),
        )

        return BuildStats(
            total_pages=result.items_processed,
            regular_pages=regular_count,
            generated_pages=generated_count,
            total_sections=section_count,
            total_assets=asset_count,
            taxonomies_count=taxonomies_count,
            build_time_ms=elapsed * 1000,
            parallel=parallel,
            incremental=False,
            # Phase timings
            discovery_time_ms=discovery_time_ms,
            taxonomy_time_ms=taxonomy_time_ms,
            rendering_time_ms=rendering_time_ms,
            assets_time_ms=assets_time_ms,
            postprocess_time_ms=postprocess_time_ms,
        )

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
        use_pipeline: bool = False,
    ) -> None:
        """
        Start a development server.

        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
            auto_port: Whether to automatically find an available port if the specified one is in use
            open_browser: Whether to automatically open the browser
            use_pipeline: Whether to use reactive dataflow pipeline for builds
        """
        from bengal.server.dev_server import DevServer

        server = DevServer(
            self,
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
            use_pipeline=use_pipeline,
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
        import shutil

        if self.output_dir.exists():
            # Use debug level to avoid noise in clean command output
            logger.debug("cleaning_output_dir", path=str(self.output_dir))
            shutil.rmtree(self.output_dir)
            logger.debug("output_dir_cleaned", path=str(self.output_dir))
        else:
            logger.debug("output_dir_does_not_exist", path=str(self.output_dir))

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
        from bengal.utils.dotdict import DotDict, wrap_data
        from bengal.utils.file_io import load_data_file

        data_dir = self.root_path / "data"

        if not data_dir.exists():
            logger.debug("data_directory_not_found", path=str(data_dir))
            return DotDict()

        logger.debug("loading_data_directory", path=str(data_dir))

        data = {}
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

                # Validate tracks.yaml structure if this is tracks data
                if parts[-1] == "tracks" and isinstance(content, dict):
                    self._validate_tracks_structure(content)

                logger.debug(
                    "data_file_loaded",
                    file=str(relative),
                    key=".".join(parts),
                    size=len(str(content)) if content else 0,
                )

            except Exception as e:
                logger.warning(
                    "data_file_load_failed",
                    file=str(relative),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        wrapped_data = wrap_data(data)

        if data:
            logger.debug(
                "data_directory_loaded",
                files_loaded=len(list(data_dir.rglob("*.*"))),
                top_level_keys=list(data.keys()) if isinstance(data, dict) else [],
            )

        return wrapped_data

    def _validate_tracks_structure(self, tracks_data: dict) -> None:
        """
        Validate tracks.yaml structure during data loading.

        Logs warnings for invalid tracks but doesn't fail the build.
        This provides early feedback during development.

        Args:
            tracks_data: Dictionary loaded from tracks.yaml
        """
        if not isinstance(tracks_data, dict):
            logger.warning(
                "tracks_invalid_structure",
                message="tracks.yaml root must be a dictionary",
            )
            return

        for track_id, track in tracks_data.items():
            if not isinstance(track, dict):
                logger.warning(
                    "track_invalid_structure",
                    track_id=track_id,
                    message=f"Track '{track_id}' must be a dictionary",
                )
                continue

            # Check required fields
            if "items" not in track:
                logger.warning(
                    "track_missing_items",
                    track_id=track_id,
                    message=f"Track '{track_id}' is missing required 'items' field",
                )
                continue

            if not isinstance(track["items"], list):
                logger.warning(
                    "track_items_not_list",
                    track_id=track_id,
                    message=f"Track '{track_id}' has 'items' field that is not a list",
                )
                continue

            # Warn about empty tracks (may be intentional, but worth noting)
            if len(track["items"]) == 0:
                logger.debug(
                    "track_empty_items",
                    track_id=track_id,
                    message=f"Track '{track_id}' has no items",
                )

    def __repr__(self) -> str:
        return f"Site(pages={len(self.pages)}, sections={len(self.sections)}, assets={len(self.assets)})"

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
        logger.debug("site_reset_ephemeral_state", site_root=str(self.root_path))

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
                self.xref_index = {}

        # Cached properties
        self.invalidate_regular_pages_cache()

        # Section registry (rebuilt from sections)
        self._section_registry = {}

    def _normalize_section_path(self, path: Path) -> Path:
        """
        Normalize a section path for registry lookups.

        Normalization ensures consistent lookups across platforms:
        - Resolves symlinks to canonical paths
        - Makes path relative to content/ directory
        - Lowercases on case-insensitive filesystems (macOS, Windows)

        Args:
            path: Absolute or relative section path

        Returns:
            Normalized path suitable for registry keys

        Examples:
            /site/content/blog → blog
            /site/content/docs/guides → docs/guides
            content/BLOG → blog (on macOS/Windows)
        """
        import platform

        # Resolve symlinks to canonical path
        resolved = path.resolve()

        # Make relative to content/ directory
        content_dir = (self.root_path / "content").resolve()
        try:
            relative = resolved.relative_to(content_dir)
        except ValueError:
            # Path not under content/, use as-is
            relative = resolved

        # Lowercase on case-insensitive filesystems (macOS, Windows)
        system = platform.system()
        if system in ("Darwin", "Windows"):
            # Convert to lowercase string then back to Path
            relative = Path(str(relative).lower())

        return relative

    def get_section_by_path(self, path: Path | str) -> Section | None:
        """
        Look up a section by its path (O(1) operation).

        Uses the section registry for fast lookups without scanning the section tree.
        Paths are normalized before lookup to handle case-insensitive filesystems
        and symlinks consistently.

        Args:
            path: Section path (absolute, relative to content/, or relative to root)

        Returns:
            Section object if found, None otherwise

        Examples:
            >>> section = site.get_section_by_path("blog")
            >>> section = site.get_section_by_path("docs/guides")
            >>> section = site.get_section_by_path(Path("/site/content/blog"))

        Performance:
            O(1) lookup after registry is built (via register_sections)
        """
        if isinstance(path, str):
            path = Path(path)

        # Handle relative paths that might be relative to root_path
        if not path.is_absolute():
            # Try as relative to content/ first
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                # Try as relative to root_path
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

        normalized = self._normalize_section_path(path)
        section = self._section_registry.get(normalized)

        if section is None:
            logger.debug(
                "section_not_found_in_registry",
                path=str(path),
                normalized=str(normalized),
                registry_size=len(self._section_registry),
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registry for path-based lookups.

        Scans all sections recursively and populates _section_registry with
        normalized path → Section mappings. This enables O(1) section lookups
        without scanning the section hierarchy.

        Must be called after discover_content() and before any code that uses
        get_section_by_path() or page._section property.

        Build ordering invariant:
            1. discover_content()       → Creates Page/Section objects
            2. register_sections()      → Builds path→section registry (THIS)
            3. setup_page_references()  → Sets page._section via property setter
            4. apply_cascades()         → Lookups resolve via registry
            5. generate_urls()          → Uses correct section hierarchy

        Performance:
            O(n) where n = number of sections. Typical: < 10ms for 1000 sections.

        Examples:
            >>> site.discover_content()
            >>> site.register_sections()  # Build registry
            >>> section = site.get_section_by_path("blog")  # O(1) lookup
        """
        import time

        start = time.time()
        self._section_registry = {}

        # Register all sections recursively
        for section in self.sections:
            self._register_section_recursive(section)

        elapsed_ms = (time.time() - start) * 1000

        logger.debug(
            "section_registry_built",
            sections_registered=len(self._section_registry),
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / len(self._section_registry)):.2f}"
            if self._section_registry
            else "0",
        )

    def _register_section_recursive(self, section: Section) -> None:
        """
        Recursively register a section and its subsections in the registry.

        Args:
            section: Section to register (along with all its subsections)
        """
        # Register this section
        normalized = self._normalize_section_path(section.path)
        self._section_registry[normalized] = section

        # Register subsections recursively
        for subsection in section.subsections:
            self._register_section_recursive(subsection)
