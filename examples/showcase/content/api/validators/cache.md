---
title: "validators.cache"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/cache.py"
---

# validators.cache

Cache validator - checks incremental build cache integrity.

Validates:
- Cache file exists and is readable
- Cache is not corrupted
- Cache size is reasonable
- Basic dependency tracking works

**Source:** `../../bengal/health/validators/cache.py`

---

## Classes

### CacheValidator

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




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run cache validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


