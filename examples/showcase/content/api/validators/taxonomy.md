
---
title: "validators.taxonomy"
type: python-module
source_file: "bengal/health/validators/taxonomy.py"
css_class: api-content
description: "Taxonomy validator - checks tag pages and taxonomy integrity.  Validates: - All tags have corresponding tag pages - No orphaned tag pages - Archive pages generated for sections - Pagination works correctly"
---

# validators.taxonomy

Taxonomy validator - checks tag pages and taxonomy integrity.

Validates:
- All tags have corresponding tag pages
- No orphaned tag pages
- Archive pages generated for sections
- Pagination works correctly

---

## Classes

### `TaxonomyValidator`

**Inherits from:** `BaseValidator`
Validates taxonomy system integrity.

Checks:
- Tag pages generated for all tags
- No orphaned tag pages (tag doesn't exist)
- Archive pages exist for sections with content
- Pagination pages are consistent




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run taxonomy validation checks.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`'Site'`)

:::{rubric} Returns
:class: rubric-returns
:::
`list[CheckResult]`




---
