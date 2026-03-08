# Safe Template Patterns Guide

**Audience:** Theme developers  
**Purpose:** Prevent common template errors and follow best practices  
**Source:** `bengal/themes/default/templates/SAFE_PATTERNS.md`

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

## Pattern 1: Safe Context Access

Bengal's context wrappers return empty string for missing keys:

```jinja2
{{ params.description }}
{{ params.author }}
{{ config.baseurl }}
{{ theme.hero_style }}
{{ section.title }}
```

## Pattern 2: Safe Data File Access

```jinja2
{% set resume = site.data.resume %}
{{ resume.name or page.title }}
{{ resume.contact.email }}
```

For nested loops: `{% set job = job | safe_access %}`

## Pattern 3: href vs path

- **Links**: `href ?? _path` (href first) — `_path` breaks GitHub Pages subpaths
- **Internal logic** (cache keys, current-page checks): `_path` is fine

## Pattern 4: URL Generation

Use template functions, not hardcoded paths:

```jinja2
<a href="{{ url_for(page) }}">{{ page.title }}</a>
<a href="{{ url_for_section('docs') }}">Documentation</a>
<img src="{{ asset_url('logo.png') }}">
```

## Pattern 5: Template Inheritance

Content must be in named blocks:

```jinja2
{% extends "base.html" %}
{% block title %}My Page{% endblock %}
{% block content %}
  <h1>My Content</h1>
{% endblock %}
```

## Pattern 6: Kida-Specific

- No `with context` on imports — Kida has lexical scoping
- Pipeline operator: `{{ items |> map('upper') |> join(', ') }}`
- Pattern matching: `{% match page.type %}{% case "blog" %}...{% end %}`

---

Sync with source: `bengal/themes/default/templates/SAFE_PATTERNS.md`
