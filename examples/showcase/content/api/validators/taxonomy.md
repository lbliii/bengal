---
title: "validators.taxonomy"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/taxonomy.py"
---

# validators.taxonomy

Taxonomy validator - checks tag pages and taxonomy integrity.

Validates:
- All tags have corresponding tag pages
- No orphaned tag pages
- Archive pages generated for sections
- Pagination works correctly

**Source:** `../../bengal/health/validators/taxonomy.py`

---

## Classes

### TaxonomyValidator

**Inherits from:** `BaseValidator`
Validates taxonomy system integrity.

Checks:
- Tag pages generated for all tags
- No orphaned tag pages (tag doesn't exist)
- Archive pages exist for sections with content
- Pagination pages are consistent




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run taxonomy validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


