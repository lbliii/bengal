
---
title: "validators.output"
type: python-module
source_file: "bengal/health/validators/output.py"
css_class: api-content
description: "Output validator - checks generated pages and assets.  Migrated from Site._validate_build_health() with improvements."
---

# validators.output

Output validator - checks generated pages and assets.

Migrated from Site._validate_build_health() with improvements.

---

## Classes

### `OutputValidator`

**Inherits from:** `BaseValidator`
Validates build output quality.

Checks:
- Page sizes (detect suspiciously small pages)
- Asset presence (CSS/JS files)
- Output directory structure




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run output validation checks.



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


