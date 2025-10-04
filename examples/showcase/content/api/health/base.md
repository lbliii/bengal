---
title: "health.base"
layout: api-reference
type: python-module
source_file: "../../bengal/health/base.py"
---

# health.base

Base validator interface for health checks.

All validators should inherit from BaseValidator and implement the validate() method.

**Source:** `../../bengal/health/base.py`

---

## Classes

### BaseValidator

**Inherits from:** `ABC`
Base class for all health check validators.

Each validator should:
1. Have a clear name (e.g., "Navigation", "Cache Integrity")
2. Implement validate() to return a list of CheckResult objects
3. Be fast (target: < 100ms for most validators)
4. Be independent (no dependencies on other validators)


**Attributes:**

- **name** (`str`)- **description** (`str`)- **enabled_by_default** (`bool`)

**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List['CheckResult']
```

Run validation checks and return results.

**Parameters:**

- **self**
- **site** (`'Site'`) - The Site object being validated

**Returns:** `List['CheckResult']` - List of CheckResult objects (errors, warnings, info, or success)


**Examples:**

results = []





---
#### is_enabled

```python
def is_enabled(self, config: dict) -> bool
```

Check if this validator is enabled in config.

**Parameters:**

- **self**
- **config** (`dict`) - Site configuration dictionary

**Returns:** `bool` - True if validator should run






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


