
---
title: "content_types.registry"
type: python-module
source_file: "bengal/content_types/registry.py"
css_class: api-content
description: "Content type strategy registry.  Maps content type names to their strategies and provides lookup functionality."
---

# content_types.registry

Content type strategy registry.

Maps content type names to their strategies and provides lookup functionality.

---


## Functions

### `get_strategy`
```python
def get_strategy(content_type: str) -> ContentTypeStrategy
```

Get the strategy for a content type.



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
* - `content_type`
  - `str`
  - -
  - Type name (e.g., "blog", "doc", "api-reference")
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`ContentTypeStrategy` - ContentTypeStrategy instance




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> strategy = get_strategy("blog")
    >>> sorted_posts = strategy.sort_pages(posts)
```


---
### `detect_content_type`
```python
def detect_content_type(section: 'Section') -> str
```

Auto-detect content type from section characteristics.

Uses heuristics from each strategy to determine the best type.

Priority order:
1. Explicit type in section metadata
2. Cascaded type from parent section
3. Auto-detection via strategy heuristics
4. Default to "list"



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
* - `section`
  - `'Section'`
  - -
  - Section to analyze
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Content type name




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> content_type = detect_content_type(blog_section)
    >>> assert content_type == "blog"
```


---
### `register_strategy`
```python
def register_strategy(content_type: str, strategy: ContentTypeStrategy) -> None
```

Register a custom content type strategy.

Allows users to add their own content types.



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
* - `content_type`
  - `str`
  - -
  - Type name
* - `strategy`
  - `ContentTypeStrategy`
  - -
  - Strategy instance
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> class CustomStrategy(ContentTypeStrategy):
    ...     default_template = "custom/list.html"
    >>> register_strategy("custom", CustomStrategy())
```


---
