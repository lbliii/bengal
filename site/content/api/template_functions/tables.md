
---
title: "template_functions.tables"
type: python-module
source_file: "bengal/rendering/template_functions/tables.py"
css_class: api-content
description: "Table functions for templates.  Provides functions for rendering interactive data tables from YAML/CSV files."
---

# template_functions.tables

Table functions for templates.

Provides functions for rendering interactive data tables from YAML/CSV files.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register table functions with Jinja2 environment.



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
  - Jinja2 environment
* - `site`
  - `'Site'`
  - -
  - Site instance
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `data_table`
```python
def data_table(env: 'Environment', path: str, **options: Any) -> Markup
```

Render interactive data table from YAML or CSV file.

Uses the same underlying implementation as the data-table directive,
but can be called directly from templates for more flexibility.



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
  - Jinja2 environment (injected)
* - `path`
  - `str`
  - -
  - Relative path to data file (YAML or CSV) **options: Table options - search (bool): Enable search box (default: True) - filter (bool): Enable column filters (default: True) - sort (bool): Enable column sorting (default: True) - pagination (int|False): Rows per page, or False to disable (default: 50) - height (str): Table height like "400px" (default: "auto") - columns (str): Comma-separated list of columns to show (default: all)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Markup` - Markup object with rendered HTML table




:::{rubric} Examples
:class: rubric-examples
:::
```python
{# Basic usage #}
```


---
