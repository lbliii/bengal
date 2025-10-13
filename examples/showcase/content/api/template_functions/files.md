
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

Note: site parameter kept for signature compatibility but site is now
accessed via env.site (stored by template_engine.py).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`)
- **`site`** (`'Site'`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `read_file`
```python
def read_file(env: 'Environment', path: str) -> str
```

Read file contents.

Uses bengal.utils.file_io.read_text_file internally for robust file reading
with UTF-8/latin-1 encoding fallback and comprehensive error handling.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`path`** (`str`) - Relative path to file

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
def file_exists(env: 'Environment', path: str) -> bool
```

Check if file exists.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`path`** (`str`) - Relative path to file

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
def file_size(env: 'Environment', path: str) -> str
```

Get human-readable file size.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`path`** (`str`) - Relative path to file

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
