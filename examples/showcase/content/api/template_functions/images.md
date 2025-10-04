---
title: "template_functions.images"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/images.py"
---

# template_functions.images

Image processing functions for templates.

Provides 6 functions for working with images in templates.
Note: Some functions are stubs for future PIL/Pillow integration.

**Source:** `../../bengal/rendering/template_functions/images.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register image processing functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### image_url

```python
def image_url(path: str, base_url: str, width: Optional[int] = None, height: Optional[int] = None, quality: Optional[int] = None) -> str
```

Generate image URL with optional parameters.

**Parameters:**

- **path** (`str`) - Image path
- **base_url** (`str`) - Base URL for site
- **width** (`Optional[int]`) = `None` - Target width (optional)
- **height** (`Optional[int]`) = `None` - Target height (optional)
- **quality** (`Optional[int]`) = `None` - JPEG quality (optional)

**Returns:** `str` - Image URL with query parameters


**Examples:**

{{ image_url('photos/hero.jpg', width=800) }}




---
### image_dimensions

```python
def image_dimensions(path: str, root_path: Path) -> Optional[Tuple[int, int]]
```

Get image dimensions (width, height).

Requires Pillow (PIL) library. Returns None if not available or file not found.

**Parameters:**

- **path** (`str`) - Image path
- **root_path** (`Path`) - Site root path

**Returns:** `Optional[Tuple[int, int]]` - Tuple of (width, height) or None


**Examples:**

{% set width, height = image_dimensions('photo.jpg') %}




---
### image_srcset

```python
def image_srcset(image_path: str, sizes: List[int]) -> str
```

Generate srcset attribute for responsive images.

**Parameters:**

- **image_path** (`str`) - Base image path
- **sizes** (`List[int]`) - List of widths (e.g., [400, 800, 1200])

**Returns:** `str` - srcset attribute value


**Examples:**

<img srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}" />




---
### image_srcset_gen

```python
def image_srcset_gen(image_path: str, sizes: List[int] = None) -> str
```

Generate srcset attribute with default sizes.

**Parameters:**

- **image_path** (`str`) - Base image path
- **sizes** (`List[int]`) = `None` - List of widths (default: [400, 800, 1200, 1600])

**Returns:** `str` - srcset attribute value


**Examples:**

<img srcset="{{ image_srcset_gen('hero.jpg') }}" />




---
### image_alt

```python
def image_alt(filename: str) -> str
```

Generate alt text from filename.

Converts filename to human-readable alt text by:
- Removing extension
- Replacing hyphens/underscores with spaces
- Capitalizing words

**Parameters:**

- **filename** (`str`) - Image filename

**Returns:** `str` - Alt text suggestion


**Examples:**

{{ 'mountain-sunset.jpg' | image_alt }}




---
### image_data_uri

```python
def image_data_uri(path: str, root_path: Path) -> str
```

Convert image to data URI for inline embedding.

**Parameters:**

- **path** (`str`) - Image path
- **root_path** (`Path`) - Site root path

**Returns:** `str` - Data URI string


**Examples:**

<img src="{{ image_data_uri('icons/logo.svg') }}" alt="Logo">




---
