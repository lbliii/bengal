"""
Site Object - Represents the entire website and orchestrates the build.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures
import threading
from datetime import datetime
from threading import Lock

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.asset import Asset
from bengal.core.menu import MenuItem, MenuBuilder
from bengal.utils.pagination import Paginator
from bengal.rendering.pipeline import RenderingPipeline
from bengal.utils.build_stats import BuildStats
from bengal.health import HealthCheck
from bengal.health.validators import (
    OutputValidator,
    ConfigValidatorWrapper,
    MenuValidator,
    LinkValidatorWrapper,
    NavigationValidator,
    TaxonomyValidator,
    RenderingValidator,
    CacheValidator,
    PerformanceValidator,
)

# Thread-local storage for pipelines (reuse per thread, not per page!)
_thread_local = threading.local()


# Thread-safe output lock for parallel processing
_print_lock = Lock()


@dataclass
class Site:
    """
    Represents the entire website and orchestrates the build process.
    
    Attributes:
        root_path: Root directory of the site
        config: Site configuration dictionary
        pages: All pages in the site
        sections: All sections in the site
        assets: All assets in the site
        theme: Theme name or path
        output_dir: Output directory for built site
        build_time: Timestamp of the last build
        taxonomies: Collected taxonomies (tags, categories, etc.)
    """
    
    root_path: Path
    config: Dict[str, Any] = field(default_factory=dict)
    pages: List[Page] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    theme: Optional[str] = None
    output_dir: Path = field(default_factory=lambda: Path("public"))
    build_time: Optional[datetime] = None
    taxonomies: Dict[str, Dict[str, List[Page]]] = field(default_factory=dict)
    menu: Dict[str, List[MenuItem]] = field(default_factory=dict)
    menu_builders: Dict[str, MenuBuilder] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialize site from configuration."""
        self.theme = self.config.get("theme", "default")
        
        if "output_dir" in self.config:
            self.output_dir = Path(self.config["output_dir"])
        
        # Make output_dir absolute relative to root_path
        if not self.output_dir.is_absolute():
            self.output_dir = self.root_path / self.output_dir
    
    @property
    def regular_pages(self) -> List[Page]:
        """
        Get only regular content pages (excludes generated taxonomy/archive pages).
        
        Returns:
            List of regular Page objects (excludes tag pages, archive pages, etc.)
            
        Example:
            {% for page in site.regular_pages %}
                <article>{{ page.title }}</article>
            {% endfor %}
        """
        return [p for p in self.pages if not p.metadata.get('_generated')]
    
    @classmethod
    def from_config(cls, root_path: Path, config_path: Optional[Path] = None) -> 'Site':
        """
        Create a Site instance from a configuration file.
        
        Args:
            root_path: Root directory of the site
            config_path: Optional path to config file (auto-detected if not provided)
            
        Returns:
            Configured Site instance
        """
        from bengal.config.loader import ConfigLoader
        
        loader = ConfigLoader(root_path)
        config = loader.load(config_path)
        
        return cls(root_path=root_path, config=config)
    
    def discover_content(self, content_dir: Optional[Path] = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.
        
        Args:
            content_dir: Content directory path (defaults to root_path/content)
        """
        if content_dir is None:
            content_dir = self.root_path / "content"
        
        if not content_dir.exists():
            print(f"Warning: Content directory {content_dir} does not exist")
            return
        
        from bengal.discovery.content_discovery import ContentDiscovery
        
        discovery = ContentDiscovery(content_dir)
        self.sections, self.pages = discovery.discover()
        
        # Set up page references for navigation
        self._setup_page_references()
        
        # Apply cascading frontmatter from sections to pages
        self._apply_cascades()
    
    def discover_assets(self, assets_dir: Optional[Path] = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.
        
        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.discovery.asset_discovery import AssetDiscovery
        
        self.assets = []
        
        # Discover theme assets first (lower priority)
        if self.theme:
            theme_assets_dir = self._get_theme_assets_dir()
            if theme_assets_dir and theme_assets_dir.exists():
                # Removed verbose message - shown in stats instead
                pass
                theme_discovery = AssetDiscovery(theme_assets_dir)
                self.assets.extend(theme_discovery.discover())
        
        # Discover site assets (higher priority, can override theme assets)
        if assets_dir is None:
            assets_dir = self.root_path / "assets"
        
        if assets_dir.exists():
            print(f"  Discovering site assets from {assets_dir}")
            site_discovery = AssetDiscovery(assets_dir)
            self.assets.extend(site_discovery.discover())
        elif not self.assets:
            # Only warn if we have no theme assets either
            print(f"Warning: Assets directory {assets_dir} does not exist")
    
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
        """
        # Process all top-level sections (they will recurse to subsections)
        for section in self.sections:
            self._apply_section_cascade(section, parent_cascade=None)
    
    def _apply_section_cascade(self, section: Section, parent_cascade: Optional[Dict[str, Any]] = None) -> None:
        """
        Recursively apply cascade metadata to a section and its descendants.
        
        Cascade metadata accumulates through the hierarchy - child sections inherit
        and can extend parent cascades.
        
        Args:
            section: Section to process
            parent_cascade: Cascade metadata inherited from parent sections
        """
        # Merge parent cascade with this section's cascade
        accumulated_cascade = {}
        
        if parent_cascade:
            accumulated_cascade.update(parent_cascade)
        
        if 'cascade' in section.metadata:
            # Section's cascade extends/overrides parent cascade
            accumulated_cascade.update(section.metadata['cascade'])
        
        # Apply accumulated cascade to all pages in this section
        # (but only for keys not already defined in page metadata)
        for page in section.pages:
            if accumulated_cascade:
                for key, value in accumulated_cascade.items():
                    # Page metadata takes precedence over cascade
                    if key not in page.metadata:
                        page.metadata[key] = value
        
        # Recursively apply to subsections with accumulated cascade
        for subsection in section.subsections:
            self._apply_section_cascade(subsection, accumulated_cascade)
    
    def _get_theme_assets_dir(self) -> Optional[Path]:
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
    
    def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False) -> BuildStats:
        """
        Build the entire site.
        
        Delegates to BuildOrchestrator for actual build process.
        
        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            
        Returns:
            BuildStats object with build statistics
        """
        from bengal.orchestration import BuildOrchestrator
        
        orchestrator = BuildOrchestrator(self)
        return orchestrator.build(parallel=parallel, incremental=incremental, verbose=verbose)
    
    def serve(self, host: str = "localhost", port: int = 8000, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None:
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
        
        server = DevServer(self, host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser)
        server.start()
    
    def clean(self) -> None:
        """Clean the output directory."""
        import shutil
        
        if self.output_dir.exists():
            print(f"Cleaning {self.output_dir}...")
            shutil.rmtree(self.output_dir)
            print("✓ Output directory cleaned")
        else:
            print("Output directory does not exist, nothing to clean")
    
    def __repr__(self) -> str:
        return f"Site(pages={len(self.pages)}, sections={len(self.sections)}, assets={len(self.assets)})"

