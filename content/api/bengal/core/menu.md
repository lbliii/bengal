
---
title: "menu"
type: "python-module"
source_file: "../bengal/bengal/core/menu.py"
line_number: 1
description: "Menu system for navigation."
---

# menu
**Type:** Module
**Source:** [View source](../bengal/bengal/core/menu.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›menu

Menu system for navigation.

## Classes




### `MenuItem`


Represents a single menu item with optional hierarchy.

Can be created from:
1. Config file (explicit definition)
2. Page frontmatter (page registers itself in menu)
3. Section structure (auto-generated)


```{info}
This is a dataclass.
```



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | *No description provided.* |
| `url` | - | *No description provided.* |
| `weight` | - | *No description provided.* |
| `parent` | - | *No description provided.* |
| `identifier` | - | *No description provided.* |
| `children` | - | *No description provided.* |
| `active` | - | *No description provided.* |
| `active_trail` | - | *No description provided.* |







## Methods



#### `__post_init__`
```python
def __post_init__(self)
```


Set identifier from name if not provided.




#### `add_child`
```python
def add_child(self, child: MenuItem) -> None
```


Add a child menu item and sort by weight.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `child` | `MenuItem` | - | *No description provided.* |







**Returns**


`None`



#### `mark_active`
```python
def mark_active(self, current_url: str) -> bool
```


Mark this item as active if URL matches.
Returns True if this or any child is active.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_url` | `str` | - | Current page URL to match against |







**Returns**


`bool` - True if this item or any child is active



#### `reset_active`
```python
def reset_active(self) -> None
```


Reset active states (called before each page render).



**Returns**


`None`



#### `to_dict`
```python
def to_dict(self) -> dict
```


Convert to dict for template access.



**Returns**


`dict`




### `MenuBuilder`


Builds hierarchical menu structures from various sources.

Behavior notes:
- Identifiers: Each `MenuItem` has an `identifier` (slug from name by default). Parent
  references use identifiers.
- Cycle detection: `build_hierarchy()` detects circular references in the built tree
  and raises `ValueError` when a cycle is found. Consumers should surface this early
  as a configuration error.
- Deduplication: Automatically prevents duplicate items by identifier, URL, and name









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


Add menu items from config.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `menu_config` | `list[dict]` | - | List of menu item dicts from config file |







**Returns**


`None`



#### `add_from_page`
```python
def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None
```


Add a page to menu based on frontmatter.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Any` | - | Page object |
| `menu_name` | `str` | - | Name of the menu (e.g., 'main', 'footer') |
| `menu_config` | `dict` | - | Menu configuration from page frontmatter |







**Returns**


`None`



#### `add_from_auto_nav`
```python
def add_from_auto_nav(self, site: Any, exclude_sections: set[str] | None = None) -> None
```


Add auto-discovered sections to menu, including nested sections.

This integrates auto-nav discovery directly into MenuBuilder,
ensuring deduplication happens at the builder level. Recursively
includes all sections in the hierarchy, not just top-level ones.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Any` | - | Site instance with sections |
| `exclude_sections` | `set[str] \| None` | - | Set of section names to exclude (e.g., {'api', 'cli'}) |







**Returns**


`None`



#### `build_hierarchy`
```python
def build_hierarchy(self) -> list[MenuItem]
```


Build hierarchical tree from flat list with validation.
Returns list of root items (no parent).



**Returns**


`list[MenuItem]` - List of root MenuItem objects with children populated
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If circular references detected






#### `mark_active_items`
```python
def mark_active_items(self, current_url: str, menu_items: list[MenuItem]) -> None
```


Mark active items in menu tree.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_url` | `str` | - | Current page URL |
| `menu_items` | `list[MenuItem]` | - | List of menu items to process |







**Returns**


`None`



---
*Generated by Bengal autodoc from `../bengal/bengal/core/menu.py`*
