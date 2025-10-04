---
title: "autodoc.config"
layout: api-reference
type: python-module
source_file: "../../bengal/autodoc/config.py"
---

# autodoc.config

Configuration loader for autodoc.

Loads autodoc settings from bengal.toml or provides sensible defaults.

**Source:** `../../bengal/autodoc/config.py`

---


## Functions

### load_autodoc_config

```python
def load_autodoc_config(config_path: Optional[Path] = None) -> Dict[str, Any]
```

Load autodoc configuration from bengal.toml.

**Parameters:**

- **config_path** (`Optional[Path]`) = `None` - Path to config file (default: ./bengal.toml)

**Returns:** `Dict[str, Any]` - Autodoc configuration dict with defaults





---
### get_python_config

```python
def get_python_config(config: Dict[str, Any]) -> Dict[str, Any]
```

Get Python autodoc configuration.

**Parameters:**

- **config** (`Dict[str, Any]`)

**Returns:** `Dict[str, Any]`





---
### get_openapi_config

```python
def get_openapi_config(config: Dict[str, Any]) -> Dict[str, Any]
```

Get OpenAPI autodoc configuration.

**Parameters:**

- **config** (`Dict[str, Any]`)

**Returns:** `Dict[str, Any]`





---
### get_cli_config

```python
def get_cli_config(config: Dict[str, Any]) -> Dict[str, Any]
```

Get CLI autodoc configuration.

**Parameters:**

- **config** (`Dict[str, Any]`)

**Returns:** `Dict[str, Any]`





---
