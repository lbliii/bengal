# Comprehensive Template Issues Analysis

## Issue #1: Double Rendering (CLI Templates)

**Location**: `bengal/autodoc/templates/base/cli_base.md.jinja2` + `cli/command.md.jinja2`

**Problem**: Both base and child templates render the same content sections.

**Flow**:
1. `command.md.jinja2` extends `cli_base.md.jinja2`
2. `cli_base.md.jinja2` has a `content` block that renders: description, usage, args, options (lines 50-126)
3. `command.md.jinja2` OVERRIDES `content` block and renders same sections via partials (lines 12-41)
4. Result: Content rendered twice → **duplicate descriptions**

**Evidence**: `site/content/cli/config/diff.md` lines 22-29 show duplicate description.

**Fix**:
```jinja2
{#- cli_base.md.jinja2 - Remove lines 50-126, keep structure only -#}
{% block content %}
{#- Child templates implement specific layout -#}
{% endblock %}
```

---

## Issue #2: Variable Scoping (Python Templates)

**Location**: `bengal/autodoc/templates/python/partials/module_classes.md.jinja2` lines 49-53

**Problem**: Class methods, attributes, and properties are **commented out** with TODO.

**Code**:
```jinja2
{#- TODO: Re-enable class components after fixing variable scoping
{% include 'python/partials/class_attributes.md.jinja2' %}
{% include 'python/partials/class_properties.md.jinja2' %}
{% include 'python/partials/class_methods.md.jinja2' %}
-#}
```

**Root Cause**: Jinja2 `{% include %}` doesn't automatically pass loop variables. The partials expect `current_item` but it's not in scope.

**Current Flow**:
```jinja2
{% for current_item in public_classes %}
  {#- current_item defined here -#}
  {% include 'python/partials/class_methods.md.jinja2' %}
  {#- But include can't see current_item! -#}
{% endfor %}
```

**Evidence**: `site/content/api/core/site.md` shows Site class but no methods or attributes (line 29 shows class, then ends at line 57).

**Fix Option 1**: Pass context explicitly
```jinja2
{% include 'python/partials/class_attributes.md.jinja2' with context %}
```

**Fix Option 2**: Pass variable explicitly (better)
```jinja2
{% set item = current_item %}
{% include 'python/partials/class_attributes.md.jinja2' %}
```

**Fix Option 3**: Use with block (best - already used for methods line 65)
```jinja2
{% with item = current_item %}
{% include 'python/partials/class_attributes.md.jinja2' %}
{% include 'python/partials/class_properties.md.jinja2' %}
{% include 'python/partials/class_methods.md.jinja2' %}
{% endwith %}
```

---

## Issue #3: Sentinel.UNSET in Output

**Location**: `bengal/autodoc/extractors/cli.py` line 302

**Problem**: Click uses `Sentinel.UNSET` as a special marker for unset defaults, but we're converting it to string.

**Code**:
```python
"default": str(param.default) if param.default is not None else None,
```

**Evidence**: `site/content/cli/config/diff.md` lines 71, 88 show `**Default:** Sentinel.UNSET`

**Fix**:
```python
import click

def get_param_default(param) -> str | None:
    """Get parameter default value, filtering sentinel values."""
    default = param.default

    # Check for Click's sentinel values
    if default is None:
        return None

    # Check if it's a Click sentinel (UNSET, etc.)
    if hasattr(click, 'core') and hasattr(click.core, '_missing'):
        if default is click.core._missing:
            return None

    # Also check string representation
    default_str = str(default)
    if 'Sentinel' in default_str or default_str == 'UNSET':
        return None

    return default_str

# Use in extraction:
"default": get_param_default(param),
```

---

## Issue #4: Excessive Empty Lines

**Location**: Multiple templates using `safe_section` macro

**Problem**: `safe_section` macro renders even when content is empty, leaving blank sections.

**Evidence**:
- `site/content/api/core/site.md` lines 23-26, 51-56 (lots of blank lines)
- `site/content/cli/config/diff.md` has many empty line runs

**Current safe_section**:
```jinja2
{% macro safe_section(section_name, show_errors=true) %}
{% if caller %}
{{ caller() }}
{% endif %}
{% endmacro %}
```

**Fix**: Check if caller produces content before rendering
```jinja2
{% macro safe_section(section_name, show_errors=true) %}
{% if caller %}
{% set content = caller() %}
{% if content and content.strip() %}
{{ content }}
{% endif %}
{% endif %}
{% endmacro %}
```

---

## Issue #5: Parameter Default Filtering in Templates

**Location**: `bengal/autodoc/templates/cli/partials/command_options.md.jinja2` line 34-36

**Problem**: Renders default even if it's sentinel/empty.

**Code**:
```jinja2
{% if current_item.metadata.default %}
**Default:** `{{ current_item.metadata.default }}`
{% endif %}
```

**Fix**: Add sentinel check
```jinja2
{% if current_item.metadata.default and current_item.metadata.default != 'None' %}
{% set default_str = current_item.metadata.default | string %}
{% if 'Sentinel' not in default_str and default_str != 'UNSET' %}
**Default:** `{{ current_item.metadata.default }}`
{% endif %}
{% endif %}
```

Or better, filter at extraction time (see Issue #3).

---

## Issue #6: Empty Sections with Headers

**Location**: Various partials that render headers unconditionally

**Problem**: Sections render "## Options" even when there are no options.

**Example**: `command_arguments.md.jinja2` lines 13-14 always render header
```jinja2
{% if arguments %}
## Arguments
{#- Then render arguments -#}
{% endif %}
```

**Fix**: This is actually OK - the `{% if arguments %}` check is correct. The issue is empty sections from parent templates (see Issue #4).

---

## Issue #7: Navigation Formatting

**Location**: `bengal/autodoc/templates/macros/navigation.md.jinja2` (assumed)

**Problem**: Navigation shows odd spacing: "core ›site" (with Unicode arrow)

**Evidence**: `site/content/api/core/site.md` line 16

**Status**: Minor cosmetic issue, not critical. May be intentional design.

---

## Summary of Fixes Needed

### Critical (Breaks functionality)
1. ✅ **Fix double rendering** - Remove content from `cli_base.md.jinja2`
2. ✅ **Fix variable scoping** - Un-comment class components and pass context
3. ✅ **Filter Sentinel values** - Add check in CLI extractor

### Important (User-visible issues)
4. ✅ **Remove excessive blank lines** - Improve `safe_section` macro
5. ✅ **Filter defaults in templates** - Double-check default rendering

### Nice to have
6. ⚠️ Navigation formatting - Review if intentional

---

## Testing Plan

After fixes:

1. **Regenerate CLI docs**:
   ```bash
   # Clear old docs
   rm -rf site/content/cli/
   # Regenerate
   python -m bengal.cli utils autodoc-cli
   ```

   **Verify**:
   - [ ] No duplicate descriptions in `diff.md`
   - [ ] No "Sentinel.UNSET" visible
   - [ ] No excessive blank lines

2. **Regenerate Python API docs**:
   ```bash
   rm -rf site/content/api/
   python -m bengal.cli utils autodoc
   ```

   **Verify**:
   - [ ] Site class shows methods
   - [ ] Site class shows attributes
   - [ ] Site class shows properties
   - [ ] No excessive blank lines

3. **Full site build**:
   ```bash
   python -m bengal.cli site build
   python -m bengal.cli site serve
   ```

   **Verify**:
   - [ ] Browse to `/api/core/site/`
   - [ ] Browse to `/cli/config/diff/`
   - [ ] Check HTML output quality

---

## Files to Modify

### Priority 1 (Critical)
1. `bengal/autodoc/templates/base/cli_base.md.jinja2` - Remove content duplication
2. `bengal/autodoc/templates/python/partials/module_classes.md.jinja2` - Un-comment and fix scoping
3. `bengal/autodoc/extractors/cli.py` - Add Sentinel filtering

### Priority 2 (Important)
4. `bengal/autodoc/templates/macros/safe_macros.md.jinja2` - Improve `safe_section`
5. `bengal/autodoc/templates/cli/partials/command_options.md.jinja2` - Add default filtering

### Priority 3 (Polish)
6. `bengal/autodoc/templates/cli/partials/command_arguments.md.jinja2` - Review empty section handling

---

## Estimated Fix Time

- **Fix #1 (double rendering)**: 10 min
- **Fix #2 (variable scoping)**: 15 min
- **Fix #3 (Sentinel filtering)**: 20 min
- **Fix #4 (empty lines)**: 15 min
- **Fix #5 (template defaults)**: 5 min

**Total**: ~65 minutes + testing (30 min) = ~95 minutes

---

## Risk Assessment

- **Low risk**: Fixes are localized to templates and extractors
- **High impact**: Dramatically improves documentation quality
- **Testing**: Comprehensive regeneration will catch regressions
- **Rollback**: Git checkout if issues arise
