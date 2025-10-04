---
title: "validators.menu"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/menu.py"
---

# validators.menu

Menu validator - checks navigation menu integrity.

Integrates menu validation from MenuBuilder into health check system.

**Source:** `../../bengal/health/validators/menu.py`

---

## Classes

### MenuValidator

**Inherits from:** `BaseValidator`
Validates navigation menu structure.

Checks:
- Menu items exist and have valid URLs
- No orphaned menu items (parent doesn't exist)
- No circular references
- Menu weights are sensible




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Validate menu structure.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


