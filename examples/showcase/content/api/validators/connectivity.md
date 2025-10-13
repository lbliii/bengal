
---
title: "validators.connectivity"
type: python-module
source_file: "bengal/health/validators/connectivity.py"
css_class: api-content
description: "Connectivity validator for knowledge graph analysis.  Validates site connectivity, identifies orphaned pages, over-connected hubs, and provides insights for better content structure."
---

# validators.connectivity

Connectivity validator for knowledge graph analysis.

Validates site connectivity, identifies orphaned pages, over-connected hubs,
and provides insights for better content structure.

---

## Classes

### `ConnectivityValidator`

**Inherits from:** `BaseValidator`
Validates site connectivity using knowledge graph analysis.

Checks:
- Orphaned pages (no incoming references)
- Over-connected hubs (too many incoming references)
- Overall connectivity health
- Content discovery issues

This helps writers improve SEO, content discoverability, and site structure.




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Validate site connectivity.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`'Site'`) - The Site object being validated

:::{rubric} Returns
:class: rubric-returns
:::
`list[CheckResult]` - List of CheckResult objects with connectivity issues and recommendations




---
