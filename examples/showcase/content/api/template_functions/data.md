
---
title: "template_functions.data"
type: python-module
source_file: "bengal/rendering/template_functions/data.py"
css_class: api-content
description: "Data manipulation functions for templates.  Provides 8 functions for working with JSON, YAML, and nested data structures."
---

# template_functions.data

Data manipulation functions for templates.

Provides 8 functions for working with JSON, YAML, and nested data structures.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register data manipulation functions with Jinja2 environment.

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
### `get_data`
```python
def get_data(env: 'Environment', path: str) -> Any
```

Load data from JSON or YAML file.

Uses bengal.utils.file_io.load_data_file internally for robust file loading
with error handling and logging.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`) - Jinja2 environment (injected by @pass_environment)
- **`path`** (`str`) - Relative path to data file

:::{rubric} Returns
:class: rubric-returns
:::
`Any` - Parsed data (dict, list, or primitive)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set authors = get_data('data/authors.json') %}
```


---
### `jsonify`
```python
def jsonify(data: Any, indent: int | None = None) -> str
```

Convert data to JSON string.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`Any`) - Data to convert (dict, list, etc.)
- **`indent`** (`int | None`) = `None` - Indentation level (default: None for compact)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - JSON string




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ data | jsonify }}
```


---
### `merge`
```python
def merge(dict1: dict[str, Any], dict2: dict[str, Any], deep: bool = True) -> dict[str, Any]
```

Merge two dictionaries.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`dict1`** (`dict[str, Any]`) - First dictionary
- **`dict2`** (`dict[str, Any]`) - Second dictionary (takes precedence)
- **`deep`** (`bool`) = `True` - Perform deep merge (default: True)

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Merged dictionary




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set config = defaults | merge(custom_config) %}
```


---
### `has_key`
```python
def has_key(data: dict[str, Any], key: str) -> bool
```

Check if dictionary has a key.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`dict[str, Any]`) - Dictionary to check
- **`key`** (`str`) - Key to look for

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if key exists




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% if data | has_key('author') %}
```


---
### `get_nested`
```python
def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any
```

Access nested data using dot notation.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`dict[str, Any]`) - Dictionary with nested data
- **`path`** (`str`) - Dot-separated path (e.g., "user.profile.name")
- **`default`** (`Any`) = `None` - Default value if path not found

:::{rubric} Returns
:class: rubric-returns
:::
`Any` - Value at path or default




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ data | get_nested('user.profile.name') }}
```


---
### `keys_filter`
```python
def keys_filter(data: dict[str, Any]) -> list[str]
```

Get dictionary keys as list.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`dict[str, Any]`) - Dictionary

:::{rubric} Returns
:class: rubric-returns
:::
`list[str]` - List of keys




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for key in data | keys %}
```


---
### `values_filter`
```python
def values_filter(data: dict[str, Any]) -> list[Any]
```

Get dictionary values as list.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`dict[str, Any]`) - Dictionary

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - List of values




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for value in data | values %}
```


---
### `items_filter`
```python
def items_filter(data: dict[str, Any]) -> list[tuple]
```

Get dictionary items as list of (key, value) tuples.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`data`** (`dict[str, Any]`) - Dictionary

:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple]` - List of (key, value) tuples




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for key, value in data | items %}
```


---
