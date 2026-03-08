---
name: bengal-template-fix
description: Fixes common Bengal template errors and applies safe patterns. Use when templates fail with undefined variables, href vs path issues, baseurl, or config access.
---

# Bengal Template Fix

Fix common Bengal template errors and apply safe patterns for Kida/Jinja templates.

## Quick Reference

| Old Pattern | New Pattern | Why |
|-------------|-------------|-----|
| `page.metadata.get('key')` | `params.key` | ParamsContext returns `''` for missing keys |
| `site.config.get('key')` | `config.key` | ConfigContext has safe dot access |
| `{% if x is defined %}` | `{% if x %}` | ChainableUndefined handles this |
| `site.data.resume.get('name')` | `site.data.resume.name` | DotDict returns `''` for missing keys |
| Raw dict in loop | `item \| safe_access` | Wrap for safe nested access |

## href vs path (Baseurl Footgun)

**Critical**: Use `href` (includes baseurl) for link URLs, not `path` or `_path`. Using `_path` breaks GitHub Pages project sites.

| Use case | Prefer | Avoid |
|----------|--------|-------|
| Link URLs, `<a href="...">` | `href` | `path`, `_path` |
| Pagination base URLs | `href` | `path`, `_path` |
| Current-page checks | `_path` | `href` |
| Cache keys | `_path` | `href` |

```html
{# Correct - href first for links #}
<a href="{{ page.href ?? page._path }}">...</a>
<a href="{{ section.href ?? section._path }}">...</a>

{# Wrong - breaks on subpath deployments #}
<a href="{{ page._path ?? page.href }}">...</a>
```

## Safe Context Access

Use dot notation; context wrappers return `''` for missing keys:

```jinja2
{{ params.description }}
{{ params.author }}
{{ config.baseurl }}
{{ theme.hero_style }}
{{ section.title }}
```

## Safe Data File Access

`site.data` returns DotDict; use dot notation:

```jinja2
{% set resume = site.data.resume %}
{{ resume.name or page.title }}
{{ resume.contact.email }}
```

For loops over lists of dicts, wrap with `| safe_access`:

```jinja2
{% for job in resume.experience %}
  {% set job = job | safe_access %}
  <h3>{{ job.title }}</h3>
  <p>{{ job.company }}</p>
{% endfor %}
```

## Safe Iteration Over Frontmatter Collections

Tags and link collections can be malformed. Use guards:

```jinja2
{% let safe_tags = tags ?? [] %}
{% for tag in safe_tags %}
  {% if tag %}
  <a href="/tags/{{ tag }}">{{ tag }}</a>
  {% end %}
{% endfor %}
```

## Checklist

- [ ] Use `params.x` instead of `page.metadata.get('x')`
- [ ] Use `config.x` instead of `site.config.get('x')`
- [ ] Use `| safe_access` for raw dicts from `site.data`
- [ ] Links use `href ?? _path` (href first)
- [ ] Iterating over tags/link collections: use `?? []` and `{% if item %}`

## Additional Resources

See [references/SAFE_PATTERNS.md](references/SAFE_PATTERNS.md) for the full guide including URL generation, template inheritance, and Kida-specific patterns.
