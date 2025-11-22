# Template Refactoring Issue Analysis

## Problem: Double Rendering

### Root Cause
Both `cli_base.md.jinja2` and `command.md.jinja2` render the same content sections, causing duplication.

**Current Flow**:
```
1. command.md.jinja2 extends cli_base.md.jinja2
2. cli_base.md.jinja2.content block renders: description, usage, args, options
3. command.md.jinja2 OVERRIDES content block, renders same sections via partials
4. Result: Both render → duplicate content ❌
```

### Evidence from diff.md
```markdown
Line 22-25: Description from cli_base
Line 27-29: Description from command partial → DUPLICATE
```

### Observed Issues
1. **Duplicate descriptions** - Shows twice
2. **Sentinel.UNSET visible** - Default values not filtered (line 71, 88)
3. **Empty sections** - Lots of blank space

## Solution

### Option 1: Empty Base Content Block (Recommended)
Make `cli_base.md.jinja2` provide structure only, no rendering:

```jinja2
{#- cli_base.md.jinja2 -#}
{% extends "base/base.md.jinja2" %}

{% block doc_type %}cli-reference{% endblock %}

{% block badges %}
{#- Badge rendering logic -#}
{% endblock %}

{% block navigation %}
{#- Navigation logic -#}
{% endblock %}

{% block content %}
{#- Child templates fill this -#}
{% endblock %}
```

### Option 2: Remove Content Override from command.md.jinja2
Keep logic in base, don't override in child. But this loses the benefit of partials.

### Option 3: Use Different Base for Different Types
- `cli_base_abstract.md.jinja2` - Empty content block
- `cli_base_default.md.jinja2` - With default rendering

## Additional Fixes Needed

### 1. Filter Sentinel Values
```python
# In generator or template config
def should_show_default(value):
    if value is None or str(value) == "Sentinel.UNSET":
        return None
    return value
```

### 2. Conditional Section Rendering
Only render sections that have content:

```jinja2
{% set options = element.children | selectattr('element_type', 'equalto', 'option') | list %}
{% if options and options|length > 0 %}
## Options
{#- render options -#}
{% endif %}
```

### 3. Empty Line Cleanup
The `safe_section` macro adds blank lines. Should only render if content exists.

## Recommendation

**Fix `cli_base.md.jinja2` by removing duplicate content rendering from the base template.**

Files to modify:
1. `bengal/autodoc/templates/base/cli_base.md.jinja2` - Remove content block duplication
2. `bengal/autodoc/template_safety.py` or `generator.py` - Add Sentinel value filtering
3. `bengal/autodoc/templates/macros/safe_macros.md.jinja2` - Improve empty section handling

## Testing
After fix, regenerate `site/content/cli/config/diff.md` and verify:
- [ ] Description appears only once
- [ ] No "Sentinel.UNSET" visible
- [ ] No excessive blank lines
- [ ] All sections render correctly
