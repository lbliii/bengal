# Template Variable Mismatch Fix

**Date:** 2025-10-12  
**Status:** ✅ Fixed

## Issue

Variable name mismatch in `partials/reference-header.html`:
- Documentation said to use: `icon`, `title`, `description`
- Template actually used: `ref_icon`, `ref_title`, `ref_description`
- Usage examples showed invalid Jinja2 syntax with `{% include ... with { dict } %}`

## Root Causes

### 1. Variable Name Inconsistency
The partial template used `ref_*` prefix but documentation showed plain names.

### 2. Invalid Jinja2 Syntax
The documentation showed this (which doesn't work):
```jinja2
{% include 'partials/reference-header.html' with {
  icon: '📦',
  title: page.title
} %}
```

**Jinja2 doesn't support dictionary syntax in `include` statements!**

### 3. Silent Failures
By default, Jinja2 renders undefined variables as empty strings, causing silent failures where content just doesn't appear (no error thrown).

## Changes Made

### 1. Fixed Variable Names in Partial ✅
**File:** `bengal/themes/default/templates/partials/reference-header.html`

Changed template variables to match documentation:
```diff
- {{ ref_icon | default('📄') }}
+ {{ icon | default('📄') }}

- {{ ref_title }}
+ {{ title }}

- {% if ref_description %}
+ {% if description %}
```

### 2. Fixed Template Usage ✅
**Files:**
- `bengal/themes/default/templates/api-reference/single.html`
- `bengal/themes/default/templates/cli-reference/single.html`

Changed from invalid syntax to correct Jinja2:
```jinja2
{# CORRECT - Set variables before include #}
{% set icon = '📦' %}
{% set title = page.title %}
{% set description = page.metadata.description %}
{% set type = 'api' %}
{% include 'partials/reference-header.html' %}
```

### 3. Fixed Documentation ✅
**Files:**
- `bengal/themes/default/templates/partials/reference-header.html` (usage comment)
- `plan/active/REFERENCE_DOCS_CONSISTENCY_PLAN.md`

Updated all examples to show correct Jinja2 syntax.

### 4. Added StrictUndefined for Better Error Detection ✅
**File:** `bengal/rendering/template_engine.py`

Added `StrictUndefined` when `strict_mode` is enabled:
```python
from jinja2 import Environment, StrictUndefined

# In _create_environment():
undefined_behavior = StrictUndefined if self.site.config.get("strict_mode", False) else None

env = Environment(
    # ... other config ...
    undefined=undefined_behavior,  # Raise errors for undefined variables in strict mode
)
```

## Template Error Handling in Bengal

### Default Behavior (Production)
- Undefined variables render as empty strings → **silent failures**
- Template errors are caught and logged
- Build continues with fallback HTML
- Errors collected and shown at end

### Strict Mode (`strict_mode: true`)
- **Now uses `StrictUndefined`** → undefined variables raise errors immediately
- Build fails on first template error
- Full error details displayed

### Debug Mode (`debug: true`)
- Shows full tracebacks
- More detailed error messages
- Works with or without strict mode

## How to Catch Template Errors

### Option 1: Use Strict Mode (Recommended for Development)
```toml
# bengal.toml
strict_mode = true
debug = true
```

### Option 2: Check Build Logs
Look for warnings like:
```
⚠️  Jinja2 syntax error in path/to/file.md: ...
⚠️  Template render error: ...
```

### Option 3: Look for Empty Spots
If content doesn't appear (empty header, missing icons), check:
1. Variable names match between caller and partial
2. Variables are set before `{% include %}`
3. No typos in variable names

## Jinja2 Include Patterns

### ✅ Correct Ways to Pass Variables

**Pattern 1: Set variables before include**
```jinja2
{% set icon = '📦' %}
{% set title = page.title %}
{% include 'partials/header.html' %}
```

**Pattern 2: Include with full context (pass everything)**
```jinja2
{% include 'partials/header.html' %}
{# Template has access to all variables in current scope #}
```

### ❌ Invalid Syntax

**Dictionary syntax (doesn't exist in Jinja2)**
```jinja2
{% include 'partials/header.html' with {
  icon: '📦',
  title: page.title
} %}
```

**Keyword arguments (also doesn't exist)**
```jinja2
{% include 'partials/header.html' icon='📦' title=page.title %}
```

## Testing

To verify the fix works:

```bash
cd examples/showcase

# Test with strict mode (will fail on undefined variables)
bengal build --strict-mode

# Should see proper headers with icons on:
# - /api/ pages (📦 icon)
# - /cli/ pages (⌨️ icon)
```

## Prevention

### For Template Authors
1. Always use consistent variable names
2. Document expected variables in template comments
3. Use `| default('fallback')` for optional variables
4. Test with `strict_mode = true` during development

### For Bengal Core
1. Consider enabling `StrictUndefined` by default in dev mode
2. Add template validation tool to catch undefined variables
3. Better error messages for common mistakes

## Related Files

- `/bengal/rendering/template_engine.py` - Template engine with StrictUndefined
- `/bengal/rendering/renderer.py` - Error handling and fallback
- `/bengal/rendering/errors.py` - Rich error display
- `/bengal/themes/default/templates/partials/reference-header.html` - Fixed partial
- `/bengal/themes/default/templates/api-reference/single.html` - Updated usage
- `/bengal/themes/default/templates/cli-reference/single.html` - Updated usage

## Summary

**What was wrong:** Template used `ref_icon` but documentation said `icon`, and examples showed invalid Jinja2 syntax.

**Why it failed silently:** Jinja2's default behavior is to render undefined variables as empty strings.

**How we fixed it:**
1. Unified variable names (`icon`, not `ref_icon`)
2. Fixed syntax to valid Jinja2 (`{% set var %}` before `{% include %}`)
3. Added `StrictUndefined` in strict mode to catch future errors
4. Updated all documentation

**Result:** Templates now work correctly and will throw clear errors in strict mode if variables are missing.
