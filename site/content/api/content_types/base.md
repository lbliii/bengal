
---
title: "content_types.base"
type: python-module
source_file: "bengal/content_types/base.py"
css_class: api-content
description: "Base strategy class for content types.  Defines the interface that all content type strategies must implement."
---

# content_types.base

Base strategy class for content types.

Defines the interface that all content type strategies must implement.

---

## Classes

### `ContentTypeStrategy`


Base strategy for content type behavior.

Each content type (blog, doc, api-reference, etc.) can have its own
strategy that defines:
- How pages are sorted
- What pages are shown in list views
- Whether pagination is used
- What template to use




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort pages for display in list views.



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
* - `pages`
  - `list['Page']`
  - -
  - List of pages to sort
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']` - Sorted list of pages

Default: Sort by weight (ascending), then title (alphabetical)




---
#### `filter_display_pages`
```python
def filter_display_pages(self, pages: list['Page'], index_page: 'Page | None' = None) -> list['Page']
```

Filter which pages to show in list views.



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
* - `pages`
  - `list['Page']`
  - -
  - All pages in the section
* - `index_page`
  - `'Page | None'`
  - `None`
  - The section's index page (to exclude from lists)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']` - Filtered list of pages

Default: Exclude the index page itself




---
#### `should_paginate`
```python
def should_paginate(self, page_count: int, config: dict) -> bool
```

Determine if this content type should use pagination.



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
* - `page_count`
  - `int`
  - -
  - Number of pages in section
* - `config`
  - `dict`
  - -
  - Site configuration
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if pagination should be used

Default: No pagination unless explicitly enabled




---
#### `get_template`
```python
def get_template(self) -> str
```

Get the template name for this content type.



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

`str` - Template path (e.g., "blog/list.html")




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Determine if this strategy applies to a section based on heuristics.

Override this in subclasses to provide auto-detection logic.



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
* - `section`
  - `'Section'`
  - -
  - Section to analyze
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if this strategy should be used for this section

Default: False (must be explicitly set)




---


