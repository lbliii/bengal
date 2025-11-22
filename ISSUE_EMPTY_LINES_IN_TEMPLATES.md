# Issue: Excessive Empty Lines in Generated Docs

## Root Cause Found!

You're absolutely right - the templates ARE generating excessive blank lines, and I was wrong to assume it was just "old output".

### Evidence from Generated Markdown

**File**: `site/content/cli/config/show.md`

Every option has **5-6 blank lines** after it:

```markdown
### `environment`


Environment to load (auto-detected if not specified)

**Type:** `text`




      ← 5 blank lines here!

### `profile`
```

**This happens EVEN with our `safe_section` fix!**

## The Real Problem

The template has blank lines built into the structure:

```jinja2
### `{{ current_item.name }}`
   ← blank line (line 19)
{% if current_item.metadata.short_name %}
...
{% endif %}
   ← blank line (line 23)
{% if current_item.description %}
...
{% endif %}
   ← blank line (line 29)
{% if current_item.metadata.type %}
...
{% endif %}
   ← blank line (line 33)
{% if current_item.metadata.default %}
...
{% endif %}
   ← blank line (line 40)
{% if current_item.metadata.required %}
...
{% endif %}
   ← blank line (line 46)
{% if current_item.metadata.choices %}
...
{% endif %}
   ← blank line (line 50)
{% endcall %}
```

When a condition is FALSE, the blank line still renders!

## Example Flow

For an option with no short_name, no default, no choices:

```jinja2
### `environment`              ← rendered
                                ← blank line (line 19)
{% if current_item.metadata.short_name %}  ← FALSE, skipped
{% endif %}
                                ← blank line (line 23) RENDERED!
{% if current_item.description %}
Environment to load...          ← rendered
{% endif %}
                                ← blank line (line 29) RENDERED!
{% if current_item.metadata.type %}
**Type:** `text`                ← rendered
{% endif %}
                                ← blank line (line 33) RENDERED!
{% if current_item.metadata.default %}  ← FALSE, skipped
{% endif %}
                                ← blank line (line 40) RENDERED!
```

Result: **5 blank lines** between content blocks!

## Why `safe_section` Didn't Fix This

`safe_section` filters empty content at the **section level**, but these blank lines are **between items** in a loop.

The loop renders:
```
Item 1 (with trailing blanks)
Item 2 (with trailing blanks)  
Item 3 (with trailing blanks)
```

Each item has content (not empty), so `safe_section` doesn't filter it.

## The Fix

### Option A: Remove All Template Blank Lines
```jinja2
### `{{ current_item.name }}`
{% if current_item.metadata.short_name %}
**Short form:** `-{{ current_item.metadata.short_name }}`
{% endif %}
{% if current_item.description %}
{{ current_item.description }}
{% else %}
*No description provided.*
{% endif %}
{% if current_item.metadata.type %}
**Type:** `{{ current_item.metadata.type }}`
{% endif %}
{#- ... no blank lines between blocks -#}
```

### Option B: Add Single Blank Line Only Between Items
```jinja2
{% call(current_item) safe_for(options, "*No options available.*") %}
{% call safe_render("option", current_item) %}
### `{{ current_item.name }}`
{% if current_item.metadata.short_name %}
**Short form:** `-{{ current_item.metadata.short_name }}`
{% endif %}
{#- ... compact content -#}
{% endcall %}
{% if not loop.last %}

{% endif %}  {#- Single blank line between options -#}
{% endcall %}
```

### Option C: Use Jinja2 Whitespace Control
```jinja2
### `{{ current_item.name }}`
{%- if current_item.metadata.short_name %}

**Short form:** `-{{ current_item.metadata.short_name }}`
{%- endif %}
{%- if current_item.description %}

{{ current_item.description }}
{%- else %}

*No description provided.*
{%- endif %}
```

## Recommendation

**Option A**: Remove blank lines from templates (simplest, cleanest)

The markdown will be more compact but still readable:
```markdown
### `environment`
Environment to load (auto-detected if not specified)
**Type:** `text`

### `profile`
Profile to load (optional)
**Type:** `text`
```

## Files to Fix

1. `bengal/autodoc/templates/cli/partials/command_options.md.jinja2`
2. `bengal/autodoc/templates/cli/partials/command_arguments.md.jinja2`
3. Possibly others with similar patterns

## Impact

**Before**:
- 135 lines for `show.md` (6 options = ~22 lines each!)
- 98 lines for `diff.md` (3 params = ~32 lines each!)
- Lots of whitespace, looks "broken"

**After** (estimated):
- ~80 lines for `show.md` (6 options = ~13 lines each)
- ~55 lines for `diff.md` (3 params = ~18 lines each)  
- Compact, professional looking

---

**Status**: Issue identified, fix ready to apply
**Severity**: 🟡 Important (UX issue)
**Confidence**: HIGH - this is definitely the problem
