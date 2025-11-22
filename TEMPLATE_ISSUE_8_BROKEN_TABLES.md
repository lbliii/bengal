# Template Issue #8: Broken Markdown Tables

**Status:** ✅ FIXED
**Severity:** 🔴 CRITICAL (breaks all Python API tables)
**Reported by User:** ✅ Yes

---

## Problem

Markdown tables were rendering as individual `<p>` tags instead of `<table>` elements because table rows had blank lines between them.

### Evidence from Public HTML

User reported seeing:
```html
<p>|<code>source</code>|<code>str</code>| - | <em>No description provided.</em> |</p>
```

Instead of proper table syntax.

### Root Cause

In `/bengal/autodoc/templates/macros/parameter_table.md.jinja2`, the `{% endcall %}` after each table row was adding a newline:

```jinja2
{% for attr in attributes %}
{% call safe_render("attribute", attr) %}
| `{{ safe_attr(attr, 'name', 'unknown') }}` | {{ param_type(attr) }} | {{ param_description(attr) }} |
{% endcall %}  ← This adds a newline!
{% endfor %}
```

Generated markdown:
```markdown
| Name | Type | Description |
|------|------|-------------|
| `name` | - | Element name... |
                            ← BLANK LINE!
| `qualified_name` | - | Full path... |
```

**Markdown requires consecutive table rows with NO blank lines.**

---

## Impact

- **ALL Python API attribute tables broken** (DocElement, Site, Page, etc.)
- **ALL parameter tables broken** (function signatures)
- **ALL returns tables broken** (return types)

---

## Solution

Use Jinja2 whitespace control to strip newlines: `{%-` removes leading whitespace, `-%}` removes trailing.

### Fix 1: `parameter_list_table` macro (Lines 32-36)

```jinja2
{%- for param in parameters %}
{%- call safe_render("parameter", param) %}
| `{{ safe_attr(param, 'name', 'unknown') }}` | ... |
{%- endcall %}
{%- endfor %}
```

### Fix 2: `attribute_table` macro (Lines 121-125)

```jinja2
{%- for attr in attributes %}
{%- call safe_render("attribute", attr) %}
| `{{ safe_attr(attr, 'name', 'unknown') }}` | {{ param_type(attr) }} | {{ param_description(attr) }} |
{%- endcall %}
{%- endfor %}
```

### Fix 3: `returns_table` macro (Lines 138-143)

```jinja2
{%- if returns_info is iterable and returns_info is not string %}
{%- for return_item in returns_info %}
{%- call safe_render("return", return_item) %}
| {{ param_type(return_item) }} | {{ param_description(return_item) }} |
{%- endcall %}
{%- endfor %}
{%- else %}
| {{ param_type(returns_info) }} | {{ param_description(returns_info) }} |
{%- endif %}
```

---

## Verification

After regeneration, the output should be:

```markdown
| Name | Type | Description |
|------|------|-------------|
| `name` | - | Element name... |
| `qualified_name` | - | Full path... |
| `description` | - | Main description... |
```

Which renders as a proper HTML table.

---

## Related Files

- `/bengal/autodoc/templates/macros/parameter_table.md.jinja2` ✅ FIXED
- All Python API templates using these macros (will be fixed on regeneration)

---

**Status:** Ready for testing via doc regeneration
