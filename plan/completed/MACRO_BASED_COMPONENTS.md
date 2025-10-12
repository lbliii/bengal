# Macro-Based Components: The Ergonomic Solution

**Date:** 2025-10-12  
**Status:** ✅ Implemented

## The Problem

Using Jinja2 `{% include %}` for components is unergonomic and error-prone:

### ❌ Include-Based Pattern (OLD)
```jinja2
{# Have to set variables with exact names the include expects #}
{% set icon = '📦' %}
{% set title = page.title %}
{% set description = page.metadata.description %}
{% set type = 'api' %}
{% include 'partials/reference-header.html' %}
{# All these variables now pollute the parent scope! #}
```

**Problems:**
1. No explicit API - you have to read the include file to know what variables it needs
2. Typos cause silent failures (missing content, no errors)
3. Variable names are tightly coupled between caller and include
4. Scope pollution - variables leak into parent scope
5. No type safety or IDE support
6. Refactoring breaks all callers

## The Solution: Macros

Jinja2 macros are **designed for reusable components** and solve all these issues.

### ✅ Macro-Based Pattern (NEW)
```jinja2
{% from 'partials/components.html' import reference_header %}

{{ reference_header(
  icon='📦',
  title=page.title,
  description=page.metadata.description,
  type='api'
) }}
```

**Benefits:**
1. ✅ Explicit API - looks like a function call
2. ✅ Fails fast - errors if required parameters missing
3. ✅ Self-documenting - parameters are visible at call site
4. ✅ No scope pollution - parameters don't leak
5. ✅ Easy to refactor - change signature, get clear errors
6. ✅ Default values - optional parameters with defaults
7. ✅ IDE-friendly - can generate autocomplete
8. ✅ Easier to test - isolated components

## Implementation

### 1. Created Component Library

**File:** `bengal/themes/default/templates/partials/components.html`

Contains reusable macro-based components:

```jinja2
{% macro reference_header(icon, title, description=None, type='default') %}
<div class="reference-header">
  <span class="reference-icon">{{ icon }}</span>
  <h1>{{ title }}</h1>
</div>
{% if description %}
<p class="lead">{{ description }}</p>
{% endif %}
{% endmacro %}

{% macro reference_metadata(metadata, type='default') %}
{# ... #}
{% endmacro %}
```

### 2. Updated Templates

**Changed:**
- `bengal/themes/default/templates/api-reference/single.html`
- `bengal/themes/default/templates/cli-reference/single.html`

**Before:**
```jinja2
{% set icon = '📦' %}
{% set title = page.title %}
{% include 'partials/reference-header.html' %}
```

**After:**
```jinja2
{% from 'partials/components.html' import reference_header %}

{{ reference_header(icon='📦', title=page.title) }}
```

## Comparison with Other Systems

### Hugo (Go Templates)
```go
{{/* Pass context with dot */}}
{{ partial "header.html" . }}

{{/* Pass specific data */}}
{{ partial "header.html" (dict "icon" "📦" "title" .Title) }}
```

### 11ty (Nunjucks/Liquid)
```liquid
{# Nunjucks shortcodes #}
{% header icon="📦", title=page.title %}
```

### Jinja2 (Bengal)
```jinja2
{# Macro pattern #}
{{ reference_header(icon='📦', title=page.title) }}
```

**All provide explicit parameter passing!** Bengal's old include pattern was the outlier.

## Migration Guide

### For Theme Developers

**Old Include Pattern:**
```jinja2
{% set var1 = value1 %}
{% set var2 = value2 %}
{% include 'partials/component.html' %}
```

**New Macro Pattern:**
```jinja2
{% from 'partials/components.html' import component_name %}
{{ component_name(var1=value1, var2=value2) }}
```

### For Component Authors

**Old Include (partials/my-component.html):**
```jinja2
{# Expects: icon, title, description #}
<div>
  <span>{{ icon }}</span>
  <h1>{{ title }}</h1>
  <p>{{ description }}</p>
</div>
```

**New Macro (partials/components.html):**
```jinja2
{% macro my_component(icon, title, description=None) %}
<div>
  <span>{{ icon }}</span>
  <h1>{{ title }}</h1>
  {% if description %}
  <p>{{ description }}</p>
  {% endif %}
</div>
{% endmacro %}
```

## Available Components

### `reference_header(icon, title, description=None, type='default')`
Displays header for reference documentation pages.

**Example:**
```jinja2
{{ reference_header(
  icon='📦',
  title=page.title,
  description=page.metadata.description,
  type='api'
) }}
```

### `reference_metadata(metadata, type='default')`
Displays metadata box for reference documentation.

**Example:**
```jinja2
{{ reference_metadata({
  'Module': page.metadata.module_path,
  'Source': page.metadata.source_file
}) }}
```

### `breadcrumbs(items, separator='/')`
Displays breadcrumb navigation.

**Example:**
```jinja2
{{ breadcrumbs([
  {'name': 'Home', 'url': '/'},
  {'name': 'Docs', 'url': '/docs/'},
  {'name': page.title, 'url': page.url}
]) }}
```

## Why Macros Are Better Than Includes

| Feature | Includes | Macros |
|---------|----------|--------|
| **Explicit parameters** | ❌ Hidden | ✅ Visible |
| **Type safety** | ❌ None | ✅ Runtime checks |
| **Scope isolation** | ❌ Pollutes scope | ✅ Isolated |
| **Default values** | ❌ Manual | ✅ Built-in |
| **Error detection** | ❌ Silent fails | ✅ Fails fast |
| **Refactorability** | ❌ Breaks silently | ✅ Clear errors |
| **IDE support** | ❌ Poor | ✅ Better |
| **Readability** | ❌ Implicit | ✅ Self-documenting |
| **Testing** | ❌ Hard | ✅ Easier |

## Best Practices

### 1. Use Macros for Components
If it's reusable UI logic → **use a macro**

### 2. Use Includes for Layouts
If it's layout/structure composition → **use includes**

### 3. Document Parameters
Always document macro parameters:
```jinja2
{#
  My Component

  Args:
    required_param: Description
    optional_param: Description (default: 'value')

  Example:
    {{ my_component(required_param='foo') }}
#}
{% macro my_component(required_param, optional_param='default') %}
{# ... #}
{% endmacro %}
```

### 4. Use Meaningful Names
- Component name: `reference_header` not `header`
- Parameters: `icon` not `i` or `icn`

### 5. Provide Defaults
For optional parameters, provide sensible defaults:
```jinja2
{% macro component(required, optional=None, type='default') %}
```

## Testing

```bash
cd examples/showcase
bengal build --strict-mode
```

Should see:
- ✅ No undefined variable errors
- ✅ Proper headers with icons on API/CLI pages
- ✅ Clean, readable template code

## Next Steps

### Short Term
1. ✅ Convert reference documentation to macros
2. ⏳ Convert other common includes to macros (cards, buttons, etc.)
3. ⏳ Add more components to `partials/components.html`

### Medium Term
1. Create component documentation site
2. Add component playground/preview
3. Generate TypeScript types for template data

### Long Term
1. Build custom Jinja2 extension for component syntax:
   ```jinja2
   {% component 'ReferenceHeader' icon='📦' title=page.title %}
   ```
2. Add component hot-reload in dev server
3. Component validation and testing tools

## Files Changed

- ✅ Created `bengal/themes/default/templates/partials/components.html`
- ✅ Updated `bengal/themes/default/templates/api-reference/single.html`
- ✅ Updated `bengal/themes/default/templates/cli-reference/single.html`
- ✅ Updated `bengal/rendering/template_engine.py` (StrictUndefined)
- ✅ Fixed `bengal/themes/default/templates/partials/reference-header.html` (variable names)

## Summary

**Problem:** Include-based pattern is unergonomic and error-prone.

**Solution:** Switch to macro-based components with explicit parameters.

**Result:**
- Clearer code
- Better errors
- Easier refactoring
- More maintainable themes
- Matches patterns from Hugo, 11ty, and other SSGs

**The pattern is now:**
```jinja2
{% from 'partials/components.html' import reference_header %}
{{ reference_header(icon='📦', title=page.title) }}
```

**Not:**
```jinja2
{% set icon = '📦' %}
{% set title = page.title %}
{% include 'partials/reference-header.html' %}
```

Much better! 🎉
