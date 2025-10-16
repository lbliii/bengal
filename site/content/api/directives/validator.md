
---
title: "directives.validator"
type: python-module
source_file: "bengal/rendering/plugins/directives/validator.py"
css_class: api-content
description: "Pre-parse validation for directives.  Validates directive syntax before parsing to catch errors early with helpful messages."
---

# directives.validator

Pre-parse validation for directives.

Validates directive syntax before parsing to catch errors early with
helpful messages.

---

## Classes

### `DirectiveSyntaxValidator`


Validates directive syntax before parsing.

Catches common errors early with helpful messages before expensive
parsing and recursive markdown processing.




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate_tabs_directive` @staticmethod
```python
def validate_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```

Validate tabs directive content.



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
* - `content`
  - `str`
  - -
  - Directive content (between opening and closing backticks)
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path for error messages
* - `line_number`
  - `int | None`
  - `None`
  - Optional line number for error messages
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]` - List of validation error messages (empty if valid)




---
#### `validate_code_tabs_directive` @staticmethod
```python
def validate_code_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```

Validate code-tabs directive content.



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
* - `content`
  - `str`
  - -
  - Directive content
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path
* - `line_number`
  - `int | None`
  - `None`
  - Optional line number
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]` - List of validation errors




---
#### `validate_dropdown_directive` @staticmethod
```python
def validate_dropdown_directive(content: str, title: str = '', file_path: Path | None = None, line_number: int | None = None) -> list[str]
```

Validate dropdown directive content.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `content`
  - `str`
  - -
  - Directive content
* - `title`
  - `str`
  - `''`
  - Directive title
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path
* - `line_number`
  - `int | None`
  - `None`
  - Optional line number
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]` - List of validation errors




---
#### `validate_admonition_directive` @staticmethod
```python
def validate_admonition_directive(admon_type: str, content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```

Validate admonition directive content.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `admon_type`
  - `str`
  - -
  - Type of admonition (note, tip, warning, etc.)
* - `content`
  - `str`
  - -
  - Directive content
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path
* - `line_number`
  - `int | None`
  - `None`
  - Optional line number
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]` - List of validation errors




---
#### `validate_directive` @classmethod
```python
def validate_directive(cls, directive_type: str, content: str, title: str = '', options: dict[str, Any] | None = None, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```

Validate any directive type.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 7 parameters (click to expand)
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
* - `directive_type`
  - `str`
  - -
  - Type of directive (tabs, note, dropdown, etc.)
* - `content`
  - `str`
  - -
  - Directive content
* - `title`
  - `str`
  - `''`
  - Directive title (if any)
* - `options`
  - `dict[str, Any] | None`
  - `None`
  - Directive options dictionary
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path
* - `line_number`
  - `int | None`
  - `None`
  - Optional line number
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str]` - List of validation errors (empty if valid)




---
#### `validate_directive_block` @classmethod
```python
def validate_directive_block(cls, directive_block: str, file_path: Path | None = None, start_line: int | None = None) -> dict[str, Any]
```

Validate a complete directive block from markdown.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `directive_block`
  - `str`
  - -
  - Full directive block including opening/closing backticks
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path
* - `start_line`
  - `int | None`
  - `None`
  - Optional starting line number
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Dictionary with validation results:
    {
        'valid': bool,
        'errors': List[str],
        'directive_type': str,
        'content': str,
        'title': str,
        'options': Dict[str, Any]
    }




---


## Functions

### `validate_markdown_directives`
```python
def validate_markdown_directives(markdown_content: str, file_path: Path | None = None) -> list[dict[str, Any]]
```

Validate all directive blocks in a markdown file.



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
* - `markdown_content`
  - `str`
  - -
  - Full markdown content
* - `file_path`
  - `Path | None`
  - `None`
  - Optional file path for error reporting
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`list[dict[str, Any]]` - List of validation results, one per directive block




---
### `get_directive_validation_summary`
```python
def get_directive_validation_summary(validation_results: list[dict[str, Any]]) -> dict[str, Any]
```

Get a summary of directive validation results.



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
* - `validation_results`
  - `list[dict[str, Any]]`
  - -
  - List of validation result dictionaries
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Summary dictionary with counts and error lists




---
