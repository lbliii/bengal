
---
title: "utils.pagination"
type: python-module
source_file: "bengal/utils/pagination.py"
css_class: api-content
description: "Pagination utility for splitting long lists into pages."
---

# utils.pagination

Pagination utility for splitting long lists into pages.

---

## Classes

### `Paginator`


Paginator for splitting a list of items into pages.

Usage:
    paginator = Paginator(posts, per_page=10)
    page = paginator.page(1)  # Get first page


:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `items`
  - -
  - List of items to paginate
* - `per_page`
  - -
  - Number of items per page
* - `num_pages`
  - -
  - Total number of pages
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, items: list[T], per_page: int = 10) -> None
```

Initialize the paginator.



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
* - `items`
  - `list[T]`
  - -
  - List of items to paginate
* - `per_page`
  - `int`
  - `10`
  - Number of items per page (default: 10)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `page`
```python
def page(self, number: int) -> list[T]
```

Get items for a specific page.



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
* - `number`
  - `int`
  - -
  - Page number (1-indexed)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[T]` - List of items for that page

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If page number is out of range



---
#### `page_context`
```python
def page_context(self, page_number: int, base_url: str) -> dict[str, Any]
```

Get template context for a specific page.



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
* - `page_number`
  - `int`
  - -
  - Current page number (1-indexed)
* - `base_url`
  - `str`
  - -
  - Base URL for pagination links (e.g., '/posts/')
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Dictionary with pagination context for templates




---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
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
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
