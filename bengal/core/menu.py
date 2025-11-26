"""
Menu system for navigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    parent: str | None = None
    identifier: str | None = None
    children: list[MenuItem] = field(default_factory=list)

    # Runtime state (set during rendering)
    active: bool = False
    active_trail: bool = False

    def __post_init__(self):
        """Set identifier from name if not provided."""
        if self.identifier is None:
            # Convert name to slug-like identifier
            self.identifier = self.name.lower().replace(" ", "-").replace("_", "-")

    def add_child(self, child: MenuItem) -> None:
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
        """Reset active states (called before each page render)."""
        self.active = False
        self.active_trail = False
        for child in self.children:
            child.reset_active()

    def to_dict(self) -> dict:
        """Convert to dict for template access."""
        return {
            "name": self.name,
            "url": self.url,
            "active": self.active,
            "active_trail": self.active_trail,
            "children": [child.to_dict() for child in self.children],
        }


class MenuBuilder:
    """
    Builds hierarchical menu structures from various sources.

    Behavior notes:
    - Identifiers: Each `MenuItem` has an `identifier` (slug from name by default). Parent
      references use identifiers.
    - Cycle detection: `build_hierarchy()` detects circular references in the built tree
      and raises `ValueError` when a cycle is found. Consumers should surface this early
      as a configuration error.
    - Deduplication: Automatically prevents duplicate items by identifier, URL, and name
    """

    def __init__(self):
        self.items: list[MenuItem] = []
        # Track items to prevent duplicates across all add methods
        self._seen_identifiers: set[str] = set()
        self._seen_urls: set[str] = set()
        self._seen_names: set[str] = set()

    def _is_duplicate(self, item_id: str | None, item_url: str, item_name: str) -> bool:
        """
        Check if an item is a duplicate based on identifier, URL, or name.

        Args:
            item_id: Item identifier (if any)
            item_url: Item URL (normalized)
            item_name: Item name (lowercased)

        Returns:
            True if duplicate found
        """
        if item_id and item_id in self._seen_identifiers:
            return True
        if item_url and item_url in self._seen_urls:
            return True
        return bool(item_name and item_name in self._seen_names)

    def _track_item(self, item: MenuItem) -> None:
        """Track an item to prevent future duplicates."""
        if item.identifier:
            self._seen_identifiers.add(item.identifier)
        if item.url:
            self._seen_urls.add(item.url.rstrip("/"))
        if item.name:
            self._seen_names.add(item.name.lower())

    def add_from_config(self, menu_config: list[dict]) -> None:
        """
        Add menu items from config.

        Args:
            menu_config: List of menu item dicts from config file
        """
        for item_config in menu_config:
            item_id = item_config.get("identifier")
            item_url = item_config.get("url", "").rstrip("/")
            item_name = item_config.get("name", "").lower()

            # Skip if duplicate
            if self._is_duplicate(item_id, item_url, item_name):
                logger.debug(
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
            )
            self.items.append(item)
            self._track_item(item)

    def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None:
        """
        Add a page to menu based on frontmatter.

        Args:
            page: Page object
            menu_name: Name of the menu (e.g., 'main', 'footer')
            menu_config: Menu configuration from page frontmatter
        """
        item_id = menu_config.get("identifier")
        # Use relative_url for menu items (for comparison/activation)
        # Templates apply baseurl via | absolute_url filter
        item_url = page.relative_url.rstrip("/")
        item_name = menu_config.get("name", page.title).lower()

        # Skip if duplicate
        if self._is_duplicate(item_id, item_url, item_name):
            logger.debug("menu_duplicate_skipped", item=page.title, reason="page_frontmatter")
            return

        item = MenuItem(
            name=menu_config.get("name", page.title),
            url=page.relative_url,  # Store relative URL for comparison
            weight=menu_config.get("weight", 0),
            parent=menu_config.get("parent"),
            identifier=menu_config.get("identifier"),
        )
        self.items.append(item)
        self._track_item(item)

    def add_from_auto_nav(self, site: Any, exclude_sections: set[str] | None = None) -> None:
        """
        Add auto-discovered sections to menu, including nested sections.

        This integrates auto-nav discovery directly into MenuBuilder,
        ensuring deduplication happens at the builder level. Recursively
        includes all sections in the hierarchy, not just top-level ones.

        Args:
            site: Site instance with sections
            exclude_sections: Set of section names to exclude (e.g., {'api', 'cli'})
        """
        if exclude_sections is None:
            exclude_sections = set()

        def _add_section_recursive(section: Any, parent_id: str | None = None) -> None:
            """Recursively add section and its subsections to menu."""
            # Skip sections without paths
            if not hasattr(section, "path") or not section.path:
                return

            # Skip excluded sections (e.g., dev sections being bundled)
            if hasattr(section, "name") and section.name in exclude_sections:
                return

            # Get section metadata
            section_hidden = False
            section_title = (
                getattr(section, "title", None) or section.name.replace("-", " ").title()
            )
            section_weight = getattr(section, "weight", 999)

            # Check index page metadata
            if hasattr(section, "index_page") and section.index_page:
                index_page = section.index_page
                metadata = getattr(index_page, "metadata", {})

                # Check if hidden from menu
                menu_setting = metadata.get("menu", True)
                if menu_setting is False or (
                    isinstance(menu_setting, dict) and menu_setting.get("main") is False
                ):
                    section_hidden = True

                # Get title and weight from frontmatter
                if hasattr(index_page, "title") and index_page.title:
                    section_title = index_page.title
                if "weight" in metadata:
                    section_weight = metadata["weight"]

            # Skip hidden sections
            if section_hidden:
                return

            # Build section relative URL (for menu items - templates apply baseurl via filter)
            section_url = getattr(section, "relative_url", f"/{section.name}/")
            section_id = section.name

            # Determine parent identifier from section.parent if not provided
            if parent_id is None and hasattr(section, "parent") and section.parent:
                parent_id = section.parent.name

            # Check for duplicates before adding
            if self._is_duplicate(section_id, section_url.rstrip("/"), section_title.lower()):
                logger.debug("menu_duplicate_skipped", item=section_title, reason="auto_nav")
                return

            # Create and add menu item
            item = MenuItem(
                name=section_title,
                url=section_url,
                weight=section_weight,
                identifier=section_id,
                parent=parent_id,
            )
            self.items.append(item)
            self._track_item(item)

            # Recursively add subsections
            if hasattr(section, "subsections"):
                for subsection in section.subsections:
                    _add_section_recursive(subsection, section_id)

        # Find all top-level sections (those with no parent)
        top_level_sections = []
        for section in site.sections:
            if not hasattr(section, "path") or not section.path:
                continue

            # Check if section has a parent - if not, it's top-level
            if not hasattr(section, "parent") or section.parent is None:
                top_level_sections.append(section)

        # Recursively build menu from all top-level sections
        for section in top_level_sections:
            _add_section_recursive(section, None)

    def build_hierarchy(self) -> list[MenuItem]:
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
            logger.warning(
                f"{len(orphaned_items)} menu items reference missing parents and will be added to root level",
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
        visited = set()
        for root in roots:
            if self._has_cycle(root, visited, set()):
                logger.error(
                    "menu_cycle_detected", root_item=root.name, root_identifier=root.identifier
                )
                raise ValueError(f"Menu has circular reference involving '{root.name}'")

        # Sort roots by weight
        roots.sort(key=lambda x: x.weight)

        logger.debug(
            "menu_hierarchy_built",
            root_items=len(roots),
            total_items=len(self.items),
            max_depth=max((self._get_depth(r) for r in roots), default=0),
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

        return any(self._has_cycle(child, visited, path.copy()) for child in item.children)

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

    def mark_active_items(self, current_url: str, menu_items: list[MenuItem]) -> None:
        """
        Mark active items in menu tree.

        Args:
            current_url: Current page URL
            menu_items: List of menu items to process
        """
        logger.debug(
            "marking_active_menu_items", current_url=current_url, menu_item_count=len(menu_items)
        )

        # Reset all items first
        for item in menu_items:
            item.reset_active()

        # Mark active items
        active_count = 0
        for item in menu_items:
            if item.mark_active(current_url):
                active_count += 1

        logger.debug("menu_active_items_marked", active_items=active_count)
