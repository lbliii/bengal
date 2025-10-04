---
title: "template_functions.files"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/files.py"
---

# template_functions.files

File system functions for templates.

Provides 3 functions for reading files and checking file existence.

**Source:** `../../bengal/rendering/template_functions/files.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register file system functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### read_file

```python
def read_file(path: str, root_path: Path) -> str
```

Read file contents.

**Parameters:**

- **path** (`str`) - Relative path to file
- **root_path** (`Path`) - Site root path

**Returns:** `str` - File contents as string


**Examples:**

{% set license = read_file('LICENSE') %}




---
### file_exists

```python
def file_exists(path: str, root_path: Path) -> bool
```

Check if file exists.

**Parameters:**

- **path** (`str`) - Relative path to file
- **root_path** (`Path`) - Site root path

**Returns:** `bool` - True if file exists


**Examples:**

{% if file_exists('custom.css') %}




---
### file_size

```python
def file_size(path: str, root_path: Path) -> str
```

Get human-readable file size.

**Parameters:**

- **path** (`str`) - Relative path to file
- **root_path** (`Path`) - Site root path

**Returns:** `str` - File size as human-readable string (e.g., "1.5 MB")


**Examples:**

{{ file_size('downloads/manual.pdf') }}  # "2.3 MB"




---
