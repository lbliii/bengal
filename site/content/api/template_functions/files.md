
---
title: "template_functions.files"
type: python-module
source_file: "bengal/rendering/template_functions/files.py"
css_class: api-content
description: "File system functions for templates.  Provides 3 functions for reading files and checking file existence."
---

# template_functions.files

File system functions for templates.

Provides 3 functions for reading files and checking file existence.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register file system functions with Jinja2 environment.



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
  - -
* - `site`
  - `'Site'`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `read_file`
```python
def read_file(path: str, root_path: Path) -> str
```

Read file contents.

Uses bengal.utils.file_io.read_text_file internally for robust file reading
with UTF-8/latin-1 encoding fallback and comprehensive error handling.



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
* - `path`
  - `str`
  - -
  - Relative path to file
* - `root_path`
  - `Path`
  - -
  - Site root path
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - File contents as string




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set license = read_file('LICENSE') %}
```


---
### `file_exists`
```python
def file_exists(path: str, root_path: Path) -> bool
```

Check if file exists.



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
* - `path`
  - `str`
  - -
  - Relative path to file
* - `root_path`
  - `Path`
  - -
  - Site root path
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if file exists




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if file_exists('custom.css') %}
```


---
### `file_size`
```python
def file_size(path: str, root_path: Path) -> str
```

Get human-readable file size.



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
* - `path`
  - `str`
  - -
  - Relative path to file
* - `root_path`
  - `Path`
  - -
  - Site root path
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - File size as human-readable string (e.g., "1.5 MB")




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ file_size('downloads/manual.pdf') }}  # "2.3 MB"
```


---
