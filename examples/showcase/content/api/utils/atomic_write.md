---
title: "utils.atomic_write"
layout: api-reference
type: python-module
source_file: "../../bengal/utils/atomic_write.py"
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

**Source:** `../../bengal/utils/atomic_write.py`

---

## Classes

### AtomicFile


Context manager for atomic file writing.

Useful when you need to write incrementally or use file handle directly
(e.g., with json.dump(), ElementTree.write(), etc.).

The file is written to a temporary location, then atomically renamed
on successful completion. If an exception occurs, the temp file is
cleaned up and the original file remains unchanged.




**Methods:**

#### __init__

```python
def __init__(self, path: Union[Path, str], mode: str = 'w', encoding: Optional[str] = 'utf-8', **kwargs)
```

Initialize atomic file writer.

**Parameters:**

- **self**
- **path** (`Union[Path, str]`) - Destination file path
- **mode** (`str`) = `'w'` - File open mode ('w', 'wb', 'a', etc.)
- **encoding** (`Optional[str]`) = `'utf-8'` - Text encoding (default: utf-8, ignored for binary modes) **kwargs: Additional arguments passed to open()







---
#### __enter__

```python
def __enter__(self)
```

Open temp file for writing.

**Parameters:**

- **self**







---
#### __exit__

```python
def __exit__(self, exc_type, exc_val, exc_tb)
```

Close temp file and rename atomically if successful.

**Parameters:**

- **self**
- **exc_type**
- **exc_val**
- **exc_tb**







---


## Functions

### atomic_write_text

```python
def atomic_write_text(path: Union[Path, str], content: str, encoding: str = 'utf-8', mode: Optional[int] = None) -> None
```

Write text to a file atomically.

Uses write-to-temp-then-rename to ensure the file is never partially written.
If the process crashes during write, the original file (if any) remains intact.

The rename operation is atomic on POSIX systems (Linux, macOS), meaning it
either completely succeeds or completely fails - there's no partial state.

**Parameters:**

- **path** (`Union[Path, str]`) - Destination file path
- **content** (`str`) - Text content to write
- **encoding** (`str`) = `'utf-8'` - Text encoding (default: utf-8)
- **mode** (`Optional[int]`) = `None` - File permissions (default: None, keeps system default)

**Returns:** `None`

**Raises:**

- **OSError**: If write or rename fails

**Examples:**

>>> atomic_write_text('output.html', '<html>...</html>')
    >>> atomic_write_text('data.json', json.dumps(data), encoding='utf-8')




---
### atomic_write_bytes

```python
def atomic_write_bytes(path: Union[Path, str], content: bytes, mode: Optional[int] = None) -> None
```

Write binary data to a file atomically.

**Parameters:**

- **path** (`Union[Path, str]`) - Destination file path
- **content** (`bytes`) - Binary content to write
- **mode** (`Optional[int]`) = `None` - File permissions (default: None, keeps system default)

**Returns:** `None`

**Raises:**

- **OSError**: If write or rename fails

**Examples:**

>>> atomic_write_bytes('image.png', image_data)




---
