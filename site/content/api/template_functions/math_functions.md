
---
title: "template_functions.math_functions"
type: python-module
source_file: "bengal/rendering/template_functions/math_functions.py"
css_class: api-content
description: "Math functions for templates.  Provides 6 essential mathematical operations for calculations in templates."
---

# template_functions.math_functions

Math functions for templates.

Provides 6 essential mathematical operations for calculations in templates.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register math functions with Jinja2 environment.



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
### `percentage`
```python
def percentage(part: Number, total: Number, decimals: int = 0) -> str
```

Calculate percentage.



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
* - `part`
  - `Number`
  - -
  - Part value
* - `total`
  - `Number`
  - -
  - Total value
* - `decimals`
  - `int`
  - `0`
  - Number of decimal places (default: 0)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Formatted percentage string with % sign




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ completed | percentage(total_tasks) }}  # "75%"
```


---
### `times`
```python
def times(value: Number, multiplier: Number) -> Number
```

Multiply value by multiplier.



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
  - `Number`
  - -
  - Value to multiply
* - `multiplier`
  - `Number`
  - -
  - Multiplier
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Number` - Product




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ price | times(1.1) }}  # Add 10% tax
```


---
### `divided_by`
```python
def divided_by(value: Number, divisor: Number) -> Number
```

Divide value by divisor.



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
  - `Number`
  - -
  - Value to divide
* - `divisor`
  - `Number`
  - -
  - Divisor
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Number` - Quotient (0 if divisor is 0)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ total | divided_by(count) }}       # Average
```


---
### `ceil_filter`
```python
def ceil_filter(value: Number) -> int
```

Round up to nearest integer.



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
  - `Number`
  - -
  - Value to round
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`int` - Ceiling value




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ 4.2 | ceil }}   # 5
```


---
### `floor_filter`
```python
def floor_filter(value: Number) -> int
```

Round down to nearest integer.



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
  - `Number`
  - -
  - Value to round
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`int` - Floor value




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ 4.2 | floor }}  # 4
```


---
### `round_filter`
```python
def round_filter(value: Number, decimals: int = 0) -> Number
```

Round to specified decimal places.



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
  - `Number`
  - -
  - Value to round
* - `decimals`
  - `int`
  - `0`
  - Number of decimal places (default: 0)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Number` - Rounded value




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ 4.567 | round }}     # 5
```


---
