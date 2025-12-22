"""
Menu system for navigation and site structure.

Provides menu building from configuration, page frontmatter, and section
hierarchy. Supports hierarchical menus, active state tracking, and i18n
localization. Menus are built during content discovery and cached for
template access.

Public API:
    MenuItem: Single menu item with URL, name, weight, and optional children
    MenuBuilder: Constructs hierarchical menus from various sources

Key Concepts:
    Menu Sources: Menus can be populated from:
        - Config files (bengal.toml [[menu]] entries)
        - Page frontmatter (menu: {main: {weight: 5}})
        - Section structure (auto-generated from content hierarchy)

    Hierarchical Menus: Items support parent-child relationships via the
        `parent` field. MenuBuilder.build_hierarchy() constructs the tree.

    Active State: MenuItem.mark_active() sets `active` for matching URLs
        and `active_trail` for ancestors of active items.

    Weight Sorting: Items sorted by weight (ascending) then by name.
        Lower weights appear first in navigation.

    Deduplication: MenuBuilder tracks seen identifiers, URLs, and names
        to prevent duplicate items from multiple sources.

Related Packages:
    bengal.orchestration.menu: Menu building orchestration
    bengal.core.site: Site container that holds menus
    bengal.rendering.template_functions.navigation: Template access to menus
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.errors import BengalContentError


@dataclass
class MenuItem:
    """
    Represents a single menu item with optional hierarchy.

    Menu items form hierarchical navigation structures with parent-child
    relationships. Items can be marked as active based on current page URL,
    and support weight-based sorting for display order.

    Creation:
        Config file: Explicit menu definitions in bengal.toml
        Page frontmatter: Pages register themselves via menu metadata
        Section structure: Auto-generated from section hierarchy

    Attributes:
        name: Display name for the menu item
        url: URL path for the menu item
        weight: Sort weight (lower values appear first)
        parent: Parent menu identifier (for hierarchical menus)
        identifier: Unique identifier (auto-generated from name if not provided)
        icon: Icon name from frontmatter (e.g., 'book', 'folder', 'terminal')
        children: Child menu items (populated during menu building)
        active: Whether this item matches the current page URL
        active_trail: Whether this item is in the active path (has active child)

    Relationships:
        - Used by: MenuBuilder for menu construction
        - Used by: MenuOrchestrator for menu building
        - Used in: Templates via site.menu for navigation rendering

    Examples:
        # From config
        menu_item = MenuItem(name="Home", url="/", weight=1)

        # From page frontmatter
        menu_item = MenuItem(name=page.title, url=page.href, weight=page.metadata.get("weight", 0))

        # With icon
        menu_item = MenuItem(name="API Reference", url="/api/", icon="book")
    """

    name: str
    url: str
    weight: int = 0
    parent: str | None = None
    identifier: str | None = None
    icon: str | None = None
    children: list[MenuItem] = field(default_factory=list)

    # Runtime state (set during rendering)
    active: bool = False
    active_trail: bool = False

    def __post_init__(self) -> None:
        """
        Set identifier from name if not provided.

        Automatically generates a slug-like identifier from the menu item name
        by lowercasing and replacing spaces/underscores with hyphens. This ensures
        every menu item has a unique identifier for parent-child relationships.

        Examples:
            MenuItem(name="Home Page") → identifier="home-page"
            MenuItem(name="About_Us") → identifier="about-us"
        """
        if self.identifier is None:
            # Convert name to slug-like identifier
            self.identifier = self.name.lower().replace(" ", "-").replace("_", "-")

    @property
    def href(self) -> str:
        """
        URL for templates. Alias for url property.

        Return href property for unified URL model.
        """
        return self.url

    def add_child(self, child: MenuItem) -> None:
        """
        Add a child menu item and sort children by weight.

        Adds the child to the children list and immediately sorts all children
        by weight (ascending). Lower weights appear first in the list.

        Args:
            child: MenuItem to add as a child

        Examples:
            item = MenuItem(name="Parent", url="/parent")
            item.add_child(MenuItem(name="Child 1", url="/child1", weight=2))
            item.add_child(MenuItem(name="Child 2", url="/child2", weight=1))
            # Children are sorted: Child 2 (weight=1) appears before Child 1 (weight=2)
        """
        self.children.append(child)
        self.children.sort(key=lambda x: x.weight)

    def mark_active(self, current_url: str) -> bool:
        """
        Mark this item as active if URL matches current page.

        Recursively checks this item and all children for URL matches. Sets
        `active` flag if this item matches, and `active_trail` flag if any
        child matches. URLs are normalized (trailing slashes removed) before
        comparison.

        Args:
            current_url: Current page URL to match against (will be normalized)

        Returns:
            True if this item or any child is active, False otherwise

        Examples:
            item = MenuItem(name="Blog", url="/blog")
            item.mark_active("/blog")  # Returns True, sets item.active = True
            item.mark_active("/blog/post")  # Returns False (no match)

            # With children
            item.add_child(MenuItem(name="Post", url="/blog/post"))
            item.mark_active("/blog/post")  # Returns True, sets item.active_trail = True
        """
        # Normalize URLs for comparison
        item_url = self.url.rstrip("/")
        check_url = current_url.rstrip("/")

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
        """
        Reset active states for this item and all children.

        Recursively clears `active` and `active_trail` flags. Called before
        each page render to ensure fresh state for active item detection.

        Examples:
            item.reset_active()  # Clears active flags for item and all descendants
        """
        self.active = False
        self.active_trail = False
        for child in self.children:
            child.reset_active()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert menu item to dictionary for template access.

        Creates a dictionary representation suitable for JSON serialization
        and template rendering. Recursively converts children to dictionaries.

        Returns:
            Dictionary with name, url, icon, active, active_trail, and children fields.
            Children are recursively converted to dictionaries.

        Examples:
            item = MenuItem(name="Home", url="/", icon="house")
            item.add_child(MenuItem(name="About", url="/about", icon="info"))
            data = item.to_dict()
            # Returns: {
            #     "name": "Home",
            #     "url": "/",
            #     "icon": "house",
            #     "active": False,
            #     "active_trail": False,
            #     "children": [{"name": "About", "url": "/about", "icon": "info", ...}]
            # }
        """
        return {
            "name": self.name,
            "href": self.href,
            "icon": self.icon,
            "active": self.active,
            "active_trail": self.active_trail,
            "children": [child.to_dict() for child in self.children],
        }


class MenuBuilder:
    """
    Builds hierarchical menu structures from various sources.

    Constructs menu hierarchies from config definitions, page frontmatter, and
    section structure. Handles deduplication, cycle detection, and hierarchy
    building with parent-child relationships.

    Creation:
        Direct instantiation: MenuBuilder()
            - Created by MenuOrchestrator for menu building
            - Fresh instance created for each menu build

    Attributes:
        items: List of MenuItem objects (flat list before hierarchy building)
        _seen_identifiers: Set of seen identifiers for deduplication
        _seen_urls: Set of seen URLs for deduplication
        _seen_names: Set of seen names for deduplication

    Behavior Notes:
        - Identifiers: Each MenuItem has an identifier (slug from name by default).
          Parent references use identifiers.
        - Cycle detection: build_hierarchy() detects circular references and raises
          ValueError when a cycle is found. Consumers should surface this early as
          a configuration error.
        - Deduplication: Automatically prevents duplicate items by identifier, URL, and name.

    Relationships:
        - Uses: MenuItem for menu item representation
        - Used by: MenuOrchestrator for menu building
        - Used in: Menu building during content discovery phase

    Examples:
        builder = MenuBuilder()
        builder.add_from_config(menu_config)
        builder.add_from_page(page, "main", page.metadata.get("menu", {}))
        menu_items = builder.build_hierarchy()
    """

    def __init__(self, diagnostics: Any | None = None) -> None:
        self.items: list[MenuItem] = []
        self._diagnostics: Any | None = diagnostics
        # Track items to prevent duplicates across all add methods
        self._seen_identifiers: set[str] = set()
        self._seen_urls: set[str] = set()
        self._seen_names: set[str] = set()

    def _is_duplicate(self, item_id: str | None, item_url: str, item_name: str) -> bool:
        """
        Check if an item is a duplicate based on identifier, URL, or name.

        Checks against previously seen identifiers, URLs, and names to prevent
        duplicate menu items. An item is considered duplicate if any of these
        match a previously added item.

        Args:
            item_id: Item identifier (if any). None is valid (not checked).
            item_url: Item URL (normalized, trailing slash removed).
            item_name: Item name (lowercased for case-insensitive comparison).

        Returns:
            True if duplicate found (identifier, URL, or name matches),
            False otherwise

        Examples:
            builder._is_duplicate("home", "/", "Home")  # False (first item)
            builder._is_duplicate("home", "/", "Home")  # True (duplicate identifier)
            builder._is_duplicate(None, "/", "Home")    # True (duplicate URL)
        """
        if item_id and item_id in self._seen_identifiers:
            return True
        if item_url and item_url in self._seen_urls:
            return True
        return bool(item_name and item_name in self._seen_names)

    def _track_item(self, item: MenuItem) -> None:
        """
        Track an item to prevent future duplicates.

        Adds the item's identifier, URL, and name to the seen sets for duplicate
        detection. Called automatically when items are added via add_from_config()
        or add_from_page().

        Args:
            item: MenuItem to track

        See Also:
            _is_duplicate(): Uses tracked identifiers/URLs/names for duplicate detection
        """
        if item.identifier:
            self._seen_identifiers.add(item.identifier)
        if item.href:
            self._seen_urls.add(item.href.rstrip("/"))
        if item.name:
            self._seen_names.add(item.name.lower())

    def add_from_config(self, menu_config: list[dict[str, Any]]) -> None:
        """
        Add menu items from configuration file.

        Parses menu configuration from bengal.toml or config files and creates
        MenuItem objects. Skips duplicates automatically and logs debug messages
        for skipped items.

        Args:
            menu_config: List of menu item dictionaries from config file.
                        Each dict should have: name, url, weight (optional),
                        parent (optional), identifier (optional)

        Examples:
            menu_config = [
                {"name": "Home", "url": "/", "weight": 1},
                {"name": "About", "url": "/about", "weight": 2, "parent": "home"}
            ]
            builder.add_from_config(menu_config)
        """
        for item_config in menu_config:
            item_id = item_config.get("identifier")
            item_url = item_config.get("url", "").rstrip("/")
            item_name = item_config.get("name", "").lower()

            if self._is_duplicate(item_id, item_url, item_name):
                emit_diagnostic(
                    self,
                    "debug",
                    "menu_duplicate_skipped",
                    item=item_config.get("name"),
                    reason="identifier"
                    if item_id and item_id in self._seen_identifiers
                    else "url"
                    if item_url and item_url in self._seen_urls
                    else "name",
                )
                continue

            item = MenuItem(
                name=item_config["name"],
                url=item_config["url"],
                weight=item_config.get("weight", 0),
                parent=item_config.get("parent"),
                identifier=item_config.get("identifier"),
                icon=item_config.get("icon"),
            )
            self.items.append(item)
            self._track_item(item)

    def add_from_page(self, page: Any, menu_name: str, menu_config: dict[str, Any]) -> None:
        """
        Add a page to menu based on frontmatter metadata.

        Creates a MenuItem from page frontmatter menu configuration. Uses page's
        relative_url for menu item URL (baseurl applied in templates). Skips
        duplicates automatically.

        Args:
            page: Page object with frontmatter menu configuration
            menu_name: Name of the menu (e.g., 'main', 'footer').
                      Currently used for logging, all menus share same builder
            menu_config: Menu configuration dictionary from page frontmatter.
                        Should have: name (optional, defaults to page.title),
                        url (optional, defaults to page._path),
                        weight (optional), parent (optional), identifier (optional)

        Examples:
            # Page frontmatter:
            # menu:
            #   main:
            #     name: "My Page"
            #     weight: 5
            builder.add_from_page(page, "main", page.metadata.get("menu", {}).get("main", {}))
        """
        item_id = menu_config.get("identifier")
        # Use _path for menu items (for comparison/activation)
        # Templates apply baseurl via | absolute_url filter
        item_url = page._path.rstrip("/")
        item_name = menu_config.get("name", page.title).lower()

        # Skip if duplicate
        if self._is_duplicate(item_id, item_url, item_name):
            emit_diagnostic(
                self,
                "debug",
                "menu_duplicate_skipped",
                item=page.title,
                reason="page_frontmatter",
            )
            return

        item = MenuItem(
            name=menu_config.get("name", page.title),
            url=page._path,  # Store site-relative path for comparison
            weight=menu_config.get("weight", 0),
            parent=menu_config.get("parent"),
            identifier=menu_config.get("identifier"),
        )
        self.items.append(item)
        self._track_item(item)

    def build_hierarchy(self) -> list[MenuItem]:
        """
        Build hierarchical tree from flat list with validation.

        Converts flat list of MenuItem objects into hierarchical tree structure
        based on parent-child relationships. Validates parent references and
        detects circular dependencies.

        Process:
            1. Create lookup map by identifier
            2. Validate parent references (warn about orphaned items)
            3. Build parent-child relationships
            4. Detect cycles (raises ValueError if found)
            5. Return root items (items with no parent)

        Returns:
            List of root MenuItem objects (no parent) with children populated.
            Empty list if no items or all items have parents.

        Raises:
            ValueError: If circular references detected in parent-child relationships

        Examples:
            builder.add_from_config([{"name": "Home", "url": "/"}])
            builder.add_from_config([{"name": "About", "url": "/about", "parent": "home"}])
            root_items = builder.build_hierarchy()
            # Returns: [MenuItem(name="Home", children=[MenuItem(name="About")])]
        """
        emit_diagnostic(
            self,
            "debug",
            "building_menu_hierarchy",
            total_items=len(self.items),
            items_with_parents=sum(1 for i in self.items if i.parent),
        )

        # Create lookup by identifier
        by_id = {item.identifier: item for item in self.items}

        # Validate parent references
        orphaned_items = []
        for item in self.items:
            if item.parent and item.parent not in by_id:
                orphaned_items.append((item.name, item.parent))

        if orphaned_items:
            message = (
                f"{len(orphaned_items)} menu items reference missing parents "
                "and will be added to root level"
            )
            emit_diagnostic(
                self,
                "warning",
                message,
                count=len(orphaned_items),
                items=[(name, parent) for name, parent in orphaned_items[:5]],
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
        visited: set[str] = set()
        for root in roots:
            if self._has_cycle(root, visited, set()):
                emit_diagnostic(
                    self,
                    "error",
                    "menu_cycle_detected",
                    root_item=root.name,
                    root_identifier=root.identifier,
                )
                raise BengalContentError(
                    f"Menu has circular reference involving '{root.name}'",
                    suggestion="Check menu configuration for circular parent-child relationships",
                )

        # Sort roots by weight
        roots.sort(key=lambda x: x.weight)

        emit_diagnostic(
            self,
            "debug",
            "menu_hierarchy_built",
            root_items=len(roots),
            total_items=len(self.items),
            max_depth=max((self._get_depth(r) for r in roots), default=0),
        )

        return roots

    def _has_cycle(self, item: MenuItem, visited: set[str], path: set[str]) -> bool:
        """
        Detect circular references in menu tree using DFS.

        Uses depth-first search to detect cycles in parent-child relationships.
        A cycle exists if an item appears in its own descendant chain.

        Args:
            item: Current menu item being checked
            visited: Set of all visited identifiers (for optimization)
            path: Current path identifiers from root to current item (for cycle detection)

        Returns:
            True if cycle detected (item appears in its own descendant chain),
            False otherwise

        Algorithm:
            - If item.identifier in path: cycle detected
            - Add item to path and visited
            - Recursively check all children
            - Return True if any child has cycle

        Examples:
            # Cycle: A → B → C → A
            _has_cycle(item_a, set(), set())  # Returns True
        """
        if item.identifier is None:
            return False

        if item.identifier in path:
            return True

        path.add(item.identifier)
        visited.add(item.identifier)

        return any(self._has_cycle(child, visited, path.copy()) for child in item.children)

    def _get_depth(self, item: MenuItem) -> int:
        """
        Get maximum depth of menu tree from this item.

        Recursively calculates the maximum depth of the menu tree starting from
        the given item. Used for logging and validation.

        Args:
            item: Root menu item to calculate depth from

        Returns:
            Maximum depth as integer:
            - 1: Item has no children
            - 2: Item has children but no grandchildren
            - N: Maximum depth of deepest descendant

        Examples:
            item = MenuItem(name="Root")
            _get_depth(item)  # Returns 1 (no children)

            item.add_child(MenuItem(name="Child"))
            _get_depth(item)  # Returns 2 (has children)

            item.children[0].add_child(MenuItem(name="Grandchild"))
            _get_depth(item)  # Returns 3 (has grandchildren)
        """
        if not item.children:
            return 1
        return 1 + max(self._get_depth(child) for child in item.children)

    def mark_active_items(self, current_url: str, menu_items: list[MenuItem]) -> None:
        """
        Mark active items in menu tree based on current page URL.

        Recursively marks menu items as active if their URL matches the current
        page URL. Also marks items in the active trail (items with active children).
        Resets all active states before marking to ensure clean state.

        Args:
            current_url: Current page URL to match against (will be normalized)
            menu_items: List of root MenuItem objects to process (hierarchical tree)

        Process:
            1. Reset all active states (active, active_trail) for all items
            2. Recursively call mark_active() on each root item
            3. Items with matching URLs are marked active
            4. Items with active children are marked active_trail

        Examples:
            menu_items = builder.build_hierarchy()
            builder.mark_active_items("/blog/post", menu_items)
            # Items with URL="/blog/post" are marked active
            # Items with URL="/blog" are marked active_trail (have active child)
        """
        emit_diagnostic(
            self,
            "debug",
            "marking_active_menu_items",
            current_url=current_url,
            menu_item_count=len(menu_items),
        )

        # Reset all items first
        for item in menu_items:
            item.reset_active()

        # Mark active items
        active_count = 0
        for item in menu_items:
            if item.mark_active(current_url):
                active_count += 1

        emit_diagnostic(self, "debug", "menu_active_items_marked", active_items=active_count)
