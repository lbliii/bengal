---
title: Migrate from Jinja2 to KIDA
nav_title: Migrate from Jinja2
description: Convert existing Jinja2 templates to KIDA syntax
weight: 50
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
- migration
keywords:
- jinja2 migration
- kida migration
- template migration
category: guide
---

# Migrate from Jinja2 to KIDA

Learn how to convert existing Jinja2 templates to KIDA syntax for better performance and modern features.

## Goal

Migrate your Jinja2 templates to KIDA syntax while maintaining functionality and unlocking performance benefits.

## Prerequisites

- Existing Jinja2 templates
- Bengal site configured
- Understanding of template syntax

## Migration Strategy

### Phase 1: Compatibility Mode (Zero Changes)

KIDA is Bengal's default engine and can parse Jinja2 syntax. Your existing Jinja2 templates work without changes.

:::{tip}
**Already using KIDA**: Since KIDA is the default engine, new Bengal sites already use KIDA. Your Jinja2 templates work, but you can migrate to KIDA syntax to unlock additional features and performance.
:::

### Phase 2: Gradual Migration

Migrate templates incrementally, starting with:
1. New templates (use KIDA syntax)
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

**KIDA**:
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

**KIDA**:
```kida
{% let site_title = site.config.title %}
{# Available throughout template #}
```

**Migration**: Replace `{% set %}` with `{% let %}` for template-wide variables. Keep `{% set %}` for block-scoped variables.

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

**KIDA**:
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

**KIDA**:
```kida
{{ items |> where('published', true) |> sort_by('date') |> first }}
```

**Migration**: Replace `|` with `|>` and use KIDA filter names (`where` instead of `selectattr`, `sort_by` instead of `sort`).

### Fallback Values

**Jinja2**:
```jinja
{{ items | default([]) | length }}
{{ name | default('Anonymous') | upper }}
```

**KIDA** (simple fallbacks):
```kida
{{ user.name ?? 'Anonymous' }}
{{ config.timeout ?? 30 }}
```

**KIDA** (fallbacks with filter chains):
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

**KIDA** (built-in):
```kida
{% cache "key" %}
  Expensive content
{% end %}
```

**Migration**: Replace `{% endcache %}` with `{% end %}`. Add TTL support: `{% cache "key", ttl="5m" %}`.

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

Replace filter syntax:

```kida
{# Before #}
{{ items | selectattr('published') | sort(attribute='date') }}

{# After #}
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

## Filter Name Mapping

| Jinja2 Filter | KIDA Filter | Notes |
|--------------|------------|-------|
| `selectattr('key')` | `where('key', true)` | Boolean check |
| `selectattr('key', 'eq', val)` | `where('key', val)` | Equality |
| `sort(attribute='key')` | `sort_by('key')` | Sort ascending |
| `sort(attribute='key', reverse=true)` | `sort_by('key', reverse=true)` | Sort descending |
| `first(n)` | `take(n)` | Get first n items |
| `last(n)` | `take(n) |> reverse` | Get last n items |

## Common Patterns

### Collection Filtering

**Jinja2**:
```jinja
{% set posts = site.pages | selectattr('type', 'eq', 'blog') | selectattr('draft', 'eq', false) | sort(attribute='date', reverse=true) %}
```

**KIDA**:
```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true) %}
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

**KIDA**:
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

**KIDA**:
```kida
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}
```

## Migration Checklist

- [ ] Enable KIDA in `bengal.yaml`
- [ ] Test templates work in compatibility mode
- [ ] Replace `{% endif %}`, `{% endfor %}`, etc. with `{% end %}`
- [ ] Replace template-wide `{% set %}` with `{% let %}`
- [ ] Convert long `if/elif` chains to pattern matching
- [ ] Update filter chains to use `|>` and KIDA filter names
- [ ] Add fragment caching where appropriate
- [ ] Test all templates
- [ ] Remove Jinja2 compatibility code

## Troubleshooting

### Template Not Found

```bash
# Check template lookup order
bengal build --verbose
```

### Filter Not Found

KIDA uses different filter names. Check the [KIDA Syntax Reference](/docs/reference/kida-syntax/) for available filters.

### Syntax Errors

KIDA is stricter than Jinja2. Check:
- All blocks properly closed with `{% end %}`
- Variables defined before use
- Filter names match KIDA syntax

## Complete Example

**Before (Jinja2)**:
```jinja
{% extends "baseof.html" %}

{% set site_title = site.config.title %}
{% set recent_posts = site.pages | selectattr('type', 'eq', 'blog') | selectattr('draft', 'eq', false) | sort(attribute='date', reverse=true) | first(5) %}

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

**After (KIDA)**:
```kida
{% extends "baseof.html" %}

{% let site_title = site.config.title %}
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
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

- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn KIDA from scratch
- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build new templates with KIDA

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — Available filters and functions
- [Performance Guide](/docs/building/performance/) — Performance benefits of KIDA
:::
