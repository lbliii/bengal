
---
title: "template_functions.urls"
type: python-module
source_file: "bengal/rendering/template_functions/urls.py"
css_class: api-content
description: "URL manipulation functions for templates.  Provides 3 functions for working with URLs in templates."
---

# template_functions.urls

URL manipulation functions for templates.

Provides 3 functions for working with URLs in templates.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register URL functions with Jinja2 environment.

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
### `absolute_url`
```python
def absolute_url(env: 'Environment', url: str) -> str
```

Convert relative URL to absolute URL.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`url`** (`str`) - Relative or absolute URL

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Absolute URL




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ page.url | absolute_url }}
```


---
### `url_encode`
```python
def url_encode(text: str) -> str
```

URL encode string (percent encoding).

Encodes special characters for safe use in URLs.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`text`** (`str`) - Text to encode

:::{rubric} Returns
:class: rubric-returns
:::
`str` - URL-encoded text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ search_query | url_encode }}
```


---
### `url_decode`
```python
def url_decode(text: str) -> str
```

URL decode string (decode percent encoding).

Decodes percent-encoded characters back to original form.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`text`** (`str`) - Text to decode

:::{rubric} Returns
:class: rubric-returns
:::
`str` - URL-decoded text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ encoded_text | url_decode }}
```


---
