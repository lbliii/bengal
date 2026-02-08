---
title: From Jinja2
nav_title: From Jinja2
description: Convert existing Jinja2 templates to Kida syntax
weight: 10
tags:
- how-to
- kida
- migration
---

# Migrate from Jinja2 to Kida

Learn how to convert existing Jinja2 templates to Kida syntax for unified block endings, pattern matching, and pipeline operators.

## Goal

Migrate your Jinja2 templates to Kida syntax while maintaining functionality.

## Prerequisites

- Existing Jinja2 templates
- Bengal site configured
- Understanding of template syntax

## Migration Strategy

### Phase 1: Compatibility Mode (Zero Changes)

Kida is Bengal's default engine and can parse Jinja2 syntax. Your existing Jinja2 templates work without changes.

:::{tip}
**Already using Kida**: Since Kida is the default engine, new Bengal sites already use Kida. Your Jinja2 templates work, but you can migrate to Kida syntax to use pattern matching, pipeline operators, and unified `{% end %}` blocks.
:::

### Phase 2: Gradual Migration

Migrate templates incrementally, starting with:
1. New templates (use Kida syntax)
2. Frequently-used templates (biggest performance gain)
3. Simple templates (easiest to migrate)
4. Complex templates (last)

## Syntax Changes

### Block Endings

**Jinja2**:
```jinja
{% if condition %}
  Content
{% endif %}

{% for item in items %}
  {{ item }}
{% endfor %}
```

**Kida**:
```kida
{% if condition %}
  Content
{% end %}

{% for item in items %}
  {{ item }}
{% end %}
```

**Migration**: Replace `{% endif %}`, `{% endfor %}`, `{% endblock %}`, etc. with `{% end %}`.

### Template Variables

**Jinja2**:
```jinja
{% set site_title = site.config.title %}
{# Available in current block only #}
```

**Kida**:
```kida
{% let site_title = site.config.title %}
{# Available throughout template #}
```

**Migration**: Replace `{% set %}` with `{% let %}` for template-wide variables. Keep `{% set %}` for block-scoped variables (variables that should only exist within a specific block).

**Scoping Differences**:
- `{% let %}`: Template-scoped (available throughout template)
- `{% set %}`: Block-scoped (only available within the block)
- `{% export %}`: Promotes variables from inner scopes to template scope

### Pattern Matching

**Jinja2**:
```jinja
{% if page.type == "blog" %}
  Blog post
{% elif page.type == "doc" %}
  Documentation
{% elif page.type == "tutorial" %}
  Tutorial
{% else %}
  Default
{% endif %}
```

**Kida**:
```kida
{% match page.type %}
  {% case "blog" %}
    Blog post
  {% case "doc" %}
    Documentation
  {% case "tutorial" %}
    Tutorial
  {% case _ %}
    Default
{% end %}
```

**Migration**: Replace long `if/elif` chains with `{% match %}...{% case %}`.

### Pipeline Operator

**Jinja2**:
```jinja
{{ items | selectattr('published') | sort(attribute='date') | first }}
```

**Kida** (Jinja2-compatible filters):
```kida
{{ items |> selectattr('published') |> sort(attribute='date') |> first }}
```

**Kida** (Bengal template functions - default):
```kida
{{ items |> where('published', true) |> sort_by('date') |> first }}
```

**Migration**:
- Replace `|` with `|>` for the pipeline operator
- Kida supports Jinja2 filters (`selectattr`, `sort`) for compatibility
- Bengal provides simpler alternatives (`where`, `sort_by`) that are recommended for new code

### Fallback Values

**Jinja2**:
```jinja
{{ items | default([]) | length }}
{{ name | default('Anonymous') | upper }}
```

**Kida** (simple fallbacks):
```kida
{{ user.name ?? 'Anonymous' }}
{{ config.timeout ?? 30 }}
```

**Kida** (fallbacks with filter chains):
```kida
{# Use | default() when applying filters after the fallback #}
{{ items | default([]) | length }}
{{ name | default('') | upper }}
```

:::{warning}
**Precedence gotcha**: The `??` operator has lower precedence than `|`, so filters bind to the fallback, not the result:

```kida
{# ❌ Parses as: items ?? ([] | length) — returns list, not length! #}
{{ items ?? [] | length }}

{# ✅ Correct: use | default() for filter chains #}
{{ items | default([]) | length }}
```
:::

**Migration**: Keep using `| default()` when you need to apply filters after the fallback. Use `??` for simple direct output.

### Fragment Caching

**Jinja2** (requires extension):
```jinja
{% cache "key" %}
  Expensive content
{% endcache %}
```

**Kida** (built-in):
```kida
{% cache "key" %}
  Expensive content
{% end %}
```

**Migration**: Replace `{% endcache %}` with `{% end %}`.

:::{note}
**Cache TTL**: Fragment cache TTL is configured at the environment level in `bengal.toml` (or `config/_default/`), not per-key. Set `kida.fragment_ttl` (in seconds) to control cache expiration for all fragments.
:::

## Step-by-Step Migration

### Step 1: Identify Template

Choose a template to migrate:

```bash
# List your templates
find templates/ -name "*.html"
```

### Step 2: Create Backup

```bash
# Backup original
cp templates/blog/single.html templates/blog/single.html.jinja2
```

### Step 3: Replace Block Endings

```bash
# Replace all block endings with {% end %}
sed -i 's/{% endif %}/{% end %}/g' templates/blog/single.html
sed -i 's/{% endfor %}/{% end %}/g' templates/blog/single.html
sed -i 's/{% endblock %}/{% endblock %}/g' templates/blog/single.html  # Keep endblock for compatibility
```

### Step 4: Replace Template Variables

Find `{% set %}` used for template-wide variables:

```kida
{# Before #}
{% set site_title = site.config.title %}

{# After #}
{% let site_title = site.config.title %}
```

### Step 5: Convert Pattern Matching

Find long `if/elif` chains:

```kida
{# Before #}
{% if page.type == "blog" %}
  Blog
{% elif page.type == "doc" %}
  Doc
{% else %}
  Default
{% endif %}

{# After #}
{% match page.type %}
  {% case "blog" %}
    Blog
  {% case "doc" %}
    Doc
  {% case _ %}
    Default
{% end %}
```

### Step 6: Update Filter Chains

Replace filter syntax (two options):

**Option 1: Keep Jinja2 filters, change operator**:
```kida
{# Before #}
{{ items | selectattr('published') | sort(attribute='date') }}

{# After (Jinja2-compatible) #}
{{ items |> selectattr('published') |> sort(attribute='date') }}
```

**Option 2: Use Bengal template functions (recommended)**:
```kida
{# Before #}
{{ items | selectattr('published') | sort(attribute='date') }}

{# After (Bengal functions) #}
{{ items |> where('published', true) |> sort_by('date') }}
```

### Step 7: Add Fragment Caching

Add caching to expensive operations:

```kida
{# Before #}
{% for post in expensive_calculation() %}
  {{ post.title }}
{% endfor %}

{# After #}
{% cache "posts-list" %}
  {% for post in expensive_calculation() %}
    {{ post.title }}
  {% end %}
{% end %}
```

### Step 8: Test

```bash
# Build and test
bengal build
bengal serve
```

## Functions vs Filters

Bengal distinguishes between **filters** (transform values) and **functions** (standalone operations).

**Jinja2** mixes both:
```jinja
{{ items | selectattr('published') }}  {# Filter #}
{{ range(10) }}                        {# Function #}
```

**Bengal** separates them:
```kida
{{ items |> where('published', true) }}  {# Filter #}
{{ get_page('path') }}                   {# Function #}
```

**When migrating:**
- Jinja2 filters → Bengal filters (use `|` or `|>`)
- Jinja2 functions → Bengal functions (direct call)

See [Functions vs Filters](/docs/reference/template-functions/#functions-vs-filters-understanding-the-difference) for complete explanation.

## Filter Name Mapping

Kida supports Jinja2 filters for compatibility, and Bengal provides additional template functions:

### Jinja2-Compatible Filters

Kida uses the same filter names as Jinja2. The main difference is the pipeline operator `|>` instead of `|`:

| Jinja2 Filter | Kida Filter | Notes |
|--------------|------------|-------|
| `selectattr('key')` | `selectattr('key')` | Same name, use `|>` operator |
| `selectattr('key', 'eq', val)` | `selectattr('key', 'eq', val)` | Same name, use `|>` operator |
| `sort(attribute='key')` | `sort(attribute='key')` | Same name, use `|>` operator |
| `sort(attribute='key', reverse=true)` | `sort(attribute='key', reverse=true)` | Same name, use `|>` operator |

### Bengal Template Functions (Recommended)

Bengal provides simpler alternatives that work with both `|` and `|>`:

| Jinja2 Filter | Bengal Function | Notes |
| --- | --- | --- |
| `selectattr('key', 'eq', val)` | `where('key', val)` | Simpler syntax, supports operators (`'eq'`, `'ne'`, `'gt'`, `'in'`, etc.) |
| `sort(attribute='key')` | `sort_by('key')` | Simpler syntax, supports `reverse=true` |
| `first(n)` | `take(n)` | Different name: use `take` instead of `first` |
| `last(n)` | `take(n) |> reverse` | Different name: use `take` with `reverse` |

:::{note}
**Template Functions**: `where`, `sort_by`, `take`, and other collection functions are Bengal template functions automatically available in all templates. They work with both `|` (Jinja2-style) and `|>` (Kida pipeline) operators.
:::

## Common Patterns

### Collection Filtering

**Jinja2**:
```jinja
{% set posts = site.pages | selectattr('type', 'eq', 'blog') | selectattr('draft', 'eq', false) | sort(attribute='date', reverse=true) %}
```

**Kida** (using Bengal template functions - default):
```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true) %}
```

**Kida** (using Jinja2-compatible filters):
```kida
{% let posts = site.pages
  |> selectattr('type', 'eq', 'blog')
  |> selectattr('draft', 'eq', false)
  |> sort(attribute='date', reverse=true) %}
```

### Conditional Rendering

**Jinja2**:
```jinja
{% if page.type == "blog" %}
  <article class="blog">{{ page.content | safe }}</article>
{% elif page.type == "doc" %}
  <article class="doc">{{ page.content | safe }}</article>
{% else %}
  <article>{{ page.content | safe }}</article>
{% endif %}
```

**Kida**:
```kida
{% match page.type %}
  {% case "blog" %}
    <article class="blog">{{ page.content | safe }}</article>
  {% case "doc" %}
    <article class="doc">{{ page.content | safe }}</article>
  {% case _ %}
    <article>{{ page.content | safe }}</article>
{% end %}
```

### Template Variables

**Jinja2**:
```jinja
{% set site_title = site.config.title %}
{% set nav_items = site.menus.main %}
```

**Kida**:
```kida
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}
```

## Migration Checklist

- [ ] Enable Kida in `bengal.toml`
- [ ] Test templates work in compatibility mode
- [ ] Replace `{% endif %}`, `{% endfor %}`, etc. with `{% end %}`
- [ ] Replace template-wide `{% set %}` with `{% let %}`
- [ ] Convert long `if/elif` chains to pattern matching
- [ ] Update filter chains to use `|>` and Kida filter names
- [ ] Add fragment caching where appropriate
- [ ] Test all templates
- [ ] Remove Jinja2 compatibility code

## Troubleshooting

### Validate Templates Before Building

Run template validation to catch syntax errors before a slow build:

```bash
# Validate all templates
bengal validate --templates

# Validate with migration hints
bengal validate --templates --fix

# Validate specific templates
bengal validate --templates --templates-pattern "autodoc/**/*.html"
```

### Template Not Found

```bash
# Check template lookup order
bengal build --verbose
```

### Filter Not Found

Kida uses different filter names. Check the [Kida Syntax Reference](/docs/reference/kida-syntax/) for available filters.

### Syntax Errors

Kida is stricter than Jinja2. Check:
- All blocks properly closed with `{% end %}`
- Variables defined before use
- Filter names match Kida syntax

## Common Migration Gotchas

### Macros Not Supported

Kida does not support Jinja2's `{% macro %}` syntax. Use `{% def %}` instead, which provides lexical scoping (functions can access outer variables).

**Jinja2** (not supported in Kida):
```jinja
{% macro hello(name) %}
  Hello {{ name }}
{% endmacro %}
{{ hello('World') }}
```

**Kida** (use `{% def %}` instead):
```kida
{% def hello(name) %}
  Hello {{ name }}
{% enddef %}
{{ hello('World') }}
```

**Key Difference**: `{% def %}` functions have access to outer template variables (like `site` and `config`), while Jinja2 macros are isolated. This means you don't need to pass common variables as parameters.

:::{note}
**Need full Jinja2 compatibility?** If your templates rely heavily on `{% macro %}`, you can use the Jinja2 engine by setting `template_engine: jinja2` in your `bengal.toml` config.
:::

### Include with Variables

Jinja2 allows passing variables directly in the include statement:

**Jinja2** (not supported in Kida):
```jinja
{% include 'partial.html' with param=value %}
```

**Kida** (set variables before include):
```kida
{% let param = value %}
{% include 'partial.html' %}
```

### Dict Key Access (Method Name Conflicts)

Python dict methods (`items`, `keys`, `values`, `get`) conflict with key access. Using dotted notation returns the method, not the key value.

**Problem**:
```kida
{# This returns the items() method, not the 'items' key! #}
{{ schema.items }}
```

**Solutions**:
```kida
{# Solution 1: Bracket notation #}
{{ schema['items'] }}

{# Solution 2: get() filter (cleaner syntax) #}
{{ schema | get('items') }}
{{ schema | get('items', default_value) }}
```

### Slice Filter Behavior

Kida's `slice` filter groups items (like Jinja2's slice), it doesn't do string slicing.

```kida
{# This groups items into 3 slices, not string slicing #}
{{ items | slice(3) }}

{# For string/list slicing, use Python slice syntax #}
{{ text[:5] }}
{{ items[1:4] }}
```

### Undefined Variables with Nil-Coalescing

In strict mode, use `??` to handle undefined variables safely:

```kida
{# May error if 'schemas' is undefined in strict mode #}
{% let schema = schemas[name] if schemas else none %}

{# Safe - ?? handles undefined #}
{% let schemas_dict = schemas ?? {} %}
{% let schema = schemas_dict | get(name) %}
```

## Complete Example

**Before (Jinja2)**:
```jinja
{% extends "baseof.html" %}

{% set site_title = site.config.title %}
{% set recent_posts = site.pages | selectattr('type', 'eq', 'blog') | selectattr('draft', 'eq', false) | sort(attribute='date', reverse=true) | slice(5) %}

{% block content %}
  {% if page.type == "blog" %}
    <article class="blog-post">
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% elif page.type == "doc" %}
    <article class="doc">
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% else %}
    <article>
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% endif %}
{% endblock %}
```

**After (Kida)**:
```kida
{% extends "baseof.html" %}

{% let site_title = site.config.title %}
{% let recent_posts = site.pages
  |> selectattr('type', 'eq', 'blog')
  |> selectattr('draft', 'eq', false)
  |> sort(attribute='date', reverse=true)
  |> take(5) %}

{% block content %}
  {% match page.type %}
    {% case "blog" %}
      <article class="blog-post">
        <h1>{{ page.title }}</h1>
        {{ page.content | safe }}
      </article>
    {% case "doc" %}
      <article class="doc">
        <h1>{{ page.title }}</h1>
        {{ page.content | safe }}
      </article>
    {% case _ %}
      <article>
        <h1>{{ page.title }}</h1>
        {{ page.content | safe }}
      </article>
  {% end %}
{% endblock %}
```

## Next Steps

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Kida Tutorial](/docs/tutorials/theming/getting-started-with-kida/) — Learn Kida from scratch
- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build new templates with Kida

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — Available filters and functions
- [Performance Guide](/docs/building/performance/) — Performance benefits of Kida
- [[ext:kida:docs/tutorials/migrate-from-jinja2|Kida Migration Guide]] — Standalone Kida migration documentation
:::
