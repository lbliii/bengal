---
title: Automatic Block Caching
nav_title: Automatic Caching
description: How Kida automatically caches site-scoped template blocks
weight: 10
tags:
- explanation
- kida
- caching
- performance
---

# Automatic Block Caching

Kida's template engine automatically detects which parts of your templates can be cached site-wide, rendering them **once per build** instead of once per page. This analysis happens at compile time using template introspection, requiring no changes to your template syntax.

## How It Works

Kida uses **template introspection** to analyze blocks at compile time:

1. **What variables does this block depend on?** (page-specific or site-wide)
2. **Is this block deterministic?** (pure vs impure)

Based on this analysis, each block is assigned a **cache scope**:

| Cache Scope | Meaning | Example |
|-------------|---------|---------|
| `site` | Rendered once, reused for all pages | Footer, navigation, header |
| `page` | Rendered per-page (depends on page data) | Content, title, meta tags |
| `none` | Cannot be cached (uses impure functions) | Random quotes widget |
| `unknown` | Analysis couldn't determine | Blocks with `{% include %}` |

## Writing Cacheable Blocks

### Use Site-Scoped Variables

```kida
{% block site_footer %}
    {% let _title = config.title %}
    {% let _menu = get_menu_lang('footer', current_lang()) %}

    <footer>
        <p>&copy; {{ site.build_time | dateformat('%Y') }} {{ _title }}</p>
        {% for item in _menu %}
            <a href="{{ item.href | absolute_url }}">{{ item.name }}</a>
        {% end %}
    </footer>
{% end %}
```

**Site-scoped variables include:**
- `site.*` — Site configuration and metadata
- `config.*` — Site configuration values

**Note**: `theme.*` and `bengal.*` are available in templates and are site-level, but the analyzer may not automatically recognize them as site-scoped. For best cacheability, prefer `site.*` and `config.*` when possible.

### Avoid Page-Specific Variables

```kida
{% block site_footer %}
    {# ❌ page.* makes this page-scoped, not site-scoped #}
    <footer>
        <p>You're reading: {{ page.title }}</p>
    </footer>
{% end %}
```

**Page-scoped variables that prevent site caching:**
- `page.*` — Current page data
- `params.*` — Page frontmatter parameters
- `post.*`, `doc.*`, `entry.*` — Content item aliases

### Use Pure Functions

These functions return consistent values for a given build:

```kida
{% block site_nav %}
    {% let _lang = current_lang() %}
    {% let _menu = get_menu_lang('main', _lang) %}

    <nav>
        {% for item in _menu %}
            <a href="{{ item.href | absolute_url }}">{{ item.name }}</a>
        {% end %}
    </nav>
{% end %}
```

**Pure functions recognized by Bengal:**
- `current_lang()` — Current language code
- `get_menu_lang(name, lang)` — Get menu for language
- `get_menu(name)` — Get menu by name
- `t(key, default=...)` — Translation strings
- `asset_url(path)` — Asset URL with fingerprint
- `icon(name)` — Icon helper

### Avoid Impure Functions

```kida
{% block random_quote %}
    {# ❌ shuffle is impure - different result each time #}
    {% let quote = quotes | shuffle | first %}
    <blockquote>{{ quote }}</blockquote>
{% end %}
```

**Impure filters that prevent caching:**
- `random` — Random selection
- `shuffle` — Random ordering

### Avoid `{% include %}`

`{% include %}` returns "unknown" purity because the analyzer can't see inside:

```kida
{# ❌ include makes this block's purity unknown #}
{% block site_footer %}
    {% include 'partials/footer.html' %}
{% end %}

{# ✅ Inlined content can be analyzed #}
{% block site_footer %}
    <footer>
        <p>&copy; {{ site.build_time | dateformat('%Y') }} {{ config.title }}</p>
    </footer>
{% end %}
```

## Real-World Examples

### Footer Block

```kida
{% block site_footer %}
    {% let _footer_lang = current_lang() %}
    {% let _footer_title = config.title %}
    {% let _footer_menu = get_menu_lang('footer', _footer_lang) %}
    {% let _footer_badge = site.build_badge %}

    <footer role="contentinfo">
        <div class="container">
            <p class="footer-copyright">
                &copy; {{ site.build_time | dateformat('%Y') }} {{ _footer_title }}
            </p>
            {% if _footer_menu %}
            <ul class="footer-links">
                {% for item in _footer_menu %}
                <li><a href="{{ item.href | absolute_url }}">{{ item.name }}</a></li>
                {% end %}
            </ul>
            {% end %}
        </div>
    </footer>
{% end %}
```

### Scripts Block

```kida
{% block site_scripts %}
{% let _scripts_bundle_js = config.assets.bundle_js ?? false %}
{% let _scripts_build_badge = site.build_badge %}

{% if _scripts_bundle_js %}
<script defer src="{{ asset_url('js/bundle.js') }}"></script>
{% else %}
<script defer src="{{ asset_url('js/utils.js') }}"></script>
<script defer src="{{ asset_url('js/main.js') }}"></script>
{% if _scripts_build_badge.enabled %}
<script defer src="{{ asset_url('js/core/build-badge.js') }}"></script>
{% end %}
{% end %}
{% end %}
```

## Verifying Cacheability

### Build Output

Bengal tracks block cache statistics during builds. Block cache metrics are included in build statistics and can be viewed in the build summary. The cache automatically identifies and caches site-scoped blocks during the rendering phase.

### Programmatic Verification

To check which blocks are cached and their cache scope, use the template introspection API:

```python
from bengal.rendering.kida import Environment

env = Environment(preserve_ast=True)
template = env.get_template("base.html")
meta = template.template_metadata()

if meta:
    for block_name, block_meta in meta.blocks.items():
        print(f"{block_name}: {block_meta.cache_scope}")
        # Output examples:
        # site_footer: site    (cached site-wide)
        # site_nav: site        (cached site-wide)
        # content: page         (rendered per-page)
```

The `cache_scope` field indicates:
- `"site"` — Block is cached site-wide (rendered once per build, reused across all pages)
- `"page"` — Block is page-specific (rendered per page, not cached site-wide)
- `"none"` — Block cannot be cached (uses impure functions like `random` or `shuffle`)
- `"unknown"` — Analysis couldn't determine (e.g., uses `{% include %}` with unknown dependencies)

## Summary

| Pattern | Result |
|---------|--------|
| Block with only `site.*`, `config.*` | ✅ Site-cacheable |
| Uses pure functions like `current_lang()` | ✅ Site-cacheable |
| Uses pure filters like `dateformat` | ✅ Site-cacheable |
| References `page.*` or `params.*` | ❌ Page-scoped |
| Uses `{% include %}` | ❌ Unknown purity |
| Uses `random` or `shuffle` | ❌ Impure, not cacheable |
