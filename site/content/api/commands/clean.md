
---
title: "commands.clean"
type: python-module
source_file: "bengal/cli/commands/clean.py"
css_class: api-content
description: "Clean commands for removing generated files."
---

# commands.clean

Clean commands for removing generated files.

---


## Functions

### `clean`
```python
def clean(force: bool, cache: bool, clean_all: bool, stale_server: bool, config: str, source: str) -> None
```

🧹 Clean generated files and stale processes.

By default, removes only the output directory (public/).

Options:
  --cache         Also remove build cache
  --all           Remove both output and cache
  --stale-server  Clean up stale 'bengal serve' processes



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 6 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `force`
  - `bool`
  - -
  - -
* - `cache`
  - `bool`
  - -
  - -
* - `clean_all`
  - `bool`
  - -
  - -
* - `stale_server`
  - `bool`
  - -
  - -
* - `config`
  - `str`
  - -
  - -
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal clean                  # Clean output only
```


---
### `cleanup`
```python
def cleanup(force: bool, port: int, source: str) -> None
```

Clean up stale Bengal server processes.



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
* - `force`
  - `bool`
  - -
  - -
* - `port`
  - `int`
  - -
  - -
* - `source`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
