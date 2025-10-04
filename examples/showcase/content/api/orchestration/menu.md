---
title: "orchestration.menu"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/menu.py"
---

# orchestration.menu

Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter.

**Source:** `../../bengal/orchestration/menu.py`

---

## Classes

### MenuOrchestrator


Handles navigation menu building.

Responsibilities:
    - Build menus from config definitions
    - Add items from page frontmatter
    - Mark active menu items for current page




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize menu orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance containing menu configuration







---
#### build

```python
def build(self) -> None
```

Build all menus from config and page frontmatter.
Called during site.build() after content discovery.

**Parameters:**

- **self**

**Returns:** `None`






---
#### mark_active

```python
def mark_active(self, current_page: 'Page') -> None
```

Mark active menu items for the current page being rendered.
Called during rendering for each page.

**Parameters:**

- **self**
- **current_page** (`'Page'`) - Page currently being rendered

**Returns:** `None`






---


