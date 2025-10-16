
---
title: "template_functions.images"
type: python-module
source_file: "bengal/rendering/template_functions/images.py"
css_class: api-content
description: "Image processing functions for templates.  Provides 6 functions for working with images in templates. Note: Some functions are stubs for future PIL/Pillow integration."
---

# template_functions.images

Image processing functions for templates.

Provides 6 functions for working with images in templates.
Note: Some functions are stubs for future PIL/Pillow integration.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register image processing functions with Jinja2 environment.



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
### `image_url`
```python
def image_url(path: str, base_url: str, width: int | None = None, height: int | None = None, quality: int | None = None) -> str
```

Generate image URL with optional parameters.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 5 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `path`
  - `str`
  - -
  - Image path
* - `base_url`
  - `str`
  - -
  - Base URL for site
* - `width`
  - `int | None`
  - `None`
  - Target width (optional)
* - `height`
  - `int | None`
  - `None`
  - Target height (optional)
* - `quality`
  - `int | None`
  - `None`
  - JPEG quality (optional)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Image URL with query parameters




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ image_url('photos/hero.jpg', width=800) }}
```


---
### `image_dimensions`
```python
def image_dimensions(path: str, root_path: Path) -> tuple[int, int] | None
```

Get image dimensions (width, height).

Requires Pillow (PIL) library. Returns None if not available or file not found.



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
* - `path`
  - `str`
  - -
  - Image path
* - `root_path`
  - `Path`
  - -
  - Site root path
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`tuple[int, int] | None` - Tuple of (width, height) or None




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set width, height = image_dimensions('photo.jpg') %}
```


---
### `image_srcset`
```python
def image_srcset(image_path: str, sizes: list[int]) -> str
```

Generate srcset attribute for responsive images.



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
* - `image_path`
  - `str`
  - -
  - Base image path
* - `sizes`
  - `list[int]`
  - -
  - List of widths (e.g., [400, 800, 1200])
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - srcset attribute value




:::{rubric} Examples
:class: rubric-examples
:::
```python
<img srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}" />
```


---
### `image_srcset_gen`
```python
def image_srcset_gen(image_path: str, sizes: list[int] | None = None) -> str
```

Generate srcset attribute with default sizes.



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
* - `image_path`
  - `str`
  - -
  - Base image path
* - `sizes`
  - `list[int] | None`
  - `None`
  - List of widths (default: [400, 800, 1200, 1600])
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - srcset attribute value




:::{rubric} Examples
:class: rubric-examples
:::
```python
<img srcset="{{ image_srcset_gen('hero.jpg') }}" />
```


---
### `image_alt`
```python
def image_alt(filename: str) -> str
```

Generate alt text from filename.

Converts filename to human-readable alt text by:
- Removing extension
- Replacing hyphens/underscores with spaces
- Capitalizing words



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
* - `filename`
  - `str`
  - -
  - Image filename
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Alt text suggestion




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ 'mountain-sunset.jpg' | image_alt }}
```


---
### `image_data_uri`
```python
def image_data_uri(path: str, root_path: Path) -> str
```

Convert image to data URI for inline embedding.



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
* - `path`
  - `str`
  - -
  - Image path
* - `root_path`
  - `Path`
  - -
  - Site root path
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Data URI string




:::{rubric} Examples
:class: rubric-examples
:::
```python
<img src="{{ image_data_uri('icons/logo.svg') }}" alt="Logo">
```


---
