"""
Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Set, Tuple, Optional, Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page
    from bengal.core.asset import Asset
    from bengal.cache import BuildCache, DependencyTracker


class IncrementalOrchestrator:
    """
    Handles incremental build logic.
    
    Responsibilities:
        - Cache initialization and management
        - Change detection (content, assets, templates)
        - Dependency tracking
        - Taxonomy change detection
        - Determining what needs rebuilding
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize incremental orchestrator.
        
        Args:
            site: Site instance for incremental builds
        """
        self.site = site
        self.cache: Optional['BuildCache'] = None
        self.tracker: Optional['DependencyTracker'] = None
    
    def initialize(self, enabled: bool = False) -> Tuple['BuildCache', 'DependencyTracker']:
        """
        Initialize cache and tracker.
        
        Args:
            enabled: Whether incremental builds are enabled
            
        Returns:
            Tuple of (cache, tracker)
        """
        from bengal.cache import BuildCache, DependencyTracker
        
        cache_path = self.site.output_dir / ".bengal-cache.json"
        
        if enabled:
            self.cache = BuildCache.load(cache_path)
            cache_exists = cache_path.exists()
            try:
                file_count = len(self.cache.file_hashes)
            except (AttributeError, TypeError):
                file_count = 0
            logger.info(
                "cache_initialized",
                enabled=True,
                cache_loaded=cache_exists,
                cached_files=file_count
            )
        else:
            self.cache = BuildCache()
            logger.debug("cache_initialized", enabled=False)
        
        self.tracker = DependencyTracker(self.cache)
        
        return self.cache, self.tracker
    
    def check_config_changed(self) -> bool:
        """
        Check if config file has changed (requires full rebuild).
        
        Returns:
            True if config changed
        """
        if not self.cache:
            return False
        
        config_files = [
            self.site.root_path / "bengal.toml",
            self.site.root_path / "bengal.yaml",
            self.site.root_path / "bengal.yml"
        ]
        config_file = next((f for f in config_files if f.exists()), None)
        
        if config_file:
            changed = self.cache.is_changed(config_file)
            # Always update config file hash (for next build)
            self.cache.update_file(config_file)
            
            if changed:
                logger.info("config_changed", config_file=config_file.name)
            
            return changed
        
        return False
    
    def find_work_early(self, verbose: bool = False) -> Tuple[List['Page'], List['Asset'], Dict[str, List]]:
        """
        Find pages/assets that need rebuilding (early version - before taxonomy generation).
        
        This is called BEFORE taxonomies/menus are generated, so it only checks content/asset changes.
        Generated pages (tags, etc.) will be determined later based on affected tags.
        
        Args:
            verbose: Whether to collect detailed change information
            
        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")
        
        pages_to_rebuild: Set[Path] = set()
        assets_to_process: List['Asset'] = []
        change_summary: Dict[str, List] = {
            'Modified content': [],
            'Modified assets': [],
            'Modified templates': [],
            'Taxonomy changes': []
        }
        
        # Find changed content files (skip generated pages - they don't have real source files)
        for page in self.site.pages:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get('_generated'):
                continue
                
            if self.cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary['Modified content'].append(page.source_path)
                # Track taxonomy changes
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))
        
        # Find changed assets
        for asset in self.site.assets:
            if self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary['Modified assets'].append(asset.source_path)
        
        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose:
                        change_summary['Modified templates'].append(template_file)
                    # Template changed - find affected pages
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    self.cache.update_file(template_file)
        
        # Convert to Page objects
        pages_to_build_list = [
            page for page in self.site.pages 
            if page.source_path in pages_to_rebuild and not page.metadata.get('_generated')
        ]
        
        logger.info(
            "incremental_work_detected",
            pages_to_build=len(pages_to_build_list),
            assets_to_process=len(assets_to_process),
            template_changes=len(change_summary.get('Modified templates', []))
        )
        
        return pages_to_build_list, assets_to_process, change_summary
    
    def find_work(self, verbose: bool = False) -> Tuple[List['Page'], List['Asset'], Dict[str, List]]:
        """
        Find pages/assets that need rebuilding (legacy version - after taxonomy generation).
        
        This is the old method that expects generated pages to already exist.
        Kept for backward compatibility but should be replaced with find_work_early().
        
        Args:
            verbose: Whether to collect detailed change information
            
        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")
        
        pages_to_rebuild: Set[Path] = set()
        assets_to_process: List['Asset'] = []
        change_summary: Dict[str, List] = {
            'Modified content': [],
            'Modified assets': [],
            'Modified templates': [],
            'Taxonomy changes': []
        }
        
        # Find changed content files (skip generated pages - they have virtual paths)
        for page in self.site.pages:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get('_generated'):
                continue
                
            if self.cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary['Modified content'].append(page.source_path)
                # Track taxonomy changes
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))
        
        # Find changed assets
        for asset in self.site.assets:
            if self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary['Modified assets'].append(asset.source_path)
        
        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose:
                        change_summary['Modified templates'].append(template_file)
                    # Template changed - find affected pages
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    self.cache.update_file(template_file)
        
        # Check for SPECIFIC taxonomy changes (which exact tags were added/removed)
        # Only rebuild tag pages for tags that actually changed
        affected_tags: Set[str] = set()
        affected_sections: Set[Any] = set()
        
        for page in self.site.pages:
            # Skip generated pages - they don't have real source files
            if page.metadata.get('_generated'):
                continue
            
            # Check if this page changed
            if page.source_path in pages_to_rebuild:
                # Get old and new tags
                old_tags = self.cache.get_previous_tags(page.source_path)
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
            for page in self.site.pages:
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
            for page in self.site.pages:
                if page.metadata.get('_generated'):
                    if page.metadata.get('type') == 'archive':
                        page_section = page.metadata.get('_section')
                        if page_section and page_section in affected_sections:
                            pages_to_rebuild.add(page.source_path)
        
        # Convert page paths back to Page objects
        pages_to_build = [
            page for page in self.site.pages 
            if page.source_path in pages_to_rebuild
        ]
        
        return pages_to_build, assets_to_process, change_summary
    
    def save_cache(self, pages_built: List['Page'], assets_processed: List['Asset']) -> None:
        """
        Update cache with processed files.
        
        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        if not self.cache:
            return
        
        cache_path = self.site.output_dir / ".bengal-cache.json"
        
        # Update all page hashes and tags (skip generated pages - they have virtual paths)
        for page in pages_built:
            if not page.metadata.get('_generated'):
                self.cache.update_file(page.source_path)
                # Store tags for next build's comparison
                if page.tags:
                    self.cache.update_tags(page.source_path, set(page.tags))
                else:
                    self.cache.update_tags(page.source_path, set())
        
        # Update all asset hashes
        for asset in assets_processed:
            self.cache.update_file(asset.source_path)
        
        # Update template hashes (even if not changed, to track them)
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                self.cache.update_file(template_file)
        
        # Save cache
        self.cache.save(cache_path)
    
    def _get_theme_templates_dir(self) -> Optional[Path]:
        """
        Get the templates directory for the current theme.
        
        Returns:
            Path to theme templates or None if not found
        """
        if not self.site.theme:
            return None
        
        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / self.site.theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir
        
        # Check in Bengal's bundled themes
        import bengal
        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.site.theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir
        
        return None

