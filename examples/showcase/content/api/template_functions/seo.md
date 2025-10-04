---
title: "template_functions.seo"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/seo.py"
---

# template_functions.seo

SEO helper functions for templates.

Provides 4 functions for generating SEO-friendly meta tags and content.

**Source:** `../../bengal/rendering/template_functions/seo.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register SEO helper functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### meta_description

```python
def meta_description(text: str, length: int = 160) -> str
```

Generate meta description from text.

Creates SEO-friendly description by:
- Stripping HTML
- Truncating to length
- Ending at sentence boundary if possible

**Parameters:**

- **text** (`str`) - Source text
- **length** (`int`) = `160` - Maximum length (default: 160 chars)

**Returns:** `str` - Meta description text


**Examples:**

<meta name="description" content="{{ page.content | meta_description }}">




---
### meta_keywords

```python
def meta_keywords(tags: List[str], max_count: int = 10) -> str
```

Generate meta keywords from tags.

**Parameters:**

- **tags** (`List[str]`) - List of tags/keywords
- **max_count** (`int`) = `10` - Maximum number of keywords (default: 10)

**Returns:** `str` - Comma-separated keywords


**Examples:**

<meta name="keywords" content="{{ page.tags | meta_keywords }}">




---
### canonical_url

```python
def canonical_url(path: str, base_url: str) -> str
```

Generate canonical URL for SEO.

**Parameters:**

- **path** (`str`) - Page path (relative or absolute)
- **base_url** (`str`) - Site base URL

**Returns:** `str` - Full canonical URL


**Examples:**

<link rel="canonical" href="{{ canonical_url(page.url) }}">




---
### og_image

```python
def og_image(image_path: str, base_url: str) -> str
```

Generate Open Graph image URL.

**Parameters:**

- **image_path** (`str`) - Relative path to image
- **base_url** (`str`) - Site base URL

**Returns:** `str` - Full image URL for og:image


**Examples:**

<meta property="og:image" content="{{ og_image('images/hero.jpg') }}">




---
