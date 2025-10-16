
---
title: "validators.links"
type: python-module
source_file: "bengal/health/validators/links.py"
css_class: api-content
description: "Link validator wrapper.  Integrates the existing LinkValidator into the health check system."
---

# validators.links

Link validator wrapper.

Integrates the existing LinkValidator into the health check system.

---

## Classes

### `LinkValidatorWrapper`

**Inherits from:** `BaseValidator`
Wrapper for link validation.

Note: Link validation runs during post-processing. This validator
re-runs validation or reports on previous validation results.




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Validate links in generated pages.



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
