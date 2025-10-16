
---
title: "postprocess.sitemap"
type: python-module
source_file: "bengal/postprocess/sitemap.py"
css_class: api-content
description: "Sitemap generation for SEO."
---

# postprocess.sitemap

Sitemap generation for SEO.

---

## Classes

### `SitemapGenerator`


Generates XML sitemap for SEO.

Creates a sitemap.xml file listing all pages with metadata like:
- URL location
- Last modified date
- Change frequency
- Priority

The sitemap helps search engines discover and index site content.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any) -> None
```

Initialize sitemap generator.



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
* - `self`
  - -
  - -
  - -
* - `site`
  - `Any`
  - -
  - Site instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate`
```python
def generate(self) -> None
```

Generate and write sitemap.xml to output directory.

Iterates through all pages, creates XML entries with URLs and metadata,
and writes the sitemap atomically to prevent corruption.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`Exception`**: If sitemap generation or file writing fails



---
