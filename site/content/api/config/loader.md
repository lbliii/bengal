
---
title: "config.loader"
type: python-module
source_file: "bengal/config/loader.py"
css_class: api-content
description: "Configuration loader supporting TOML and YAML formats."
---

# config.loader

Configuration loader supporting TOML and YAML formats.

---

## Classes

### `ConfigLoader`


Loads site configuration from bengal.toml or bengal.yaml.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, root_path: Path) -> None
```

Initialize the config loader.



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
* - `root_path`
  - `Path`
  - -
  - Root directory to look for config files
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `load`
```python
def load(self, config_path: Path | None = None) -> dict[str, Any]
```

Load configuration from file.



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
* - `config_path`
  - `Path | None`
  - `None`
  - Optional explicit path to config file
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Configuration dictionary




---
#### `get_warnings`
```python
def get_warnings(self) -> list[str]
```

Get configuration warnings (aliases used, unknown sections, etc).



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

`list[str]`




---
#### `print_warnings`
```python
def print_warnings(self, verbose: bool = False) -> None
```

Print configuration warnings if verbose mode is enabled.



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
* - `verbose`
  - `bool`
  - `False`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


## Functions

### `pretty_print_config`
```python
def pretty_print_config(config: dict[str, Any], title: str = 'Configuration') -> None
```

Pretty print configuration using Rich (if available) or fallback to pprint.



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
* - `config`
  - `dict[str, Any]`
  - -
  - Configuration dictionary to display
* - `title`
  - `str`
  - `'Configuration'`
  - Title for the output
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
