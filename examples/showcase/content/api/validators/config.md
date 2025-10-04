---
title: "validators.config"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/config.py"
---

# validators.config

Configuration validator wrapper.

Integrates the existing ConfigValidator into the health check system.

**Source:** `../../bengal/health/validators/config.py`

---

## Classes

### ConfigValidatorWrapper

**Inherits from:** `BaseValidator`
Wrapper for config validation.

Note: Config validation happens at load time, so by the time we get to
health checks, the config has already been validated. This validator
confirms that validation occurred and reports any config-related concerns.




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Validate configuration.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


