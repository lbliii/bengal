"""
Site Object - Represents the entire website and orchestrates the build.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures
from datetime import datetime
from threading import Lock

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.asset import Asset
from bengal.core.menu import MenuItem, MenuBuilder
from bengal.utils.pagination import Paginator
from bengal.rendering.pipeline import RenderingPipeline


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
                print(f"  Discovering theme assets from {theme_assets_dir}")
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
    
    def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False) -> 'BuildStats':
        """
        Build the entire site.
        
        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show detailed build information
            
        Returns:
            BuildStats object with build statistics
        """
        from bengal.rendering.pipeline import RenderingPipeline
        from bengal.cache import BuildCache, DependencyTracker
        from bengal.utils.build_stats import BuildStats
        import time
        
        # Start timing
        build_start = time.time()
        
        # Initialize stats
        stats = BuildStats(parallel=parallel, incremental=incremental)
        
        print(f"Building site at {self.root_path}...")
        self.build_time = datetime.now()
        
        # Initialize cache and tracker
        cache_path = self.output_dir / ".bengal-cache.json"
        cache = BuildCache.load(cache_path) if incremental else BuildCache()
        tracker = DependencyTracker(cache)
        
        # Discover content and assets
        discovery_start = time.time()
        self.discover_content()
        self.discover_assets()
        stats.discovery_time_ms = (time.time() - discovery_start) * 1000
        
        # Track config file as a global dependency
        config_files = [
            self.root_path / "bengal.toml",
            self.root_path / "bengal.yaml",
            self.root_path / "bengal.yml"
        ]
        config_file = next((f for f in config_files if f.exists()), None)
        
        if config_file:
            if incremental:
                # Check if config changed - if so, force full rebuild
                if cache.is_changed(config_file):
                    print("  Config file changed - performing full rebuild")
                    incremental = False
                    cache.clear()
            # Always update config file hash (for next build)
            cache.update_file(config_file)
        
        # Collect taxonomies (tags, categories, etc.)
        taxonomy_start = time.time()
        self.collect_taxonomies()
        
        # Generate dynamic pages (archives, tag pages, etc.)
        self.generate_dynamic_pages()
        
        # Build navigation menus
        self.build_menus()
        stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
        
        # Determine what to build
        pages_to_build = self.pages
        assets_to_process = self.assets
        
        if incremental:
            pages_to_build, assets_to_process, change_summary = self._find_incremental_work(
                cache, tracker, verbose=verbose
            )
            
            if not pages_to_build and not assets_to_process:
                print("✓ No changes detected - skipping build")
                stats.skipped = True
                stats.build_time_ms = (time.time() - build_start) * 1000
                return stats
            
            print(f"  Incremental build: {len(pages_to_build)} pages, "
                  f"{len(assets_to_process)} assets")
            
            if verbose and change_summary:
                print(f"\n  📝 Changes detected:")
                for change_type, items in change_summary.items():
                    if items:
                        print(f"    • {change_type}: {len(items)} file(s)")
                        for item in items[:5]:  # Show first 5
                            print(f"      - {item.name if hasattr(item, 'name') else item}")
                        if len(items) > 5:
                            print(f"      ... and {len(items) - 5} more")
                print()
        
        # Initialize rendering pipeline with tracker
        pipeline = RenderingPipeline(self, tracker)
        
        # Build pages
        rendering_start = time.time()
        original_pages = self.pages
        self.pages = pages_to_build  # Temporarily replace with subset
        
        if parallel and len(pages_to_build) > 1:
            self._build_parallel(pipeline)
        else:
            self._build_sequential(pipeline)
        
        self.pages = original_pages  # Restore full page list
        stats.rendering_time_ms = (time.time() - rendering_start) * 1000
        
        # Copy and optimize assets
        assets_start = time.time()
        original_assets = self.assets
        self.assets = assets_to_process  # Temporarily replace with subset
        self._process_assets()
        self.assets = original_assets  # Restore full asset list
        stats.assets_time_ms = (time.time() - assets_start) * 1000
        
        # Post-processing
        postprocess_start = time.time()
        self._post_process()
        stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000
        
        # Update cache with all processed files
        if incremental or self.config.get("cache_enabled", True):
            # Update all page hashes and tags (skip generated pages - they have virtual paths)
            for page in pages_to_build:
                if not page.metadata.get('_generated'):
                    cache.update_file(page.source_path)
                    # Store tags for next build's comparison
                    if page.tags:
                        cache.update_tags(page.source_path, set(page.tags))
                    else:
                        cache.update_tags(page.source_path, set())
            
            # Update all asset hashes
            for asset in assets_to_process:
                cache.update_file(asset.source_path)
            
            # Update template hashes (even if not changed, to track them)
            theme_templates_dir = self._get_theme_templates_dir()
            if theme_templates_dir and theme_templates_dir.exists():
                for template_file in theme_templates_dir.rglob("*.html"):
                    cache.update_file(template_file)
            
            # Save cache
            cache.save(cache_path)
        
        # Run build health checks
        self._validate_build_health()
        
        # Collect final stats
        stats.total_pages = len(self.pages)
        stats.regular_pages = len([p for p in self.pages if not p.metadata.get('_generated')])
        stats.generated_pages = len([p for p in self.pages if p.metadata.get('_generated')])
        stats.total_assets = len(self.assets)
        stats.total_sections = len(self.sections)
        stats.taxonomies_count = sum(len(terms) for terms in self.taxonomies.values())
        stats.build_time_ms = (time.time() - build_start) * 1000
        
        print(f"✓ Site built successfully in {self.output_dir}")
        
        return stats
    
    def _build_sequential(self, pipeline: Any) -> None:
        """
        Build pages sequentially.
        
        Args:
            pipeline: Rendering pipeline instance
        """
        for page in self.pages:
            pipeline.process_page(page)
    
    def _build_parallel(self, pipeline: Any) -> None:
        """
        Build pages in parallel for better performance.
        
        Args:
            pipeline: Rendering pipeline instance (template for creating thread-local copies)
        """
        max_workers = self.config.get("max_workers", 4)
        tracker = pipeline.dependency_tracker
        
        def process_page_with_pipeline(page):
            """Process a page with its own pipeline instance (thread-safe)."""
            # Create a new pipeline instance for this thread with tracker set in constructor
            thread_pipeline = RenderingPipeline(self, tracker)
            thread_pipeline.process_page(page)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_page_with_pipeline, page) for page in self.pages]
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing page: {e}")
    
    def _process_assets(self) -> None:
        """Process and copy all assets to output directory."""
        if not self.assets:
            return
        
        print(f"Processing {len(self.assets)} assets...")
        
        # Get configuration
        minify = self.config.get("minify_assets", True)
        optimize = self.config.get("optimize_assets", True)
        fingerprint = self.config.get("fingerprint_assets", True)
        parallel = self.config.get("parallel", True)
        
        # Use parallel processing only for larger workloads to avoid overhead
        # Threshold of 5 assets balances parallelism benefit vs thread overhead
        MIN_ASSETS_FOR_PARALLEL = 5
        
        if parallel and len(self.assets) >= MIN_ASSETS_FOR_PARALLEL:
            self._process_assets_parallel(minify, optimize, fingerprint)
        else:
            self._process_assets_sequential(minify, optimize, fingerprint)
    
    def _process_assets_sequential(self, minify: bool, optimize: bool, fingerprint: bool) -> None:
        """Process assets sequentially (fallback or for small workloads)."""
        assets_output = self.output_dir / "assets"
        
        for asset in self.assets:
            try:
                if minify and asset.asset_type in ('css', 'javascript'):
                    asset.minify()
                
                if optimize and asset.asset_type == 'image':
                    asset.optimize()
                
                asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
            except Exception as e:
                print(f"Warning: Failed to process asset {asset.source_path}: {e}")
    
    def _process_assets_parallel(self, minify: bool, optimize: bool, fingerprint: bool) -> None:
        """Process assets in parallel for better performance."""
        assets_output = self.output_dir / "assets"
        max_workers = self.config.get("max_workers", min(8, (len(self.assets) + 3) // 4))
        
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._process_single_asset,
                    asset,
                    assets_output,
                    minify,
                    optimize,
                    fingerprint
                )
                for asset in self.assets
            ]
            
            # Collect results and errors
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(str(e))
        
        # Report errors after all processing is complete
        if errors:
            with _print_lock:
                print(f"  ⚠️  {len(errors)} asset(s) failed to process:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"    • {error}")
                if len(errors) > 5:
                    print(f"    ... and {len(errors) - 5} more errors")
    
    def _process_single_asset(
        self,
        asset: Asset,
        assets_output: Path,
        minify: bool,
        optimize: bool,
        fingerprint: bool
    ) -> None:
        """
        Process a single asset (called in parallel).
        
        Args:
            asset: Asset to process
            assets_output: Output directory for assets
            minify: Whether to minify CSS/JS
            optimize: Whether to optimize images
            fingerprint: Whether to add fingerprint to filename
        
        Raises:
            Exception: If asset processing fails
        """
        try:
            if minify and asset.asset_type in ('css', 'javascript'):
                asset.minify()
            
            if optimize and asset.asset_type == 'image':
                asset.optimize()
            
            asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
        except Exception as e:
            # Re-raise with asset context for better error messages
            raise Exception(f"Failed to process {asset.source_path}: {e}") from e
    
    def _post_process(self) -> None:
        """Perform post-processing tasks (sitemap, RSS, link validation, etc.)."""
        print("Running post-processing...")
        
        # Collect enabled tasks
        tasks = []
        
        if self.config.get("generate_sitemap", True):
            tasks.append(('sitemap', self._generate_sitemap))
        
        if self.config.get("generate_rss", True):
            tasks.append(('rss', self._generate_rss))
        
        if self.config.get("validate_links", True):
            tasks.append(('link validation', self._validate_links))
        
        if not tasks:
            return
        
        # Run in parallel if enabled and multiple tasks
        # Threshold of 2 tasks (always parallel if multiple tasks since they're independent)
        parallel = self.config.get("parallel", True)
        
        if parallel and len(tasks) > 1:
            self._run_postprocess_parallel(tasks)
        else:
            self._run_postprocess_sequential(tasks)
    
    def _run_postprocess_sequential(self, tasks: List[tuple]) -> None:
        """Run post-processing tasks sequentially."""
        for task_name, task_fn in tasks:
            try:
                task_fn()
            except Exception as e:
                with _print_lock:
                    print(f"  ✗ {task_name}: {e}")
    
    def _run_postprocess_parallel(self, tasks: List[tuple]) -> None:
        """Run post-processing tasks in parallel."""
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(task_fn): name for name, task_fn in tasks}
            
            for future in concurrent.futures.as_completed(futures):
                task_name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    errors.append((task_name, str(e)))
        
        # Report errors
        if errors:
            with _print_lock:
                print(f"  ⚠️  {len(errors)} post-processing task(s) failed:")
                for task_name, error in errors:
                    print(f"    • {task_name}: {error}")
    
    def _generate_sitemap(self) -> None:
        """Generate sitemap (extracted for parallel execution)."""
        from bengal.postprocess.sitemap import SitemapGenerator
        generator = SitemapGenerator(self)
        generator.generate()
    
    def _generate_rss(self) -> None:
        """Generate RSS feed (extracted for parallel execution)."""
        from bengal.postprocess.rss import RSSGenerator
        generator = RSSGenerator(self)
        generator.generate()
    
    def _validate_links(self) -> None:
        """Validate links (extracted for parallel execution)."""
        from bengal.rendering.link_validator import LinkValidator
        validator = LinkValidator()
        broken_links = validator.validate_site(self)
        if broken_links:
            with _print_lock:
                print(f"Warning: Found {len(broken_links)} broken links")
    
    def _find_incremental_work(self, cache: Any, tracker: Any, verbose: bool = False) -> tuple[List[Page], List[Asset], Dict[str, List]]:
        """
        Determine which pages and assets need to be rebuilt based on changes.
        
        Args:
            cache: BuildCache instance
            tracker: DependencyTracker instance
            verbose: Whether to collect detailed change information
            
        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        from bengal.cache import BuildCache
        
        pages_to_rebuild = set()
        assets_to_process = []
        change_summary = {
            'Modified content': [],
            'Modified assets': [],
            'Modified templates': [],
            'Taxonomy changes': []
        }
        
        # Find changed content files (skip generated pages - they have virtual paths)
        for page in self.pages:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get('_generated'):
                continue
                
            if cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary['Modified content'].append(page.source_path)
                # Track taxonomy changes
                if page.tags:
                    tracker.track_taxonomy(page.source_path, set(page.tags))
        
        # Find changed assets
        for asset in self.assets:
            if cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary['Modified assets'].append(asset.source_path)
        
        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        changed_templates = []
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if cache.is_changed(template_file):
                    changed_templates.append(template_file)
                    if verbose:
                        change_summary['Modified templates'].append(template_file)
                    # Template changed - find affected pages
                    affected = cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    cache.update_file(template_file)
        
        # Check for SPECIFIC taxonomy changes (which exact tags were added/removed)
        # Only rebuild tag pages for tags that actually changed
        affected_tags = set()
        affected_sections = set()
        
        for page in self.pages:
            # Skip generated pages - they don't have real source files
            if page.metadata.get('_generated'):
                continue
            
            # Check if this page changed
            if page.source_path in pages_to_rebuild:
                # Get old and new tags
                old_tags = cache.get_previous_tags(page.source_path)
                new_tags = set(page.tags) if page.tags else set()
                
                # Find which specific tags changed
                added_tags = new_tags - old_tags
                removed_tags = old_tags - new_tags
                
                # Track affected tags
                for tag in (added_tags | removed_tags):
                    affected_tags.add(tag.lower().replace(' ', '-'))
                    if verbose:
                        change_summary['Taxonomy changes'].append(
                            f"Tag '{tag}' changed on {page.source_path.name}"
                        )
                
                # Check if page changed sections (affects archive pages)
                # For now, mark section as affected if page changed
                if hasattr(page, 'section'):
                    affected_sections.add(page.section)
        
        # Only rebuild specific tag pages that were affected
        if affected_tags:
            for page in self.pages:
                if page.metadata.get('_generated'):
                    # Rebuild tag pages only for affected tags
                    if page.metadata.get('type') == 'tag' or page.metadata.get('type') == 'tag-index':
                        tag_slug = page.metadata.get('_tag_slug')
                        if tag_slug and tag_slug in affected_tags:
                            pages_to_rebuild.add(page.source_path)
                        # Always rebuild tag index if any tags changed
                        elif page.metadata.get('type') == 'tag-index':
                            pages_to_rebuild.add(page.source_path)
        
        # Rebuild archive pages only for affected sections
        if affected_sections:
            for page in self.pages:
                if page.metadata.get('_generated'):
                    if page.metadata.get('type') == 'archive':
                        page_section = page.metadata.get('_section')
                        if page_section and page_section in affected_sections:
                            pages_to_rebuild.add(page.source_path)
        
        # Convert page paths back to Page objects
        pages_to_build = [
            page for page in self.pages 
            if page.source_path in pages_to_rebuild
        ]
        
        return pages_to_build, assets_to_process, change_summary
    
    def _get_theme_templates_dir(self) -> Optional[Path]:
        """
        Get the templates directory for the current theme.
        
        Returns:
            Path to theme templates or None if not found
        """
        if not self.theme:
            return None
        
        # Check in site's themes directory first
        site_theme_dir = self.root_path / "themes" / self.theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir
        
        # Check in Bengal's bundled themes
        import bengal
        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir
        
        return None
    
    def serve(self, host: str = "localhost", port: int = 8000, watch: bool = True, auto_port: bool = True) -> None:
        """
        Start a development server.
        
        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
            auto_port: Whether to automatically find an available port if the specified one is in use
        """
        from bengal.server.dev_server import DevServer
        
        server = DevServer(self, host=host, port=port, watch=watch, auto_port=auto_port)
        server.start()
    
    def _validate_build_health(self) -> None:
        """
        Validate build output quality after building.
        
        Run basic health checks to catch obvious issues like:
        - Pages that are suspiciously small (likely fallback HTML)
        - Missing theme assets
        - Unrendered Jinja2 syntax
        """
        if not self.config.get("validate_build", True):
            return
        
        issues = []
        strict_mode = self.config.get("strict_mode", False)
        
        # Check 1: Are all pages large enough?
        min_size = self.config.get("min_page_size", 1000)  # 1KB minimum
        for page in self.pages:
            if page.output_path and page.output_path.exists():
                size = page.output_path.stat().st_size
                if size < min_size:
                    issues.append(
                        f"Page {page.output_path.relative_to(self.output_dir)} "
                        f"is suspiciously small ({size} bytes, expected >{min_size})"
                    )
        
        # Check 2: Are theme assets present?
        assets_dir = self.output_dir / "assets"
        if assets_dir.exists():
            css_count = len(list(assets_dir.glob("css/*.css")))
            js_count = len(list(assets_dir.glob("js/*.js")))
            
            if css_count == 0:
                issues.append("No CSS files found in output (theme may not be applied)")
            if js_count == 0 and self.config.get("theme") == "default":
                # JS files are expected for default theme
                issues.append("No JS files found in output")
        else:
            issues.append("No assets directory found in output")
        
        # Check 3: Any unrendered Jinja2 syntax?
        unrendered_count = 0
        ignore_files = self.config.get("health_check_ignore_files", [])
        for html_file in self.output_dir.rglob("*.html"):
            # Skip files in ignore list (e.g., docs with intentional Jinja2 examples)
            rel_path = str(html_file.relative_to(self.output_dir))
            if any(rel_path == ignore or rel_path.endswith(ignore) for ignore in ignore_files):
                continue
            
            try:
                content = html_file.read_text()
                
                # Check for obvious unrendered syntax, but skip code blocks
                if "{{ page." in content or "{% if page" in content or "{{ site." in content:
                    # Might be unrendered, but could be in code blocks (documentation)
                    # Use smarter detection to avoid false positives
                    if self._has_unrendered_jinja2(content):
                        unrendered_count += 1
                        if unrendered_count <= 3:  # Only report first few
                            issues.append(
                                f"Unrendered Jinja2 syntax in {html_file.relative_to(self.output_dir)}"
                            )
            except Exception:
                # Ignore files we can't read
                pass
        
        if unrendered_count > 3:
            issues.append(f"... and {unrendered_count - 3} more files with unrendered syntax")
        
        # Report issues
        if issues:
            print("\n⚠️  Build Health Check Issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  • {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more issues")
            
            if strict_mode:
                # In strict mode, health check failures should fail the build
                raise Exception(
                    f"Build failed health checks: {len(issues)} issue(s) found. "
                    "Review output or disable strict_mode."
                )
            else:
                print("  (These may be acceptable in production - review output)")
    
    def _has_unrendered_jinja2(self, html_content: str) -> bool:
        """
        Detect if HTML has unrendered Jinja2 syntax (not in code blocks).
        
        Distinguishes between:
        - Actual unrendered templates (bad) 
        - Documented/escaped syntax in code blocks (ok)
        
        Args:
            html_content: HTML content to check
            
        Returns:
            True if unrendered Jinja2 found (not in code blocks)
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove all code blocks first (they're allowed to have Jinja2 syntax)
            for code_block in soup.find_all(['code', 'pre']):
                code_block.decompose()
            
            # Now check the remaining HTML for Jinja2 syntax
            remaining_text = soup.get_text()
            
            # Check for unrendered syntax patterns
            jinja2_patterns = [
                '{{ page.',
                '{{ site.',
                '{% if page',
                '{% if site',
                '{% for page',
                '{% for site'
            ]
            
            for pattern in jinja2_patterns:
                if pattern in remaining_text:
                    return True
            
            return False
            
        except ImportError:
            # BeautifulSoup not available, fall back to simple check
            # (will have false positives for docs with code examples)
            return ('{{ page.' in html_content or 
                    '{{ site.' in html_content or 
                    '{% if page' in html_content)
        except Exception:
            # On any parsing error, assume it's ok to avoid false positives
            return False
    
    def collect_taxonomies(self) -> None:
        """
        Collect taxonomies (tags, categories, etc.) from all pages.
        Organizes pages by their taxonomic terms.
        """
        print("  Collecting taxonomies...")
        
        # Initialize taxonomy structure
        self.taxonomies = {'tags': {}, 'categories': {}}
        
        # Collect from all pages
        for page in self.pages:
            # Collect tags
            if page.tags:
                for tag in page.tags:
                    tag_key = tag.lower().replace(' ', '-')
                    if tag_key not in self.taxonomies['tags']:
                        self.taxonomies['tags'][tag_key] = {
                            'name': tag,
                            'slug': tag_key,
                            'pages': []
                        }
                    self.taxonomies['tags'][tag_key]['pages'].append(page)
            
            # Collect categories (if present in metadata)
            if 'category' in page.metadata:
                category = page.metadata['category']
                cat_key = category.lower().replace(' ', '-')
                if cat_key not in self.taxonomies['categories']:
                    self.taxonomies['categories'][cat_key] = {
                        'name': category,
                        'slug': cat_key,
                        'pages': []
                    }
                self.taxonomies['categories'][cat_key]['pages'].append(page)
        
        # Sort pages within each taxonomy by date (newest first)
        for taxonomy_type in self.taxonomies:
            for term_data in self.taxonomies[taxonomy_type].values():
                term_data['pages'].sort(
                    key=lambda p: p.date if p.date else datetime.min,
                    reverse=True
                )
        
        tag_count = len(self.taxonomies.get('tags', {}))
        cat_count = len(self.taxonomies.get('categories', {}))
        print(f"  ✓ Found {tag_count} tags, {cat_count} categories")
    
    def generate_dynamic_pages(self) -> None:
        """
        Generate dynamic pages (archives, tag pages, etc.) that don't have source files.
        """
        print("  Generating dynamic pages...")
        
        generated_count = 0
        
        # Generate section archive pages (with pagination)
        for section in self.sections:
            if section.pages and section.name != 'root':
                # Create archive pages for this section (may create multiple for pagination)
                archive_pages = self._create_archive_pages(section)
                for page in archive_pages:
                    self.pages.append(page)
                    generated_count += 1
        
        # Generate tag pages
        if self.taxonomies.get('tags'):
            # Create tag index page
            tag_index = self._create_tag_index_page()
            if tag_index:
                self.pages.append(tag_index)
                generated_count += 1
            
            # Create individual tag pages (with pagination)
            for tag_slug, tag_data in self.taxonomies['tags'].items():
                tag_pages = self._create_tag_pages(tag_slug, tag_data)
                for page in tag_pages:
                    self.pages.append(page)
                    generated_count += 1
        
        print(f"  ✓ Generated {generated_count} dynamic pages")
    
    def _create_archive_pages(self, section: Section) -> List[Page]:
        """Create archive pages for a section (with pagination if needed)."""
        # Don't create if section already has an index page
        if section.index_page:
            return []
        
        pages_to_create = []
        per_page = self.config.get('pagination', {}).get('per_page', 10)
        
        # Create paginator
        paginator = Paginator(section.pages, per_page=per_page)
        
        # Use dedicated virtual namespace for generated pages
        virtual_base = self.root_path / ".bengal" / "generated"
        
        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            # Create unique, namespaced virtual path
            virtual_path = virtual_base / "archives" / section.name / f"page_{page_num}.md"
            
            # Validate it doesn't exist (should never happen with .bengal namespace)
            if virtual_path.exists():
                print(f"⚠️  Warning: Virtual path conflict: {virtual_path} exists as real file")
            
            # Create virtual page
            archive_page = Page(
                source_path=virtual_path,
                content="",
                metadata={
                    'title': f"{section.title}",
                    'template': 'archive.html',
                    'type': 'archive',
                    '_generated': True,
                    '_virtual': True,  # Flag for special handling
                    '_section': section,
                    '_posts': section.pages,
                    '_paginator': paginator,
                    '_page_num': page_num
                }
            )
            
            # Set output path
            if page_num == 1:
                archive_page.output_path = self.output_dir / section.name / "index.html"
            else:
                archive_page.output_path = self.output_dir / section.name / f"page/{page_num}/index.html"
            
            pages_to_create.append(archive_page)
        
        return pages_to_create
    
    def _create_tag_index_page(self) -> Page:
        """Create the main tags index page."""
        # Use dedicated virtual namespace
        virtual_base = self.root_path / ".bengal" / "generated"
        virtual_path = virtual_base / "tags" / "index.md"
        
        tag_index = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': 'All Tags',
                'template': 'tags.html',
                'type': 'tag-index',
                '_generated': True,
                '_virtual': True,
                '_tags': self.taxonomies['tags']
            }
        )
        
        tag_index.output_path = self.output_dir / "tags" / "index.html"
        return tag_index
    
    def _create_tag_pages(self, tag_slug: str, tag_data: Dict[str, Any]) -> List[Page]:
        """Create pages for an individual tag (with pagination if needed)."""
        pages_to_create = []
        per_page = self.config.get('pagination', {}).get('per_page', 10)
        
        # Create paginator
        paginator = Paginator(tag_data['pages'], per_page=per_page)
        
        # Use dedicated virtual namespace
        virtual_base = self.root_path / ".bengal" / "generated"
        
        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            # Create unique, namespaced virtual path
            virtual_path = virtual_base / "tags" / tag_slug / f"page_{page_num}.md"
            
            tag_page = Page(
                source_path=virtual_path,
                content="",
                metadata={
                    'title': f"Posts tagged '{tag_data['name']}'",
                    'template': 'tag.html',
                    'type': 'tag',
                    '_generated': True,
                    '_virtual': True,
                    '_tag': tag_data['name'],
                    '_tag_slug': tag_slug,
                    '_posts': tag_data['pages'],
                    '_paginator': paginator,
                    '_page_num': page_num
                }
            )
            
            # Set output path
            if page_num == 1:
                tag_page.output_path = self.output_dir / "tags" / tag_slug / "index.html"
            else:
                tag_page.output_path = self.output_dir / "tags" / tag_slug / f"page/{page_num}/index.html"
            
            pages_to_create.append(tag_page)
        
        return pages_to_create
    
    def build_menus(self) -> None:
        """
        Build all menus from config and page frontmatter.
        Called during site.build() after content discovery.
        """
        # Get menu definitions from config
        menu_config = self.config.get('menu', {})
        
        if not menu_config:
            # No menus defined, skip
            return
        
        verbose = self.config.get('verbose', False)
        if verbose:
            print("  Building navigation menus...")
        
        for menu_name, items in menu_config.items():
            builder = MenuBuilder()
            
            # Add config-defined items
            if isinstance(items, list):
                builder.add_from_config(items)
            
            # Add items from page frontmatter
            for page in self.pages:
                page_menu = page.metadata.get('menu', {})
                if menu_name in page_menu:
                    builder.add_from_page(page, menu_name, page_menu[menu_name])
            
            # Build hierarchy
            self.menu[menu_name] = builder.build_hierarchy()
            self.menu_builders[menu_name] = builder
            
            if verbose:
                print(f"    ✓ Built menu '{menu_name}': {len(self.menu[menu_name])} items")
    
    def mark_active_menu_items(self, current_page: Page) -> None:
        """
        Mark active menu items for the current page being rendered.
        Called during rendering for each page.
        
        Args:
            current_page: Page currently being rendered
        """
        current_url = current_page.url
        for menu_name, builder in self.menu_builders.items():
            builder.mark_active_items(current_url, self.menu[menu_name])
    
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

