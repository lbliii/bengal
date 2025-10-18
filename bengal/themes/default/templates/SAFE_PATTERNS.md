# Safe Template Patterns Guide

**Audience:** Theme developers  
**Purpose:** Prevent common template errors and follow best practices  
**Last Updated:** 2025-10-12

---

## Quick Reference

| ❌ Unsafe Pattern | ✅ Safe Pattern | Why |
|-------------------|-----------------|-----|
| `page.metadata.key` | `page.metadata.get('key')` | Dict key might not exist |
| `site.config.key` | `site.config.get('key')` | Config value might be missing |
| `{% from '...' import macro %}` | `{% from '...' import macro with context %}` | Macro needs access to `site`, `page` |
| `{% if page.keywords %}` | `{% if page.keywords is defined and page.keywords %}` | Attribute might not exist on SimpleNamespace |
| `{{ value }}` (untrusted) | `{{ value \| e }}` or `{{ value \| escape }}` | Prevent XSS attacks |

---

## Pattern 1: Safe Dictionary Access

### The Problem

Templates receive dictionaries like `page.metadata` and `site.config`. Using dot notation on missing keys causes `UndefinedError` in strict mode:

```jinja2
❌ UNSAFE
{{ page.metadata.description }}
<!-- Error if 'description' key doesn't exist -->
```

### The Solution

Use `.get()` method with optional default value:

```jinja2
✅ SAFE
{{ page.metadata.get('description', '') }}
<!-- Returns empty string if key missing -->

✅ SAFE with default
{{ page.metadata.get('author', 'Anonymous') }}
<!-- Returns 'Anonymous' if key missing -->

✅ SAFE in conditionals
{% if page.metadata.get('featured') %}
  <span class="badge">Featured</span>
{% endif %}
```

### Common Locations

Apply this pattern to:
- `page.metadata.*` - All frontmatter fields
- `site.config.*` - All configuration values
- `section.metadata.*` - Section-level metadata
- `subsection.metadata.*` - Subsection metadata

### Examples

```jinja2
{# Metadata access #}
<article class="{{ page.metadata.get('css_class', '') }}">
  <h1>{{ page.title }}</h1>

  {% if page.metadata.get('description') %}
    <p class="lead">{{ page.metadata.get('description') }}</p>
  {% endif %}

  {% if page.metadata.get('author') %}
    <span class="author">By {{ page.metadata.get('author') }}</span>
  {% endif %}
</article>

{# Config access #}
{% if site.config.get('og_image') %}
  <meta property="og:image" content="{{ og_image(site.config.get('og_image')) }}">
{% endif %}

{% if site.config.get('github_edit_base') %}
  <a href="{{ site.config.get('github_edit_base') }}{{ page.source_path }}">
    Edit this page
  </a>
{% endif %}
```

---

## Pattern 2: Macro Imports with Context

### The Problem

Macros imported without `with context` cannot access template variables like `site` and `page`:

```jinja2
❌ UNSAFE
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(page) }}
<!-- Macro can't access 'site' inside, causes UndefinedError -->
```

### The Solution

Add `with context` to macro imports:

```jinja2
✅ SAFE
{% from 'partials/navigation-components.html' import breadcrumbs with context %}
{{ breadcrumbs(page) }}
<!-- Macro now has access to full template context -->
```

### When to Use

Always use `with context` when importing macros that:
- Access `site` for configuration or site-wide data
- Use template functions like `url_for()`, `og_image()`, etc.
- Need access to current page context

### Examples

```jinja2
{# Navigation macros #}
{% from 'partials/navigation-components.html' import breadcrumbs, page_navigation with context %}

{# Content macros #}
{% from 'partials/content-components.html' import tag_list, random_posts with context %}

{# Reference macros #}
{% from 'partials/reference-components.html' import reference_header, reference_metadata with context %}
```

---

## Pattern 3: Safe Attribute Checks

### The Problem

Not all page objects have all attributes. Special pages (404, search) use `SimpleNamespace` with minimal attributes:

```jinja2
❌ UNSAFE
{% if page.keywords %}
  <!-- Error if 'keywords' attribute doesn't exist -->
{% endif %}
```

### The Solution

Use `is defined` check before accessing:

```jinja2
✅ SAFE
{% if page.keywords is defined and page.keywords %}
  <meta name="keywords" content="{{ page.keywords | join(', ') }}">
{% endif %}

✅ SAFE with fallback
{% if page.keywords is defined and page.keywords %}
  {% set meta_keywords = page.keywords %}
{% elif page.tags is defined and page.tags %}
  {% set meta_keywords = page.tags %}
{% endif %}
```

### Common Attributes to Check

- `page.keywords` - May not exist on special pages
- `page.tags` - May not exist on all page types
- `page.kind` - Usually exists but check in filters
- `page.draft` - May not exist on generated pages

### Examples

```jinja2
{# Keywords with fallback to tags #}
{% if page.keywords is defined and page.keywords %}
  <meta name="keywords" content="{{ page.keywords | join(', ') }}">
{% elif page.tags is defined and page.tags %}
  <meta name="keywords" content="{{ page.tags | meta_keywords(10) }}">
{% endif %}

{# Body classes #}
<body class="page-kind-{{ page.kind if page.kind is defined else 'page' }}
             {% if page.draft is defined and page.draft %}draft-page{% endif %}">

{# Conditional rendering #}
{% if page.tags is defined and (page | has_tag('featured')) %}
  <span class="badge">Featured</span>
{% endif %}
```

---

## Pattern 4: Safe String Operations

### The Problem

User-generated content or metadata values might contain HTML or special characters:

```jinja2
❌ UNSAFE (XSS vulnerability)
<div>{{ page.metadata.get('user_bio') }}</div>
<!-- If user_bio contains <script>, it will execute -->
```

### The Solution

Use explicit escaping filters:

```jinja2
✅ SAFE (auto-escaped in Jinja2)
<div>{{ page.metadata.get('user_bio') }}</div>
<!-- Jinja2 auto-escapes by default -->

✅ EXPLICIT escape
<div>{{ page.metadata.get('user_bio') | e }}</div>
<!-- Explicitly escape HTML -->

✅ SAFE HTML (when trusted)
<div>{{ page.content | safe }}</div>
<!-- Only use 'safe' for trusted, processed content -->
```

### When to Escape

- **Auto-escaped by default:** Most template output
- **Explicitly escape:** User input, external data
- **Mark as safe:** Pre-processed content (like `page.content`)

### Examples

```jinja2
{# Auto-escaped #}
<h1>{{ page.title }}</h1>
<meta name="description" content="{{ page.metadata.get('description', '') }}">

{# Trusted HTML #}
<div class="content">
  {{ page.content | safe }}
</div>

{# Explicitly escaped user data #}
<div class="user-comment">
  {{ comment.text | e }}
</div>

{# JSON encoding #}
<script>
  const pageData = {{ page_json | tojson }};
</script>
```

---

## Pattern 5: Loop Safety

### The Problem

Looping over collections that might be empty or undefined:

```jinja2
❌ UNSAFE
{% for tag in page.tags %}
  <!-- Error if page.tags is undefined -->
{% endfor %}
```

### The Solution

Check before looping or use default empty list:

```jinja2
✅ SAFE with check
{% if page.tags is defined and page.tags %}
  {% for tag in page.tags %}
    <a href="/tags/{{ tag }}">{{ tag }}</a>
  {% endfor %}
{% endif %}

✅ SAFE with default
{% for tag in (page.tags if page.tags is defined else []) %}
  <a href="/tags/{{ tag }}">{{ tag }}</a>
{% else %}
  <p>No tags</p>
{% endfor %}

✅ SAFE with length check
{% if page.tags is defined and page.tags | length > 0 %}
  <ul>
    {% for tag in page.tags %}
      <li>{{ tag }}</li>
    {% endfor %}
  </ul>
{% endif %}
```

---

## Pattern 6: Template Inheritance

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

### Common Blocks

Default theme provides these blocks:
- `title` - Page title
- `meta_tags` - Additional meta tags
- `extra_css` - Additional stylesheets
- `content` - Main content area
- `extra_js` - Additional scripts

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

## Error Prevention Checklist

Use this checklist when creating new templates:

- [ ] All `page.metadata.*` uses `.get()`
- [ ] All `site.config.*` uses `.get()`
- [ ] All macro imports have `with context`
- [ ] All attribute checks use `is defined`
- [ ] All loops check for empty/undefined
- [ ] All user content properly escaped
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

3. **Test in strict mode:**
   ```bash
   bengal site serve  # Strict mode enabled by default
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

# Empty metadata (test safety)
---
title: Empty Metadata Page
description: ""
author:
tags: []
---
```

---

## Strict Mode

### What is Strict Mode?

Strict mode makes Jinja2 raise errors on undefined variables instead of silently rendering empty strings.

### When is Strict Mode Enabled?

- ✅ **Always in `bengal site serve`** (auto-enabled for development)
- ⚠️ **Optional in `bengal site build`** (use `--strict` flag)

### Why Use Strict Mode?

```jinja2
# Without strict mode (silent failures)
{{ page.metadata.typo }}  
<!-- Renders as empty string, hard to debug -->

# With strict mode (explicit errors)
{{ page.metadata.typo }}
<!-- UndefinedError: 'dict object' has no attribute 'typo' -->
```

### Recommended Workflow

```bash
# Development (always strict)
bengal site serve

# Production build (optional strict)
bengal site build          # Lenient (renders as empty)
bengal site build --strict # Strict (fails on errors)

# CI/CD (recommended)
bengal site build --strict # Catch template errors early
```

---

## Enhanced Error Messages

Bengal provides enhanced error messages in strict mode:

### Dict Access Errors

```
❌ UndefinedError: 'dict object' has no attribute 'og_image'

💡 Suggestions:
   [red bold]Unsafe dict access detected![/red bold]
   Replace dict.og_image with dict.get('og_image')
   Common locations: page.metadata, site.config, section.metadata

   Note: This error only appears in strict mode (serve).
   Use 'bengal site build --strict' to catch in builds.
```

### Attribute Errors

```
❌ UndefinedError: 'keywords' is undefined

💡 Suggestions:
   Use safe access: {{ page.keywords | default([]) }}
   Or check first: {% if page.keywords is defined %}
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
3. **Test in serve mode** - Strict mode catches errors early
4. **Check examples** - Look at existing templates

**Questions?** Open an issue on GitHub or check the documentation.
