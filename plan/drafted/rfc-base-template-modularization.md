# RFC: Base Template Modularization

**Status:** Draft  
**Author:** Bengal Team  
**Created:** 2024-12-23  
**Target Release:** v0.next  

---

## Summary

Refactor `base.html` from a 619-line monolith into a clean ~50-line orchestration layer that includes well-scoped partials. This improves maintainability, enables selective customization, and makes the template architecture easy to reason about.

**Vision:** A `base.html` that reads like a table of contents — each `{% include %}` documents what happens, and developers can dive into partials only when needed.

---

## Why This Matters

### The Problem

`base.html` currently contains:

| Section | Lines | Concern |
|---------|-------|---------|
| SEO/Social meta tags | ~50 | Open Graph, Twitter Cards, robots, keywords |
| Bengal config meta | ~15 | JS-readable config via `<meta>` tags |
| Links (canonical, RSS, hreflang) | ~25 | SEO and i18n |
| Assets (favicon, fonts, CSS) | ~30 | Resource loading |
| Theme initialization | ~35 | FOUC prevention, palette/theme setup |
| Speculation rules | ~30 | View transitions prefetching |
| Header/navigation | ~110 | Desktop nav with menus, dropdowns |
| Mobile navigation | ~100 | Dialog-based mobile menu |
| Footer | ~40 | Copyright, links, badges |
| Script loading | ~75 | Bundle vs individual JS strategy |
| Feature containers | ~20 | Back-to-top, lightbox markup |

**Total: 619 lines** of interleaved concerns.

### Why This Is Painful

1. **Cognitive overload** — Finding where "Twitter Cards" are defined requires scrolling through 600 lines
2. **Risky edits** — Changing favicon logic risks accidentally breaking Open Graph tags
3. **No selective override** — Theme customizers must copy the entire `base.html` to change the footer
4. **Duplicate logic** — Desktop and mobile nav repeat similar menu rendering
5. **Testing difficulty** — Can't test header changes in isolation

### The Goal

```jinja2
{# base.html — The Orchestration Layer #}
<!DOCTYPE html>
<html lang="{{ _current_lang }}">
<head>
    {% include 'partials/head/_meta.html' %}
    {% include 'partials/head/_links.html' %}
    {% include 'partials/head/_assets.html' %}
    {% include 'partials/head/_theme-init.html' %}
    {% block extra_head %}{% endblock %}
</head>
<body>
    {% include 'partials/header.html' %}
    {% include 'partials/mobile-nav.html' %}
    <main id="main-content">{% block content %}{% endblock %}</main>
    {% include 'partials/footer.html' %}
    {% include 'partials/_scripts.html' %}
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**~50 lines** that anyone can understand in 30 seconds.

---

## Proposed Architecture

### Directory Structure

```
partials/
├── head/                       # <head> section partials
│   ├── _meta.html              # All meta tags (SEO, social, bengal config)
│   ├── _links.html             # canonical, RSS, hreflang, favicon, preconnect
│   ├── _assets.html            # fonts, stylesheets
│   ├── _theme-init.html        # FOUC prevention, theme/palette setup
│   └── _speculation.html       # View transitions speculation rules
├── header.html                 # Full header with desktop navigation
├── mobile-nav.html             # Mobile navigation dialog
├── footer.html                 # Site footer
├── _scripts.html               # JS loading (bundle vs individual)
└── _page-features.html         # Back-to-top, lightbox containers
```

### Naming Convention

| Pattern | Meaning | Example |
|---------|---------|---------|
| `name.html` | Public partial — standalone component, safe to override | `header.html`, `footer.html` |
| `_name.html` | Private partial — implementation detail, tightly coupled to parent | `_scripts.html`, `_meta.html` |
| `dir/` | Grouped partials — related concerns in subdirectory | `head/`, `page-hero/` |

**Rationale:**
- The `_` prefix convention already exists in `page-hero/_share-dropdown.html`
- It signals "this is internal, not a customization point"
- Public partials become documented extension points

---

## Detailed Breakdown

### 1. `partials/head/_meta.html`

**Contains:** All `<meta>` tags

```jinja2
{# SEO Meta #}
<meta name="description" content="{{ meta_desc }}">
{% if page.keywords %}
<meta name="keywords" content="{{ page.keywords | join(', ') }}">
{% elif page.tags %}
<meta name="keywords" content="{{ page.tags | meta_keywords(10) }}">
{% endif %}
{% if page.robots_meta and page.robots_meta != 'index, follow' %}
<meta name="robots" content="{{ page.robots_meta }}">
{% endif %}

{# Open Graph / Facebook #}
<meta property="og:type" content="article">
<meta property="og:title" content="{{ _page_title or _site_title }}">
{% if meta_desc %}
<meta property="og:description" content="{{ meta_desc }}">
{% endif %}
{# ... rest of OG tags ... #}

{# Twitter Card #}
<meta name="twitter:card" content="summary_large_image">
{# ... Twitter tags ... #}

{# Bengal Config Meta (for JS) #}
<meta name="bengal:search_preload" content="{{ config.get('search_preload', 'smart') }}">
<meta name="bengal:baseurl" content="{{ config.baseurl or '' }}">
{# ... rest of bengal meta ... #}
```

**~65 lines** — All metadata in one place.

---

### 2. `partials/head/_links.html`

**Contains:** All `<link>` tags

```jinja2
{# Canonical URL #}
{% if config.baseurl %}
<link rel="canonical" href="{{ canonical_url(_page_url) }}">
{% endif %}

{# RSS Feed #}
<link rel="alternate" type="application/rss+xml" title="{{ config.title }} RSS Feed" href="{{ _rss_href }}">

{# hreflang alternates #}
{% for alt in alternate_links(page) %}
<link rel="alternate" hreflang="{{ alt.hreflang }}" href="{{ alt.href }}">
{% endfor %}

{# Favicon #}
{% set favicon_path = config.get('site', {}).get('favicon') %}
{% if favicon_path %}
<link rel="icon" type="image/png" href="{{ favicon_path }}">
{% else %}
<link rel="icon" type="image/x-icon" href="{{ asset_url('favicon.ico') }}">
{# ... rest of favicon variants ... #}
{% endif %}

{# Preconnect #}
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="preconnect" href="https://d3js.org" crossorigin>
<link rel="dns-prefetch" href="https://cdn.jsdelivr.net">
<link rel="dns-prefetch" href="https://d3js.org">
```

**~35 lines**

---

### 3. `partials/head/_assets.html`

**Contains:** Fonts and stylesheets

```jinja2
{# Fonts - Preload critical fonts, load CSS non-blocking #}
{% if config.get('fonts') %}
<link rel="preload" href="{{ asset_url('fonts/outfit-700.woff2') }}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{{ asset_url('fonts.css') }}" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript>
    <link rel="stylesheet" href="{{ asset_url('fonts.css') }}">
</noscript>
{% endif %}

{# Main Stylesheet #}
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
```

**~15 lines**

---

### 4. `partials/head/_theme-init.html`

**Contains:** Theme defaults and FOUC prevention script

```jinja2
{# Theme configuration defaults from bengal.toml #}
<script>
    window.BENGAL_THEME_DEFAULTS = {
        appearance: '{{ theme.default_appearance }}',
        palette: '{{ theme.default_palette }}'
    };
    window.Bengal = window.Bengal || {};
    window.Bengal.enhanceBaseUrl = '{{ asset_url("js/enhancements") }}';
    window.Bengal.watchDom = {{ config.get('enhancements', {}).get('watch_dom', true) | lower }};
    window.Bengal.debug = {{ config.get('enhancements', {}).get('debug', false) | lower }};
</script>

{# Theme & Palette initialization - INLINED to prevent FOUC #}
<script>
    (function () {
        try {
            var defaults = window.BENGAL_THEME_DEFAULTS || { appearance: 'system', palette: '' };
            {# ... FOUC prevention logic ... #}
        } catch (e) { document.documentElement.setAttribute('data-theme', 'light'); }
    })();
</script>
```

**~35 lines**

---

### 5. `partials/head/_speculation.html`

**Contains:** View transitions speculation rules

```jinja2
{% set _speculation = _doc_app.speculation %}
{% set _speculation_enabled = _doc_app.enabled and _speculation.enabled %}
{% set _speculation_feature = _doc_app.features.get('speculation_rules', true) %}
{% if _speculation_enabled and _speculation_feature %}
<script type="speculationrules">
{
  "prerender": [...],
  "prefetch": [...]
}
</script>
{% endif %}
```

**~30 lines**

---

### 6. `partials/header.html`

**Contains:** Full header with desktop navigation

```jinja2
<header role="banner" class="header-appshell">
    <nav role="navigation" aria-label="Main navigation">
        <div class="header-nav-content">
            {# Logo #}
            <a href="{{ '/' | absolute_url }}" class="logo">
                {% include 'partials/header/_logo.html' %}
            </a>

            {# Desktop Navigation #}
            {% if _main_menu or _auto_nav %}
            <ul class="nav-main hidden-mobile">
                {% include 'partials/header/_nav-items.html' %}
                {% block nav_items %}{% endblock %}
            </ul>
            {% endif %}

            {# Header Actions #}
            <div class="header-actions hidden-mobile">
                {% include 'partials/header/_search-trigger.html' %}
                {% include 'partials/theme-controls.html' %}
            </div>

            {# Mobile Toggle #}
            <button class="mobile-nav-toggle visible-mobile" ...>
                {{ icon('list', size=24) }}
            </button>
        </div>
    </nav>
</header>
```

**~40 lines** (with sub-partials for nav items)

**Sub-partials:**
- `partials/header/_logo.html` — Logo rendering logic
- `partials/header/_nav-items.html` — Menu item rendering (shared with mobile)
- `partials/header/_search-trigger.html` — Search button/link

---

### 7. `partials/mobile-nav.html`

**Contains:** Mobile navigation dialog

```jinja2
<dialog id="mobile-nav-dialog" class="mobile-nav-dialog" aria-label="Mobile navigation">
    <form method="dialog" class="mobile-nav-header">
        <span class="logo">
            {% include 'partials/header/_logo.html' %}
        </span>
        <div class="mobile-nav-actions">
            {% if modal_enabled %}
            <button type="button" class="mobile-nav-search" aria-label="Search" data-open-search>
                {{ icon('magnifying-glass', size=16) }}
                <span>Search</span>
            </button>
            {% endif %}
            <button type="submit" value="close" class="mobile-nav-close" aria-label="Close menu">
                {{ icon('x', size=16) }}
                <span>Close</span>
            </button>
        </div>
    </form>

    {% if _main_menu or _auto_nav %}
    <nav class="mobile-nav-content" role="navigation">
        <ul>
            {% include 'partials/header/_nav-items.html' with context %}
            {% block mobile_nav_items %}{% endblock %}
        </ul>
    </nav>
    {% endif %}

    <div class="mobile-nav-footer">
        {% include 'partials/theme-controls.html' %}
    </div>
</dialog>
```

**~45 lines** — Reuses `_logo.html` and `_nav-items.html`

---

### 8. `partials/footer.html`

**Contains:** Site footer

```jinja2
<footer role="contentinfo">
    <div class="container">
        <div class="footer-bottom">
            <div class="footer-left">
                <p class="footer-copyright">
                    &copy; {{ site.build_time | dateformat('%Y') }} {{ _site_title }}
                </p>
                {% if _footer_menu %}
                <ul class="footer-links">
                    {% for item in _footer_menu %}
                    <li><a href="{{ item.href | absolute_url }}">{{ item.name }}</a></li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            <div class="footer-right">
                {% if _build_badge.enabled %}
                <a class="bengal-build-time" data-bengal-build-badge ...>
                    {# Build badge content #}
                </a>
                {% endif %}
                <a href="https://github.com/lbliii/bengal" class="bengal-badge" ...>
                    {# Bengal cat badge #}
                </a>
            </div>
        </div>
    </div>
</footer>
```

**~40 lines**

---

### 9. `partials/_scripts.html`

**Contains:** All JavaScript loading logic

```jinja2
{# ============================================================== #}
{# JavaScript Loading Strategy (Render Performance Optimized)     #}
{# ============================================================== #}

{% set _bundle_js = config.get('assets', {}).get('bundle_js', false) %}

{% if _bundle_js %}
{# Bundled JS #}
<script defer src="{{ asset_url('js/bundle.js') }}"></script>
<script defer src="{{ asset_url('js/vendor/lunr.min.js') }}"></script>
{% else %}
{# Individual Scripts #}
<script defer src="{{ asset_url('js/utils.js') }}"></script>
<script defer src="{{ asset_url('js/bengal-enhance.js') }}"></script>
{# ... core modules ... #}
{# ... enhancements ... #}
{% endif %}

{# Lazy-loaded Library URLs #}
<script>
    window.BENGAL_LAZY_ASSETS = { ... };
    window.BENGAL_ICONS = { ... };
</script>
<script defer src="{{ asset_url('js/enhancements/lazy-loaders.js') }}"></script>
```

**~75 lines**

---

### 10. `partials/_page-features.html`

**Contains:** Bottom-of-page feature containers

```jinja2
{# Back to Top Button #}
{% if 'navigation.back_to_top' in theme.features %}
<button class="back-to-top" aria-label="Scroll to top" title="Back to top">
    {{ icon("arrow-up", size=24) }}
</button>
{% endif %}

{# Image Lightbox Container #}
{% if 'content.lightbox' in theme.features %}
<div class="lightbox" role="dialog" aria-label="Image lightbox" aria-hidden="true">
    <img class="lightbox__image" alt="">
    <button class="lightbox__close" aria-label="Close lightbox">
        {{ icon("close", size=24) }}
    </button>
    <div class="lightbox__caption"></div>
</div>
{% endif %}
```

**~20 lines**

---

## Final `base.html`

```jinja2
<!DOCTYPE html>
{#
================================================================================
TEMPLATE VARIABLES
================================================================================
Bengal provides: page, site, config, params (page.metadata alias), meta, section

Cache expensive function calls once per render. Page properties like title,
_path, kind, tags are always defined - no defensive checks needed.
================================================================================
#}
{# Page shortcuts #}
{% set _page_title = page.title %}
{% set _page_url = page._path %}

{# Navigation - cache function calls #}
{% set _current_lang = current_lang() %}
{% set _main_menu = get_menu_lang('main', _current_lang) %}
{% set _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}
{% set _footer_menu = get_menu_lang('footer', _current_lang) %}

{# Site config shortcuts #}
{% set _site_title = config.title %}

{# Normalized config objects #}
{% set _build_badge = site.build_badge %}
{% set _doc_app = site.document_application %}
{% set _view_transitions = _doc_app.enabled and _doc_app.navigation.view_transitions %}
{% set _transition_style = _doc_app.navigation.transition_style %}

{# RSS href (computed for i18n) #}
{% set _lang = _current_lang %}
{% set _i18n = config.get('i18n', {}) %}
{% set _rss_href = '/rss.xml' %}
{% if _i18n and _i18n.get('strategy') == 'prefix' %}
{% set _default_lang = _i18n.get('default_language', 'en') %}
{% set _default_in_subdir = _i18n.get('default_in_subdir', False) %}
{% if _lang and (_default_in_subdir or _lang != _default_lang) %}
{% set _rss_href = '/' ~ _lang ~ '/rss.xml' %}
{% endif %}
{% endif %}

{# Meta description #}
{% set meta_desc = meta_desc | default(config.get('description'), '') %}

{# OG Image path (computed once) #}
{% set _og_image_path = '' %}
{% if params.get('image') %}
{% set _og_image_path = og_image(params.get('image'), page) %}
{% else %}
{% set _og_image_path = og_image('', page) %}
{% endif %}
{% if not _og_image_path and config.get('og_image') %}
{% set _og_image_path = og_image(config.get('og_image')) %}
{% endif %}

<html lang="{{ _current_lang }}" {% if _view_transitions and _transition_style != 'crossfade' %}
    data-transition-style="{{ _transition_style }}" {% endif %}>

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">

    {% if _view_transitions %}
    <meta name="view-transition" content="same-origin">
    {% endif %}

    <title>{% block title %}{{ _page_title if _page_title else _site_title }}{% if _page_title %} - {{ _site_title }}{% endif %}{% endblock %}</title>

    {% include 'partials/head/_meta.html' %}
    {% include 'partials/head/_links.html' %}
    {% include 'partials/head/_assets.html' %}
    {% include 'partials/head/_theme-init.html' %}
    {% include 'partials/head/_speculation.html' %}

    {% block extra_head %}{% endblock %}
    {% include 'partials/meta-generator.html' %}

    {# Optional JSON bootstrap #}
    {% if config.get('expose_metadata_json') %}
    <script id="bengal-bootstrap" type="application/json">{{ bengal | jsonify }}</script>
    <script>
        (function () {
            var el = document.getElementById('bengal-bootstrap');
            if (el) { window.__BENGAL__ = JSON.parse(el.textContent || '{}'); }
        })();
    </script>
    {% endif %}
</head>

<body data-type="{{ page.type }}" data-variant="{{ page.variant or '' }}"
    class="page-kind-{{ page.kind or 'page' }}{% if page is draft %} draft-page{% endif %}{% if page.hidden %} hidden-page{% endif %}{% if page is featured %} featured-content{% endif %}">

    {# Skip Link #}
    {% if 'accessibility.skip_link' in theme.features %}
    <a href="#main-content" class="skip-link">Skip to main content</a>
    {% endif %}

    {% include 'partials/search-modal.html' %}
    {% include 'partials/header.html' %}
    {% include 'partials/mobile-nav.html' %}

    <main id="main-content" role="main">
        {% block content %}{% endblock %}
    </main>

    {% include 'partials/footer.html' %}
    {% include 'partials/_scripts.html' %}
    {% block extra_js %}{% endblock %}
    {% include 'partials/_page-features.html' %}

</body>
</html>
```

**~110 lines** — Variable setup + clean includes. The orchestration is now visible at a glance.

---

## Variable Scoping Strategy

### Problem: Partials Need Access to Cached Variables

The current `base.html` caches expensive function calls at the top:

```jinja2
{% set _main_menu = get_menu_lang('main', _current_lang) %}
```

These must remain accessible to included partials.

### Solution: Keep Variable Setup in `base.html`

Variables defined before `{% include %}` are automatically available in the included template (Jinja2's default behavior with `{% include ... with context %}`).

**Rules:**
1. All `{% set %}` statements stay in `base.html` at the top
2. Partials receive the full context automatically
3. Partials should NOT define variables used by other partials (no cross-partial dependencies)
4. Partials CAN define local variables for their own use

---

## Block Inheritance Strategy

### Problem: Blocks Must Stay in `base.html`

Blocks like `{% block nav_items %}` allow child templates to inject content. These cannot be moved into partials.

### Solution: Blocks Remain, Partials Include Around Them

```jinja2
{# In base.html #}
{% include 'partials/header.html' %}

{# In partials/header.html #}
<ul class="nav-main">
    {% include 'partials/header/_nav-items.html' %}
    {% block nav_items %}{% endblock %}  {# ← This stays in header.html #}
</ul>
```

**Important:** Blocks defined in partials are still overridable by templates extending `base.html`. Jinja2 flattens the include tree.

---

## Migration Plan

### Phase 1: Create Head Partials (Low Risk)

1. Create `partials/head/` directory
2. Extract `_meta.html` — All meta tags
3. Extract `_links.html` — All link tags
4. Extract `_assets.html` — Fonts and CSS
5. Extract `_theme-init.html` — Theme setup scripts
6. Extract `_speculation.html` — View transitions
7. Update `base.html` to include them
8. **Test:** Full site build, visual inspection

### Phase 2: Create Body Partials (Medium Risk)

1. Extract `footer.html`
2. Extract `_scripts.html`
3. Extract `_page-features.html`
4. Update `base.html` to include them
5. **Test:** Full site build, JS functionality

### Phase 3: Extract Navigation (Higher Risk)

1. Create `partials/header/` directory
2. Extract `header/_logo.html`
3. Extract `header/_nav-items.html` (shared desktop/mobile)
4. Extract `header/_search-trigger.html`
5. Extract `header.html` (using sub-partials)
6. Extract `mobile-nav.html` (reusing sub-partials)
7. **Test:** Navigation on desktop and mobile, all breakpoints

### Phase 4: Cleanup and Documentation

1. Add header comments to each partial explaining its purpose
2. Update theme developer documentation
3. Remove any dead code from original `base.html`

---

## Testing Checklist

### Functional Tests

- [ ] Site builds without errors
- [ ] All pages render correctly
- [ ] Desktop navigation works (menus, dropdowns, active states)
- [ ] Mobile navigation works (dialog open/close, search)
- [ ] Theme switching works (light/dark/system)
- [ ] Search modal opens (Cmd/Ctrl+K)
- [ ] Back-to-top button appears on scroll
- [ ] Lightbox opens for images
- [ ] RSS feed link correct
- [ ] Canonical URLs correct
- [ ] Open Graph tags present in source
- [ ] Twitter Card tags present in source

### Visual Tests

- [ ] No FOUC (Flash of Unstyled Content)
- [ ] Header renders identically
- [ ] Footer renders identically
- [ ] Mobile nav renders identically
- [ ] No layout shifts

### Override Tests

- [ ] Can override `header.html` in site theme
- [ ] Can override `footer.html` in site theme
- [ ] `{% block nav_items %}` still works
- [ ] `{% block extra_head %}` still works
- [ ] `{% block extra_js %}` still works

---

## Files Changed Summary

| Action | File |
|--------|------|
| **Modify** | `templates/base.html` |
| **Create** | `templates/partials/head/_meta.html` |
| **Create** | `templates/partials/head/_links.html` |
| **Create** | `templates/partials/head/_assets.html` |
| **Create** | `templates/partials/head/_theme-init.html` |
| **Create** | `templates/partials/head/_speculation.html` |
| **Create** | `templates/partials/header.html` |
| **Create** | `templates/partials/header/_logo.html` |
| **Create** | `templates/partials/header/_nav-items.html` |
| **Create** | `templates/partials/header/_search-trigger.html` |
| **Create** | `templates/partials/mobile-nav.html` |
| **Create** | `templates/partials/footer.html` |
| **Create** | `templates/partials/_scripts.html` |
| **Create** | `templates/partials/_page-features.html` |

**New files:** 13  
**Modified files:** 1

---

## Success Criteria

After implementation:

- [ ] `base.html` is under 120 lines
- [ ] Each partial has a single, clear responsibility
- [ ] No logic duplication between desktop and mobile nav
- [ ] Theme developers can override `header.html` or `footer.html` independently
- [ ] All existing block overrides continue to work
- [ ] Build time is not measurably impacted
- [ ] No visual regressions

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| 1 | 2 hours | Head partials extraction |
| 2 | 1 hour | Body partials extraction |
| 3 | 3 hours | Navigation refactoring |
| 4 | 1 hour | Documentation and cleanup |

**Total:** ~7 hours focused work

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Block inheritance breaks | Medium | High | Test all extending templates before/after |
| Variable scoping issues | Low | Medium | Jinja2 includes inherit context by default |
| Performance regression | Low | Low | Jinja2 compiles includes; no runtime penalty |
| Theme override breaks | Medium | Medium | Document which partials are override-safe |

---

## Future Opportunities

Once modularized, additional improvements become easier:

1. **Component variants** — Multiple header styles (e.g., `header-minimal.html`)
2. **Conditional loading** — Skip partials based on page type
3. **A/B testing** — Swap partials for experiments
4. **Documentation** — Auto-generate partial reference from file structure
5. **Theme composition** — Mix partials from multiple theme sources

---

## Appendix: Existing Partial Patterns

The codebase already uses these patterns:

```
partials/
├── page-hero/
│   ├── _element-stats.html    # Private (underscore)
│   ├── _share-dropdown.html   # Private (underscore)
│   ├── _wrapper.html          # Private (underscore)
│   ├── element.html           # Public
│   └── section.html           # Public
├── theme-controls.html        # Public, used by header + mobile-nav
├── search-modal.html          # Public
└── meta-generator.html        # Public
```

This RFC extends the established convention with `head/` and `header/` subdirectories.
