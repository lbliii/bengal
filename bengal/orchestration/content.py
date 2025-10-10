"""
Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup,
and cascading frontmatter.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.section import Section


class ContentOrchestrator:
    """
    Handles content and asset discovery.
    
    Responsibilities:
        - Discover content (pages and sections)
        - Discover assets (site and theme)
        - Set up page/section references for navigation
        - Apply cascading frontmatter from sections to pages
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize content orchestrator.
        
        Args:
            site: Site instance to populate with content
        """
        self.site = site
        self.logger = get_logger(__name__)
    
    def discover(self) -> None:
        """
        Discover all content and assets.
        Main entry point called during build.
        """
        self.discover_content()
        self.discover_assets()
    
    def discover_content(self, content_dir: Optional[Path] = None) -> None:
        """
        Discover all content (pages, sections) in the content directory.
        
        Args:
            content_dir: Content directory path (defaults to root_path/content)
        """
        if content_dir is None:
            content_dir = self.site.root_path / "content"
        
        if not content_dir.exists():
            self.logger.warning("content_dir_not_found", path=str(content_dir))
            return
        
        self.logger.debug("discovering_content", path=str(content_dir))
        
        from bengal.discovery.content_discovery import ContentDiscovery
        
        discovery = ContentDiscovery(content_dir)
        self.site.sections, self.site.pages = discovery.discover()
        
        self.logger.debug("raw_content_discovered", 
                         pages=len(self.site.pages), 
                         sections=len(self.site.sections))
        
        # Set up page references for navigation
        self._setup_page_references()
        self.logger.debug("page_references_setup")
        
        # Apply cascading frontmatter from sections to pages
        self._apply_cascades()
        self.logger.debug("cascades_applied")
        
        # Build cross-reference index for O(1) lookups
        self._build_xref_index()
        self.logger.debug("xref_index_built", 
                         index_size=len(self.site.xref_index.get('by_path', {})))
    
    def discover_assets(self, assets_dir: Optional[Path] = None) -> None:
        """
        Discover all assets in the assets directory and theme assets.
        
        Args:
            assets_dir: Assets directory path (defaults to root_path/assets)
        """
        from bengal.discovery.asset_discovery import AssetDiscovery
        
        self.site.assets = []
        theme_asset_count = 0
        site_asset_count = 0
        
        # Discover theme assets first (lower priority)
        if self.site.theme:
            theme_assets_dir = self._get_theme_assets_dir()
            if theme_assets_dir and theme_assets_dir.exists():
                self.logger.debug("discovering_theme_assets", 
                                theme=self.site.theme,
                                path=str(theme_assets_dir))
                theme_discovery = AssetDiscovery(theme_assets_dir)
                theme_assets = theme_discovery.discover()
                self.site.assets.extend(theme_assets)
                theme_asset_count = len(theme_assets)
        
        # Discover site assets (higher priority, can override theme assets)
        if assets_dir is None:
            assets_dir = self.site.root_path / "assets"
        
        if assets_dir.exists():
            self.logger.debug("discovering_site_assets", path=str(assets_dir))
            site_discovery = AssetDiscovery(assets_dir)
            site_assets = site_discovery.discover()
            self.site.assets.extend(site_assets)
            site_asset_count = len(site_assets)
        elif not self.site.assets:
            # Only warn if we have no theme assets either
            self.logger.warning("assets_dir_not_found", path=str(assets_dir))
        
        self.logger.debug("assets_discovered",
                         theme_assets=theme_asset_count,
                         site_assets=site_asset_count,
                         total=len(self.site.assets))
    
    def _setup_page_references(self) -> None:
        """
        Set up page references for navigation (next, prev, parent, etc.).
        
        This method sets _site and _section references on all pages to enable
        navigation properties (next, prev, ancestors, etc.).
        
        Top-level pages (those not in any section) will have _section = None.
        """
        # Set site reference on all pages (including top-level pages)
        for page in self.site.pages:
            page._site = self.site
            # Initialize _section to None for pages not yet assigned
            if not hasattr(page, '_section'):
                page._section = None
        
        # Set section references
        for section in self.site.sections:
            # Set site reference on section
            section._site = self.site
            
            # Set section reference on all pages in this section
            for page in section.pages:
                page._section = section
            
            # Recursively set for subsections
            self._setup_section_references(section)
    
    def _setup_section_references(self, section: 'Section') -> None:
        """
        Recursively set up references for a section and its subsections.
        
        Args:
            section: Section to set up references for
        """
        for subsection in section.subsections:
            subsection._site = self.site
            
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
        # First, check for root-level cascade from top-level pages (like content/index.md)
        root_cascade = None
        for page in self.site.pages:
            # Check if this is a top-level page (not in any section)
            is_top_level = not any(page in section.pages for section in self.site.sections)
            if is_top_level and 'cascade' in page.metadata:
                # Found root-level cascade - merge it
                if root_cascade is None:
                    root_cascade = {}
                root_cascade.update(page.metadata['cascade'])
        
        # Process all top-level sections with root cascade (they will recurse to subsections)
        for section in self.site.sections:
            self._apply_section_cascade(section, parent_cascade=root_cascade)
        
        # Also apply root cascade to other top-level pages
        if root_cascade:
            for page in self.site.pages:
                is_top_level = not any(page in section.pages for section in self.site.sections)
                # Skip the page that defined the cascade itself
                if is_top_level and 'cascade' not in page.metadata:
                    for key, value in root_cascade.items():
                        if key not in page.metadata:
                            page.metadata[key] = value
    
    def _apply_section_cascade(self, section: 'Section', 
                              parent_cascade: Optional[Dict[str, Any]] = None) -> None:
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
    
    def _build_xref_index(self) -> None:
        """
        Build cross-reference index for O(1) page lookups.
        
        Creates multiple indices to support different reference styles:
        - by_path: Reference by file path (e.g., 'docs/installation')
        - by_slug: Reference by slug (e.g., 'installation')
        - by_id: Reference by custom ID from frontmatter (e.g., 'install-guide')
        - by_heading: Reference by heading text for anchor links
        
        Performance: O(n) build time, O(1) lookup time
        Thread-safe: Read-only after building, safe for parallel rendering
        """
        self.site.xref_index = {
            'by_path': {},      # 'docs/getting-started' -> Page
            'by_slug': {},      # 'getting-started' -> [Pages]
            'by_id': {},        # Custom IDs from frontmatter -> Page
            'by_heading': {},   # Heading text -> [(Page, anchor)]
        }
        
        content_dir = self.site.root_path / "content"
        
        for page in self.site.pages:
            # Index by relative path (without extension)
            try:
                rel_path = page.source_path.relative_to(content_dir)
                # Remove extension and normalize path separators
                path_key = str(rel_path.with_suffix('')).replace('\\', '/')
                # Also handle _index.md -> directory path
                if path_key.endswith('/_index'):
                    path_key = path_key[:-7]  # Remove '/_index'
                self.site.xref_index['by_path'][path_key] = page
            except ValueError:
                # Page is not relative to content_dir (e.g., generated page)
                pass
            
            # Index by slug (multiple pages can have same slug)
            if hasattr(page, 'slug') and page.slug:
                self.site.xref_index['by_slug'].setdefault(page.slug, []).append(page)
            
            # Index custom IDs from frontmatter
            if 'id' in page.metadata:
                ref_id = page.metadata['id']
                self.site.xref_index['by_id'][ref_id] = page
            
            # Index headings from TOC (for anchor links)
            # NOTE: This accesses toc_items BEFORE parsing (during discovery phase).
            # This is safe because toc_items property returns [] when toc is not set,
            # and importantly does NOT cache the empty result. After parsing, when
            # toc is set, the property will extract and cache the real structure.
            if hasattr(page, 'toc_items') and page.toc_items:
                for toc_item in page.toc_items:
                    heading_text = toc_item.get('title', '').lower()
                    anchor_id = toc_item.get('id', '')
                    if heading_text and anchor_id:
                        self.site.xref_index['by_heading'].setdefault(
                            heading_text, []
                        ).append((page, anchor_id))
    
    def _get_theme_assets_dir(self) -> Optional[Path]:
        """
        Get the assets directory for the current theme.
        
        Returns:
            Path to theme assets or None if not found
        """
        if not self.site.theme:
            return None
        
        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / self.site.theme / "assets"
        if site_theme_dir.exists():
            return site_theme_dir
        
        # Check in Bengal's bundled themes
        import bengal
        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.site.theme / "assets"
        if bundled_theme_dir.exists():
            return bundled_theme_dir
        
        return None

