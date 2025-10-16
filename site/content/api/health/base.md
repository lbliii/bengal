
---
title: "health.base"
type: python-module
source_file: "bengal/health/base.py"
css_class: api-content
description: "Base validator interface for health checks.  All validators should inherit from BaseValidator and implement the validate() method."
---

# health.base

Base validator interface for health checks.

All validators should inherit from BaseValidator and implement the validate() method.

---

## Classes

### `BaseValidator`

**Inherits from:** `ABC`
Base class for all health check validators.

Each validator should:
1. Have a clear name (e.g., "Navigation", "Cache Integrity")
2. Implement validate() to return a list of CheckResult objects
3. Be fast (target: < 100ms for most validators)
4. Be independent (no dependencies on other validators)


:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `name`
  - `str`
  - -
* - `description`
  - `str`
  - -
* - `enabled_by_default`
  - `bool`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list['CheckResult']
```

Run validation checks and return results.



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
* - `self`
  - -
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - The Site object being validated
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['CheckResult']` - List of CheckResult objects (errors, warnings, info, or success)




:::{rubric} Examples
:class: rubric-examples
:::
```python
results = []
```


---
#### `is_enabled`
```python
def is_enabled(self, config: dict) -> bool
```

Check if this validator is enabled in config.



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
* - `self`
  - -
  - -
  - -
* - `config`
  - `dict`
  - -
  - Site configuration dictionary
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if validator should run




---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
