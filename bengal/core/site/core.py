"""
Core Site dataclass for Bengal SSG.

The Site object is the central container for all content (pages, sections,
assets) and coordinates discovery, rendering, and output generation. It
maintains caches for expensive operations and provides query interfaces
for templates.

Key Concepts:
    - Content organization: Pages, sections, and assets organized hierarchically
    - Caching: Expensive property caches invalidated when content changes
    - Theme integration: Theme resolution and template/asset discovery
    - Query interfaces: Taxonomy, menu, and page query APIs for templates

Related Modules:
    - bengal.orchestration.build: Build orchestration using Site
    - bengal.rendering.template_engine: Template rendering with Site context
    - bengal.cache.build_cache: Build state persistence

See Also:
    - plan/active/rfc-incremental-builds.md: Incremental build design
"""

from __future__ import annotations

import shutil
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
from bengal.core.site.data import DataLoadingMixin
from bengal.core.site.discovery import ContentDiscoveryMixin
from bengal.core.site.factories import SiteFactoriesMixin
from bengal.core.site.page_caches import PageCachesMixin
from bengal.core.site.properties import SitePropertiesMixin
from bengal.core.site.section_registry import SectionRegistryMixin
from bengal.core.site.theme import ThemeIntegrationMixin
from bengal.core.theme import Theme
from bengal.utils.build_stats import BuildStats
from bengal.utils.dotdict import DotDict
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.utils.profile import BuildProfile

logger = get_logger(__name__)

# Thread-local storage for rendering pipelines.
# NOTE: Pipelines are reused per thread (not per page) for performance.
#       Each thread gets its own pipeline instance to avoid contention.
_thread_local = threading.local()


# Thread-safe output lock for parallel processing.
# NOTE: Used to serialize print/log output when multiple threads render pages concurrently.
_print_lock = Lock()


@dataclass
class Site(
    SitePropertiesMixin,
    PageCachesMixin,
    SiteFactoriesMixin,
    ContentDiscoveryMixin,
    ThemeIntegrationMixin,
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
    # Localized menus when i18n is enabled: {lang: {menu_name: [MenuItem]}}.
    # NOTE: Populated by MenuBuilder when i18n is configured. See: bengal/core/menu.py
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)
    # Current language context for rendering (set per page during rendering).
    # NOTE: Used by template functions to return localized content. Set by RenderingPipeline.
    current_language: str | None = None
    # Global data from data/ directory (YAML, JSON, TOML files).
    # NOTE: Loaded from site root data/ directory. Accessible in templates as site.data.
    data: Any = field(default_factory=dict)

    # Private caches for expensive properties (invalidated when pages change)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _generated_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _listable_pages_cache: list[Page] | None = field(default=None, repr=False, init=False)
    _theme_obj: Theme | None = field(default=None, repr=False, init=False)
    _query_registry: Any = field(default=None, repr=False, init=False)

    # Section registry for path-based lookups (O(1) section access by path)
    _section_registry: dict[Path, Section] = field(default_factory=dict, repr=False, init=False)

    # Section URL registry for virtual sections (O(1) section access by URL)
    # See: plan/active/rfc-page-section-reference-contract.md
    _section_url_registry: dict[str, Section] = field(default_factory=dict, repr=False, init=False)

    # Config hash for cache invalidation (computed on init)
    _config_hash: str | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)

        # Ensure root_path is always absolute to eliminate CWD-dependent behavior.
        # See: plan/active/rfc-path-resolution-architecture.md
        if not self.root_path.is_absolute():
            self.root_path = self.root_path.resolve()

        theme_section = self.config.get("theme", {})
        if isinstance(theme_section, dict):
            self.theme = theme_section.get("name", "default")
        else:
            # Fallback for legacy config where theme was a string
            self.theme = theme_section if isinstance(theme_section, str) else "default"

        self._theme_obj = Theme.from_config(self.config)

        if "output_dir" in self.config:
            self.output_dir = Path(self.config["output_dir"])

        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir

        self.data = self._load_data_directory()
        self._compute_config_hash()

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
            profile_templates: Enable template profiling for performance analysis

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
            profile_templates=profile_templates,
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
            self,
            host=host,
            port=port,
            watch=watch,
            auto_port=auto_port,
            open_browser=open_browser,
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
            logger.debug("cleaning_output_dir", path=str(self.output_dir))
            shutil.rmtree(self.output_dir)
            logger.debug("output_dir_cleaned", path=str(self.output_dir))
        else:
            logger.debug("output_dir_does_not_exist", path=str(self.output_dir))

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

        # Section registries (rebuilt from sections)
        self._section_registry = {}
        self._section_url_registry = {}

    def __repr__(self) -> str:
        return f"Site(pages={len(self.pages)}, sections={len(self.sections)}, assets={len(self.assets)})"

