
---
title: "orchestration.related_posts"
type: python-module
source_file: "bengal/orchestration/related_posts.py"
css_class: api-content
description: "Related Posts orchestration for Bengal SSG.  Builds related posts index during build phase for O(1) template access."
---

# orchestration.related_posts

Related Posts orchestration for Bengal SSG.

Builds related posts index during build phase for O(1) template access.

---

## Classes

### `RelatedPostsOrchestrator`


Builds related posts relationships during build phase.

Strategy: Use taxonomy index for efficient tag-based matching.
Complexity: O(n·t) where n=pages, t=avg tags per page (typically 2-5)

This moves expensive related posts computation from render-time (O(n²))
to build-time (O(n·t)), resulting in O(1) template access.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize related posts orchestrator.



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
  - Site instance
:::

::::




---
#### `build_index`
```python
def build_index(self, limit: int = 5, parallel: bool = True, affected_pages: list['Page'] | None = None) -> None
```

Compute related posts for pages using tag-based matching.

This is called once during the build phase. Each page gets a
pre-computed list of related pages stored in page.related_posts.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `limit`
  - `int`
  - `5`
  - Maximum related posts per page (default: 5)
* - `parallel`
  - `bool`
  - `True`
  - Whether to use parallel processing (default: True)
* - `affected_pages`
  - `list['Page'] | None`
  - `None`
  - List of pages whose related posts should be recomputed. If None, computes for all pages (full build). If provided, only updates affected pages (incremental).
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
