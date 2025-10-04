---
title: "validators.directives"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/directives.py"
---

# validators.directives

Directive validator - checks directive syntax, usage, and performance.

Validates:
- Directive syntax is well-formed
- Required directive options present
- Tab markers properly formatted
- Nesting depth reasonable
- Performance warnings for directive-heavy pages

**Source:** `../../bengal/health/validators/directives.py`

---

## Classes

### DirectiveValidator

**Inherits from:** `BaseValidator`
Validates directive syntax and usage across the site.

Checks:
- Directive blocks are well-formed (opening and closing)
- Required options are present
- Tab markers are properly formatted
- Nesting depth is reasonable
- Performance warnings for heavy directive usage




**Methods:**

#### validate

```python
def validate(self, site: 'Site') -> List[CheckResult]
```

Run directive validation checks.

**Parameters:**

- **self**
- **site** (`'Site'`)

**Returns:** `List[CheckResult]`






---


