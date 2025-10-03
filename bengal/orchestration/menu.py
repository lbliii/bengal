"""
Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page


class MenuOrchestrator:
    """
    Handles navigation menu building.
    
    Responsibilities:
        - Build menus from config definitions
        - Add items from page frontmatter
        - Mark active menu items for current page
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize menu orchestrator.
        
        Args:
            site: Site instance containing menu configuration
        """
        self.site = site
    
    def build(self) -> None:
        """
        Build all menus from config and page frontmatter.
        Called during site.build() after content discovery.
        """
        from bengal.core.menu import MenuBuilder
        
        # Get menu definitions from config
        menu_config = self.site.config.get('menu', {})
        
        if not menu_config:
            # No menus defined, skip
            return
        
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

