---
title: "config.loader"
layout: api-reference
type: python-module
source_file: "../../bengal/config/loader.py"
---

# config.loader

Configuration loader supporting TOML and YAML formats.

**Source:** `../../bengal/config/loader.py`

---

## Classes

### ConfigLoader


Loads site configuration from bengal.toml or bengal.yaml.




**Methods:**

#### __init__

```python
def __init__(self, root_path: Path) -> None
```

Initialize the config loader.

**Parameters:**

- **self**
- **root_path** (`Path`) - Root directory to look for config files

**Returns:** `None`






---
#### load

```python
def load(self, config_path: Optional[Path] = None) -> Dict[str, Any]
```

Load configuration from file.

**Parameters:**

- **self**
- **config_path** (`Optional[Path]`) = `None` - Optional explicit path to config file

**Returns:** `Dict[str, Any]` - Configuration dictionary






---
#### get_warnings

```python
def get_warnings(self) -> List[str]
```

Get configuration warnings (aliases used, unknown sections, etc).

**Parameters:**

- **self**

**Returns:** `List[str]`






---
#### print_warnings

```python
def print_warnings(self, verbose: bool = False) -> None
```

Print configuration warnings if verbose mode is enabled.

**Parameters:**

- **self**
- **verbose** (`bool`) = `False`

**Returns:** `None`






---


