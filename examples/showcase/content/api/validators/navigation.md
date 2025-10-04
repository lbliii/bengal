---
title: "validators.navigation"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/navigation.py"
---

# validators.navigation

Navigation validator - checks page navigation integrity.

Validates:
- next/prev chains work correctly
- Breadcrumb paths are valid
- Section navigation is consistent
- No broken navigation references

**Source:** `../../bengal/health/validators/navigation.py`

---

## Classes

### NavigationValidator

**Inherits from:** `BaseValidator`
Validates page navigation integrity.

Checks:
- next/prev links form valid chains
- Breadcrumbs (ancestors) are valid
- Section navigation is consistent
- No orphaned pages in navigation




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run navigation validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


