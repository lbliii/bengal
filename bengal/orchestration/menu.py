"""
Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter.
"""

from typing import TYPE_CHECKING, Set, Optional
from pathlib import Path
import hashlib
import json

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page


class MenuOrchestrator:
    """
    Handles navigation menu building with incremental caching.
    
    Responsibilities:
        - Build menus from config definitions
        - Add items from page frontmatter
        - Mark active menu items for current page
        - Cache menus when config/pages unchanged (incremental optimization)
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize menu orchestrator.
        
        Args:
            site: Site instance containing menu configuration
        """
        self.site = site
        self._menu_cache_key: Optional[str] = None
    
    def build(self, changed_pages: Optional[Set[Path]] = None, config_changed: bool = False) -> bool:
        """
        Build all menus from config and page frontmatter.
        
        With incremental building:
        - If config unchanged AND no pages with menu frontmatter changed
        - Skip rebuild and reuse cached menus
        
        Args:
            changed_pages: Set of paths for pages that changed (for incremental builds)
            config_changed: Whether config file changed (forces rebuild)
        
        Returns:
            True if menus were rebuilt, False if cached menus reused
        
        Called during site.build() after content discovery.
        """
        # Check if we can skip menu rebuild
        if not config_changed and changed_pages is not None:
            if self._can_skip_rebuild(changed_pages):
                verbose = self.site.config.get('verbose', False)
                if verbose:
                    print("  ✓ Menus unchanged (using cache)")
                return False
        
        # Full menu rebuild needed
        return self._build_full()
    
    def _can_skip_rebuild(self, changed_pages: Set[Path]) -> bool:
        """
        Check if menu rebuild can be skipped (incremental optimization).
        
        Menus need rebuild only if:
        1. Config changed (menu definitions)
        2. Pages with 'menu' frontmatter changed
        
        Args:
            changed_pages: Set of changed page paths
        
        Returns:
            True if rebuild can be skipped (menus unchanged)
        """
        # No existing menus - need full build
        if not self.site.menu:
            return False
        
        # Check if any changed pages have menu frontmatter
        for page in self.site.pages:
            if page.source_path in changed_pages:
                # Check if this page has menu frontmatter
                if 'menu' in page.metadata:
                    # Menu-related page changed - need rebuild
                    return False
        
        # Compute cache key based on menu config and pages with menu frontmatter
        current_key = self._compute_menu_cache_key()
        
        # Compare with previous cache key
        if self._menu_cache_key is None:
            # First build - need full rebuild
            self._menu_cache_key = current_key
            return False
        
        if current_key == self._menu_cache_key:
            # Menu config and pages unchanged - can skip!
            return True
        
        # Config or pages changed - need rebuild
        self._menu_cache_key = current_key
        return False
    
    def _compute_menu_cache_key(self) -> str:
        """
        Compute cache key for current menu configuration.
        
        Key includes:
        - Menu config from bengal.toml
        - List of pages with menu frontmatter and their menu data
        
        Returns:
            SHA256 hash of menu-related data
        """
        # Get menu config
        menu_config = self.site.config.get('menu', {})
        
        # Get pages with menu frontmatter
        menu_pages = []
        for page in self.site.pages:
            if 'menu' in page.metadata:
                menu_pages.append({
                    'path': str(page.source_path),
                    'menu': page.metadata['menu'],
                    'title': page.title,
                    'url': page.url
                })
        
        # Create cache key data
        cache_data = {
            'config': menu_config,
            'pages': menu_pages
        }
        
        # Hash to create cache key
        data_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _build_full(self) -> bool:
        """
        Build all menus from scratch.
        
        Returns:
            True (menus were rebuilt)
        """
        from bengal.core.menu import MenuBuilder
        
        # Get menu definitions from config
        menu_config = self.site.config.get('menu', {})
        
        if not menu_config:
            # No menus defined, skip
            return False
        
        verbose = self.site.config.get('verbose', False)
        if verbose:
            print("  Building navigation menus...")
        
        for menu_name, items in menu_config.items():
            builder = MenuBuilder()
            
            # Add config-defined items
            if isinstance(items, list):
                builder.add_from_config(items)
            
            # Add items from page frontmatter
            for page in self.site.pages:
                page_menu = page.metadata.get('menu', {})
                if menu_name in page_menu:
                    builder.add_from_page(page, menu_name, page_menu[menu_name])
            
            # Build hierarchy
            self.site.menu[menu_name] = builder.build_hierarchy()
            self.site.menu_builders[menu_name] = builder
            
            if verbose:
                print(f"    ✓ Built menu '{menu_name}': {len(self.site.menu[menu_name])} items")
        
        # Update cache key
        self._menu_cache_key = self._compute_menu_cache_key()
        
        return True
    
    def mark_active(self, current_page: 'Page') -> None:
        """
        Mark active menu items for the current page being rendered.
        Called during rendering for each page.
        
        Args:
            current_page: Page currently being rendered
        """
        current_url = current_page.url
        for menu_name, builder in self.site.menu_builders.items():
            builder.mark_active_items(current_url, self.site.menu[menu_name])

