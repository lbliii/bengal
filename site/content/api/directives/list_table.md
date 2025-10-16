
---
title: "directives.list_table"
type: python-module
source_file: "bengal/rendering/plugins/directives/list_table.py"
css_class: api-content
description: "List table directive for Bengal SSG.  Provides MyST-style list-table directive for creating tables from nested lists, avoiding the pipe character collision issue in type annotations."
---

# directives.list_table

List table directive for Bengal SSG.

Provides MyST-style list-table directive for creating tables from nested lists,
avoiding the pipe character collision issue in type annotations.

---

## Classes

### `ListTableDirective`

**Inherits from:** `DirectivePlugin`
List table directive using MyST syntax.

Syntax:
    :::{list-table}
    :header-rows: 1
    :widths: 20 30 50

    * - Header 1
      - Header 2
      - Header 3
    * - Row 1, Col 1
      - Row 1, Col 2
      - Row 1, Col 3
    * - Row 2, Col 1
      - Row 2, Col 2
      - Row 2, Col 3
    :::

Supports:
- :header-rows: number - Number of header rows (default: 0)
- :widths: space-separated percentages - Column widths
- :class: CSS class for the table




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse list-table directive.



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
* - `self`
  - -
  - -
  - -
* - `block`
  - `Any`
  - -
  - Block parser
* - `m`
  - `Match`
  - -
  - Regex match object
* - `state`
  - `Any`
  - -
  - Parser state
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Token dict with type 'list_table'




---
#### `__call__`
```python
def __call__(self, directive: Any, md: Any) -> Any
```

Register the directive and renderer.



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
* - `directive`
  - `Any`
  - -
  - -
* - `md`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any`




---


## Functions

### `render_list_table`
```python
def render_list_table(renderer: Any, text: str, **attrs: Any) -> str
```

Render list table to HTML.



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
* - `renderer`
  - `Any`
  - -
  - Mistune renderer
* - `text`
  - `str`
  - -
  - Rendered children content (unused for list tables) **attrs: Table attributes from directive
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for list table




---
