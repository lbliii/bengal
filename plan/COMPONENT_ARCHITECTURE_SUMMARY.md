# Component Architecture Summary

**TL;DR:** No new layer. Domain-grouped macro files in `partials/`.

## The Answer to Your Question

> "does this add a third layer that needs to be organized?"

**No.** Everything stays in `partials/`, just with clear naming:

```
partials/
├── reference-components.html    # Macros for reference docs
├── navigation-components.html   # Macros for navigation
├── content-components.html      # Macros for content display
├── breadcrumbs.html             # Old include (to deprecate)
└── docs-nav.html                # Complex include (keep)
```

**Naming convention:** `*-components.html` = macros, everything else = includes

## Three Patterns in Bengal Templates

### 1. Layouts (Extends) - Page Structure
```jinja2
{% extends 'layouts/docs.html' %}
```
**Use for:** Base HTML structure, page templates

### 2. Components (Macros) - Reusable UI ← **NEW DEFAULT**
```jinja2
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(items) }}
```
**Use for:** Small, reusable components with parameters

### 3. Includes - Complex Chunks ← **LIMITED USE**
```jinja2
{% include 'partials/docs-nav.html' %}
```
**Use for:** Large, complex, context-heavy chunks (>100 lines)

## What Gets Converted

### ✅ Convert to Macros (11 components)
Small, reusable, parameter-driven:
- article-card
- breadcrumbs  
- child-page-tiles
- page-navigation
- pagination
- popular-tags
- random-posts
- reference-header ✅ done
- reference-metadata ✅ done
- section-navigation
- tag-list
- toc-sidebar

### ⚠️ Keep as Includes (3-5 components)
Large, complex, context-dependent:
- docs-nav (recursive tree, 100+ lines)
- docs-nav-section (helper for above)
- docs-meta (complex metadata)
- search (stateful interface)

## Organization Strategy

### Domain-Grouped Files
Each component file contains related macros:

**`reference-components.html`** - Reference documentation
```jinja2
{% macro reference_header(icon, title, description=None) %}
{% macro reference_metadata(metadata) %}
{% macro api_signature(signature) %}
```

**`navigation-components.html`** - Navigation elements  
```jinja2
{% macro breadcrumbs(items, separator='/') %}
{% macro pagination(current, total, base_url) %}
{% macro toc(headings, max_depth=3) %}
```

**`content-components.html`** - Content display
```jinja2
{% macro article_card(post, show_excerpt=True) %}
{% macro tag_list(tags, show_count=True) %}
{% macro child_page_tiles(pages, columns=3) %}
```

### File Size Guidelines
- **Small:** < 100 lines ✅
- **Medium:** 100-300 lines ✅
- **Large:** 300-500 lines ⚠️
- **Too Large:** > 500 lines ❌ (split into multiple files)

## Usage Pattern

### In Templates
```jinja2
{# Import what you need #}
{% from 'partials/reference-components.html' import reference_header %}
{% from 'partials/navigation-components.html' import breadcrumbs, pagination %}
{% from 'partials/content-components.html' import article_card %}

{# Use like functions #}
{{ reference_header(icon='📦', title=page.title) }}
{{ breadcrumbs() }}

{% for post in posts %}
  {{ article_card(post) }}
{% endfor %}

{{ pagination(current=1, total=10, base_url='/blog/') }}
```

## Benefits

### No New Layer
- ✅ Everything in `partials/` (familiar)
- ✅ Clear naming convention (`*-components.html`)
- ✅ No new directories to learn
- ✅ Gradual migration path

### Better Organization
- ✅ Related components grouped together
- ✅ Easy to find (domain-based names)
- ✅ Scalable (add more files as needed)
- ✅ Each file ~100-200 lines (manageable)

### Better DX
- ✅ Explicit parameters (self-documenting)
- ✅ Fails fast (errors on typos)
- ✅ No scope pollution
- ✅ Easy to refactor
- ✅ IDE-friendly

## Migration Timeline

**Week 1:** Navigation components (breadcrumbs, pagination, etc.)
**Week 2:** Content components (cards, tiles, tags, etc.)  
**Week 3:** Update all templates
**Week 4:** Documentation and deprecation warnings

**Bengal 1.0:** Remove old includes

## Answer: Is it a third layer?

**No.** It's a better **organization pattern within the existing `partials/` layer**.

- Layouts = Structure (extends)
- Partials = Reusable pieces (includes + macros)
  - `*-components.html` = Macros ← better pattern
  - `*.html` = Includes ← limited use

Same layer, clearer organization, better ergonomics.
