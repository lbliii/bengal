
---
title: "validators.assets"
type: python-module
source_file: "bengal/health/validators/assets.py"
css_class: api-content
description: "Asset validator - checks asset processing and optimization.  Validates: - Asset files copied to output - Asset hashing/fingerprinting works (if enabled) - Minification applied (if enabled) - No dup..."
---

# validators.assets

Asset validator - checks asset processing and optimization.

Validates:
- Asset files copied to output
- Asset hashing/fingerprinting works (if enabled)
- Minification applied (if enabled)
- No duplicate assets
- Reasonable asset sizes

---

## Classes

### `AssetValidator`

**Inherits from:** `BaseValidator`
Validates asset processing and optimization.

Checks:
- Assets directory exists and has files
- Asset types are present (CSS, JS, images)
- No duplicate assets (same content, different names)
- Asset sizes are reasonable
- Minification hints (file size analysis)




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run asset validation checks.



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
