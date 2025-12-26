---
title: Creating Cacheable Template Blocks
description: How to write template blocks that are automatically cached and reused across all pages
weight: 50
---

# Creating Cacheable Template Blocks

Bengal's Kida template engine can automatically detect which parts of your templates can be cached site-wide, rendering them **once per build** instead of once per page. For a 500-page site, this means your footer is rendered 1 time instead of 500.

## How It Works

Kida uses **template introspection** to analyze your template blocks at compile time. It determines:

1. **What variables does this block depend on?** (page-specific or site-wide)
2. **Is this block deterministic?** (pure vs impure)

Based on this analysis, each block is assigned a **cache scope**:

| Cache Scope | Meaning | Example |
|-------------|---------|---------|
| `site` | Rendered once, reused for all pages | Footer, navigation, header |
| `page` | Rendered per-page (depends on page data) | Content, title, meta tags |
| `none` | Cannot be cached (uses random/impure functions) | Random quotes widget |
| `unknown` | Analysis couldn't determine | Blocks with `{% include %}` |

## The Cacheable Block Pattern

To create a site-cacheable block, follow these rules:

### ✅ DO: Use Only Site-Scoped Variables

```jinja
{% block site_footer %}
    {# ✅ These are all site-scoped #}
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
- `theme.*` — Theme settings
- `bengal.*` — Build-time capabilities

### ❌ DON'T: Reference Page-Specific Variables

```jinja
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

### ✅ DO: Use Known Pure Functions

These functions return consistent values for a given build:

```jinja
{% block site_nav %}
    {% let _lang = current_lang() %}
    {% let _menu = get_menu_lang('main', _lang) %}
    {% let _auto = get_auto_nav() %}

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
- `get_auto_nav()` — Auto-discovered navigation
- `t(key, default=...)` — Translation strings
- `asset_url(path)` — Asset URL with fingerprint
- `absolute_url(path)` — Absolute URL
- `canonical_url(path)` — Canonical URL
- `icon(name)` — Icon helper
- `alternate_links(page)` — Hreflang alternates

### ✅ DO: Use Known Pure Filters

```jinja
{% block site_footer %}
    <p>&copy; {{ site.build_time | dateformat('%Y') }}</p>
    <a href="{{ '/about/' | absolute_url }}">About</a>
{% end %}
```

**Pure filters recognized by Bengal:**
- `dateformat`, `date_iso`, `date` — Date formatting
- `absolute_url`, `relative_url` — URL transformation
- `upper`, `lower`, `title`, `capitalize` — String case
- `join`, `first`, `last`, `sort` — List operations
- `default`, `truncate`, `escape` — Common utilities

### ❌ DON'T: Use {% include %} in Cacheable Blocks

`{% include %}` returns "unknown" purity because the analyzer can't see inside the included template:

```jinja
{% block site_footer %}
    {# ❌ include makes this block's purity "unknown" #}
    {% include 'partials/footer.html' %}
{% end %}
```

**Instead, inline the content:**

```jinja
{% block site_footer %}
    {# ✅ Inlined content can be analyzed #}
    <footer>
        <p>&copy; {{ site.build_time | dateformat('%Y') }} {{ config.title }}</p>
    </footer>
{% end %}
```

### ❌ DON'T: Use Impure Filters

```jinja
{% block random_quote %}
    {# ❌ shuffle is impure - different result each time #}
    {% let quote = quotes | shuffle | first %}
    <blockquote>{{ quote }}</blockquote>
{% end %}
```

**Impure filters that prevent caching:**
- `random` — Random selection
- `shuffle` — Random ordering

## Real-World Examples from Bengal's Default Theme

Bengal's default theme uses four site-cacheable blocks. Here are the patterns:

```jinja
{# Footer - Site-Scoped Block #}
{# Only depends on site.*, config.*, and pure functions #}
{% block site_footer %}
    {% let _footer_lang = current_lang() %}
    {% let _footer_title = config.title %}
    {% let _footer_menu = get_menu_lang('footer', _footer_lang) %}
    {% let _footer_badge = site.build_badge %}

    <footer role="contentinfo">
        <div class="container">
            <div class="footer-bottom">
                <div class="footer-left">
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
                <div class="footer-right">
                    {% if _footer_badge.enabled %}
                    <a class="build-badge" href="#">
                        <span>{{ _footer_badge.label }}</span>
                    </a>
                    {% end %}
                </div>
            </div>
        </div>
    </footer>
{% end %}
```

This block:
- Uses `{% let %}` to cache function calls
- Only references `site.*` and `config.*`
- Uses pure functions: `current_lang()`, `get_menu_lang()`
- Uses pure filters: `dateformat()`, `absolute_url()`
- **Result**: Rendered once, reused for all pages

### Example 2: Search Modal

```jinja
{% block site_search_modal %}
{% let _search_config = config.search %}
{% let _ui_config = _search_config.ui %}
{% let _modal_enabled = _ui_config.modal ?? false %}

{% if _modal_enabled %}
<dialog id="search-modal" class="search-modal"
  aria-label="{{ t('search.aria_label', default='Search documentation') }}">
  <header class="search-modal__header">
    {{ icon('magnifying-glass', size=20) }}
    <input type="search" id="search-modal-input"
      placeholder="{{ _ui_config.placeholder | default(t('search.placeholder', default='Search...')) }}">
  </header>
  <footer class="search-modal__footer">
    <kbd>↑</kbd><kbd>↓</kbd> {{ t('search.hint_navigate', default='Navigate') }}
    <kbd>ESC</kbd> {{ t('search.hint_close', default='Close') }}
  </footer>
</dialog>
{% end %}
{% end %}
```

This block uses:
- `config.search.*` for configuration (site-scoped)
- `t()` for translations (pure function)
- `icon()` for icons (pure function)

### Example 3: JavaScript Loading

```jinja
{% block site_scripts %}
{% let _scripts_bundle_js = config.assets.bundle_js ?? false %}
{% let _scripts_build_badge = site.build_badge %}
{% let _scripts_link_previews = site.link_previews %}
{% let _scripts_per_page_json = 'json' in (config.output_formats.per_page ?? []) %}

{% if _scripts_bundle_js %}
<script defer src="{{ asset_url('js/bundle.js') }}"></script>
{% else %}
<script defer src="{{ asset_url('js/utils.js') }}"></script>
<script defer src="{{ asset_url('js/main.js') }}"></script>
{% if _scripts_build_badge.enabled %}
<script defer src="{{ asset_url('js/core/build-badge.js') }}"></script>
{% end %}
{% end %}

{% if _scripts_link_previews.enabled and _scripts_per_page_json %}
<script id="bengal-config" type="application/json">
{
  "linkPreviews": {
    "enabled": true,
    "hoverDelay": {{ _scripts_link_previews.hover_delay ?? 200 }}
  }
}
</script>
{% end %}
{% end %}
```

This block uses:
- `config.*` and `site.*` for all configuration
- `asset_url()` for fingerprinted asset URLs (pure function)
- No page-specific references

### Example 4: Site Dialogs

```jinja
{% block site_dialogs %}
{% if 'navigation.back_to_top' in theme.features %}
<button class="back-to-top" aria-label="Scroll to top">
    {{ icon("arrow-up", size=24) }}
</button>
{% end %}

{% if 'content.lightbox' in theme.features %}
<dialog id="lightbox-dialog" class="lightbox-dialog" aria-label="Image lightbox">
    <img class="lightbox-dialog__image" alt="">
    <button type="submit" class="lightbox-dialog__close">
        {{ icon("close", size=24) }}
    </button>
</dialog>
{% end %}
{% end %}
```

This block only uses:
- `theme.features` for feature flags (site-scoped)
- `icon()` for icons (pure function)

## Verifying Your Block is Cacheable

During builds with `--verbose`, Bengal logs block cache statistics:

```
✓ Block cache: 3 site blocks cached
  - base.html:site_footer (site-scoped)
  - base.html:site_nav (site-scoped)
  - base.html:site_head (site-scoped)
```

You can also inspect template metadata programmatically:

```python
from bengal.rendering.kida import Environment

env = Environment(preserve_ast=True)
template = env.get_template("base.html")
meta = template.template_metadata()

for name, block in meta.blocks.items():
    print(f"{name}: scope={block.cache_scope}, pure={block.is_pure}")
    print(f"  depends_on: {block.depends_on}")
```

## Performance Impact

Bengal's default theme includes 4 site-cacheable blocks totaling ~200 lines of template code:

| Block | Lines | Purpose |
|-------|-------|---------|
| `site_footer` | ~45 | Footer with menus, copyright, badges |
| `site_search_modal` | ~100 | Command palette search dialog |
| `site_scripts` | ~80 | All JavaScript loading |
| `site_dialogs` | ~20 | Back-to-top, lightbox dialogs |

**Rendering savings per build:**

| Site Size | Lines Rendered (Before) | Lines Rendered (After) | Savings |
|-----------|------------------------|------------------------|---------|
| 100 pages | 20,000 | 200 | 99% |
| 500 pages | 100,000 | 200 | 99.8% |
| 1000 pages | 200,000 | 200 | 99.9% |

For complex templates with expensive operations (menus, icon rendering, URL generation), this can significantly reduce build times.

## Summary

| Pattern | Result |
|---------|--------|
| `{% block %}` with only `site.*`, `config.*` | ✅ Site-cacheable |
| Uses pure functions like `current_lang()` | ✅ Site-cacheable |
| Uses pure filters like `dateformat` | ✅ Site-cacheable |
| References `page.*` or `params.*` | ❌ Page-scoped |
| Uses `{% include %}` | ❌ Unknown purity |
| Uses `random` or `shuffle` filters | ❌ Impure, not cacheable |

By following these patterns, you can ensure your site-wide template elements are rendered efficiently.
