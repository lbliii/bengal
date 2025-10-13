
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

Note: site parameter kept for signature compatibility but site is now
accessed via env.site (stored by template_engine.py).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`)
- **`site`** (`'Site'`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `related_posts`
```python
def related_posts(env: 'Environment', page: Any, limit: int = 5) -> list[Any]
```

Get related posts by shared tags (no closures).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`page`** (`Any`) - Current page
- **`limit`** (`int`) = `5` - Maximum number of related posts

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - List of related pages




---
### `popular_tags`
```python
def popular_tags(env: 'Environment', limit: int = 10) -> list[tuple]
```

Get most popular tags.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`limit`** (`int`) = `10` - Maximum number of tags

:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple]` - List of (tag_slug, count) tuples




---
### `tag_url`
```python
def tag_url(ctx, tag: str) -> str
```

Generate tag URL (locale-aware for i18n).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`ctx`** - Jinja2 context (injected by @pass_context)
- **`tag`** (`str`) - Tag slug

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Tag URL with i18n prefix if needed




---
### `has_tag`
```python
def has_tag(page: Any, tag: str) -> bool
```

Check if page has a specific tag.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`page`** (`Any`) - Page to check
- **`tag`** (`str`) - Tag to look for

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
