
---
title: "template_functions.debug"
type: python-module
source_file: "bengal/rendering/template_functions/debug.py"
css_class: api-content
description: "Debug utility functions for templates.  Provides 3 functions for debugging templates during development."
---

# template_functions.debug

Debug utility functions for templates.

Provides 3 functions for debugging templates during development.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register debug utility functions with Jinja2 environment.



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
### `debug`
```python
def debug(var: Any, pretty: bool = True) -> str
```

Pretty-print variable for debugging.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`var`** (`Any`) - Variable to debug
- **`pretty`** (`bool`) = `True` - Use pretty printing (default: True)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - String representation of variable




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ page | debug }}
```


---
### `typeof`
```python
def typeof(var: Any) -> str
```

Get the type of a variable.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`var`** (`Any`) - Variable to check

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Type name as string




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ page | typeof }}  # "Page"
```


---
### `inspect`
```python
def inspect(obj: Any) -> str
```

Inspect object attributes and methods.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`obj`** (`Any`) - Object to inspect

:::{rubric} Returns
:class: rubric-returns
:::
`str` - List of attributes and methods




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ page | inspect }}
```


---
