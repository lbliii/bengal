
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
- **`self`**
- **`site`** (`'Site'`) - Site instance





---
#### `build_index`
```python
def build_index(self, limit: int = 5) -> None
```

Compute related posts for all pages using tag-based matching.

This is called once during the build phase. Each page gets a
pre-computed list of related pages stored in page.related_posts.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`limit`** (`int`) = `5` - Maximum related posts per page (default: 5)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
