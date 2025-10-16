
---
title: "rendering.errors"
type: python-module
source_file: "bengal/rendering/errors.py"
css_class: api-content
description: "Rich template error objects with line numbers, context, and suggestions."
---

# rendering.errors

Rich template error objects with line numbers, context, and suggestions.

---

## Classes

### `TemplateErrorContext`


Context around an error in a template.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 6 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `template_name`
  - `str`
  - -
* - `line_number`
  - `int | None`
  - -
* - `column`
  - `int | None`
  - -
* - `source_line`
  - `str | None`
  - -
* - `surrounding_lines`
  - `list[tuple[int, str]]`
  - -
* - `template_path`
  - `Path | None`
  - -
:::

::::



### `InclusionChain`


Represents the template inclusion chain.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 1 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `entries`
  - `list[tuple[str, int | None]]`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `__str__`
```python
def __str__(self) -> str
```

Format as readable chain.



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

`str`




---

### `TemplateRenderError`


Rich template error with all debugging information.

This replaces the simple string error messages with structured data
that can be displayed beautifully and used for IDE integration.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 7 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `error_type`
  - `str`
  - -
* - `message`
  - `str`
  - -
* - `template_context`
  - `TemplateErrorContext`
  - -
* - `inclusion_chain`
  - `InclusionChain | None`
  - -
* - `page_source`
  - `Path | None`
  - -
* - `suggestion`
  - `str | None`
  - -
* - `available_alternatives`
  - `list[str]`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `from_jinja2_error` @classmethod
```python
def from_jinja2_error(cls, error: Exception, template_name: str, page_source: Path | None, template_engine: Any) -> 'TemplateRenderError'
```

Extract rich error information from Jinja2 exception.



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
* - `cls`
  - -
  - -
  - -
* - `error`
  - `Exception`
  - -
  - Jinja2 exception
* - `template_name`
  - `str`
  - -
  - Template being rendered
* - `page_source`
  - `Path | None`
  - -
  - Source content file (if applicable)
* - `template_engine`
  - `Any`
  - -
  - Template engine instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'TemplateRenderError'` - Rich error object




---


## Functions

### `display_template_error`
```python
def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None
```

Display a rich template error in the terminal.



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
* - `error`
  - `TemplateRenderError`
  - -
  - Rich error object
* - `use_color`
  - `bool`
  - `True`
  - Whether to use terminal colors
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
