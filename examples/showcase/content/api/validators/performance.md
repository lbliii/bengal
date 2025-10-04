---
title: "validators.performance"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/performance.py"
---

# validators.performance

Performance validator - checks build performance (basic checks only).

Validates:
- Detects slow pages (> 1 second render)
- Warns if build is unusually slow
- Reports basic throughput metrics

**Source:** `../../bengal/health/validators/performance.py`

---

## Classes

### PerformanceValidator

**Inherits from:** `BaseValidator`
Validates build performance (basic checks only).

Checks:
- Build time is reasonable for page count
- No individual pages are very slow
- Basic throughput metrics

Skips:
- Memory profiling (complex)
- Parallel efficiency analysis (advanced)
- Build time regression detection (needs history)




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run performance validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


