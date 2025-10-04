---
title: "validators.output"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/output.py"
---

# validators.output

Output validator - checks generated pages and assets.

Migrated from Site._validate_build_health() with improvements.

**Source:** `../../bengal/health/validators/output.py`

---

## Classes

### OutputValidator

**Inherits from:** `BaseValidator`
Validates build output quality.

Checks:
- Page sizes (detect suspiciously small pages)
- Asset presence (CSS/JS files)
- Output directory structure




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run output validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


