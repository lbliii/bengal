---
title: "validators.links"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/links.py"
---

# validators.links

Link validator wrapper.

Integrates the existing LinkValidator into the health check system.

**Source:** `../../bengal/health/validators/links.py`

---

## Classes

### LinkValidatorWrapper

**Inherits from:** `BaseValidator`
Wrapper for link validation.

Note: Link validation runs during post-processing. This validator
re-runs validation or reports on previous validation results.




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Validate links in generated pages.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


