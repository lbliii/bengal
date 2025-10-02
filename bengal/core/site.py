"""
Site Object - Represents the entire website and orchestrates the build.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import concurrent.futures
from datetime import datetime

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.asset import Asset
from bengal.utils.pagination import Paginator


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
    
    def build(self, parallel: bool = True, incremental: bool = False) -> None:
        """
        Build the entire site.
        
        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
        """
        print(f"Building site at {self.root_path}...")
        self.build_time = datetime.now()
        
        # Discover content and assets
        self.discover_content()
        self.discover_assets()
        
        # Collect taxonomies (tags, categories, etc.)
        self.collect_taxonomies()
        
        # Generate dynamic pages (archives, tag pages, etc.)
        self.generate_dynamic_pages()
        
        # Initialize rendering pipeline
        from bengal.rendering.pipeline import RenderingPipeline
        
        pipeline = RenderingPipeline(self)
        
        # Build pages
        if parallel:
            self._build_parallel(pipeline)
        else:
            self._build_sequential(pipeline)
        
        # Copy and optimize assets
        self._process_assets()
        
        # Post-processing
        self._post_process()
        
        print(f"✓ Site built successfully in {self.output_dir}")
    
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
            pipeline: Rendering pipeline instance
        """
        max_workers = self.config.get("max_workers", 4)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(pipeline.process_page, page) for page in self.pages]
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing page: {e}")
    
    def _process_assets(self) -> None:
        """Process and copy all assets to output directory."""
        print(f"Processing {len(self.assets)} assets...")
        
        minify = self.config.get("minify_assets", True)
        optimize = self.config.get("optimize_assets", True)
        fingerprint = self.config.get("fingerprint_assets", True)
        
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
    
    def _post_process(self) -> None:
        """Perform post-processing tasks (sitemap, RSS, link validation, etc.)."""
        print("Running post-processing...")
        
        # Generate sitemap
        if self.config.get("generate_sitemap", True):
            from bengal.postprocess.sitemap import SitemapGenerator
            generator = SitemapGenerator(self)
            generator.generate()
        
        # Generate RSS feed
        if self.config.get("generate_rss", True):
            from bengal.postprocess.rss import RSSGenerator
            generator = RSSGenerator(self)
            generator.generate()
        
        # Validate links
        if self.config.get("validate_links", True):
            from bengal.rendering.link_validator import LinkValidator
            validator = LinkValidator()
            broken_links = validator.validate_site(self)
            if broken_links:
                print(f"Warning: Found {len(broken_links)} broken links")
    
    def serve(self, host: str = "localhost", port: int = 8000, watch: bool = True) -> None:
        """
        Start a development server.
        
        Args:
            host: Server host
            port: Server port
            watch: Whether to watch for file changes and rebuild
        """
        from bengal.server.dev_server import DevServer
        
        server = DevServer(self, host=host, port=port, watch=watch)
        server.start()
    
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
        
        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            # Create virtual page
            archive_page = Page(
                source_path=section.path / f"_generated_archive_p{page_num}.md",
                content="",
                metadata={
                    'title': f"{section.title}",
                    'template': 'archive.html',
                    'type': 'archive',
                    '_generated': True,
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
        tag_index = Page(
            source_path=self.root_path / "_generated_tags_index.md",
            content="",
            metadata={
                'title': 'All Tags',
                'template': 'tags.html',
                'type': 'tag-index',
                '_generated': True,
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
        
        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            tag_page = Page(
                source_path=self.root_path / f"_generated_tag_{tag_slug}_p{page_num}.md",
                content="",
                metadata={
                    'title': f"Posts tagged '{tag_data['name']}'",
                    'template': 'tag.html',
                    'type': 'tag',
                    '_generated': True,
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

