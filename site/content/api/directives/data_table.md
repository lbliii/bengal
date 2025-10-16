
---
title: "directives.data_table"
type: python-module
source_file: "bengal/rendering/plugins/directives/data_table.py"
css_class: api-content
description: "Data table directive for Bengal SSG.  Provides interactive tables for hardware/software support matrices and other complex tabular data with filtering, sorting, and searching capabilities."
---

# directives.data_table

Data table directive for Bengal SSG.

Provides interactive tables for hardware/software support matrices and other
complex tabular data with filtering, sorting, and searching capabilities.

---

## Classes

### `DataTableDirective`

**Inherits from:** `DirectivePlugin`
Data table directive using Mistune's fenced syntax.

Syntax:
    ```{data-table} path/to/data.yaml
    :search: true
    :filter: true
    :sort: true
    :pagination: 50
    :height: 400px
    :columns: col1,col2,col3
    ```

Supports:
- YAML files (with metadata and column definitions)
- CSV files (auto-detect headers)
- Interactive filtering, sorting, searching
- Responsive design
- Keyboard navigation




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse data-table directive.



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

`dict[str, Any]` - Token dict with type 'data_table'




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

### `render_data_table`
```python
def render_data_table(renderer: Any, text: str, **attrs: Any) -> str
```

Render data table to HTML.



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
  - Rendered children content (unused for data tables) **attrs: Table attributes from directive
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for data table




---
