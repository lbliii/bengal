
---
title: "orchestration.menu"
type: python-module
source_file: "bengal/orchestration/menu.py"
css_class: api-content
description: "Menu orchestration for Bengal SSG.  Handles navigation menu building from config and page frontmatter."
---

# orchestration.menu

Menu orchestration for Bengal SSG.

Handles navigation menu building from config and page frontmatter.

---

## Classes

### `MenuOrchestrator`


Handles navigation menu building with incremental caching.

Responsibilities:
    - Build menus from config definitions
    - Add items from page frontmatter
    - Mark active menu items for current page
    - Cache menus when config/pages unchanged (incremental optimization)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize menu orchestrator.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - Site instance containing menu configuration
:::

::::




---
#### `build`
```python
def build(self, changed_pages: set[Path] | None = None, config_changed: bool = False) -> bool
```

Build all menus from config and page frontmatter.

With incremental building:
- If config unchanged AND no pages with menu frontmatter changed
- Skip rebuild and reuse cached menus



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `changed_pages`
  - `set[Path] | None`
  - `None`
  - Set of paths for pages that changed (for incremental builds)
* - `config_changed`
  - `bool`
  - `False`
  - Whether config file changed (forces rebuild)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if menus were rebuilt, False if cached menus reused

Called during site.build() after content discovery.




---
#### `mark_active`
```python
def mark_active(self, current_page: 'Page') -> None
```

Mark active menu items for the current page being rendered.
Called during rendering for each page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `current_page`
  - `'Page'`
  - -
  - Page currently being rendered
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


