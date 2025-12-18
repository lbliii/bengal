# Bengal Templates Guide

This directory contains Jinja2 templates for the Bengal default theme. This guide covers critical patterns for working with Bengal's templating system.

## Key Concepts

Bengal uses Jinja2 with **StrictUndefined** mode in development (`bengal serve`). This means accessing undefined variables or attributes raises errors rather than silently returning empty strings. This catches bugs early but requires careful template design.

---

## The Macro/Include Separation Pattern

### The Problem

When you use `{% from 'file.html' import macro_name %}`, Jinja2 executes **all top-level code** in that file, not just the macro definition. In StrictUndefined mode, this causes errors if the body code references variables that don't exist in the importing context.

```jinja
{# BAD: cards.html - mixes macro with body code #}
{% macro element_card(child) %}
  <div>{{ child.name }}</div>
{% endmacro %}

{# This body code runs during import! #}
{% if children %}  {# ERROR: 'children' is undefined #}
  {% for child in children %}
    {{ element_card(child) }}
  {% endfor %}
{% endif %}
```

When another template does `{% from 'cards.html' import element_card %}`, the `{% if children %}` line executes and fails because `children` doesn't exist in that context.

### The Solution: Separate Macros from Body Code

Split templates that need both macros AND body code into two files:

```
partials/
├── _macros/
│   └── element-card.html    # Pure macro file (safe to import)
└── cards.html               # Include-only file (uses the macro)
```

**Pure macro file** (`_macros/element-card.html`):
```jinja
{# Only macro definitions - no body code #}
{% macro element_card(child) %}
  <div>{{ child.name }}</div>
{% endmacro %}
```

**Include-only file** (`cards.html`):
```jinja
{% from 'partials/_macros/element-card.html' import element_card %}

{# Body code is safe here - this file is included, not imported #}
{% if children %}
  {% for child in children %}
    {{ element_card(child) }}
  {% endfor %}
{% endif %}
```

### When to Use Each Pattern

| Pattern | When to Use | How to Reference |
|---------|-------------|------------------|
| **Pure macro file** | Macro needs to be imported by multiple templates | `{% from '...' import macro %}` |
| **Include-only file** | Template renders content directly | `{% include '...' %}` |
| **Self-contained template** | Macro is only used within same file | Define macro inline |

---

## Safe Attribute Access with `getattr()`

### The Problem

DocElement objects from autodoc may have optional attributes. In StrictUndefined mode, accessing a missing attribute fails:

```jinja
{# BAD: Fails if element.children doesn't exist #}
{% for child in element.children %}
```

The common workaround `element.children or []` also fails because it still accesses the attribute first.

### The Solution: Use `getattr()`

Bengal exposes Python's `getattr()` as a Jinja2 global:

```jinja
{# GOOD: Safe access with default value #}
{% for child in getattr(element, 'children', []) %}

{# Also works for nested access #}
{% set params = getattr(element.metadata, 'parameters', []) %}
```

### When to Use `getattr()`

- Accessing attributes on DocElement objects (`element`, `child`, `method`, etc.)
- Any attribute that might not exist on all element types
- When iterating over optional collections

### When NOT Needed

- Accessing template variables you control (e.g., `{% set foo = 'bar' %}`)
- Using Jinja2's `default` filter on simple values: `{{ value | default('fallback') }}`
- Accessing dictionary keys with `.get()`: `{{ dict.get('key', 'default') }}`

---

## Template Organization

```
templates/
├── base.html                    # Base layout (extends nothing)
├── README.md                    # This file
│
├── partials/                    # Shared components
│   ├── _macros/                 # Pure macro files (safe to import)
│   ├── navigation-components.html  # Pure macros
│   ├── content-components.html     # Pure macros
│   └── page-hero-*.html            # Include-only (have body code)
│
├── autodoc/                     # Autodoc-specific templates
│   └── partials/
│       ├── _macros/             # Pure macro files
│       │   └── element-card.html
│       ├── header.html          # Include-only partials
│       ├── signature.html
│       └── cards.html           # Uses macro from _macros/
│
├── autodoc/python/               # Python API docs
│   ├── module.html
│   └── partials/
│       ├── _macros/
│       │   └── render-method.html
│       └── method-item.html
│
├── autodoc/cli/               # CLI docs
│   ├── command.html
│   └── command-group.html
│
└── openautodoc/python/           # OpenAPI docs
    └── endpoint.html
```

### Naming Conventions

- `_macros/` directories contain pure macro files (the underscore signals "internal")
- Files in `_macros/` should only define macros, never render content
- Files outside `_macros/` can be either include-only or pure macros

---

## Common Patterns

### Pattern 1: Iterating Over Optional Children

```jinja
{# Safe iteration over children #}
{% set element_children = getattr(element, 'children', []) %}
{% set methods = element_children | selectattr('element_type', 'eq', 'method') | list %}

{% for method in methods %}
  {{ render_method(method) }}
{% endfor %}
```

### Pattern 2: Conditional Sections Based on Children

```jinja
{% set options = getattr(element, 'children', []) | selectattr('element_type', 'eq', 'option') | list %}

{% if options %}
<section class="autodoc-section">
  <h2>Options</h2>
  {# ... render options ... #}
</section>
{% endif %}
```

### Pattern 3: Importing Macros for Use in Another Template

```jinja
{# Import from _macros/ directory - safe, no body code will execute #}
{% from 'autodoc/partials/_macros/element-card.html' import element_card %}

{# Now use the macro #}
{% for child in children %}
  {{ element_card(child) }}
{% endfor %}
```

### Pattern 4: Include-Only Template with Context

```jinja
{# In the parent template #}
{% set element = some_element %}
{% include 'autodoc/partials/header.html' %}

{# header.html expects 'element' to be defined in context #}
```

---

## Debugging Template Errors

### Error: `'X' is undefined`

1. **Check if you're importing a file with body code**
   - Look for `{% from 'file.html' import ... %}`
   - Check if `file.html` has code outside macros
   - Solution: Move macro to `_macros/` subdirectory

2. **Check if you're accessing an optional attribute**
   - Use `getattr(obj, 'attr', default)` instead of `obj.attr`

3. **Check if variable exists in context**
   - For include-only files, ensure parent sets needed variables
   - Use `{% if var is defined %}` guards if variable is truly optional

### Error: `'dict object' has no attribute 'X'`

- You're using dot notation on a dict that needs bracket notation
- Use `dict.get('key', default)` or `dict['key']`

### Error: `'DocElement object' has no attribute 'get'`

- You're using dict methods on a DocElement object
- Use direct attribute access: `element.name` not `element.get('name')`

---

## Testing Templates

Run `bengal serve` (not `bengal build`) to test templates with StrictUndefined mode enabled. This catches errors that would silently pass in production builds.

```bash
cd site
bengal s
```

Watch for warnings like:
```
● autodoc_template_render_failed  template=... error='X' is undefined
```

---

## Quick Reference

| Task | Pattern |
|------|---------|
| Import a macro | `{% from 'path/_macros/macro.html' import macro_name %}` |
| Include a partial | `{% include 'path/partial.html' %}` |
| Safe attribute access | `getattr(element, 'children', [])` |
| Filter with default | `element.description \| default('No description')` |
| Check if defined | `{% if var is defined and var %}` |
| Dict key with default | `dict.get('key', 'default')` |

---

## Further Reading

- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/)
- Bengal's `bengal/rendering/template_engine/environment.py` - Jinja2 environment setup
- Bengal's `bengal/autodoc/orchestration/template_env.py` - Autodoc-specific environment
