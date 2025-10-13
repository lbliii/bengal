
---
title: "utils.cli_output"
type: python-module
source_file: "bengal/utils/cli_output.py"
css_class: api-content
description: "Centralized CLI output system for Bengal.  Provides a unified interface for all CLI messaging with: - Profile-aware formatting (Writer, Theme-Dev, Developer) - Consistent indentation and spacing - ..."
---

# utils.cli_output

Centralized CLI output system for Bengal.

Provides a unified interface for all CLI messaging with:
- Profile-aware formatting (Writer, Theme-Dev, Developer)
- Consistent indentation and spacing
- Automatic TTY detection
- Rich/fallback rendering

---

## Classes

### `MessageLevel`

**Inherits from:** `Enum`
Message importance levels.





### `OutputStyle`

**Inherits from:** `Enum`
Visual styles for messages.





### `CLIOutput`


Centralized CLI output manager.

Handles all terminal output with profile-aware formatting,
consistent spacing, and automatic TTY detection.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, profile: Any | None = None, quiet: bool = False, verbose: bool = False, use_rich: bool | None = None)
```

Initialize CLI output manager.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `profile` | `Any | None` | `None` | Build profile (Writer, Theme-Dev, Developer) |
| `quiet` | `bool` | `False` | Suppress non-critical output |
| `verbose` | `bool` | `False` | Show detailed output |
| `use_rich` | `bool | None` | `None` | Force rich/plain output (None = auto-detect) |





---
#### `should_show`
```python
def should_show(self, level: MessageLevel) -> bool
```

Determine if message should be shown based on level and settings.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`level`** (`MessageLevel`)

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---
#### `header`
```python
def header(self, text: str, mascot: bool = True) -> None
```

Print a header message.

Example: "ᓚᘏᗢ  Building your site..."



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`mascot`** (`bool`) = `True`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `phase`
```python
def phase(self, name: str, status: str = 'Done', duration_ms: float | None = None, details: str | None = None, icon: str = '✓') -> None
```

Print a phase status line.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `name` | `str` | - | - |
| `status` | `str` | `'Done'` | - |
| `duration_ms` | `float | None` | `None` | - |
| `details` | `str | None` | `None` | - |
| `icon` | `str` | `'✓'` | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
✓ Discovery     Done
```


---
#### `detail`
```python
def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None
```

Print a detail/sub-item.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`indent`** (`int`) = `1`
- **`icon`** (`str | None`) = `None`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
├─ RSS feed ✓
```


---
#### `success`
```python
def success(self, text: str, icon: str = '✨') -> None
```

Print a success message.

Example: "✨ Built 245 pages in 0.8s"



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`icon`** (`str`) = `'✨'`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `info`
```python
def info(self, text: str, icon: str | None = None) -> None
```

Print an info message.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`icon`** (`str | None`) = `None`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `warning`
```python
def warning(self, text: str, icon: str = '⚠️') -> None
```

Print a warning message.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`icon`** (`str`) = `'⚠️'`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `error`
```python
def error(self, text: str, icon: str = '❌') -> None
```

Print an error message.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`text`** (`str`)
- **`icon`** (`str`) = `'❌'`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `path`
```python
def path(self, path: str, icon: str = '📂', label: str = 'Output') -> None
```

Print a path.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`path`** (`str`)
- **`icon`** (`str`) = `'📂'`
- **`label`** (`str`) = `'Output'`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
📂 Output:
```


---
#### `metric`
```python
def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None
```

Print a metric.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `label` | `str` | - | - |
| `value` | `Any` | - | - |
| `unit` | `str | None` | `None` | - |
| `indent` | `int` | `0` | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
⏱️  Performance:
```


---
#### `table`
```python
def table(self, data: list[dict[str, str]], headers: list[str]) -> None
```

Print a table (rich only, falls back to simple list).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`data`** (`list[dict[str, str]]`)
- **`headers`** (`list[str]`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `blank`
```python
def blank(self, count: int = 1) -> None
```

Print blank lines.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`count`** (`int`) = `1`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---


## Functions

### `get_cli_output`
```python
def get_cli_output() -> CLIOutput
```

Get the global CLI output instance.



:::{rubric} Returns
:class: rubric-returns
:::
`CLIOutput`




---
### `init_cli_output`
```python
def init_cli_output(profile: Any | None = None, quiet: bool = False, verbose: bool = False) -> CLIOutput
```

Initialize the global CLI output instance with settings.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`profile`** (`Any | None`) = `None`
- **`quiet`** (`bool`) = `False`
- **`verbose`** (`bool`) = `False`

:::{rubric} Returns
:class: rubric-returns
:::
`CLIOutput`




---
