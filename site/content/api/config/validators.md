
---
title: "config.validators"
type: python-module
source_file: "bengal/config/validators.py"
css_class: api-content
description: "Configuration validation without external dependencies.  Provides type-safe configuration validation with helpful error messages, following Bengal's minimal dependencies and single-responsibility p..."
---

# config.validators

Configuration validation without external dependencies.

Provides type-safe configuration validation with helpful error messages,
following Bengal's minimal dependencies and single-responsibility principles.

---

## Classes

### `ConfigValidationError`

**Inherits from:** `ValueError`
Raised when configuration validation fails.





### `ConfigValidator`


Validates configuration with helpful error messages.

Single-responsibility validator class that checks:
- Type correctness (bool, int, str)
- Value ranges (min/max)
- Required fields
- Type coercion where sensible




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, config: dict[str, Any], source_file: Path | None = None) -> dict[str, Any]
```

Validate configuration and return normalized version.



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
* - `self`
  - -
  - -
  - -
* - `config`
  - `dict[str, Any]`
  - -
  - Raw configuration dictionary
* - `source_file`
  - `Path | None`
  - `None`
  - Optional source file for error context
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Validated and normalized configuration

:::{rubric} Raises
:class: rubric-raises
:::
- **`ConfigValidationError`**: If validation fails



---
