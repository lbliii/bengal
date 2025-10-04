---
title: "template_functions.urls"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/urls.py"
---

# template_functions.urls

URL manipulation functions for templates.

Provides 3 functions for working with URLs in templates.

**Source:** `../../bengal/rendering/template_functions/urls.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register URL functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### absolute_url

```python
def absolute_url(url: str, base_url: str) -> str
```

Convert relative URL to absolute URL.

**Parameters:**

- **url** (`str`) - Relative or absolute URL
- **base_url** (`str`) - Base URL to prepend

**Returns:** `str` - Absolute URL


**Examples:**

{{ page.url | absolute_url }}




---
### url_encode

```python
def url_encode(text: str) -> str
```

URL encode string (percent encoding).

Encodes special characters for safe use in URLs.

**Parameters:**

- **text** (`str`) - Text to encode

**Returns:** `str` - URL-encoded text


**Examples:**

{{ search_query | url_encode }}




---
### url_decode

```python
def url_decode(text: str) -> str
```

URL decode string (decode percent encoding).

Decodes percent-encoded characters back to original form.

**Parameters:**

- **text** (`str`) - Text to decode

**Returns:** `str` - URL-decoded text


**Examples:**

{{ encoded_text | url_decode }}




---
