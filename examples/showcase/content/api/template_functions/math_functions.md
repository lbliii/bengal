---
title: "template_functions.math_functions"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/math_functions.py"
---

# template_functions.math_functions

Math functions for templates.

Provides 6 essential mathematical operations for calculations in templates.

**Source:** `../../bengal/rendering/template_functions/math_functions.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register math functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### percentage

```python
def percentage(part: Number, total: Number, decimals: int = 0) -> str
```

Calculate percentage.

**Parameters:**

- **part** (`Number`) - Part value
- **total** (`Number`) - Total value
- **decimals** (`int`) = `0` - Number of decimal places (default: 0)

**Returns:** `str` - Formatted percentage string with % sign


**Examples:**

{{ completed | percentage(total_tasks) }}  # "75%"




---
### times

```python
def times(value: Number, multiplier: Number) -> Number
```

Multiply value by multiplier.

**Parameters:**

- **value** (`Number`) - Value to multiply
- **multiplier** (`Number`) - Multiplier

**Returns:** `Number` - Product


**Examples:**

{{ price | times(1.1) }}  # Add 10% tax




---
### divided_by

```python
def divided_by(value: Number, divisor: Number) -> Number
```

Divide value by divisor.

**Parameters:**

- **value** (`Number`) - Value to divide
- **divisor** (`Number`) - Divisor

**Returns:** `Number` - Quotient (0 if divisor is 0)


**Examples:**

{{ total | divided_by(count) }}       # Average




---
### ceil_filter

```python
def ceil_filter(value: Number) -> int
```

Round up to nearest integer.

**Parameters:**

- **value** (`Number`) - Value to round

**Returns:** `int` - Ceiling value


**Examples:**

{{ 4.2 | ceil }}   # 5




---
### floor_filter

```python
def floor_filter(value: Number) -> int
```

Round down to nearest integer.

**Parameters:**

- **value** (`Number`) - Value to round

**Returns:** `int` - Floor value


**Examples:**

{{ 4.2 | floor }}  # 4




---
### round_filter

```python
def round_filter(value: Number, decimals: int = 0) -> Number
```

Round to specified decimal places.

**Parameters:**

- **value** (`Number`) - Value to round
- **decimals** (`int`) = `0` - Number of decimal places (default: 0)

**Returns:** `Number` - Rounded value


**Examples:**

{{ 4.567 | round }}     # 5




---
