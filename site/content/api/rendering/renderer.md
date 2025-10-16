
---
title: "rendering.renderer"
type: python-module
source_file: "bengal/rendering/renderer.py"
css_class: api-content
description: "Renderer for converting pages to final HTML output."
---

# rendering.renderer

Renderer for converting pages to final HTML output.

---

## Classes

### `Renderer`


Renders pages using templates.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, template_engine: Any, build_stats: Any = None) -> None
```

Initialize the renderer.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `template_engine`
  - `Any`
  - -
  - Template engine instance
* - `build_stats`
  - `Any`
  - `None`
  - Optional BuildStats object for error collection
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `render_content`
```python
def render_content(self, content: str) -> str
```

Render raw content (already parsed HTML).

Automatically strips the first H1 tag to avoid duplication with
the template-rendered title.



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
* - `content`
  - `str`
  - -
  - Parsed HTML content
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Content with first H1 removed




---
#### `render_page`
```python
def render_page(self, page: Page, content: str | None = None) -> str
```

Render a complete page with template.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `page`
  - `Page`
  - -
  - Page to render
* - `content`
  - `str | None`
  - `None`
  - Optional pre-rendered content (uses page.parsed_ast if not provided)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Fully rendered HTML page




---
