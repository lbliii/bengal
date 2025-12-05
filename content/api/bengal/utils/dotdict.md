
---
title: "dotdict"
type: "python-module"
source_file: "bengal/bengal/utils/dotdict.py"
line_number: 1
description: "DotDict - Dictionary with dot notation access. Provides clean attribute-style access to dictionary data while avoiding Jinja2 template gotchas (like .items, .keys, .values accessing methods)."
---

# dotdict
**Type:** Module
**Source:** [View source](bengal/bengal/utils/dotdict.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›dotdict

DotDict - Dictionary with dot notation access.

Provides clean attribute-style access to dictionary data while avoiding
Jinja2 template gotchas (like .items, .keys, .values accessing methods).

## Classes




### `DotDict`


Dictionary wrapper that allows dot notation access without method name conflicts.

This class solves a common Jinja2 gotcha: when using dot notation
on a regular dict, Jinja2 will access dict methods (like .items())
instead of dictionary keys named "items".

Example Problem:
    >>> data = {"skills": [{"category": "Programming", "items": ["Python"]}]}
    >>> # In Jinja2 template:
    >>> # {{ skill_group.items }}  # Accesses .items() method! ❌

Solution with DotDict:
    >>> data = DotDict({"skills": [{"category": "Programming", "items": ["Python"]}]})
    >>> # In Jinja2 template:
    >>> # {{ skill_group.items }}  # Accesses "items" field! ✅

Features:
    - Dot notation: obj.key
    - Bracket notation: obj['key']
    - Recursive wrapping of nested dicts (with caching for performance)
    - Dict-like interface (but not inheriting from dict)
    - No method name collisions

Usage:
    >>> # Create from dict
    >>> data = DotDict({"name": "Alice", "age": 30})
    >>> data.name
    'Alice'

    >>> # Nested dicts auto-wrapped
    >>> data = DotDict({"user": {"name": "Bob"}})
    >>> data.user.name
    'Bob'

    >>> # Lists preserved
    >>> data = DotDict({"items": ["a", "b", "c"]})
    >>> data.items  # Returns list, not a method!
    ['a', 'b', 'c']

Implementation Note:
    Unlike traditional dict subclasses, DotDict does NOT inherit from dict.
    This avoids method name collisions. We implement the dict interface
    manually to work with Jinja2 and other dict-expecting code.

Performance:
    Nested dictionaries are wrapped lazily and cached on first access.
    This prevents repeatedly creating new DotDict objects for the same
    nested data, which is especially important for deeply nested structures
    or when accessed in template loops.









## Methods



#### `__init__`
```python
def __init__(self, data: dict[str, Any] | None = None)
```


Initialize with a dictionary and a cache for wrapped nested objects.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any] \| None` | - | *No description provided.* |








#### `__getattribute__`
```python
def __getattribute__(self, key: str) -> Any
```


Intercept attribute access to prioritize data fields over methods.

This ensures that if a data field has the same name as a method
(like 'items', 'keys', 'values'), the data field is returned.

For Jinja2 compatibility, if a key doesn't exist in data and isn't
a real attribute, we return None instead of raising AttributeError.
This allows templates to safely check `if obj.field` without errors.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | The attribute name |







**Returns**


`Any` - The data value if it exists, the attribute, or None



#### `__setattr__`
```python
def __setattr__(self, key: str, value: Any) -> None
```


Allow dot notation assignment. Invalidates cache for the key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |
| `value` | `Any` | - | *No description provided.* |







**Returns**


`None`



#### `__delattr__`
```python
def __delattr__(self, key: str) -> None
```


Allow dot notation deletion. Invalidates cache for the key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `__getitem__`
```python
def __getitem__(self, key: str) -> Any
```


Bracket notation access with caching.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







**Returns**


`Any`



#### `__setitem__`
```python
def __setitem__(self, key: str, value: Any) -> None
```


Bracket notation assignment. Invalidates cache for the key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |
| `value` | `Any` | - | *No description provided.* |







**Returns**


`None`



#### `__delitem__`
```python
def __delitem__(self, key: str) -> None
```


Bracket notation deletion. Invalidates cache for the key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `__contains__`
```python
def __contains__(self, key: str) -> bool
```


Check if key exists.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







**Returns**


`bool`



#### `__len__`
```python
def __len__(self) -> int
```


Return number of keys.



**Returns**


`int`



#### `__iter__`
```python
def __iter__(self) -> Iterator[str]
```


Iterate over keys.



**Returns**


`Iterator[str]`



#### `__repr__`
```python
def __repr__(self) -> str
```


Custom repr showing it's a DotDict.



**Returns**


`str`



#### `get`
```python
def get(self, key: str, default: Any = None) -> Any
```


Get value with default.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |
| `default` | `Any` | - | *No description provided.* |







**Returns**


`Any`



#### `keys`
```python
def keys(self)
```


Return dict keys.




#### `values`
```python
def values(self)
```


Return dict values.




#### `items`
```python
def items(self)
```


Return dict items - note this is the METHOD, not a field.




#### `from_dict` @classmethod
```python
def from_dict(cls, data: dict[str, Any]) -> DotDict
```


Create DotDict from a regular dict, recursively wrapping nested dicts.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Source dictionary |







**Returns**


`DotDict` - DotDict with all nested dicts also wrapped



#### `to_dict`
```python
def to_dict(self) -> dict
```


Convert back to regular dict.



**Returns**


`dict`

## Functions



### `wrap_data`


```python
def wrap_data(data: Any) -> Any
```



Recursively wrap dictionaries in DotDict for clean access.

This is the main helper function for wrapping data loaded from
YAML/JSON files before passing to templates.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `Any` | - | Data to wrap (can be dict, list, or primitive) |







**Returns**


`Any` - Wrapped data with DotDict for all dicts
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> data = {
    ...     "team": [
    ...         {"name": "Alice", "skills": {"items": ["Python"]}},
    ...         {"name": "Bob", "skills": {"items": ["JavaScript"]}}
    ...     ]
    ... }
    >>> wrapped = wrap_data(data)
    >>> wrapped.team[0].skills.items  # Clean access!
    ['Python']
```



---
*Generated by Bengal autodoc from `bengal/bengal/utils/dotdict.py`*

