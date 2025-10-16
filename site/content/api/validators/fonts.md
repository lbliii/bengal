
---
title: "validators.fonts"
type: python-module
source_file: "bengal/health/validators/fonts.py"
css_class: api-content
description: "Font validator - checks font downloads and CSS generation.  Validates: - Font files downloaded successfully - CSS generated correctly - Font variants match config - No broken font references - Reas..."
---

# validators.fonts

Font validator - checks font downloads and CSS generation.

Validates:
- Font files downloaded successfully
- CSS generated correctly
- Font variants match config
- No broken font references
- Reasonable font file sizes

---

## Classes

### `FontValidator`

**Inherits from:** `BaseValidator`
Validates font downloads and CSS generation.

Checks:
- Font configuration is valid
- Font files downloaded (if fonts configured)
- CSS generated with correct @font-face rules
- Font file sizes are reasonable
- No broken font references in CSS




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run font validation checks.



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
