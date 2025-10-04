---
title: "validators.rendering"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/rendering.py"
---

# validators.rendering

Rendering validator - checks output HTML quality.

Validates:
- HTML structure is valid
- No unrendered Jinja2 variables (outside code blocks)
- Template functions are available
- SEO metadata present

**Source:** `../../bengal/health/validators/rendering.py`

---

## Classes

### RenderingValidator

**Inherits from:** `BaseValidator`
Validates HTML rendering quality.

Checks:
- Basic HTML structure (<html>, <head>, <body>)
- No unrendered Jinja2 variables in output
- Template functions registered and working
- Basic SEO metadata present




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run rendering validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


