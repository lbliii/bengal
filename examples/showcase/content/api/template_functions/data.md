---
title: "template_functions.data"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/data.py"
---

# template_functions.data

Data manipulation functions for templates.

Provides 8 functions for working with JSON, YAML, and nested data structures.

**Source:** `../../bengal/rendering/template_functions/data.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register data manipulation functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### get_data

```python
def get_data(path: str, root_path: Any) -> Any
```

Load data from JSON or YAML file.

**Parameters:**

- **path** (`str`) - Relative path to data file
- **root_path** (`Any`) - Site root path

**Returns:** `Any` - Parsed data (dict, list, or primitive)


**Examples:**

{% set authors = get_data('data/authors.json') %}




---
### jsonify

```python
def jsonify(data: Any, indent: Optional[int] = None) -> str
```

Convert data to JSON string.

**Parameters:**

- **data** (`Any`) - Data to convert (dict, list, etc.)
- **indent** (`Optional[int]`) = `None` - Indentation level (default: None for compact)

**Returns:** `str` - JSON string


**Examples:**

{{ data | jsonify }}




---
### merge

```python
def merge(dict1: Dict[str, Any], dict2: Dict[str, Any], deep: bool = True) -> Dict[str, Any]
```

Merge two dictionaries.

**Parameters:**

- **dict1** (`Dict[str, Any]`) - First dictionary
- **dict2** (`Dict[str, Any]`) - Second dictionary (takes precedence)
- **deep** (`bool`) = `True` - Perform deep merge (default: True)

**Returns:** `Dict[str, Any]` - Merged dictionary


**Examples:**

{% set config = defaults | merge(custom_config) %}




---
### has_key

```python
def has_key(data: Dict[str, Any], key: str) -> bool
```

Check if dictionary has a key.

**Parameters:**

- **data** (`Dict[str, Any]`) - Dictionary to check
- **key** (`str`) - Key to look for

**Returns:** `bool` - True if key exists


**Examples:**

{% if data | has_key('author') %}




---
### get_nested

```python
def get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any
```

Access nested data using dot notation.

**Parameters:**

- **data** (`Dict[str, Any]`) - Dictionary with nested data
- **path** (`str`) - Dot-separated path (e.g., "user.profile.name")
- **default** (`Any`) = `None` - Default value if path not found

**Returns:** `Any` - Value at path or default


**Examples:**

{{ data | get_nested('user.profile.name') }}




---
### keys_filter

```python
def keys_filter(data: Dict[str, Any]) -> List[str]
```

Get dictionary keys as list.

**Parameters:**

- **data** (`Dict[str, Any]`) - Dictionary

**Returns:** `List[str]` - List of keys


**Examples:**

{% for key in data | keys %}




---
### values_filter

```python
def values_filter(data: Dict[str, Any]) -> List[Any]
```

Get dictionary values as list.

**Parameters:**

- **data** (`Dict[str, Any]`) - Dictionary

**Returns:** `List[Any]` - List of values


**Examples:**

{% for value in data | values %}




---
### items_filter

```python
def items_filter(data: Dict[str, Any]) -> List[tuple]
```

Get dictionary items as list of (key, value) tuples.

**Parameters:**

- **data** (`Dict[str, Any]`) - Dictionary

**Returns:** `List[tuple]` - List of (key, value) tuples


**Examples:**

{% for key, value in data | items %}




---
