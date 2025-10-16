
---
title: "utils.atomic_write"
type: python-module
source_file: "bengal/utils/atomic_write.py"
css_class: api-content
description: "Atomic file writing utilities.  Provides crash-safe file writes using the write-to-temp-then-rename pattern. This ensures files are never left in a partially written state.  If a process crashes du..."
---

# utils.atomic_write

Atomic file writing utilities.

Provides crash-safe file writes using the write-to-temp-then-rename pattern.
This ensures files are never left in a partially written state.

If a process crashes during write, the original file (if any) remains intact.
Files are always either in their old complete state or new complete state,
never partially written.

Example:
    >>> from bengal.utils.atomic_write import atomic_write_text
    >>> atomic_write_text('output.html', '<html>...</html>')
    # If crash occurs during write:
    # - output.html is either old version (if existed) or missing
    # - Never partially written!

---

## Classes

### `AtomicFile`


Context manager for atomic file writing.

Useful when you need to write incrementally or use file handle directly
(e.g., with json.dump(), ElementTree.write(), etc.).

The file is written to a temporary location, then atomically renamed
on successful completion. If an exception occurs, the temp file is
cleaned up and the original file remains unchanged.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, path: Path | str, mode: str = 'w', encoding: str | None = 'utf-8', **kwargs)
```

Initialize atomic file writer.



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
* - `path`
  - `Path | str`
  - -
  - Destination file path
* - `mode`
  - `str`
  - `'w'`
  - File open mode ('w', 'wb', 'a', etc.)
* - `encoding`
  - `str | None`
  - `'utf-8'`
  - Text encoding (default: utf-8, ignored for binary modes) **kwargs: Additional arguments passed to open()
:::

::::




---
#### `__enter__`
```python
def __enter__(self)
```

Open temp file for writing.



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
#### `__exit__`
```python
def __exit__(self, exc_type, *args)
```

Close temp file and rename atomically if successful.



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
* - `exc_type`
  - -
  - -
  - -
:::

::::




---


## Functions

### `atomic_write_text`
```python
def atomic_write_text(path: Path | str, content: str, encoding: str = 'utf-8', mode: int | None = None) -> None
```

Write text to a file atomically.

Uses write-to-temp-then-rename to ensure the file is never partially written.
If the process crashes during write, the original file (if any) remains intact.

The rename operation is atomic on POSIX systems (Linux, macOS), meaning it
either completely succeeds or completely fails - there's no partial state.



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
* - `path`
  - `Path | str`
  - -
  - Destination file path
* - `content`
  - `str`
  - -
  - Text content to write
* - `encoding`
  - `str`
  - `'utf-8'`
  - Text encoding (default: utf-8)
* - `mode`
  - `int | None`
  - `None`
  - File permissions (default: None, keeps system default)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`OSError`**: If write or rename fails



:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> atomic_write_text('output.html', '<html>...</html>')
    >>> atomic_write_text('data.json', json.dumps(data), encoding='utf-8')
```


---
### `atomic_write_bytes`
```python
def atomic_write_bytes(path: Path | str, content: bytes, mode: int | None = None) -> None
```

Write binary data to a file atomically.



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
* - `path`
  - `Path | str`
  - -
  - Destination file path
* - `content`
  - `bytes`
  - -
  - Binary content to write
* - `mode`
  - `int | None`
  - `None`
  - File permissions (default: None, keeps system default)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`OSError`**: If write or rename fails



:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> atomic_write_bytes('image.png', image_data)
```


---
