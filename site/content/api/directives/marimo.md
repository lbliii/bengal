
---
title: "directives.marimo"
type: python-module
source_file: "bengal/rendering/plugins/directives/marimo.py"
css_class: api-content
description: "Marimo directive for Mistune.  Provides executable Python code blocks with output rendering using Marimo's reactive notebook system."
---

# directives.marimo

Marimo directive for Mistune.

Provides executable Python code blocks with output rendering using Marimo's
reactive notebook system.

---

## Classes

### `MarimoCellDirective`

**Inherits from:** `DirectivePlugin`
Marimo cell directive for executable Python code blocks.

Syntax:
    ```{marimo}
    import pandas as pd
    pd.DataFrame({"x": [1, 2, 3]})
    ```

Options:
    :show-code: true/false - Display source code (default: true)
    :cache: true/false - Cache execution results (default: true)
    :label: str - Cell identifier for caching and cross-references

Features:
- Execute Python code at build time
- Render outputs (text, tables, plots, etc.)
- Cache results for fast rebuilds
- Show/hide source code
- Graceful error handling




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

Initialize Marimo directive.



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




---
#### `parse`
```python
def parse(self, block: Any, m: Any, state: Any) -> dict[str, Any]
```

Parse Marimo cell directive.



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
  - `Any`
  - -
  - Regex match
* - `state`
  - `Any`
  - -
  - Parser state
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Token dict with type and attributes




---
#### `__call__`
```python
def __call__(self, directive: Any, md: Any) -> Any
```

Register directive with Mistune.



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
  - FencedDirective instance
* - `md`
  - `Any`
  - -
  - Mistune Markdown instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any` - Result of directive registration




---


## Functions

### `render_marimo_cell`
```python
def render_marimo_cell(renderer: Any, html: str, cell_id: int, label: str = '') -> str
```

Render Marimo cell HTML output.



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
* - `renderer`
  - `Any`
  - -
  - Mistune HTML renderer
* - `html`
  - `str`
  - -
  - Cell HTML content
* - `cell_id`
  - `int`
  - -
  - Numeric cell identifier
* - `label`
  - `str`
  - `''`
  - Optional cell label
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Wrapped HTML with cell container




---
