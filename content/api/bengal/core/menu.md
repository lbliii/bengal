
---
title: "menu"
type: "python-module"
source_file: "bengal/bengal/core/menu.py"
line_number: 1
description: "Menu system for navigation and site structure. Provides menu building from configuration, page frontmatter, and section hierarchy. Supports hierarchical menus, active state tracking, and i18n localiza..."
---

# menu
**Type:** Module
**Source:** [View source](bengal/bengal/core/menu.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›menu

Menu system for navigation and site structure.

Provides menu building from configuration, page frontmatter, and section
hierarchy. Supports hierarchical menus, active state tracking, and i18n
localization. Menus are built during content discovery and cached for
template access.

Key Concepts:
    - Menu sources: Config files, page frontmatter, section structure
    - Hierarchical menus: Parent-child relationships with weight-based sorting
    - Active state: Current page and active trail tracking
    - i18n menus: Localized menu variants per language

Related Modules:
    - bengal.orchestration.menu: Menu building orchestration
    - bengal.core.site: Site container that holds menus
    - bengal.rendering.template_functions.navigation: Template access to menus

See Also:
    - bengal/core/menu.py:MenuItem class for menu item representation
    - bengal/core/menu.py:MenuBuilder class for menu construction

## Classes




### `MenuItem`


Represents a single menu item with optional hierarchy.

Menu items form hierarchical navigation structures with parent-child
relationships. Items can be marked as active based on current page URL,
and support weight-based sorting for display order.

Creation:
    Config file: Explicit menu definitions in bengal.toml
    Page frontmatter: Pages register themselves via menu metadata
    Section structure: Auto-generated from section hierarchy


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | Display name for the menu item |
| `url` | - | URL path for the menu item |
| `weight` | - | Sort weight (lower values appear first) |
| `parent` | - | Parent menu identifier (for hierarchical menus) |
| `identifier` | - | Unique identifier (auto-generated from name if not provided) |
| `children` | - | Child menu items (populated during menu building) |
| `active` | - | Whether this item matches the current page URL |
| `active_trail` | - | Whether this item is in the active path (has active child) |
| `Relationships` | - | - Used by: MenuBuilder for menu construction - Used by: MenuOrchestrator for menu building - Used in: Templates via site.menu for navigation rendering |







## Methods



#### `__post_init__`
```python
def __post_init__(self)
```


Set identifier from name if not provided.

Automatically generates a slug-like identifier from the menu item name
by lowercasing and replacing spaces/underscores with hyphens. This ensures
every menu item has a unique identifier for parent-child relationships.

:::{rubric} Examples
:class: rubric-examples
:::


```python
MenuItem(name="Home Page") → identifier="home-page"
    MenuItem(name="About_Us") → identifier="about-us"
```




#### `add_child`
```python
def add_child(self, child: MenuItem) -> None
```


Add a child menu item and sort children by weight.

Adds the child to the children list and immediately sorts all children
by weight (ascending). Lower weights appear first in the list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `child` | `MenuItem` | - | MenuItem to add as a child |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
item = MenuItem(name="Parent", url="/parent")
    item.add_child(MenuItem(name="Child 1", url="/child1", weight=2))
    item.add_child(MenuItem(name="Child 2", url="/child2", weight=1))
    # Children are sorted: Child 2 (weight=1) appears before Child 1 (weight=2)
```




#### `mark_active`
```python
def mark_active(self, current_url: str) -> bool
```


Mark this item as active if URL matches current page.

Recursively checks this item and all children for URL matches. Sets
`active` flag if this item matches, and `active_trail` flag if any
child matches. URLs are normalized (trailing slashes removed) before
comparison.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_url` | `str` | - | Current page URL to match against (will be normalized) |







**Returns**


`bool` - True if this item or any child is active, False otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
item = MenuItem(name="Blog", url="/blog")
    item.mark_active("/blog")  # Returns True, sets item.active = True
    item.mark_active("/blog/post")  # Returns False (no match)

    # With children
    item.add_child(MenuItem(name="Post", url="/blog/post"))
    item.mark_active("/blog/post")  # Returns True, sets item.active_trail = True
```




#### `reset_active`
```python
def reset_active(self) -> None
```


Reset active states for this item and all children.

Recursively clears `active` and `active_trail` flags. Called before
each page render to ensure fresh state for active item detection.



**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
item.reset_active()  # Clears active flags for item and all descendants
```




#### `to_dict`
```python
def to_dict(self) -> dict
```


Convert menu item to dictionary for template access.

Creates a dictionary representation suitable for JSON serialization
and template rendering. Recursively converts children to dictionaries.



**Returns**


`dict` - Dictionary with name, url, active, active_trail, and children fields.
    Children are recursively converted to dictionaries.
:::{rubric} Examples
:class: rubric-examples
:::


```python
item = MenuItem(name="Home", url="/")
    item.add_child(MenuItem(name="About", url="/about"))
    data = item.to_dict()
    # Returns: {
    #     "name": "Home",
    #     "url": "/",
    #     "active": False,
    #     "active_trail": False,
    #     "children": [{"name": "About", "url": "/about", ...}]
    # }
```




### `MenuBuilder`


Builds hierarchical menu structures from various sources.

Constructs menu hierarchies from config definitions, page frontmatter, and
section structure. Handles deduplication, cycle detection, and hierarchy
building with parent-child relationships.

Creation:
    Direct instantiation: MenuBuilder()
        - Created by MenuOrchestrator for menu building
        - Fresh instance created for each menu build



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `items` | - | List of MenuItem objects (flat list before hierarchy building) |
| `_seen_identifiers` | - | Set of seen identifiers for deduplication |
| `_seen_urls` | - | Set of seen URLs for deduplication |
| `_seen_names` | - | Set of seen names for deduplication Behavior Notes: - Identifiers: Each MenuItem has an identifier (slug from name by default). Parent references use identifiers. - Cycle detection: build_hierarchy() detects circular references and raises ValueError when a cycle is found. Consumers should surface this early as a configuration error. - Deduplication: Automatically prevents duplicate items by identifier, URL, and name. |
| `Relationships` | - | - Uses: MenuItem for menu item representation - Used by: MenuOrchestrator for menu building - Used in: Menu building during content discovery phase |







## Methods



#### `__init__`
```python
def __init__(self)
```


*No description provided.*






#### `add_from_config`
```python
def add_from_config(self, menu_config: list[dict]) -> None
```


Add menu items from configuration file.

Parses menu configuration from bengal.toml or config files and creates
MenuItem objects. Skips duplicates automatically and logs debug messages
for skipped items.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `menu_config` | `list[dict]` | - | List of menu item dictionaries from config file. Each dict should have: name, url, weight (optional), parent (optional), identifier (optional) |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
menu_config = [
        {"name": "Home", "url": "/", "weight": 1},
        {"name": "About", "url": "/about", "weight": 2, "parent": "home"}
    ]
    builder.add_from_config(menu_config)
```




#### `add_from_page`
```python
def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None
```


Add a page to menu based on frontmatter metadata.

Creates a MenuItem from page frontmatter menu configuration. Uses page's
relative_url for menu item URL (baseurl applied in templates). Skips
duplicates automatically.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Any` | - | Page object with frontmatter menu configuration |
| `menu_name` | `str` | - | Name of the menu (e.g., 'main', 'footer'). Currently used for logging, all menus share same builder |
| `menu_config` | `dict` | - | Menu configuration dictionary from page frontmatter. Should have: name (optional, defaults to page.title), url (optional, defaults to page.relative_url), weight (optional), parent (optional), identifier (optional) |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Page frontmatter:
    # menu:
    #   main:
    #     name: "My Page"
    #     weight: 5
    builder.add_from_page(page, "main", page.metadata.get("menu", {}).get("main", {}))
```




#### `add_from_auto_nav`
```python
def add_from_auto_nav(self, site: Any, exclude_sections: set[str] | None = None) -> None
```


Add auto-discovered sections to menu, including nested sections.

Automatically creates menu items from section hierarchy. Recursively
includes all sections (not just top-level), respects section visibility
settings (hidden, menu: false), and uses section metadata for title/weight.

Process:
    1. Find all top-level sections (no parent)
    2. Recursively add sections and subsections
    3. Skip hidden sections (hidden: true or menu: false)
    4. Use section index page metadata for title/weight
    5. Build parent-child relationships from section hierarchy


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Any` | - | Site instance with sections populated |
| `exclude_sections` | `set[str] \| None` | - | Set of section names to exclude from menu (e.g., {'api', 'cli'}). None means include all sections. |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Add all sections to menu
    builder.add_from_auto_nav(site)

    # Exclude API and CLI sections
    builder.add_from_auto_nav(site, exclude_sections={'api', 'cli'})
```




#### `build_hierarchy`
```python
def build_hierarchy(self) -> list[MenuItem]
```


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



**Returns**


`list[MenuItem]` - List of root MenuItem objects (no parent) with children populated.
    Empty list if no items or all items have parents.
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If circular references detected in parent-child relationships

:::{rubric} Examples
:class: rubric-examples
:::


```python
builder.add_from_config([{"name": "Home", "url": "/"}])
    builder.add_from_config([{"name": "About", "url": "/about", "parent": "home"}])
    root_items = builder.build_hierarchy()
    # Returns: [MenuItem(name="Home", children=[MenuItem(name="About")])]
```






#### `mark_active_items`
```python
def mark_active_items(self, current_url: str, menu_items: list[MenuItem]) -> None
```


Mark active items in menu tree based on current page URL.

Recursively marks menu items as active if their URL matches the current
page URL. Also marks items in the active trail (items with active children).
Resets all active states before marking to ensure clean state.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_url` | `str` | - | Current page URL to match against (will be normalized) |
| `menu_items` | `list[MenuItem]` | - | List of root MenuItem objects to process (hierarchical tree) |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
menu_items = builder.build_hierarchy()
    builder.mark_active_items("/blog/post", menu_items)
    # Items with URL="/blog/post" are marked active
    # Items with URL="/blog" are marked active_trail (have active child)
```



---
*Generated by Bengal autodoc from `bengal/bengal/core/menu.py`*

