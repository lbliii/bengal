
---
title: "validators.menu"
type: python-module
source_file: "bengal/health/validators/menu.py"
css_class: api-content
description: "Menu validator - checks navigation menu integrity.  Integrates menu validation from MenuBuilder into health check system."
---

# validators.menu

Menu validator - checks navigation menu integrity.

Integrates menu validation from MenuBuilder into health check system.

---

## Classes

### `MenuValidator`

**Inherits from:** `BaseValidator`
Validates navigation menu structure.

Checks:
- Menu items exist and have valid URLs
- No orphaned menu items (parent doesn't exist)
- No circular references
- Menu weights are sensible




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Validate menu structure.



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


