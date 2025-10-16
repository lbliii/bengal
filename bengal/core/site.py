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

    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        # Ensure root_path is a Path object
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        self.theme = self.config.get("theme", "default")

        if "output_dir" in self.config:
            self.output_dir = Path(self.config["output_dir"])

        # Make output_dir absolute relative to root_path
        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir

        # Load data from data/ directory
        self.data = self._load_data_directory()

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
    def from_config(cls, root_path: Path, config_path: Path | None = None) -> Site:
        """
        Create a Site instance from a configuration file.

        This is the PREFERRED way to create a Site - it loads configuration
        from bengal.toml (or bengal.yaml) and applies all settings properly.

        Config Loading:
            1. Searches for config file: bengal.toml, bengal.yaml, bengal.yml
            2. Parses and validates configuration
            3. Flattens nested sections for easy access
            4. Returns Site with all settings applied

        Important Config Sections:
            - [site]: title, baseurl, author, etc.
            - [build]: parallel, max_workers, incremental, etc.
            - [markdown]: parser selection ('mistune' recommended)
            - [features]: syntax_highlighting, search, etc.
            - [taxonomies]: tags, categories, series

        Args:
            root_path: Root directory of the site
            config_path: Optional explicit path to config file
                        (auto-detected from root_path if not provided)

        Returns:
            Configured Site instance with all settings loaded

        Example:
            site = Site.from_config(Path('/path/to/site'))
            # Loads /path/to/site/bengal.toml automatically

        Use Cases:
            1. Unit testing: Site(root_path=path, config={})
               - Tests can control exact state without config files
               - Allows isolated testing of specific features

            2. Manual config loading: Site(root_path=path, config=loaded_config)
               - When you need to modify config programmatically
               - Advanced use case for custom build scripts

        Warning:
            In production/normal builds, use Site.from_config() instead!
            Passing config={} will override bengal.toml settings and use defaults.
        """
        from bengal.config.loader import ConfigLoader

        loader = ConfigLoader(root_path)
        config = loader.load(config_path)

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

        from bengal.discovery.content_discovery import ContentDiscovery

        discovery = ContentDiscovery(content_dir, site=self)
        self.sections, self.pages = discovery.discover()

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
        incremental: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        profile: BuildProfile = None,
        memory_optimized: bool = False,
        strict: bool = False,
        full_output: bool = False,
    ) -> BuildStats:
        """
        Build the entire site.

        Delegates to BuildOrchestrator for actual build process.

        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            quiet: Whether to suppress progress output (minimal output mode)
            profile: Build profile (writer, theme-dev, or dev)
            memory_optimized: Use streaming build for memory efficiency (best for 5K+ pages)
            strict: Whether to fail on warnings
            full_output: Show full traditional output instead of live progress

        Returns:
            BuildStats object with build statistics
        """
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
        )

    def serve(
        self,
        host: str = "localhost",
        port: int = 5173,
        watch: bool = True,
        auto_port: bool = True,
        open_browser: bool = False,
    ) -> None:
        """
        Start a development server.

        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
            auto_port: Whether to automatically find an available port if the specified one is in use
            open_browser: Whether to automatically open the browser
        """
        from bengal.server.dev_server import DevServer

        server = DevServer(
            self, host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser
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
