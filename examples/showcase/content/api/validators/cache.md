
---
title: "validators.cache"
type: python-module
source_file: "bengal/health/validators/cache.py"
css_class: api-content
description: "Cache validator - checks incremental build cache integrity.  Validates: - Cache file exists and is readable - Cache is not corrupted - Cache size is reasonable - Basic dependency tracking works"
---

# validators.cache

Cache validator - checks incremental build cache integrity.

Validates:
- Cache file exists and is readable
- Cache is not corrupted
- Cache size is reasonable
- Basic dependency tracking works

---

## Classes

### `CacheValidator`

**Inherits from:** `BaseValidator`
Validates build cache integrity (essential checks only).

Checks:
- Cache file exists and is readable
- Cache format is valid JSON
- Cache size is reasonable (not corrupted/bloated)
- Has expected structure (file_hashes, dependencies)

Skips:
- Deep dependency graph validation (complex)
- File hash verification (too slow)
- Advanced corruption detection (overkill)




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run cache validation checks.



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
