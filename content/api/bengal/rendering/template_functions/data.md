
---
title: "data"
type: "python-module"
source_file: "bengal/bengal/rendering/template_functions/data.py"
line_number: 1
description: "Data manipulation functions for templates. Provides 8 functions for working with JSON, YAML, and nested data structures."
---

# data
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/template_functions/data.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[template_functions](/api/bengal/rendering/template_functions/) ›data

Data manipulation functions for templates.

Provides 8 functions for working with JSON, YAML, and nested data structures.

## Functions



### `register`


```python
def register(env: Environment, site: Site) -> None
```



Register data manipulation functions with Jinja2 environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `env` | `Environment` | - | *No description provided.* |
| `site` | `Site` | - | *No description provided.* |







**Returns**


`None`




### `get_data`


```python
def get_data(path: str, root_path: Any) -> Any
```



Load data from JSON or YAML file.

Uses bengal.utils.file_io.load_data_file internally for robust file loading
with error handling and logging.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `path` | `str` | - | Relative path to data file |
| `root_path` | `Any` | - | Site root path |







**Returns**


`Any` - Parsed data (dict, list, or primitive)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set authors = get_data('data/authors.json') %}
    {% for author in authors %}
        {{ author.name }}
    {% endfor %}
```





### `jsonify`


```python
def jsonify(data: Any, indent: int | None = None) -> str
```



Convert data to JSON string.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `Any` | - | Data to convert (dict, list, etc.) |
| `indent` | `int \| None` | - | Indentation level (default: None for compact) |







**Returns**


`str` - JSON string
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ data | jsonify }}
    {{ data | jsonify(2) }}  # Pretty-printed
```





### `merge`


```python
def merge(dict1: dict[str, Any], dict2: dict[str, Any], deep: bool = True) -> dict[str, Any]
```



Merge two dictionaries.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `dict1` | `dict[str, Any]` | - | First dictionary |
| `dict2` | `dict[str, Any]` | - | Second dictionary (takes precedence) |
| `deep` | `bool` | `True` | Perform deep merge (default: True) |







**Returns**


`dict[str, Any]` - Merged dictionary
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set config = defaults | merge(custom_config) %}
```





### `has_key`


```python
def has_key(data: dict[str, Any], key: str) -> bool
```



Check if dictionary has a key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary to check |
| `key` | `str` | - | Key to look for |







**Returns**


`bool` - True if key exists
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% if data | has_key('author') %}
        {{ data.author }}
    {% endif %}
```





### `get_nested`


```python
def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any
```



Access nested data using dot notation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary with nested data |
| `path` | `str` | - | Dot-separated path (e.g., "user.profile.name") |
| `default` | `Any` | - | Default value if path not found |







**Returns**


`Any` - Value at path or default
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ data | get_nested('user.profile.name') }}
    {{ data | get_nested('user.email', 'no-email') }}
```





### `keys_filter`


```python
def keys_filter(data: dict[str, Any]) -> list[str]
```



Get dictionary keys as list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary or DotDict |







**Returns**


`list[str]` - List of keys
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for key in data | keys %}
        {{ key }}
    {% endfor %}
```





### `values_filter`


```python
def values_filter(data: dict[str, Any]) -> list[Any]
```



Get dictionary values as list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary or DotDict |







**Returns**


`list[Any]` - List of values
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for value in data | values %}
        {{ value }}
    {% endfor %}
```





### `items_filter`


```python
def items_filter(data: dict[str, Any]) -> list[tuple]
```



Get dictionary items as list of (key, value) tuples.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary or DotDict |







**Returns**


`list[tuple]` - List of (key, value) tuples
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for key, value in data | items %}
        {{ key }}: {{ value }}
    {% endfor %}
```



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/template_functions/data.py`*
