
---
title: "template_functions.taxonomies"
type: python-module
source_file: "bengal/rendering/template_functions/taxonomies.py"
css_class: api-content
description: "Taxonomy helper functions for templates.  Provides 4 functions for working with tags, categories, and related content."
---

# template_functions.taxonomies

Taxonomy helper functions for templates.

Provides 4 functions for working with tags, categories, and related content.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register taxonomy helper functions with Jinja2 environment.



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
### `related_posts`
```python
def related_posts(page: Any, all_pages: list[Any] | None = None, limit: int = 5) -> list[Any]
```

Find related posts based on shared tags.

PERFORMANCE NOTE: This function now uses pre-computed related posts
for O(1) access. The old O(n²) algorithm is kept as a fallback for
backward compatibility with custom templates.

RECOMMENDED: Use `page.related_posts` directly in templates instead
of calling this function.



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
* - `page`
  - `Any`
  - -
  - Current page
* - `all_pages`
  - `list[Any] | None`
  - `None`
  - All site pages (optional, only needed for fallback)
* - `limit`
  - `int`
  - `5`
  - Maximum number of related posts
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - List of related pages sorted by relevance

Example (NEW - recommended):
    {% set related = page.related_posts[:3] %}

Example (OLD - backward compatible):
    {% set related = related_posts(page, limit=3) %}
    {% for post in related %}
      <a href="{{ url_for(post) }}">{{ post.title }}</a>
    {% endfor %}




---
### `popular_tags`
```python
def popular_tags(tags_dict: dict[str, list[Any]], limit: int = 10) -> list[tuple]
```

Get most popular tags sorted by count.



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
* - `tags_dict`
  - `dict[str, list[Any]]`
  - -
  - Dictionary of tag -> pages
* - `limit`
  - `int`
  - `10`
  - Maximum number of tags
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple]` - List of (tag, count) tuples




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set top_tags = popular_tags(limit=5) %}
```


---
### `tag_url`
```python
def tag_url(tag: str) -> str
```

Generate URL for a tag page.

Uses bengal.utils.text.slugify for tag slug generation.



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
* - `tag`
  - `str`
  - -
  - Tag name
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - URL path to tag page




:::{rubric} Examples
:class: rubric-examples
:::
```python
<a href="{{ tag_url('python') }}">Python</a>
```


---
### `has_tag`
```python
def has_tag(page: Any, tag: str) -> bool
```

Check if page has a specific tag.



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
* - `page`
  - `Any`
  - -
  - Page to check
* - `tag`
  - `str`
  - -
  - Tag to look for
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if page has the tag




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if page | has_tag('tutorial') %}
```


---
