# RFC-002: Template Organization & Naming

**Status**: ❌ Archived  
**Created**: 2024-12-08  
**Archived**: 2024-12-08  
**Part of**: [Theme Architecture Series](../active/rfc-theme-architecture-series.md)  

---

> **Why Archived**: Template renaming (`single.html` → `article.html`) creates migration burden with no functional benefit. Hugo-style naming is familiar and works fine. Current template resolution handles all use cases.  

---

## Summary

Reorganize theme templates with clearer naming conventions, separating layouts from content-type templates, and introducing a macros directory for reusable Jinja2 logic.

---

## Problem Statement

### Current State

```
themes/default/templates/
├── 404.html
├── archive-year.html
├── archive.html
├── author.html
├── base.html
├── home.html
├── index.html              # Unused?
├── page.html
├── post.html
├── search.html
├── tag.html
├── tags.html
├── api-reference/
│   ├── home.html
│   ├── list.html
│   └── single.html
├── blog/
│   ├── home.html
│   ├── list.html
│   └── single.html
├── cli-reference/
│   └── ...
├── doc/
│   └── ...
├── partials/
│   └── (25 files)
└── ...
```

### Problems

1. **Hugo naming legacy** - `single.html`, `list.html` conventions unclear
2. **Flat structure for some, nested for others** - Inconsistent
3. **No macros directory** - Reusable logic scattered in partials
4. **Unclear hierarchy** - What extends what?
5. **Partials overloaded** - Mix of includes and callable components

---

## Proposal

### New Structure

```
themes/default/templates/
├── layouts/                    # Base layouts (skeletons)
│   ├── base.html               # Root HTML structure
│   ├── page.html               # Generic content page
│   ├── listing.html            # List/archive layout
│   ├── home.html               # Homepage layout
│   └── minimal.html            # Minimal layout (no nav/footer)
│
├── content-types/              # Type-specific templates
│   ├── blog/
│   │   ├── article.html        # Blog post (extends layouts/page)
│   │   ├── feed.html           # Blog listing (extends layouts/listing)
│   │   └── home.html           # Blog index
│   ├── docs/
│   │   ├── page.html           # Doc page (3-column layout)
│   │   ├── section.html        # Section index
│   │   └── home.html           # Docs landing
│   ├── api-reference/
│   │   ├── module.html         # API module page
│   │   ├── section.html        # API section index
│   │   └── home.html           # API landing
│   ├── cli-reference/
│   │   ├── command.html        # CLI command page
│   │   └── ...
│   └── tutorial/
│       └── ...
│
├── pages/                      # Standalone pages
│   ├── 404.html
│   ├── search.html
│   ├── tags.html
│   └── archive.html
│
├── partials/                   # Includable fragments
│   ├── head.html               # <head> content
│   ├── header.html             # Site header
│   ├── footer.html             # Site footer
│   ├── nav/
│   │   ├── main.html           # Main navigation
│   │   ├── mobile.html         # Mobile navigation
│   │   ├── docs-sidebar.html   # Docs sidebar
│   │   └── breadcrumbs.html
│   ├── content/
│   │   ├── hero.html           # Page hero section
│   │   ├── toc.html            # Table of contents
│   │   └── pagination.html
│   └── meta/
│       ├── og-tags.html        # Open Graph tags
│       └── schema.html         # JSON-LD schema
│
└── macros/                     # Callable Jinja2 macros
    ├── components.html         # UI components (cards, buttons, badges)
    ├── navigation.html         # Nav macros (breadcrumbs, menu)
    ├── content.html            # Content macros (code blocks, callouts)
    ├── forms.html              # Form macros
    └── api.html                # API documentation macros
```

### Naming Conventions

| Convention | Example | Use Case |
|------------|---------|----------|
| `layouts/*.html` | `layouts/page.html` | Skeleton layouts |
| `content-types/<type>/<variant>.html` | `content-types/blog/article.html` | Content type templates |
| `pages/<name>.html` | `pages/404.html` | Standalone pages |
| `partials/<category>/<name>.html` | `partials/nav/main.html` | Includable fragments |
| `macros/<domain>.html` | `macros/components.html` | Callable macros |

### Layouts vs Content-Types

**Layouts** define structural skeletons:

```jinja2
{# layouts/page.html #}
{% extends "layouts/base.html" %}

{% block body_class %}layout-page{% endblock %}

{% block main %}
<main class="page-layout">
  {% block page_header %}{% endblock %}

  <article class="page-content">
    {% block content %}{% endblock %}
  </article>

  {% block page_footer %}{% endblock %}
</main>
{% endblock %}
```

**Content-types** add type-specific structure:

```jinja2
{# content-types/blog/article.html #}
{% extends "layouts/page.html" %}

{% block page_header %}
  {% include 'partials/content/hero.html' %}
  <div class="article-meta">
    <time>{{ page.date | dateformat }}</time>
    <span class="author">{{ page.author }}</span>
  </div>
{% endblock %}

{% block content %}
  {{ content | safe }}

  {% if page.tags %}
    {% include 'partials/meta/tags.html' %}
  {% endif %}
{% endblock %}

{% block page_footer %}
  {% include 'partials/content/pagination.html' %}
{% endblock %}
```

### Macros vs Partials

**Partials** are included fragments (stateless, context-dependent):

```jinja2
{# partials/nav/breadcrumbs.html #}
<nav class="breadcrumbs" aria-label="Breadcrumb">
  <ol>
    {% for crumb in page.breadcrumbs %}
    <li><a href="{{ crumb.url }}">{{ crumb.title }}</a></li>
    {% endfor %}
  </ol>
</nav>

{# Usage #}
{% include 'partials/nav/breadcrumbs.html' %}
```

**Macros** are callable with parameters (reusable, explicit inputs):

```jinja2
{# macros/components.html #}
{% macro card(title, variant='default', href=none) %}
<div class="card card--{{ variant }}">
  {% if href %}<a href="{{ href }}">{% endif %}
    <h3 class="card__title">{{ title }}</h3>
    <div class="card__body">{{ caller() }}</div>
  {% if href %}</a>{% endif %}
</div>
{% endmacro %}

{% macro badge(text, variant='default') %}
<span class="badge badge--{{ variant }}">{{ text }}</span>
{% endmacro %}

{% macro button(text, href=none, variant='primary', size='md') %}
{% if href %}
<a href="{{ href }}" class="btn btn--{{ variant }} btn--{{ size }}">{{ text }}</a>
{% else %}
<button class="btn btn--{{ variant }} btn--{{ size }}">{{ text }}</button>
{% endif %}
{% endmacro %}

{# Usage #}
{% from 'macros/components.html' import card, badge, button %}

{% call card('My Card', variant='elevated', href='/page') %}
  <p>Card content goes here.</p>
{% endcall %}

{{ badge('New', variant='success') }}
{{ button('Click Me', href='/action', variant='primary') }}
```

### Template Resolution

When resolving a template for a page:

1. **Explicit** - `template: content-types/blog/article.html` in frontmatter
2. **Type-based** - `type: blog` → `content-types/blog/article.html`
3. **Kind-based** - `kind: list` → appropriate list template
4. **Fallback** - `layouts/page.html`

Resolution order for `type: blog`:
```
1. content-types/blog/article.html  (explicit type template)
2. content-types/blog/single.html   (legacy name, deprecated)
3. layouts/page.html                (fallback)
```

### Backward Compatibility

Old paths continue to work with deprecation warnings:

| Old Path | New Path | Status |
|----------|----------|--------|
| `single.html` | `layouts/page.html` | Deprecated |
| `list.html` | `layouts/listing.html` | Deprecated |
| `blog/single.html` | `content-types/blog/article.html` | Deprecated |
| `post.html` | `content-types/blog/article.html` | Deprecated |
| `partials/docs-nav.html` | `partials/nav/docs-sidebar.html` | Deprecated |

---

## Benefits

1. **Clear hierarchy** - Layouts → Content-types → Pages
2. **Discoverable** - Directory names explain purpose
3. **Composable** - Macros enable reuse without duplication
4. **Extensible** - Add new content-types easily
5. **Familiar** - Similar to Django, Rails template conventions

---

## Implementation

### Phase 1: Create New Structure
- [ ] Create `layouts/` directory with base templates
- [ ] Create `content-types/` with migrated templates
- [ ] Create `macros/` with extracted reusable logic
- [ ] Reorganize `partials/` into subcategories

### Phase 2: Update Resolution
- [ ] Update template resolver to check new paths
- [ ] Add deprecation warnings for old paths
- [ ] Update virtual orchestrator for new paths

### Phase 3: Migrate Default Theme
- [ ] Move templates to new locations
- [ ] Update all extends/includes
- [ ] Test all page types

### Phase 4: Documentation
- [ ] Document new structure
- [ ] Add template development guide
- [ ] Update theme creation tutorial

---

## Open Questions

1. **Should we support both `single.html` and `article.html` long-term?**  
   Proposal: No, deprecate after v2.0

2. **Where do email templates go?**  
   Proposal: `templates/email/` if we add email support

3. **Should macros auto-load?**  
   Proposal: No, explicit import keeps dependencies clear
