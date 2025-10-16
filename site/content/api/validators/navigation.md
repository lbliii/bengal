
---
title: "validators.navigation"
type: python-module
source_file: "bengal/health/validators/navigation.py"
css_class: api-content
description: "Navigation validator - checks page navigation integrity.  Validates: - next/prev chains work correctly - Breadcrumb paths are valid - Section navigation is consistent - No broken navigation references"
---

# validators.navigation

Navigation validator - checks page navigation integrity.

Validates:
- next/prev chains work correctly
- Breadcrumb paths are valid
- Section navigation is consistent
- No broken navigation references

---

## Classes

### `NavigationValidator`

**Inherits from:** `BaseValidator`
Validates page navigation integrity.

Checks:
- next/prev links form valid chains
- Breadcrumbs (ancestors) are valid
- Section navigation is consistent
- No orphaned pages in navigation




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run navigation validation checks.



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
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[CheckResult]`




---
