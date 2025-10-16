
---
title: "rendering.jinja_utils"
type: python-module
source_file: "bengal/rendering/jinja_utils.py"
css_class: api-content
description: "Jinja2 utility functions for template development.  Provides helpers for working with Jinja2's Undefined objects and accessing template context safely."
---

# rendering.jinja_utils

Jinja2 utility functions for template development.

Provides helpers for working with Jinja2's Undefined objects and accessing
template context safely.

---


## Functions

### `is_undefined`
```python
def is_undefined(value: Any) -> bool
```

Check if a value is a Jinja2 Undefined object.

This is a wrapper around jinja2.is_undefined() that provides a clean API
for template function developers.



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
* - `value`
  - `Any`
  - -
  - Value to check
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if value is Undefined, False otherwise




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> from jinja2 import Undefined
    >>> is_undefined(Undefined())
    True
    >>> is_undefined("hello")
    False
    >>> is_undefined(None)
    False
```


---
### `safe_get`
```python
def safe_get(obj: Any, attr: str, default: Any = None) -> Any
```

Safely get attribute from object, handling Jinja2 Undefined values.

This is a replacement for hasattr()/getattr() that also handles Jinja2's
Undefined objects and returns default for missing attributes, even when
__getattr__ is implemented.



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
* - `obj`
  - `Any`
  - -
  - Object to get attribute from
* - `attr`
  - `str`
  - -
  - Attribute name
* - `default`
  - `Any`
  - `None`
  - Default value if undefined or missing
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Any` - Attribute value or default




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> class Page:
    ...     title = "Hello"
    >>> safe_get(Page(), "title", "Untitled")
    'Hello'
    >>> safe_get(Page(), "missing", "Default")
    'Default'

    # In templates with Undefined objects:
    {% set title = safe_get(page, "title", "Untitled") %}
```


---
### `has_value`
```python
def has_value(value: Any) -> bool
```

Check if value is defined and not None/empty.

More strict than is_undefined() - also checks for None and falsy values.
Returns False for: Undefined, None, False, 0, "", [], {}



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
* - `value`
  - `Any`
  - -
  - Value to check
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if value is defined and truthy




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> has_value("hello")
    True
    >>> has_value("")
    False
    >>> has_value(None)
    False
    >>> has_value(0)
    False
    >>> has_value([])
    False
    >>> has_value(False)
    False
```


---
### `safe_get_attr`
```python
def safe_get_attr(obj: Any, *attrs: str) -> Any
```

Safely get nested attribute from object using dot notation.



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
* - `obj`
  - `Any`
  - -
  - Object to get attribute from *attrs: Attribute names (can be nested)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Any` - Final attribute value or default




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> class User:
    ...     class Profile:
    ...         name = "John"
    ...     profile = Profile()
    >>> safe_get_attr(user, "profile", "name", default="Unknown")
    'John'
    >>> safe_get_attr(user, "profile", "missing", default="Unknown")
    'Unknown'
```


---
### `ensure_defined`
```python
def ensure_defined(value: Any, default: Any = '') -> Any
```

Ensure value is defined and not None, replacing Undefined/None with default.

This is useful in templates to ensure a value is always usable, even if
it's missing or explicitly set to None.



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
* - `value`
  - `Any`
  - -
  - Value to check
* - `default`
  - `Any`
  - `''`
  - Default value to use if undefined or None (default: "")
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Any` - Original value if defined and not None, default otherwise




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> ensure_defined("hello")
    'hello'
    >>> ensure_defined(Undefined(), "fallback")
    'fallback'
    >>> ensure_defined(None, "fallback")
    'fallback'
    >>> ensure_defined(0)  # 0 is a valid value
    0
```


---
