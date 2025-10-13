
---
title: "validators.rendering"
type: python-module
source_file: "bengal/health/validators/rendering.py"
css_class: api-content
description: "Rendering validator - checks output HTML quality.  Validates: - HTML structure is valid - No unrendered Jinja2 variables (outside code blocks) - Template functions are available - SEO metadata present"
---

# validators.rendering

Rendering validator - checks output HTML quality.

Validates:
- HTML structure is valid
- No unrendered Jinja2 variables (outside code blocks)
- Template functions are available
- SEO metadata present

---

## Classes

### `RenderingValidator`

**Inherits from:** `BaseValidator`
Validates HTML rendering quality.

Checks:
- Basic HTML structure (<html>, <head>, <body>)
- No unrendered Jinja2 variables in output
- Template functions registered and working
- Basic SEO metadata present




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run rendering validation checks.



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
