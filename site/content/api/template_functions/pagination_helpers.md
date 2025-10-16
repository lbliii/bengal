
---
title: "template_functions.pagination_helpers"
type: python-module
source_file: "bengal/rendering/template_functions/pagination_helpers.py"
css_class: api-content
description: "Pagination helper functions for templates.  Provides 3 functions for building pagination controls."
---

# template_functions.pagination_helpers

Pagination helper functions for templates.

Provides 3 functions for building pagination controls.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register pagination helper functions with Jinja2 environment.



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
* - `env`
  - `'Environment'`
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `paginate_items`
```python
def paginate_items(items: list[Any], per_page: int = 10, current_page: int = 1) -> dict
```

Paginate a list of items.



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
* - `items`
  - `list[Any]`
  - -
  - List to paginate
* - `per_page`
  - `int`
  - `10`
  - Items per page (default: 10)
* - `current_page`
  - `int`
  - `1`
  - Current page number (1-indexed)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`dict` - Dictionary with pagination data




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set pagination = posts | paginate(10, current_page) %}
```


---
### `page_url`
```python
def page_url(base_path: str, page_num: int) -> str
```

Generate URL for a pagination page.



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
* - `base_path`
  - `str`
  - -
  - Base path (e.g., "/posts/")
* - `page_num`
  - `int`
  - -
  - Page number
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - URL for that page




:::{rubric} Examples
:class: rubric-examples
:::
```python
<a href="{{ page_url('/posts/', 2) }}">Page 2</a>
```


---
### `page_range`
```python
def page_range(current_page: int, total_pages: int, window: int = 2) -> list[int | None]
```

Generate page range with ellipsis for pagination controls.



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
* - `current_page`
  - `int`
  - -
  - Current page number
* - `total_pages`
  - `int`
  - -
  - Total number of pages
* - `window`
  - `int`
  - `2`
  - Number of pages to show around current (default: 2)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[int | None]` - List of page numbers with None for ellipsis




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for page_num in page_range(5, 20, window=2) %}
```


---
