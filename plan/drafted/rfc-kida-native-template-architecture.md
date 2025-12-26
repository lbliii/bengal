# RFC: Kida-Native Template Architecture

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: Medium  
**Scope**: `bengal/themes/default/templates/`

---

## Executive Summary

Bengal's default theme templates were originally written for Jinja2 and later adapted to Kida by changing block endings (`{% endif %}` → `{% end %}`). However, they don't leverage Kida's unique features that enable cleaner, more maintainable templates.

This RFC proposes a comprehensive restructuring of the template architecture to:

1. **Leverage Kida-native features**: `{% match %}`, `{% let %}`, `{% slot %}`, `{% cache %}`, pipelines
2. **Separate concerns**: Split large files into focused modules (components vs defs vs layouts)
3. **Improve performance**: Use `{% cache %}` for expensive fragments
4. **Reduce complexity**: Replace nested if/elif chains with pattern matching

---

## Problem Statement

### Current State

The default theme templates exhibit several anti-patterns:

| Issue | Example | Impact |
| :--- | :--- | :--- |
| **Monolithic base.html** | 655 lines with inlined JS, setup, navigation | Hard to maintain, slow to parse |
| **Flat partials directory** | 33+ files in `partials/` | No organization by purpose |
| **Jinja patterns in Kida** | Nested `{% if %}...{% elif %}...{% elif %}` | `{% match %}` would be cleaner |
| **No explicit scoping** | All variables use `{% set %}` | Unclear which variables "leak" |
| **No fragment caching** | Repeated expensive calls | `{% cache %}` would help performance |
| **Mixed file purposes** | Some partials contain both defs and inline code | Unclear what to import vs include |

### Kida Features Not Leveraged

```yaml
match:
  status: Not used
  benefit: Cleaner branching than if/elif chains
  example: "page.type → different hero styles"

let_vs_set:
  status: All use {% set %}
  benefit: Explicit template-wide vs block-scoped variables
  example: "{% let _cached_menu = get_menu() %} at top"

slot:
  status: Not used
  benefit: Component content injection (like React children)
  example: "{% def card() %}...{% slot %}...{% end %}"

cache:
  status: Not used
  benefit: Fragment caching for expensive operations
  example: "{% cache 'nav-' ~ page.version %}...{% end %}"

capture:
  status: Not used (uses {% set x %}...{% endset %})
  benefit: Clearer intent for block capture
  example: "{% capture meta_description %}...{% end %}"

pipeline:
  status: Not used
  benefit: Readable filter chains
  example: "items |> where(published=true) |> sort_by('date') |> take(5)"
```

---

## Proposed Architecture

### Directory Structure

```text
templates/
├── base.html                    # Minimal shell (head, body, scripts)
├── layouts/                     # Page-level layouts
│   ├── single.html              # Single content page
│   ├── list.html                # List/archive page
│   ├── docs.html                # Documentation with sidebar
│   └── home.html                # Homepage layout
│
├── components/                  # Reusable UI components ({% def %} + {% slot %})
│   ├── cards/
│   │   ├── article.html         # Article preview card
│   │   ├── content-tile.html    # Generic content tile
│   │   └── feature.html         # Feature highlight card
│   ├── navigation/
│   │   ├── breadcrumbs.html     # Breadcrumb trail
│   │   ├── pagination.html      # Prev/next pagination
│   │   └── toc.html             # Table of contents
│   ├── header/
│   │   ├── site-header.html     # Main site header
│   │   ├── mobile-nav.html      # Mobile navigation dialog
│   │   └── theme-controls.html  # Theme/palette switcher
│   ├── footer/
│   │   └── site-footer.html     # Site footer
│   ├── hero/                    # Page hero variants
│   │   ├── default.html         # Standard hero
│   │   ├── editorial.html       # Editorial style
│   │   ├── overview.html        # Section overview
│   │   └── _resolver.html       # {% match %} hero type resolver
│   ├── meta/
│   │   ├── og-tags.html         # Open Graph meta tags
│   │   ├── twitter-card.html    # Twitter card meta
│   │   └── json-ld.html         # Structured data
│   └── widgets/
│       ├── tag-list.html        # Tag badge list
│       ├── share-buttons.html   # Social share buttons
│       └── search-modal.html    # Search modal dialog
│
├── defs/                        # Logic-only definitions (no HTML output)
│   ├── context.html             # Context setup helpers
│   ├── navigation.html          # Menu/nav tree helpers
│   ├── seo.html                 # SEO/meta helpers
│   └── formatting.html          # Text/date formatting helpers
│
├── fragments/                   # Includable HTML fragments (no defs)
│   ├── scripts.html             # JavaScript loading
│   ├── stylesheets.html         # CSS loading
│   ├── analytics.html           # Analytics snippets
│   └── preconnect.html          # Resource hints
│
├── pages/                       # Page-type specific templates
│   ├── page.html
│   ├── post.html
│   ├── doc/
│   │   ├── detail.html
│   │   └── index.html
│   ├── blog/
│   │   ├── list.html
│   │   └── single.html
│   └── ...existing page types...
│
└── autodoc/                     # Keep existing structure (already well-organized)
    └── ...existing autodoc templates...
```

### Key Principles

#### 1. Components Use `{% def %}` + `{% slot %}`

Components are reusable UI elements. They define a function with optional slots for content injection.

```jinja2
{# components/cards/article.html #}

{% def article_card(article, show_image=false) %}
<article class="article-card">
  {% if show_image and article.metadata.image %}
  <img src="{{ article.metadata.image | image_url(800) }}" alt="" loading="lazy">
  {% end %}

  <div class="article-card-content">
    <h2><a href="{{ article.href }}">{{ article.title }}</a></h2>

    {# Slot for custom content #}
    {% slot %}

    {# Default slot content if none provided #}
    {% if article.metadata.description %}
    <p>{{ article.metadata.description }}</p>
    {% end %}
  </div>
</article>
{% end %}
```

Usage:

```jinja2
{% from 'components/cards/article.html' import article_card %}

{# Simple usage #}
{{ article_card(post) }}

{# With custom slot content #}
{% call article_card(post, show_image=true) %}
  <p class="custom-excerpt">{{ post.content | excerpt(200) }}</p>
  {{ tag_list(post.tags) }}
{% end %}
```

#### 2. `{% match %}` for Type-Based Branching

Replace complex if/elif chains with pattern matching:

```jinja2
{# components/hero/_resolver.html #}

{% def render_hero(page, style=none) %}
{% let hero_style = style or page.metadata.hero_style or 'default' %}

{% match hero_style %}
  {% case 'editorial' %}
    {% include 'components/hero/editorial.html' %}

  {% case 'overview' %}
    {% include 'components/hero/overview.html' %}

  {% case 'magazine' %}
    {% include 'components/hero/magazine.html' %}

  {% case 'minimal' %}
    {# Inline minimal hero #}
    <header class="hero hero-minimal">
      <h1>{{ page.title }}</h1>
    </header>

  {% case _ %}
    {# Default fallback #}
    {% include 'components/hero/default.html' %}
{% end %}
{% end %}
```

#### 3. `{% let %}` for Template-Wide Variables

Use `{% let %}` for variables that should persist across the template, and `{% set %}` for block-scoped temporaries:

```jinja2
{# At top of base.html - template-wide cached values #}
{% let _current_lang = current_lang() %}
{% let _main_menu = get_menu_lang('main', _current_lang) %}
{% let _site_title = config.title %}
{% let _page_title = page.title %}

{# Inside a loop - block-scoped #}
{% for item in _main_menu %}
  {% set item_class = 'active' if item.active else '' %}
  <a class="{{ item_class }}">{{ item.name }}</a>
{% end %}
```

#### 4. `{% cache %}` for Expensive Fragments

Cache fragments that are expensive to compute but stable:

```jinja2
{# Cache navigation tree per version #}
{% cache 'nav-tree-' ~ (page.version or 'default') %}
  {% for item in get_nav_tree(page) %}
    {{ nav_node(item, 0) }}
  {% end %}
{% end %}

{# Cache footer with TTL (rebuild daily) #}
{% cache 'footer', ttl='24h' %}
  {% include 'components/footer/site-footer.html' %}
{% end %}

{# Cache per-page sidebar based on section #}
{% cache 'sidebar-' ~ page._section._path if page._section else 'root' %}
  {% include 'components/navigation/docs-nav.html' %}
{% end %}
```

#### 5. `{% capture %}` for Block Content

Use `{% capture %}` instead of `{% set x %}...{% endset %}`:

```jinja2
{# Before (Jinja pattern) #}
{% set meta_desc %}
{% if page.metadata.description %}{{ page.metadata.description }}{% elif page.content %}{{ page.content | strip_html | excerpt(160) }}{% else %}{{ config.description }}{% end %}
{% endset %}

{# After (Kida pattern) #}
{% capture meta_desc %}
{% match %}
  {% case page.metadata.description %}
    {{ page.metadata.description }}
  {% case page.content %}
    {{ page.content | strip_html | excerpt(160) }}
  {% case _ %}
    {{ config.description }}
{% end %}
{% end %}
```

#### 6. Pipeline `|>` for Filter Chains

Use the pipeline operator for readable filter chains:

```jinja2
{# Before (nested filters) #}
{{ page.related_posts | selectattr('published') | sort(attribute='date', reverse=true) | list | slice(0, 5) }}

{# After (pipeline) #}
{{ page.related_posts |> where(published=true) |> sort_by('date', reverse=true) |> take(5) }}
```

---

## Migration Strategy

### Phase 1: Structural Reorganization (Week 1)

**No syntax changes** — just move files into the new directory structure.

| Current Location | New Location |
| :--- | :--- |
| `partials/theme-controls.html` | `components/header/theme-controls.html` |
| `partials/docs-nav.html` | `components/navigation/docs-nav.html` |
| `partials/page-hero.html` | `components/hero/default.html` |
| `partials/search-modal.html` | `components/widgets/search-modal.html` |
| `partials/content-components.html` | Split into `components/cards/*.html` |

**Update imports** in all templates to use new paths.

### Phase 2: Extract from base.html (Week 1)

Split `base.html` (655 lines) into focused fragments:

| Extract | New File | Lines |
| :--- | :--- | :--- |
| Meta tags (OG, Twitter) | `components/meta/og-tags.html` | ~40 |
| Script loading | `fragments/scripts.html` | ~80 |
| Header component | `components/header/site-header.html` | ~100 |
| Mobile nav dialog | `components/header/mobile-nav.html` | ~70 |
| Footer | `components/footer/site-footer.html` | ~40 |

**Result**: `base.html` becomes ~200 lines of skeleton + includes.

### Phase 3: Kida-Native Syntax (Week 2)

Convert patterns to Kida-native equivalents:

| Pattern | Count | Conversion |
| :--- | :--- | :--- |
| if/elif/else chains | ~25 | → `{% match %}` |
| `{% set %}` at template top | ~15 | → `{% let %}` |
| `{% set x %}...{% endset %}` | ~5 | → `{% capture %}` |
| Nested filter chains | ~10 | → Pipeline `|>` |

### Phase 4: Add Caching (Week 2)

Identify cacheable fragments:

| Fragment | Cache Key | TTL |
| :--- | :--- | :--- |
| Navigation tree | `nav-{version}` | Build-time |
| Footer | `footer` | 24h |
| Popular tags | `tags-popular` | 1h |
| OG image URLs | `og-{page._path}` | Build-time |

### Phase 5: Component Slots (Week 3)

Refactor key components to use slots:

| Component | Slot Purpose |
| :--- | :--- |
| `article_card` | Custom excerpt/content |
| `hero` | Hero actions/CTA area |
| `card` | Generic card body |
| `modal` | Modal content area |

---

## Detailed Refactoring Examples

### Example 1: Hero Type Resolution

**Before** (partials/page-hero.html):

```jinja2
{% set hero_style = params.hero_style | default('default') %}
{% if hero_style == 'editorial' %}
  {% include 'partials/page-hero-editorial.html' %}
{% elif hero_style == 'magazine' %}
  {% include 'partials/page-hero-magazine.html' %}
{% elif hero_style == 'overview' %}
  {% include 'partials/page-hero-overview.html' %}
{% elif hero_style == 'classic' %}
  {% include 'partials/page-hero-classic.html' %}
{% else %}
  {# Default hero inline #}
  <header class="page-hero">
    <h1>{{ page.title }}</h1>
  </header>
{% end %}
```

**After** (components/hero/_resolver.html):

```jinja2
{% def resolve_hero(page) %}
{% let style = page.metadata.hero_style or 'default' %}

{% match style %}
  {% case 'editorial' %}
    {{ editorial_hero(page) }}
  {% case 'magazine' %}
    {{ magazine_hero(page) }}
  {% case 'overview' %}
    {{ overview_hero(page) }}
  {% case 'classic' %}
    {{ classic_hero(page) }}
  {% case _ %}
    {{ default_hero(page) }}
{% end %}
{% end %}
```

### Example 2: Content Tiles with Slot

**Before** (partials/content-components.html):

```jinja2
{% def article_card(article, show_excerpt=True, show_image=False) %}
<article class="article-card">
  {# ... lots of conditional content ... #}
</article>
{% end %}
```

**After** (components/cards/article.html):

```jinja2
{% def article_card(article, show_excerpt=true, show_image=false) %}
<article class="article-card {% if article is featured %}featured{% end %}">
  {% if show_image and article.metadata.image %}
  <img src="{{ article.metadata.image |> image_url(800) }}"
       srcset="{{ article.metadata.image |> image_srcset([400, 800, 1200]) }}"
       alt="{{ article.metadata.image |> image_alt }}"
       loading="lazy">
  {% end %}

  <div class="article-card-content">
    {# Badges via match #}
    <div class="article-card-badges">
      {% match %}
        {% case article is featured %}
          <span class="badge badge-featured">⭐ Featured</span>
        {% case article | has_tag('tutorial') %}
          <span class="badge badge-tutorial">📚 Tutorial</span>
        {% case article | has_tag('new') %}
          <span class="badge badge-new">✨ New</span>
      {% end %}
    </div>

    <h2><a href="{{ article.href }}">{{ article.title }}</a></h2>

    {# Slot for custom content, with default fallback #}
    {% slot %}
      {% if show_excerpt and article.metadata.description %}
      <p class="article-card-excerpt">{{ article.metadata.description }}</p>
      {% end %}
    {% end %}

    {% if article.tags %}
    <footer class="article-card-footer">
      {{ tag_list(article.tags, small=true) }}
    </footer>
    {% end %}
  </div>
</article>
{% end %}
```

### Example 3: Scoped Variables with `{% let %}` and `{% export %}`

**Before**:

```jinja2
{% set total = 0 %}
{% for item in items %}
  {% set total = total + item.count %}
{% end %}
{# total is now undefined outside the loop in strict scoping! #}
```

**After**:

```jinja2
{% let total = 0 %}
{% for item in items %}
  {% export total = total + item.count %}
{% end %}
{# total is explicitly exported and available #}
{{ total }}
```

---

## New base.html Structure

```jinja2
<!DOCTYPE html>
{# ============================================
   TEMPLATE-WIDE CONTEXT SETUP
   Use {% let %} for values used throughout
   ============================================ #}
{% let _lang = current_lang() %}
{% let _site_title = config.title %}
{% let _page_title = page.title %}
{% let _main_menu = get_menu_lang('main', _lang) %}
{% let _footer_menu = get_menu_lang('footer', _lang) %}

<html lang="{{ _lang }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>{% block title %}{{ _page_title or _site_title }}{% if _page_title %} - {{ _site_title }}{% end %}{% end %}</title>

  {# Meta tags component #}
  {% from 'components/meta/og-tags.html' import og_meta, twitter_meta %}
  {{ og_meta(page, _site_title) }}
  {{ twitter_meta(page, _site_title) }}

  {# Stylesheets fragment #}
  {% include 'fragments/stylesheets.html' %}

  {# Theme initialization (inlined for FOUC prevention) #}
  {% include 'fragments/theme-init.html' %}

  {% block extra_head %}{% end %}
</head>

<body data-type="{{ page.type }}" data-kind="{{ page.kind }}">
  {# Header component #}
  {% from 'components/header/site-header.html' import site_header %}
  {{ site_header(_main_menu, _site_title) }}

  {# Mobile navigation dialog #}
  {% include 'components/header/mobile-nav.html' %}

  {# Search modal #}
  {% include 'components/widgets/search-modal.html' %}

  <main id="main-content" role="main">
    {% block content %}{% end %}
  </main>

  {# Footer component #}
  {% from 'components/footer/site-footer.html' import site_footer %}
  {{ site_footer(_footer_menu, _site_title) }}

  {# Scripts fragment #}
  {% include 'fragments/scripts.html' %}

  {% block extra_js %}{% end %}
</body>
</html>
```

**Result**: ~80 lines vs current 655 lines.

---

## File Organization Rules

### `components/` Directory

- **Purpose**: Reusable UI components
- **Pattern**: Each file exports one or more `{% def %}` functions
- **May use**: `{% slot %}` for content injection
- **Import**: `{% from 'components/x.html' import component_name %}`

### `defs/` Directory

- **Purpose**: Logic-only helpers (no HTML output)
- **Pattern**: Pure functions that return values, not markup
- **Use case**: Complex conditionals, data transformation
- **Import**: `{% from 'defs/x.html' import helper_name %}`

### `fragments/` Directory

- **Purpose**: Includable HTML snippets (no defs)
- **Pattern**: Raw HTML/template to be inlined
- **Use case**: Scripts, stylesheets, analytics
- **Include**: `{% include 'fragments/x.html' %}`

### `layouts/` Directory

- **Purpose**: Page-level layout structures
- **Pattern**: Extends `base.html`, defines content blocks
- **Use case**: Different page layouts (docs, blog, home)
- **Extends**: `{% extends 'layouts/x.html' %}`

---

## Compatibility Notes

### Import Path Updates

All import paths change with the restructure. Provide a migration script:

```python
# scripts/migrate_template_imports.py
IMPORT_MAPPINGS = {
    "partials/content-components.html": {
        "article_card": "components/cards/article.html",
        "content_tiles": "components/cards/content-tile.html",
        "tag_list": "components/widgets/tag-list.html",
    },
    "partials/theme-controls.html": "components/header/theme-controls.html",
    "partials/docs-nav.html": "components/navigation/docs-nav.html",
    # ...
}
```

### Backward Compatibility Layer

During migration, provide compatibility includes:

```jinja2
{# partials/content-components.html (compatibility shim) #}
{% from 'components/cards/article.html' import article_card %}
{% from 'components/cards/content-tile.html' import content_tiles %}
{% from 'components/widgets/tag-list.html' import tag_list %}

{# Deprecation warning in dev mode #}
{% if bengal.debug %}
<!-- DEPRECATED: Import directly from components/ instead of partials/ -->
{% end %}
```

---

## Testing Strategy

### Template Compilation Tests

```python
# tests/themes/test_kida_templates.py

def test_all_templates_compile():
    """Ensure all templates parse without syntax errors."""
    env = KidaEnvironment(loader=FileSystemLoader("templates/"))
    for path in glob("templates/**/*.html", recursive=True):
        template = env.get_template(path)
        assert template is not None

def test_component_slots():
    """Test slot-based components work correctly."""
    env = KidaEnvironment(...)
    template = env.from_string("""
    {% from 'components/cards/article.html' import article_card %}
    {% call article_card(mock_article) %}
      <p>Custom content</p>
    {% end %}
    """)
    result = template.render(mock_article=mock)
    assert "Custom content" in result

def test_match_exhaustiveness():
    """Test match patterns have fallback cases."""
    # Verify all {% match %} blocks have {% case _ %} fallback
    ...
```

### Visual Regression Tests

Run visual diff on rendered output before/after migration.

### Performance Tests

```python
def test_cache_fragments_hit():
    """Verify cached fragments don't re-render."""
    # Render same page twice, check cache hits
    ...

def test_base_template_reduced():
    """Verify base.html is under 100 lines."""
    with open("templates/base.html") as f:
        lines = len(f.readlines())
    assert lines < 100
```

---

## Success Criteria

| Metric | Current | Target |
| :--- | :--- | :--- |
| `base.html` lines | 655 | < 100 |
| Partials directory files | 33 | 0 (migrated to `components/`) |
| `{% match %}` usage | 0 | 20+ |
| `{% let %}` usage | 0 | 30+ (template-wide vars) |
| `{% cache %}` fragments | 0 | 5+ |
| `{% slot %}` components | 0 | 10+ |
| Nested if/elif depth | 4+ | 1 (via match) |

---

## Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Breaking custom themes | Provide compatibility shims for 2 versions |
| Performance regression | Benchmark before/after; `{% cache %}` should improve |
| Learning curve | Document new patterns in `TEMPLATE-PATTERNS.md` |
| Migration effort | Phase incrementally; don't require big-bang |

---

## Implementation Timeline

| Phase | Duration | Deliverables |
| :--- | :--- | :--- |
| Phase 1: Structure | 3 days | New directory structure, moved files, updated imports |
| Phase 2: base.html | 2 days | Split base.html into fragments/components |
| Phase 3: Syntax | 4 days | Convert to match/let/capture/pipeline |
| Phase 4: Caching | 2 days | Add cache directives to expensive fragments |
| Phase 5: Slots | 3 days | Refactor key components to use slots |
| Documentation | 2 days | Update TEMPLATE-CONTEXT.md, add PATTERNS.md |

**Total**: ~2.5 weeks

---

## References

- Kida AST nodes: `bengal/rendering/kida/nodes.py`
- Kida documentation: `bengal/rendering/kida/__init__.py`
- Current templates: `bengal/themes/default/templates/`
- Template context: `bengal/themes/default/templates/TEMPLATE-CONTEXT.md`
- Related RFC: `plan/drafted/rfc-engine-agnostic-context-layer.md`

---

## Appendix: Kida Syntax Quick Reference

### Block Endings

All blocks end with `{% end %}`:

```jinja2
{% if x %}...{% end %}
{% for x in y %}...{% end %}
{% def name() %}...{% end %}
{% match x %}...{% end %}
{% cache key %}...{% end %}
```

### Variable Scoping

```jinja2
{% let x = value %}      {# Template-wide scope #}
{% set x = value %}      {# Block-scoped #}
{% export x = value %}   {# Escape inner scope to parent #}
{% capture x %}...{% end %} {# Capture block to variable #}
```

### Pattern Matching

```jinja2
{% match expression %}
  {% case "value1" %}
    ...
  {% case "value2" %}
    ...
  {% case _ %}
    {# Default fallback #}
{% end %}
```

### Slots (Component Content)

```jinja2
{# Definition #}
{% def card(title) %}
<div class="card">
  <h3>{{ title }}</h3>
  <div class="body">{% slot %}</div>
</div>
{% end %}

{# Usage #}
{% call card("My Title") %}
  <p>This goes in the slot!</p>
{% end %}
```

### Pipeline Operator

```jinja2
{{ items |> where(active=true) |> sort_by('name') |> take(10) }}
```

### Caching

```jinja2
{% cache 'key' %}...{% end %}
{% cache 'key', ttl='5m' %}...{% end %}
{% cache 'dynamic-' ~ page.id %}...{% end %}
```

---

## Changelog

| Date | Change |
| :--- | :--- |
| 2025-12-26 | Initial draft |
