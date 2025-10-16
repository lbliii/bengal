
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
### `absolute_url`
```python
def absolute_url(url: str, base_url: str) -> str
```

Convert relative URL to absolute URL.



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
* - `url`
  - `str`
  - -
  - Relative or absolute URL
* - `base_url`
  - `str`
  - -
  - Base URL to prepend
:::

::::
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

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `text`
  - `str`
  - -
  - Text to encode
:::

::::
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

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `text`
  - `str`
  - -
  - Text to decode
:::

::::
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
