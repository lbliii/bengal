
---
title: "validators.config"
type: python-module
source_file: "bengal/health/validators/config.py"
css_class: api-content
description: "Configuration validator wrapper.  Integrates the existing ConfigValidator into the health check system."
---

# validators.config

Configuration validator wrapper.

Integrates the existing ConfigValidator into the health check system.

---

## Classes

### `ConfigValidatorWrapper`

**Inherits from:** `BaseValidator`
Wrapper for config validation.

Note: Config validation happens at load time, so by the time we get to
health checks, the config has already been validated. This validator
confirms that validation occurred and reports any config-related concerns.




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Validate configuration.



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
