---
title: "template_functions.debug"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/debug.py"
---

# template_functions.debug

Debug utility functions for templates.

Provides 3 functions for debugging templates during development.

**Source:** `../../bengal/rendering/template_functions/debug.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register debug utility functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### debug

```python
def debug(var: Any, pretty: bool = True) -> str
```

Pretty-print variable for debugging.

**Parameters:**

- **var** (`Any`) - Variable to debug
- **pretty** (`bool`) = `True` - Use pretty printing (default: True)

**Returns:** `str` - String representation of variable


**Examples:**

{{ page | debug }}




---
### typeof

```python
def typeof(var: Any) -> str
```

Get the type of a variable.

**Parameters:**

- **var** (`Any`) - Variable to check

**Returns:** `str` - Type name as string


**Examples:**

{{ page | typeof }}  # "Page"




---
### inspect

```python
def inspect(obj: Any) -> str
```

Inspect object attributes and methods.

**Parameters:**

- **obj** (`Any`) - Object to inspect

**Returns:** `str` - List of attributes and methods


**Examples:**

{{ page | inspect }}




---
