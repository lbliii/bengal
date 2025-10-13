
---
title: "autodoc.config"
type: python-module
source_file: "bengal/autodoc/config.py"
css_class: api-content
description: "Configuration loader for autodoc.  Loads autodoc settings from bengal.toml or provides sensible defaults."
---

# autodoc.config

Configuration loader for autodoc.

Loads autodoc settings from bengal.toml or provides sensible defaults.

---


## Functions

### `load_autodoc_config`
```python
def load_autodoc_config(config_path: Path | None = None) -> dict[str, Any]
```

Load autodoc configuration from bengal.toml.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`config_path`** (`Path | None`) = `None` - Path to config file (default: ./bengal.toml)

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Autodoc configuration dict with defaults




---
### `get_python_config`
```python
def get_python_config(config: dict[str, Any]) -> dict[str, Any]
```

Get Python autodoc configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`config`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---
### `get_openapi_config`
```python
def get_openapi_config(config: dict[str, Any]) -> dict[str, Any]
```

Get OpenAPI autodoc configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`config`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---
### `get_cli_config`
```python
def get_cli_config(config: dict[str, Any]) -> dict[str, Any]
```

Get CLI autodoc configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`config`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---
