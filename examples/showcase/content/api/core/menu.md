
---
title: "core.menu"
type: python-module
source_file: "bengal/core/menu.py"
css_class: api-content
description: "Menu system for navigation."
---

# core.menu

Menu system for navigation.

---

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

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`name`** (`str`)- **`url`** (`str`)- **`weight`** (`int`)- **`parent`** (`str | None`)- **`identifier`** (`str | None`)- **`children`** (`list['MenuItem']`)- **`active`** (`bool`)- **`active_trail`** (`bool`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__post_init__`
```python
def __post_init__(self)
```

Set identifier from name if not provided.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `add_child`
```python
def add_child(self, child: 'MenuItem') -> None
```

Add a child menu item and sort by weight.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`child`** (`'MenuItem'`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `mark_active`
```python
def mark_active(self, current_url: str) -> bool
```

Mark this item as active if URL matches.
Returns True if this or any child is active.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`current_url`** (`str`) - Current page URL to match against

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if this item or any child is active




---
#### `reset_active`
```python
def reset_active(self) -> None
```

Reset active states (called before each page render).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `to_dict`
```python
def to_dict(self) -> dict
```

Convert to dict for template access.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict`




---

### `MenuBuilder`


Builds hierarchical menu structures from various sources.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `add_from_config`
```python
def add_from_config(self, menu_config: list[dict]) -> None
```

Add menu items from config.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`menu_config`** (`list[dict]`) - List of menu item dicts from config file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `add_from_page`
```python
def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None
```

Add a page to menu based on frontmatter.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page`** (`Any`) - Page object
- **`menu_name`** (`str`) - Name of the menu (e.g., 'main', 'footer')
- **`menu_config`** (`dict`) - Menu configuration from page frontmatter

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `build_hierarchy`
```python
def build_hierarchy(self) -> list[MenuItem]
```

Build hierarchical tree from flat list with validation.
Returns list of root items (no parent).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[MenuItem]` - List of root MenuItem objects with children populated

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If circular references detected



---
#### `mark_active_items`
```python
def mark_active_items(self, current_url: str, menu_items: list[MenuItem]) -> None
```

Mark active items in menu tree.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`current_url`** (`str`) - Current page URL
- **`menu_items`** (`list[MenuItem]`) - List of menu items to process

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
