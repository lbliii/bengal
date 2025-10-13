
---
title: "validators.directives"
type: python-module
source_file: "bengal/health/validators/directives.py"
css_class: api-content
description: "Directive validator - checks directive syntax, usage, and performance.  Validates: - Directive syntax is well-formed - Required directive options present - Tab markers properly formatted - Nesting ..."
---

# validators.directives

Directive validator - checks directive syntax, usage, and performance.

Validates:
- Directive syntax is well-formed
- Required directive options present
- Tab markers properly formatted
- Nesting depth reasonable
- Performance warnings for directive-heavy pages

---

## Classes

### `DirectiveValidator`

**Inherits from:** `BaseValidator`
Validates directive syntax and usage across the site.

Checks:
- Directive blocks are well-formed (opening and closing)
- Required options are present
- Tab markers are properly formatted
- Nesting depth is reasonable
- Performance warnings for heavy directive usage




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run directive validation checks.



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
