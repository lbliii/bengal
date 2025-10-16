
---
title: "validators.performance"
type: python-module
source_file: "bengal/health/validators/performance.py"
css_class: api-content
description: "Performance validator - checks build performance (basic checks only).  Validates: - Detects slow pages (> 1 second render) - Warns if build is unusually slow - Reports basic throughput metrics"
---

# validators.performance

Performance validator - checks build performance (basic checks only).

Validates:
- Detects slow pages (> 1 second render)
- Warns if build is unusually slow
- Reports basic throughput metrics

---

## Classes

### `PerformanceValidator`

**Inherits from:** `BaseValidator`
Validates build performance (basic checks only).

Checks:
- Build time is reasonable for page count
- No individual pages are very slow
- Basic throughput metrics

Skips:
- Memory profiling (complex)
- Parallel efficiency analysis (advanced)
- Build time regression detection (needs history)




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run performance validation checks.



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


