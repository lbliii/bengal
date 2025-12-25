# RFC: Page Hero Template Flattening

**Status**: Draft  
**Created**: 2025-12-25  
**Author**: AI Assistant  
**Subsystem**: Themes (Templates)  
**Confidence**: 90% 🟢 (verified against template source 2025-12-25)  
**Priority**: P3 (Low-Medium) — Template rendering optimization  
**Estimated Effort**: 0.5 days  
**Depends On**: None (standalone optimization)  
**Inspired By**: `docs-nav.html` macro refactor (11,000+ includes → 1 macro)

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Flatten `page-hero.html` dispatcher chain from 5 nested includes to inline macros |
| **Why** | Eliminate per-include overhead (context copy, template lookup, compilation) |
| **Effort** | ~4 hours |
| **Risk** | Low — cosmetic change, no behavior change |
| **Impact** | ~5-10% reduction in template rendering time for autodoc pages |

**The Pattern**: Apply the same macro-based optimization that fixed `docs-nav.html` (11,000+ includes → single macro, ~3× faster) to the `page-hero` template chain.

---

## Problem Statement

### Current Include Chain

The `page-hero.html` template is a **dispatcher** that routes to one of 5 variants, each with potential sub-includes:

```
page-hero.html (dispatcher)
    ↓ (conditional routing - always 1 of these)
    ├── page-hero-editorial.html   → 0 sub-includes
    ├── page-hero-magazine.html    → 0 sub-includes  
    ├── page-hero-overview.html    → 0 sub-includes
    ├── page-hero-classic.html     → 1 sub-include (action-bar.html)
    └── page-hero/element.html     → 4 sub-includes ← HEAVIEST
            ├── _wrapper.html
            │       └── _share-dropdown.html
            ├── autodoc/partials/badges.html
            └── _element-stats.html
```

### Cost Per Include

Each `{% include %}` in Jinja2 incurs:

| Operation | Cost | Frequency |
|-----------|------|-----------|
| Template lookup | O(1) hash | Per include |
| Template compilation | Cached after first | First render only |
| Context copy | O(context_size) | **Per include** ← expensive |
| Result string concatenation | O(output_size) | Per include |

**For autodoc element pages**: 5 includes × context copy = measurable overhead.

### Evidence: docs-nav Success

The `docs-nav-node.html` refactor proved this pattern works:

```
Before: Recursive {% include %} → 11,000+ instantiations/page
After:  Recursive macro        → 1 call, ~3× faster
```

From `docs-nav-node.html`:

```jinja
{# DEPRECATED: Navigation Node Component
Reason: Recursive {% include %} was causing 11,000+ template instantiations
per page render. Converting to a macro eliminates this overhead.
#}
```

---

## Proposed Solution

### Strategy: Inline Macros

Convert the `page-hero` dispatcher and its variants to a single template with inline macros:

```
BEFORE (5 templates, 5 includes for element pages):
  page-hero.html
  page-hero-editorial.html
  page-hero-magazine.html
  page-hero-overview.html
  page-hero-classic.html
  page-hero/element.html
  page-hero/_wrapper.html
  page-hero/_share-dropdown.html
  page-hero/_element-stats.html

AFTER (1 template, 0 includes):
  page-hero.html  ← all variants as macros
```

### Implementation

#### Phase 1: Create Unified page-hero.html with Macros

```jinja
{#
Page Hero Component (Unified)

All hero variants as macros for optimal rendering performance.
Uses same pattern as docs-nav.html macro refactor.

Variants:
- editorial: Clean magazine layout (default for single pages)
- overview: Section index with page count
- magazine: Editorial with container styling
- classic: Traditional action-bar + header
- element: Autodoc elements (modules, classes, commands)
- section: Autodoc section indexes

Usage:
  {% include 'partials/page-hero.html' %}

  Or call macros directly:
  {% from 'partials/page-hero.html' import hero_editorial, hero_element %}
  {{ hero_editorial(page, params) }}
#}

{# =============================================================================
   SHARED COMPONENTS (internal macros)
   ============================================================================= #}

{% macro _share_dropdown() %}
{# Share dropdown - Twitter, LinkedIn, copy link #}
<div class="page-hero__share">
  <button class="page-hero__share-trigger" aria-haspopup="true" aria-expanded="false">
    {{ icon('share-network', size=16) }}
    <span class="visually-hidden">Share</span>
  </button>
  <div class="page-hero__share-menu" role="menu">
    <a href="https://twitter.com/intent/tweet?url={{ page.permalink | urlencode }}&text={{ page.title | urlencode }}"
       target="_blank" rel="noopener" role="menuitem">
      {{ icon('twitter-logo', size=16) }} Twitter
    </a>
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ page.permalink | urlencode }}"
       target="_blank" rel="noopener" role="menuitem">
      {{ icon('linkedin-logo', size=16) }} LinkedIn
    </a>
    <button type="button" data-copy-link="{{ page.permalink }}" role="menuitem">
      {{ icon('link', size=16) }} Copy link
    </button>
  </div>
</div>
{% endmacro %}

{% macro _wrapper_open(page, params, show_share=true) %}
{# Common wrapper opening - breadcrumbs + share #}
<div class="page-hero" data-variant="{{ page.variant or 'default' }}">
  {% if page.breadcrumbs %}
  <nav class="page-hero__breadcrumbs" aria-label="Breadcrumb">
    <ol>
      {% for crumb in page.breadcrumbs %}
      <li>
        {% if crumb.href and not loop.last %}
        <a href="{{ crumb.href }}">{{ crumb.title }}</a>
        {% else %}
        <span aria-current="page">{{ crumb.title }}</span>
        {% endif %}
      </li>
      {% endfor %}
    </ol>
  </nav>
  {% endif %}

  {% if show_share %}
  {{ _share_dropdown() }}
  {% endif %}
{% endmacro %}

{% macro _element_stats(children) %}
{# Stats row for autodoc elements #}
{% set methods = children | selectattr('element_type', 'eq', 'method') | list %}
{% set properties = children | selectattr('element_type', 'eq', 'property') | list %}
{% set classes = children | selectattr('element_type', 'eq', 'class') | list %}
{% set functions = children | selectattr('element_type', 'eq', 'function') | list %}

<div class="page-hero__stats">
  {% if classes %}
  <span class="page-hero__stat">{{ icon('cube', size=14) }} {{ classes | length }} classes</span>
  {% endif %}
  {% if functions %}
  <span class="page-hero__stat">{{ icon('function', size=14) }} {{ functions | length }} functions</span>
  {% endif %}
  {% if methods %}
  <span class="page-hero__stat">{{ icon('brackets-curly', size=14) }} {{ methods | length }} methods</span>
  {% endif %}
  {% if properties %}
  <span class="page-hero__stat">{{ icon('gear', size=14) }} {{ properties | length }} properties</span>
  {% endif %}
</div>
{% endmacro %}

{# =============================================================================
   VARIANT MACROS (public API)
   ============================================================================= #}

{% macro hero_editorial(page, params) %}
{# Editorial: Clean layout for documentation pages (DEFAULT) #}
{{ _wrapper_open(page, params) }}

  <h1 class="page-hero__title">{{ page.title }}</h1>

  {% if page.description %}
  <p class="page-hero__description">{{ page.description }}</p>
  {% endif %}

  {% if page.reading_time %}
  <div class="page-hero__meta">
    <span class="page-hero__reading-time">{{ icon('clock', size=14) }} {{ page.reading_time }} min read</span>
  </div>
  {% endif %}
</div>
{% endmacro %}

{% macro hero_overview(page, params, child_count=0) %}
{# Overview: Section index pages with child count #}
{{ _wrapper_open(page, params) }}

  <h1 class="page-hero__title">{{ page.title }}</h1>

  {% if page.description %}
  <p class="page-hero__description">{{ page.description }}</p>
  {% endif %}

  {% if child_count > 0 %}
  <div class="page-hero__meta">
    <span class="page-hero__page-count">{{ icon('files', size=14) }} {{ child_count }} pages</span>
  </div>
  {% endif %}
</div>
{% endmacro %}

{% macro hero_magazine(page, params) %}
{# Magazine: Editorial with container/background styling #}
<div class="page-hero page-hero--magazine" data-variant="magazine">
  {{ _wrapper_open(page, params, show_share=false) }}

  <div class="page-hero__container">
    <h1 class="page-hero__title">{{ page.title }}</h1>

    {% if page.description %}
    <p class="page-hero__description">{{ page.description }}</p>
    {% endif %}
  </div>
</div>
{% endmacro %}

{% macro hero_classic(page, params) %}
{# Classic: Traditional action-bar + header (legacy) #}
{% include 'partials/action-bar.html' %}

{{ _wrapper_open(page, params, show_share=false) }}
  <h1 class="page-hero__title">{{ page.title }}</h1>

  {% if page.description %}
  <p class="page-hero__description">{{ page.description }}</p>
  {% endif %}
</div>
{% endmacro %}

{% macro hero_element(element, page, config, section=none) %}
{# Element: Autodoc pages (modules, classes, functions, commands) #}
{{ _wrapper_open(page, {}) }}

  {# Badges #}
  <div class="page-hero__badges">
    {% if element.deprecated %}
    <span class="badge badge--deprecated">Deprecated</span>
    {% endif %}
    {% if element.async %}
    <span class="badge badge--async">async</span>
    {% endif %}
    <span class="badge badge--type">{{ element.element_type }}</span>
  </div>

  {# Title - qualified name #}
  <h1 class="page-hero__title page-hero__title--code">
    <code>{{ element.qualified_name }}</code>
  </h1>

  {# Description #}
  {% if element.description %}
  <div class="page-hero__description page-hero__description--prose">
    {{ element.description | markdownify | safe }}
  </div>
  {% endif %}

  {# Footer: Source link + stats #}
  <div class="page-hero__footer">
    {% if element.display_source_file or element.source_file %}
    {% if config %}
    <a href="{{ config.github_repo }}/blob/{{ config.github_branch | default('main') }}/{{ element.display_source_file or element.source_file }}{% if element.line_number %}#L{{ element.line_number }}{% endif %}"
       class="page-hero__source-link" target="_blank" rel="noopener">
      {{ icon('file-code', size=14) }}
      <span>View source</span>
    </a>
    {% endif %}
    {% endif %}

    {% set children = getattr(element, 'children', []) %}
    {{ _element_stats(children) }}
  </div>
</div>
{% endmacro %}

{% macro hero_section(section, page, config) %}
{# Section: Autodoc section indexes #}
{{ _wrapper_open(page, {}) }}

  <h1 class="page-hero__title">{{ section.title or page.title }}</h1>

  {% if section.description or page.description %}
  <p class="page-hero__description">{{ section.description or page.description }}</p>
  {% endif %}

  {% set child_count = section.children | length if section.children else 0 %}
  {% if child_count > 0 %}
  <div class="page-hero__meta">
    <span class="page-hero__page-count">{{ icon('files', size=14) }} {{ child_count }} items</span>
  </div>
  {% endif %}
</div>
{% endmacro %}

{# =============================================================================
   DISPATCHER (backwards-compatible include interface)
   ============================================================================= #}

{# Determine hero style: page variant > frontmatter > template default > theme config #}
{% set _page_variant = page.variant if page else none %}
{% set _page_hero_style = params.hero_style if params else none %}
{% set _template_default = _list_hero_default if _list_hero_default is defined else none %}
{% set _theme_hero_style = theme.config.hero_style | default('editorial') if theme else 'editorial' %}

{% set hero_style = _page_variant if _page_variant else (_page_hero_style if _page_hero_style else (_template_default if _template_default else _theme_hero_style)) %}

{# Route to appropriate macro #}
{% if hero_style == 'magazine' %}
{{ hero_magazine(page, params) }}
{% elif hero_style == 'classic' %}
{{ hero_classic(page, params) }}
{% elif hero_style == 'overview' %}
{{ hero_overview(page, params) }}
{% elif hero_style == 'api' or hero_style == 'element' %}
  {% if element %}
  {{ hero_element(element, page, config, section) }}
  {% elif section %}
  {{ hero_section(section, page, config) }}
  {% else %}
  {{ hero_editorial(page, params) }}
  {% endif %}
{% else %}
{{ hero_editorial(page, params) }}
{% endif %}
```

#### Phase 2: Deprecate Old Templates

Add deprecation notices to old templates (keep for backwards compatibility):

```jinja
{# page-hero-editorial.html #}
{# DEPRECATED: Use {% include 'partials/page-hero.html' %} instead.
   This template is now inlined as a macro for performance.
   See: plan/drafted/rfc-page-hero-template-flattening.md #}
{% from 'partials/page-hero.html' import hero_editorial %}
{{ hero_editorial(page, params) }}
```

#### Phase 3: Update Callers (Optional)

Templates can optionally call macros directly for explicit control:

```jinja
{# Instead of: #}
{% include 'partials/page-hero.html' %}

{# Can use: #}
{% from 'partials/page-hero.html' import hero_element %}
{{ hero_element(element, page, config) }}
```

---

## Impact Analysis

### Performance Improvement

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| Editorial page | 2 includes | 0 includes | ~5% faster |
| Overview page | 2 includes | 0 includes | ~5% faster |
| Autodoc element | 5 includes | 0 includes | ~10% faster |
| Autodoc section | 3 includes | 0 includes | ~8% faster |

**Site-wide estimate** (200-page site with 50 autodoc pages):

```
Before: 150 × 2 includes + 50 × 5 includes = 550 template instantiations
After:  200 × 0 includes                    = 0 template instantiations
                                            ────────────────────────────
                                            550 fewer context copies
```

### Why This Works

Macros vs. Includes:

| Aspect | `{% include %}` | `{% macro %}` |
|--------|-----------------|---------------|
| Template lookup | Per call | Once at import |
| Compilation | Per call (cached) | Once at import |
| Context copy | **Full context copied** | Only explicit args |
| Call overhead | High | Low (function call) |

The key win is **eliminating context copies**. Jinja copies the entire template context for each `{% include %}`, while macros receive only their explicit arguments.

---

## Migration Path

### Phase 1: Implement (Day 1)
- [ ] Create unified `page-hero.html` with all macros
- [ ] Test all 6 variants render correctly
- [ ] Verify no visual regression

### Phase 2: Deprecate (Day 1)
- [ ] Add deprecation notices to old templates
- [ ] Update `page-hero/element.html` to use macro
- [ ] Update `page-hero/section.html` to use macro

### Phase 3: Clean Up (Future)
- [ ] Remove deprecated templates after 1 release cycle
- [ ] Update any direct callers to use macros

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Visual regression | Low | Side-by-side screenshot comparison |
| Missing context variable | Low | Explicit macro args catch missing data |
| Third-party theme breakage | Medium | Keep old templates as shims |

---

## Alternatives Considered

### 1. Keep Current Structure
**Rejected**: Misses easy performance win with proven pattern (docs-nav).

### 2. Server-Side Include Caching
**Rejected**: Jinja doesn't support include-level caching. Would require custom extension.

### 3. Full Template Pre-rendering
**Rejected**: Overkill for this problem. Macros solve it elegantly.

---

## Success Criteria

- [ ] Zero visual regression (screenshot diff)
- [ ] `page-hero` chain: 5 includes → 0 includes
- [ ] Template render time for autodoc pages: ~10% reduction
- [ ] All existing `{% include 'partials/page-hero.html' %}` calls work unchanged

---

## Appendix: Template Include Counts

Current state (from grep analysis):

```
partials/docs-nav.html         → 20+ templates (FIXED with macro ✅)
partials/page-hero.html        → 10+ templates (THIS RFC)
partials/docs-toc-sidebar.html → 10+ templates
partials/action-bar.html       → 8+ templates
```

After this RFC, `page-hero.html` joins `docs-nav.html` as a macro-based template.

---

## References

- `bengal/themes/default/templates/partials/docs-nav.html` — Macro refactor precedent
- `bengal/themes/default/templates/partials/docs-nav-node.html` — Deprecation example
- `plan/drafted/rfc-benchmark-refresh-and-worker-optimization.md` — Benchmark methodology
- Jinja2 docs: [Macros](https://jinja.palletsprojects.com/en/3.1.x/templates/#macros)
