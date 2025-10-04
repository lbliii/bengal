---
title: "config.validators"
layout: api-reference
type: python-module
source_file: "../../bengal/config/validators.py"
---

# config.validators

Configuration validation without external dependencies.

Provides type-safe configuration validation with helpful error messages,
following Bengal's minimal dependencies and single-responsibility principles.

**Source:** `../../bengal/config/validators.py`

---

## Classes

### ConfigValidationError

**Inherits from:** `ValueError`
Raised when configuration validation fails.





### ConfigValidator


Validates configuration with helpful error messages.

Single-responsibility validator class that checks:
- Type correctness (bool, int, str)
- Value ranges (min/max)
- Required fields
- Type coercion where sensible




**Methods:**

#### validate

```python
def validate(self, config: Dict[str, Any], source_file: Optional[Path] = None) -> Dict[str, Any]
```

Validate configuration and return normalized version.

**Parameters:**

- **self**
- **config** (`Dict[str, Any]`) - Raw configuration dictionary
- **source_file** (`Optional[Path]`) = `None` - Optional source file for error context

**Returns:** `Dict[str, Any]` - Validated and normalized configuration

**Raises:**

- **ConfigValidationError**: If validation fails





---


