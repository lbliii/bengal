
---
title: "postprocess.special_pages"
type: python-module
source_file: "bengal/postprocess/special_pages.py"
css_class: api-content
description: "Special pages generation for Bengal SSG.  Handles generation of special pages that don't come from markdown content: - 404 error page - search page (future) - other static utility pages"
---

# postprocess.special_pages

Special pages generation for Bengal SSG.

Handles generation of special pages that don't come from markdown content:
- 404 error page
- search page (future)
- other static utility pages

---

## Classes

### `SpecialPagesGenerator`


Generates special pages like 404, search, etc.

These pages use templates from the theme but don't have corresponding
markdown source files. They need to be rendered during the build process
to ensure they have proper styling and navigation.

Currently generates:
- 404.html: Custom 404 error page with site styling

Future:
- search.html: Client-side search page
- sitemap.html: Human-readable sitemap




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site') -> None
```

Initialize special pages generator.



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
  - `'Site'`
  - -
  - Site instance with configuration and template engine
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

Generate all special pages that are enabled.

Currently generates:
- 404 page if 404.html template exists in theme
- search page if enabled and template exists (and no user content overrides)
Failures are logged but don't stop the build process.



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




---


