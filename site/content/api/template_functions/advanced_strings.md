
---
title: "template_functions.advanced_strings"
type: python-module
source_file: "bengal/rendering/template_functions/advanced_strings.py"
css_class: api-content
description: "Advanced string manipulation functions for templates.  Provides 5 advanced string transformation functions."
---

# template_functions.advanced_strings

Advanced string manipulation functions for templates.

Provides 5 advanced string transformation functions.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register advanced string functions with Jinja2 environment.



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
### `camelize`
```python
def camelize(text: str) -> str
```

Convert string to camelCase.



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
* - `text`
  - `str`
  - -
  - Text to convert
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - camelCase text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ "hello_world" | camelize }}  # "helloWorld"
```


---
### `underscore`
```python
def underscore(text: str) -> str
```

Convert string to snake_case.



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
* - `text`
  - `str`
  - -
  - Text to convert
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - snake_case text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ "helloWorld" | underscore }}  # "hello_world"
```


---
### `titleize`
```python
def titleize(text: str) -> str
```

Convert string to Title Case (proper title capitalization).

More sophisticated than str.title() - handles articles, conjunctions,
and prepositions correctly.



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
* - `text`
  - `str`
  - -
  - Text to convert
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Properly title-cased text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ "the lord of the rings" | titleize }}
```


---
### `wrap_text`
```python
def wrap_text(text: str, width: int = 80) -> str
```

Wrap text to specified width.



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
* - `text`
  - `str`
  - -
  - Text to wrap
* - `width`
  - `int`
  - `80`
  - Maximum line width (default: 80)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Wrapped text with newlines




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ long_text | wrap(60) }}
```


---
### `indent_text`
```python
def indent_text(text: str, spaces: int = 4, first_line: bool = True) -> str
```

Indent text by specified number of spaces.



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
* - `text`
  - `str`
  - -
  - Text to indent
* - `spaces`
  - `int`
  - `4`
  - Number of spaces to indent (default: 4)
* - `first_line`
  - `bool`
  - `True`
  - Indent first line too (default: True)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Indented text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ code | indent(2) }}
```


---
### `softwrap_identifier`
```python
def softwrap_identifier(text: str) -> str
```

Insert soft wrap opportunities into API identifiers and dotted paths.

Adds zero-width space (​) after sensible breakpoints like dots, underscores,
and before uppercase letters in camelCase/PascalCase to allow titles like
"cache.dependency_tracker" to wrap nicely.



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
* - `text`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
### `last_segment`
```python
def last_segment(text: str) -> str
```

Return the last segment of a dotted or path-like identifier.



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
* - `text`
  - `str`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str`




:::{rubric} Examples
:class: rubric-examples
:::
```python
- "cache.dependency_tracker" -> "dependency_tracker"
```


---
