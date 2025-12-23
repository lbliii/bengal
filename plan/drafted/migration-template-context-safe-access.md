# Template Migration Plan: Safe Access Patterns

**RFC:** `rfc-template-context-redesign.md`  
**Status:** Phase 1 Complete  
**Created:** 2024-12-23  

---

## Executive Summary

The template context redesign infrastructure is complete. This document outlines the remaining template migration work to eliminate defensive `.get()` and `is defined` patterns.

### Current State

| Pattern | Original | Current | Remaining |
|---------|----------|---------|-----------|
| `.get()` calls | 776 | 701 | 701 |
| `is defined` checks | 104 | 92 | 92 |
| `or {}` patterns | 3 | 3 | 3 |

### Infrastructure Complete ✅

- [x] `ChainableUndefined` configured in Jinja2
- [x] `SiteContext`, `ConfigContext`, `ThemeContext` wired into globals
- [x] `ParamsContext` with recursive wrapping
- [x] `CascadingParamsContext` for data cascade
- [x] `SectionContext` always available
- [x] `build_page_context()` as single source of truth
- [x] Core templates migrated (base.html, index.html, page.html)
- [x] Build validated (1134 pages)

---

## Migration Priority Tiers

### Tier 1: High-Impact Templates (390 patterns)

These templates have the most defensive patterns and affect the most pages.

| Template | `.get()` | `is defined` | Effort | Notes |
|----------|----------|--------------|--------|-------|
| `resume/single.html` | 100 | 1 | High | Resume data fields |
| `resume/list.html` | 100 | 1 | High | Resume data fields |
| `changelog/list.html` | 63 | 2 | Medium | Release entries |
| `blog/single.html` | 31 | 0 | Medium | Blog post metadata |
| `changelog/single.html` | 31 | 0 | Medium | Release entry |
| `home.html` | 30 | 0 | Medium | Landing page widgets |
| `tutorial/single.html` | 27 | 0 | Medium | Tutorial metadata |
| `blog/list.html` | 20 | 1 | Low | Blog index |
| `tutorial/list.html` | 16 | 1 | Low | Tutorial index |

**Total: 418 patterns across 9 files**

---

### Tier 2: Section Home Templates (70 patterns)

These are section landing pages with widget configurations.

| Template | `.get()` | `is defined` | Effort |
|----------|----------|--------------|--------|
| `autodoc/python/home.html` | 14 | 0 | Low |
| `autodoc/cli/home.html` | 14 | 0 | Low |
| `doc/home.html` | 14 | 0 | Low |
| `blog/home.html` | 9 | 0 | Low |
| `archive-year.html` | 9 | 0 | Low |
| `doc/list.html` | 8 | 0 | Low |
| `autodoc/python/list.html` | 8 | 1 | Low |
| `autodoc/cli/list.html` | 8 | 1 | Low |

**Total: 84 patterns across 8 files**

---

### Tier 3: Partials (50 patterns)

Reusable template fragments.

| Template | `.get()` | `is defined` | Notes |
|----------|----------|--------------|-------|
| `partials/action-bar.html` | 7 | 1 | Page actions |
| `partials/navigation-components.html` | 7 | 1 | Breadcrumbs, nav |
| `partials/page-hero-editorial.html` | 5 | 1 | Hero variant |
| `partials/page-hero-magazine.html` | 5 | 1 | Hero variant |
| `partials/search-modal.html` | 4 | 0 | Search UI |
| `partials/stale-content-banner.html` | 4 | 0 | Content warning |
| `partials/nav-menu.html` | 3 | 1 | Navigation |
| `partials/archive-sidebar.html` | 3 | 0 | Archive nav |
| `partials/page-hero.html` | 2 | 6 | Main hero |
| `partials/page-hero-classic.html` | 2 | 0 | Hero variant |
| `partials/page-hero-overview.html` | 2 | 1 | Hero variant |
| `partials/page-hero/section.html` | 2 | 3 | Section hero |
| `partials/docs-nav.html` | 0 | 2 | Docs navigation |
| `partials/docs-nav-node.html` | 0 | 1 | Nav tree node |
| `partials/version-selector.html` | 0 | 2 | Version picker |
| `partials/tag-nav.html` | 0 | 2 | Tag navigation |
| `partials/meta-generator.html` | 1 | 4 | Meta tags |
| `partials/page-hero/element.html` | 0 | 1 | Element hero |
| `partials/page-hero/_share-dropdown.html` | 0 | 1 | Share dropdown |
| `partials/track-sidebar.html` | 1 | 0 | Track nav |
| `partials/track-helpers.html` | 1 | 0 | Track helpers |

**Total: 49 `.get()` + 28 `is defined` across 21 files**

---

### Tier 4: Autodoc Templates (55 patterns)

API documentation templates with element context.

| Template | `.get()` | `is defined` | Notes |
|----------|----------|--------------|-------|
| `autodoc/openapi/schema.html` | 10 | 0 | OpenAPI schema |
| `autodoc/openapi/endpoint.html` | 6 | 0 | OpenAPI endpoint |
| `autodoc/partials/members.html` | 8 | 8 | Member list |
| `autodoc/partials/_macros/function-member.html` | 6 | 4 | Function macro |
| `autodoc/partials/params-table.html` | 6 | 4 | Params table |
| `autodoc/partials/params-list.html` | 5 | 5 | Params list |
| `autodoc/partials/raises.html` | 2 | 2 | Raises section |
| `autodoc/partials/examples.html` | 0 | 1 | Examples |
| `autodoc/openapi/overview.html` | 0 | 4 | OpenAPI overview |
| `autodoc/python/section-index.html` | 2 | 0 | Python index |
| `autodoc/cli/section-index.html` | 2 | 0 | CLI index |
| `autodoc/openapi/section-index.html` | 2 | 0 | OpenAPI index |
| `autodoc/python/single.html` | 1 | 0 | Python single |
| `autodoc/cli/single.html` | 1 | 0 | CLI single |
| `openapi-reference/schema.html` | 10 | 0 | OpenAPI (legacy) |
| `openapi-reference/endpoint.html` | 6 | 0 | OpenAPI (legacy) |
| `openapi-reference/section-index.html` | 2 | 0 | OpenAPI (legacy) |
| `openapi-reference/overview.html` | 0 | 4 | OpenAPI (legacy) |

**Total: 69 `.get()` + 32 `is defined` across 18 files**

---

### Tier 5: Specialized Templates (33 patterns)

Less frequently used templates.

| Template | `.get()` | `is defined` | Notes |
|----------|----------|--------------|-------|
| `author.html` | 10 | 1 | Author page |
| `author/single.html` | 8 | 1 | Author single |
| `author/list.html` | 8 | 0 | Author list |
| `category-browser.html` | 8 | 0 | Category browse |
| `archive.html` | 4 | 2 | Archive index |
| `api-hub/home.html` | 4 | 1 | API hub |
| `api-hub/section-index.html` | 3 | 1 | API hub index |
| `tracks/single.html` | 1 | 0 | Learning track |
| `doc/single.html` | 1 | 0 | Doc single |

**Total: 47 `.get()` + 6 `is defined` across 9 files**

---

## Migration Patterns

### Pattern 1: Simple Config Access

```jinja2
{# BEFORE #}
{{ config.get('title', '') }}
{{ params.get('author', '') }}

{# AFTER #}
{{ config.title }}
{{ params.author }}
```

### Pattern 2: Nested Config Access

```jinja2
{# BEFORE #}
{{ config.get('i18n', {}).get('default_language', 'en') }}

{# AFTER #}
{{ config.i18n.default_language | default('en') }}
```

### Pattern 3: Conditional with Default

```jinja2
{# BEFORE #}
{% if params.get('hero_style') %}
  {% set hero = params.get('hero_style') %}
{% endif %}

{# AFTER #}
{% if params.hero_style %}
  {% set hero = params.hero_style %}
{% endif %}
```

### Pattern 4: `is defined` Check

```jinja2
{# BEFORE #}
{% if page is defined and page %}
{% if section is defined and section %}

{# AFTER #}
{% if page %}
{% if section %}
```

### Pattern 5: `or {}` Fallback

```jinja2
{# BEFORE #}
{% set opts = (params.hero or {}).get('options', {}) %}

{# AFTER #}
{% set opts = params.hero.options %}
```

### Pattern 6: Metadata Access

```jinja2
{# BEFORE #}
{{ article.metadata.get('author', '') }}
{{ section.metadata.get('description', '') }}

{# AFTER #}
{{ article.metadata.author }}
{{ section.params.description }}
```

### Pattern 7: Theme Config

```jinja2
{# BEFORE #}
{{ theme.config.get('hero_style', 'default') }}
{% if theme.features.get('navigation.toc') %}

{# AFTER #}
{{ theme.hero_style | default('default') }}
{% if theme.has('navigation.toc') %}
```

---

## Batch Migration Scripts

### Find and Replace Patterns

```bash
# Find all .get() patterns
rg "\.get\(" bengal/themes/default/templates/ --glob "*.html"

# Find is defined patterns
rg "is defined" bengal/themes/default/templates/ --glob "*.html"

# Find or {} patterns
rg "or \{\}" bengal/themes/default/templates/ --glob "*.html"
```

### Common Replacements (Regex)

| Pattern | Find | Replace |
|---------|------|---------|
| Simple get | `params\.get\(['"](\w+)['"]\)` | `params.$1` |
| Get with default | `params\.get\(['"](\w+)['"],\s*['"](\w*)['"]?\)` | `params.$1 \| default('$2')` |
| Config get | `config\.get\(['"](\w+)['"]\)` | `config.$1` |
| Metadata get | `\.metadata\.get\(['"](\w+)['"]\)` | `.metadata.$1` |
| is defined and | `(\w+) is defined and \1` | `$1` |

---

## Commit Strategy

Follow atomic commits per batch:

```
refactor(templates): migrate home.html to safe access patterns
refactor(templates): migrate blog templates to safe access patterns
refactor(templates): migrate changelog templates to safe access patterns
refactor(templates): migrate tutorial templates to safe access patterns
refactor(templates): migrate partials to safe access patterns
refactor(templates): migrate autodoc templates to safe access patterns
refactor(templates): migrate resume templates to safe access patterns
refactor(templates): migrate author templates to safe access patterns
refactor(templates): migrate remaining templates to safe access patterns
```

---

## Validation Checklist

After each batch migration:

- [ ] Run build: `bengal build site/`
- [ ] Check for template errors in output
- [ ] Verify no `UndefinedError` exceptions
- [ ] Spot-check rendered pages visually

---

## Rollback Plan

If issues arise:

1. Git revert the specific template batch
2. Templates using old patterns still work (ChainableUndefined is permissive)
3. Infrastructure changes are backward compatible

---

## Timeline Estimate

| Tier | Files | Patterns | Estimated Time |
|------|-------|----------|----------------|
| Tier 1 | 9 | 418 | 4 hours |
| Tier 2 | 8 | 84 | 1 hour |
| Tier 3 | 21 | 77 | 2 hours |
| Tier 4 | 18 | 101 | 2 hours |
| Tier 5 | 9 | 53 | 1 hour |
| **Total** | **65** | **733** | **~10 hours** |

---

## Success Criteria

- [ ] `rg "\.get\(" templates/ | wc -l` returns 0 (excluding .md docs)
- [ ] `rg "is defined" templates/ | wc -l` returns 0 (excluding .md docs)
- [ ] `rg "or {}" templates/ | wc -l` returns 0
- [ ] All existing tests pass
- [ ] Bengal docs site builds without error
- [ ] No visual regressions in rendered output

---

## Notes

### Resume Templates (200 patterns)

The resume templates have the highest pattern count (200 combined). These access deeply nested resume data structures:

```jinja2
{# Common patterns in resume templates #}
{{ resume.get('basics', {}).get('name', '') }}
{{ resume.get('work', []) }}
{{ job.get('highlights', []) }}
```

Consider creating a `ResumeContext` wrapper class if resume templates are a priority, or migrate incrementally with the existing infrastructure.

### Autodoc Templates

Autodoc templates access `element` context which contains API documentation data:

```jinja2
{# Common patterns #}
{{ element.metadata.get('description', '') }}
{% if element.children is defined %}
```

These are already safe due to ChainableUndefined, but migration improves readability.
