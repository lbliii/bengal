"""
Menu system for navigation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MenuItem:
    """
    Represents a single menu item with optional hierarchy.
    
    Can be created from:
    1. Config file (explicit definition)
    2. Page frontmatter (page registers itself in menu)
    3. Section structure (auto-generated)
    """
    name: str
    url: str
    weight: int = 0
    parent: Optional[str] = None
    identifier: Optional[str] = None
    children: List['MenuItem'] = field(default_factory=list)
    
    # Runtime state (set during rendering)
    active: bool = False
    active_trail: bool = False
    
    def __post_init__(self):
        """Set identifier from name if not provided."""
        if self.identifier is None:
            # Convert name to slug-like identifier
            self.identifier = self.name.lower().replace(' ', '-').replace('_', '-')
    
    def add_child(self, child: 'MenuItem') -> None:
        """Add a child menu item and sort by weight."""
        self.children.append(child)
        self.children.sort(key=lambda x: x.weight)
    
    def mark_active(self, current_url: str) -> bool:
        """
        Mark this item as active if URL matches.
        Returns True if this or any child is active.
        
        Args:
            current_url: Current page URL to match against
            
        Returns:
            True if this item or any child is active
        """
        # Normalize URLs for comparison
        item_url = self.url.rstrip('/')
        check_url = current_url.rstrip('/')
        
        if item_url == check_url:
            self.active = True
            return True
        
        # Check children
        child_active = False
        for child in self.children:
            if child.mark_active(current_url):
                child_active = True
        
        if child_active:
            self.active_trail = True
            
        return child_active or self.active
    
    def reset_active(self) -> None:
        """Reset active states (called before each page render)."""
        self.active = False
        self.active_trail = False
        for child in self.children:
            child.reset_active()
    
    def to_dict(self) -> dict:
        """Convert to dict for template access."""
        return {
            'name': self.name,
            'url': self.url,
            'active': self.active,
            'active_trail': self.active_trail,
            'children': [child.to_dict() for child in self.children]
        }


class MenuBuilder:
    """
    Builds hierarchical menu structures from various sources.
    """
    
    def __init__(self):
        self.items: List[MenuItem] = []
    
    def add_from_config(self, menu_config: List[dict]) -> None:
        """
        Add menu items from config.
        
        Args:
            menu_config: List of menu item dicts from config file
        """
        for item_config in menu_config:
            item = MenuItem(
                name=item_config['name'],
                url=item_config['url'],
                weight=item_config.get('weight', 0),
                parent=item_config.get('parent'),
                identifier=item_config.get('identifier')
            )
            self.items.append(item)
    
    def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None:
        """
        Add a page to menu based on frontmatter.
        
        Args:
            page: Page object
            menu_name: Name of the menu (e.g., 'main', 'footer')
            menu_config: Menu configuration from page frontmatter
        """
        item = MenuItem(
            name=menu_config.get('name', page.title),
            url=page.url,
            weight=menu_config.get('weight', 0),
            parent=menu_config.get('parent'),
            identifier=menu_config.get('identifier')
        )
        self.items.append(item)
    
    def build_hierarchy(self) -> List[MenuItem]:
        """
        Build hierarchical tree from flat list with validation.
        Returns list of root items (no parent).
        
        Returns:
            List of root MenuItem objects with children populated
            
        Raises:
            ValueError: If circular references detected
        """
        logger.debug(
            "building_menu_hierarchy",
            total_items=len(self.items),
            items_with_parents=sum(1 for i in self.items if i.parent)
        )
        
        # Create lookup by identifier
        by_id = {item.identifier: item for item in self.items}
        
        # Validate parent references
        orphaned_items = []
        for item in self.items:
            if item.parent and item.parent not in by_id:
                orphaned_items.append((item.name, item.parent))
        
        if orphaned_items:
            logger.warning(
                f"{len(orphaned_items)} menu items reference missing parents and will be added to root level",
                count=len(orphaned_items),
                items=[(name, parent) for name, parent in orphaned_items[:5]]
            )
        
        # Build tree
        roots = []
        for item in self.items:
            if item.parent:
                parent = by_id.get(item.parent)
                if parent:
                    parent.add_child(item)
                else:
                    # Parent not found, treat as root
                    roots.append(item)
            else:
                roots.append(item)
        
        # Detect cycles
        visited = set()
        for root in roots:
            if self._has_cycle(root, visited, set()):
                logger.error(
                    "menu_cycle_detected",
                    root_item=root.name,
                    root_identifier=root.identifier
                )
                raise ValueError(f"Menu has circular reference involving '{root.name}'")
        
        # Sort roots by weight
        roots.sort(key=lambda x: x.weight)
        
        logger.debug(
            "menu_hierarchy_built",
            root_items=len(roots),
            total_items=len(self.items),
            max_depth=max((self._get_depth(r) for r in roots), default=0)
        )
        
        return roots
    
    def _has_cycle(self, item: MenuItem, visited: set, path: set) -> bool:
        """
        Detect circular references in menu tree.
        
        Args:
            item: Current menu item
            visited: Set of all visited identifiers
            path: Current path identifiers (for cycle detection)
            
        Returns:
            True if cycle detected
        """
        if item.identifier in path:
            return True
        
        path.add(item.identifier)
        visited.add(item.identifier)
        
        for child in item.children:
            if self._has_cycle(child, visited, path.copy()):
                return True
        
        return False
    
    def _get_depth(self, item: MenuItem) -> int:
        """
        Get maximum depth of menu tree from this item.
        
        Args:
            item: Root menu item
            
        Returns:
            Maximum depth (1 = no children, 2 = children but no grandchildren, etc.)
        """
        if not item.children:
            return 1
        return 1 + max(self._get_depth(child) for child in item.children)
    
    def mark_active_items(self, current_url: str, menu_items: List[MenuItem]) -> None:
        """
        Mark active items in menu tree.
        
        Args:
            current_url: Current page URL
            menu_items: List of menu items to process
        """
        logger.debug(
            "marking_active_menu_items",
            current_url=current_url,
            menu_item_count=len(menu_items)
        )
        
        # Reset all items first
        for item in menu_items:
            item.reset_active()
        
        # Mark active items
        active_count = 0
        for item in menu_items:
            if item.mark_active(current_url):
                active_count += 1
        
        logger.debug(
            "menu_active_items_marked",
            active_items=active_count
        )

