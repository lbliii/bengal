
---
title: "page.operations"
type: python-module
source_file: "bengal/core/page/operations.py"
css_class: api-content
description: "Page Operations Mixin - Operations and transformations on pages."
---

# page.operations

Page Operations Mixin - Operations and transformations on pages.

---

## Classes

### `PageOperationsMixin`


Mixin providing operations for pages.

This mixin handles:
- Rendering with templates
- Link validation and extraction
- Template application




:::{rubric} Methods
:class: rubric-methods
:::
#### `render`
```python
def render(self, template_engine: Any) -> str
```

Render the page using the provided template engine.



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
* - `template_engine`
  - `Any`
  - -
  - Template engine instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Rendered HTML content




---
#### `validate_links`
```python
def validate_links(self) -> list[str]
```

Validate all links in the page.



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

`list[str]` - List of broken link URLs




---
#### `apply_template`
```python
def apply_template(self, template_name: str, context: dict[str, Any] | None = None) -> str
```

Apply a specific template to this page.



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
* - `template_name`
  - `str`
  - -
  - Name of the template to apply
* - `context`
  - `dict[str, Any] | None`
  - `None`
  - Additional context variables
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Rendered content with template applied




---
#### `extract_links`
```python
def extract_links(self) -> list[str]
```

Extract all links from the page content.



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

`list[str]` - List of link URLs found in the page




---


