---
title: "core.menu"
layout: api-reference
type: python-module
source_file: "../../bengal/core/menu.py"
---

# core.menu

Menu system for navigation.

**Source:** `../../bengal/core/menu.py`

---

## Classes

### MenuItem


Represents a single menu item with optional hierarchy.

Can be created from:
1. Config file (explicit definition)
2. Page frontmatter (page registers itself in menu)
3. Section structure (auto-generated)

::: info
This is a dataclass.
:::

**Attributes:**

- **name** (`str`)- **url** (`str`)- **weight** (`int`)- **parent** (`Optional[str]`)- **identifier** (`Optional[str]`)- **children** (`List['MenuItem']`)- **active** (`bool`)- **active_trail** (`bool`)

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

Set identifier from name if not provided.

**Parameters:**

- **self**







---
#### add_child

```python
def add_child(self, child: 'MenuItem') -> None
```

Add a child menu item and sort by weight.

**Parameters:**

- **self**
- **child** (`'MenuItem'`)

**Returns:** `None`






---
#### mark_active

```python
def mark_active(self, current_url: str) -> bool
```

Mark this item as active if URL matches.
Returns True if this or any child is active.

**Parameters:**

- **self**
- **current_url** (`str`) - Current page URL to match against

**Returns:** `bool` - True if this item or any child is active






---
#### reset_active

```python
def reset_active(self) -> None
```

Reset active states (called before each page render).

**Parameters:**

- **self**

**Returns:** `None`






---
#### to_dict

```python
def to_dict(self) -> dict
```

Convert to dict for template access.

**Parameters:**

- **self**

**Returns:** `dict`






---

### MenuBuilder


Builds hierarchical menu structures from various sources.




**Methods:**

#### __init__

```python
def __init__(self)
```

*No description provided.*

**Parameters:**

- **self**







---
#### add_from_config

```python
def add_from_config(self, menu_config: List[dict]) -> None
```

Add menu items from config.

**Parameters:**

- **self**
- **menu_config** (`List[dict]`) - List of menu item dicts from config file

**Returns:** `None`






---
#### add_from_page

```python
def add_from_page(self, page: Any, menu_name: str, menu_config: dict) -> None
```

Add a page to menu based on frontmatter.

**Parameters:**

- **self**
- **page** (`Any`) - Page object
- **menu_name** (`str`) - Name of the menu (e.g., 'main', 'footer')
- **menu_config** (`dict`) - Menu configuration from page frontmatter

**Returns:** `None`






---
#### build_hierarchy

```python
def build_hierarchy(self) -> List[MenuItem]
```

Build hierarchical tree from flat list with validation.
Returns list of root items (no parent).

**Parameters:**

- **self**

**Returns:** `List[MenuItem]` - List of root MenuItem objects with children populated

**Raises:**

- **ValueError**: If circular references detected





---
#### mark_active_items

```python
def mark_active_items(self, current_url: str, menu_items: List[MenuItem]) -> None
```

Mark active items in menu tree.

**Parameters:**

- **self**
- **current_url** (`str`) - Current page URL
- **menu_items** (`List[MenuItem]`) - List of menu items to process

**Returns:** `None`






---


