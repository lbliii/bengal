
---
title: "template_functions.seo"
type: python-module
source_file: "bengal/rendering/template_functions/seo.py"
css_class: api-content
description: "SEO helper functions for templates.  Provides 4 functions for generating SEO-friendly meta tags and content."
---

# template_functions.seo

SEO helper functions for templates.

Provides 4 functions for generating SEO-friendly meta tags and content.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register SEO helper functions with Jinja2 environment.

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
### `meta_description`
```python
def meta_description(text: str, length: int = 160) -> str
```

Generate meta description from text.

Creates SEO-friendly description by:
- Stripping HTML
- Truncating to length
- Ending at sentence boundary if possible



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`text`** (`str`) - Source text
- **`length`** (`int`) = `160` - Maximum length (default: 160 chars)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Meta description text




:::{rubric} Examples
:class: rubric-examples
:::
```python
<meta name="description" content="{{ page.content | meta_description }}">
```


---
### `meta_keywords`
```python
def meta_keywords(tags: list[str], max_count: int = 10) -> str
```

Generate meta keywords from tags.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`tags`** (`list[str]`) - List of tags/keywords
- **`max_count`** (`int`) = `10` - Maximum number of keywords (default: 10)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Comma-separated keywords




:::{rubric} Examples
:class: rubric-examples
:::
```python
<meta name="keywords" content="{{ page.tags | meta_keywords }}">
```


---
### `canonical_url`
```python
def canonical_url(env: 'Environment', path: str) -> str
```

Generate canonical URL for SEO.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`path`** (`str`) - Page path (relative or absolute)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Full canonical URL




:::{rubric} Examples
:class: rubric-examples
:::
```python
<link rel="canonical" href="{{ canonical_url(page.url) }}">
```


---
### `og_image`
```python
def og_image(env: 'Environment', image_path: str) -> str
```

Generate Open Graph image URL.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`image_path`** (`str`) - Relative path to image

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Full image URL for og:image




:::{rubric} Examples
:class: rubric-examples
:::
```python
<meta property="og:image" content="{{ og_image('images/hero.jpg') }}">
```


---
