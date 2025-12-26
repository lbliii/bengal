# Safe Template Patterns Guide

**Audience:** Theme developers  
**Purpose:** Prevent common template errors and follow best practices  
**Last Updated:** 2025-12-23

---

## Quick Reference

| ❌ Old Pattern | ✅ New Pattern | Why |
|----------------|----------------|-----|
| `page.metadata.get('key')` | `params.key` | ParamsContext returns `''` for missing keys |
| `site.config.get('key')` | `config.key` | ConfigContext has safe dot access |
| `{% if x is defined %}` | `{% if x %}` | ChainableUndefined + finalize handles this |
| `site.data.resume.get('name')` | `site.data.resume.name` | DotDict returns `''` for missing keys |
| Raw dict in loop | `item \| safe_access` | Wrap for safe nested access |

---

## Pattern 1: Safe Context Access (New!)

### The Old Way (Deprecated)

Previously, templates needed defensive `.get()` calls everywhere:

```jinja2
❌ OLD PATTERN (no longer needed)
{{ page.metadata.get('description', '') }}
{{ params.get('author') }}
{{ config.get('baseurl') }}
```

### The New Way

Bengal's context wrappers (`ParamsContext`, `ConfigContext`, etc.) return empty string for missing keys:

```jinja2
✅ NEW PATTERN (clean and safe)
{{ params.description }}
{{ params.author }}
{{ config.baseurl }}
{{ theme.hero_style }}
{{ section.title }}
```

### Why This Works

1. **ParamsContext** wraps `params` (page.metadata) with safe access
2. **ConfigContext** wraps `config` (site.config) with safe access
3. **ThemeContext** wraps `theme` with safe access
4. **SectionContext** wraps `section` with safe access
5. **ChainableUndefined** + `finalize` converts remaining `None` → `''`

---

## Pattern 2: Safe Data File Access

### The Problem

Data loaded from `site.data` (YAML/JSON files) returns `DotDict` objects. Previously, missing keys needed `.get()`:

```jinja2
❌ OLD PATTERN
{% set resume = site.data.get('resume') %}
{{ resume.get('name', page.title) }}
{{ resume.get('contact', {}).get('email', '') }}
```

### The Solution

`DotDict` now returns `''` for missing keys (consistent with ParamsContext):

```jinja2
✅ NEW PATTERN (DotDict returns '' for missing)
{% set resume = site.data.resume %}
{{ resume.name or page.title }}
{{ resume.contact.email }}
```

### For Nested Loops

When looping over lists of dicts from data files, use `| safe_access` to wrap each item:

```jinja2
✅ SAFE NESTED ACCESS
{% for job in resume.experience %}
  {% set job = job | safe_access %}
  <h3>{{ job.title }}</h3>
  <p>{{ job.company }}</p>
  {% if job.location %}
    <span>{{ job.location }}</span>
  {% endif %}
{% endfor %}
```

---

## Pattern 3: Function Imports (Kida)

### Kida Functions Have Lexical Scoping

Kida functions (`{% def %}`) have true lexical scoping - they automatically access variables from their enclosing scope. **You do NOT need `with context`**:

```jinja2
✅ CORRECT (Kida)
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(page) }}
<!-- Function automatically has access to 'site', 'page', etc. via lexical scoping -->
```

### Why No `with context`?

Kida functions use `_outer_ctx` for closure access, so they:
- ✅ Automatically access globals (`site`, `theme`, filters, etc.)
- ✅ Automatically access outer scope variables
- ✅ Don't need `with context` (it's dead code from Jinja2)

### Legacy Jinja2 Pattern (Don't Use)

```jinja2
❌ OLD PATTERN (Jinja2 - not needed in Kida)
{% from 'partials/navigation-components.html' import breadcrumbs with context %}
<!-- 'with context' is unnecessary and can cause issues -->
```

---

## Pattern 4: Conditional Checks

### The Old Way

```jinja2
❌ OLD PATTERN (verbose)
{% if page.keywords is defined and page.keywords %}
  <meta name="keywords" content="{{ page.keywords | join(', ') }}">
{% endif %}
```

### The New Way

With ChainableUndefined and safe context wrappers, most checks can be simplified:

```jinja2
✅ NEW PATTERN (clean)
{% if page.keywords %}
  <meta name="keywords" content="{{ page.keywords | join(', ') }}">
{% endif %}
```

### Use Template Tests for Semantics

Bengal provides cleaner template tests for common checks:

```jinja2
✅ PREFERRED - Use template tests
{% if page is draft %}...{% endif %}
{% if page is featured %}...{% endif %}
{% if page is outdated %}...{% endif %}
{% if page is outdated(30) %}...{% endif %}

❌ VERBOSE - Old pattern
{% if page.draft is defined and page.draft %}...{% endif %}
```

---

## Pattern 5: Safe String Operations

### The Problem

User-generated content or metadata values might contain HTML or special characters:

```jinja2
❌ UNSAFE (XSS vulnerability)
<div>{{ params.user_bio | safe }}</div>
<!-- If user_bio contains <script>, it will execute -->
```

### The Solution

Use explicit escaping filters:

```jinja2
✅ SAFE (auto-escaped by default)
<div>{{ params.user_bio }}</div>
<!-- Jinja2 auto-escapes by default -->

✅ SAFE HTML (when trusted)
<div>{{ content }}</div>
<!-- content is pre-processed and marked safe -->
```

---

## Pattern 6: Loop Safety

### The Old Way

```jinja2
❌ OLD PATTERN (verbose)
{% if page.tags is defined and page.tags %}
  {% for tag in page.tags %}
    <a href="/tags/{{ tag }}">{{ tag }}</a>
  {% endfor %}
{% endif %}
```

### The New Way

```jinja2
✅ NEW PATTERN (cleaner)
{% if page.tags %}
  {% for tag in page.tags %}
    <a href="/tags/{{ tag }}">{{ tag }}</a>
  {% endfor %}
{% endif %}

✅ WITH ELSE BLOCK
{% for tag in page.tags %}
  <a href="/tags/{{ tag }}">{{ tag }}</a>
{% else %}
  <p>No tags</p>
{% endfor %}
```

---

## Pattern 7: URL Generation

### The Problem

Hardcoding URLs breaks when site moves or uses subpaths:

```jinja2
❌ HARDCODED
<a href="/docs/getting-started">Getting Started</a>
<img src="/assets/logo.png">
```

### The Solution

Use template functions for URL generation:

```jinja2
✅ DYNAMIC
<a href="{{ url_for(page) }}">{{ page.title }}</a>
<a href="{{ url_for_section('docs') }}">Documentation</a>

✅ ASSET URLs
<img src="{{ asset_url('logo.png') }}">
<link rel="stylesheet" href="{{ asset_url('css/main.css') }}">

✅ CANONICAL URLs
<link rel="canonical" href="{{ canonical_url(page) }}">
```

---

## Pattern 8: Template Inheritance

### The Problem

Child templates need to properly extend parents and override blocks:

```jinja2
❌ INCORRECT
{% extends "base.html" %}
<h1>My Content</h1>
<!-- Content outside blocks is ignored -->
```

### The Solution

Always put content in named blocks:

```jinja2
✅ CORRECT
{% extends "base.html" %}

{% block title %}My Page{% endblock %}

{% block content %}
  <h1>My Content</h1>
  <p>This will render properly.</p>
{% endblock %}

{% block extra_js %}
  {{ super() }}  {# Include parent block content #}
  <script src="/my-script.js"></script>
{% endblock %}
```

---

## Available Filters

### `safe_access`

Wraps a dict in `ParamsContext` for safe dot-notation access:

```jinja2
{% set resume = site.data.resume | safe_access %}
{{ resume.contact.email }}  {# Returns '' if missing #}

{# Useful for items in loops #}
{% for job in resume.experience %}
  {% set job = job | safe_access %}
  {{ job.title }}
{% endfor %}
```

---

## Error Prevention Checklist

Use this checklist when creating new templates:

- [ ] Use `params.x` instead of `page.metadata.get('x')`
- [ ] Use `config.x` instead of `site.config.get('x')`
- [ ] Use `| safe_access` for raw dicts from `site.data`
- [ ] All function imports do NOT use `with context` (Kida has lexical scoping)
- [ ] All URLs use template functions
- [ ] All blocks properly named in extends
- [ ] Template tested with minimal frontmatter
- [ ] Template tested with 404/special pages

---

## Testing Your Templates

### Manual Testing

1. **Test with minimal content:**
   ```markdown
   ---
   title: Test Page
   ---
   # Test
   ```

2. **Test special pages:** Visit `/404.html` and `/search/`

3. **Test in serve mode:**
   ```bash
   bengal site serve  # Catches template errors in dev
   ```

### Common Test Cases

```markdown
# Minimal page (test defaults)
---
title: Minimal Page
---

# Full page (test all features)
---
title: Full Page
description: Test description
author: Test Author
keywords: [test, example]
tags: [featured, important]
css_class: custom-page
draft: false
---
```

---

## Additional Resources

- **Jinja2 Documentation:** https://jinja.palletsprojects.com/
- **Template README:** `/themes/default/templates/README.md`
- **Component Examples:** `/themes/default/dev/components/`
- **Theme Documentation:** `/themes/default/README.md`

---

## Getting Help

If you encounter template errors:

1. **Check error message** - Enhanced messages show exact fix
2. **Review this guide** - Common patterns covered
3. **Test in serve mode** - Catches errors early
4. **Check examples** - Look at existing templates

**Questions?** Open an issue on GitHub or check the documentation.
