# RFC: Page Hero Template Separation

**Status**: Draft  
**Created**: 2025-01-11  
**Author**: AI Assistant  
**Subsystems**: Rendering, Templates, Autodoc

---

## Executive Summary

The `page-hero-api.html` template currently serves two distinct use cases with incompatible data shapes, leading to fragile conditional logic and repeated bugs. This RFC proposes separating it into focused templates with a shared base, improving maintainability and reducing template complexity.

---

## Problem Statement

### Current State

The `partials/page-hero-api.html` template handles both:
1. **DocElement pages** (modules, classes, functions) - receive `element` with rich properties
2. **Section-index pages** - receive only `section`, with `element=None`

This leads to:

```jinja
{# Complex conditional chains #}
{% set description = element.description if (element and element.description) else
  (page.metadata.get('description', '') if page.metadata.get('description', '') else
   (section.metadata.get('description', '') if section else '')) %}
```

### Problems Identified

1. **Template Overloading**: Single template serves two different contracts
2. **Inconsistent Data Access**:
   - `element.description` (attribute access)
   - `section.metadata.get('description')` (dict access)
3. **Fragile Conditionals**: Multiple fallback chains are error-prone
4. **Debugging Difficulty**: Errors like `'None' has no attribute 'element_type'` or `'dict object' has no attribute 'description'` require tracing through complex logic
5. **Jinja Gotchas**: `is defined` returns `True` for `None`, causing unexpected behavior

### Evidence

Recent bug cascade (2025-01-11):
- Issue 1: `Section` passed as `element` → `'Section object' has no attribute 'element_type'`
- Issue 2: Fixed to `element=None` → `'None' has no attribute 'element_type'`
- Issue 3: Fixed `is defined` → `'dict object' has no attribute 'description'`

Each fix revealed another layer of the architectural mismatch.

---

## Goals

1. **Single Responsibility**: Each template handles one use case
2. **Clear Contracts**: Templates document what context they expect
3. **Consistent Access**: No mixing attribute/dict access within a template
4. **Easier Debugging**: Errors point to specific templates, not conditional branches
5. **DRY**: Share common elements (breadcrumbs, actions) via base template

## Non-Goals

- Changing the `Section` or `DocElement` data models
- Modifying the rendering pipeline's context passing
- Full template refactoring beyond page hero components

---

## Proposed Solution

### Template Structure

```
themes/default/templates/partials/
├── page-hero/
│   ├── _base.html          # Shared structure (breadcrumbs, share dropdown)
│   ├── element.html        # For DocElement pages (modules, classes, functions)
│   ├── section.html        # For section-index pages
│   └── simple.html         # For non-API pages (docs, blog) - optional
└── page-hero-api.html      # DEPRECATED: Redirects to appropriate sub-template
```

### Template Contracts

#### `page-hero/_base.html`
**Receives**: `page`, `site`, `config`  
**Renders**: Breadcrumbs, share dropdown, wrapper structure

```jinja
{# Base hero structure - shared by all variants #}
{% macro hero_wrapper(title, description='', show_badges=false) %}
<div class="page-hero page-hero--api">
  {# Breadcrumbs #}
  <div class="page-hero__top">
    <nav class="page-hero__eyebrow" aria-label="Breadcrumb">
      {% set breadcrumb_items = get_breadcrumbs(page) %}
      {% if breadcrumb_items and breadcrumb_items | length > 1 %}
      <ol class="page-hero__breadcrumbs">
        {% for item in breadcrumb_items[:-1] %}
        <li><a href="{{ item.url | absolute_url }}">{{ item.title }}</a></li>
        {% endfor %}
      </ol>
      {% endif %}
    </nav>
    {# Share dropdown - same for all #}
    {% include 'partials/page-hero/_share-dropdown.html' %}
  </div>

  {# Caller provides badges, title, description, footer #}
  {{ caller() }}
</div>
{% endmacro %}
```

#### `page-hero/element.html`
**Receives**: `element` (DocElement), `page`, `section`, `site`, `config`  
**Contract**: `element` MUST be a DocElement (not None)

```jinja
{# Element hero - for modules, classes, functions #}
{% from 'partials/page-hero/_base.html' import hero_wrapper %}

{% call hero_wrapper(element.qualified_name or element.name) %}
  {# Badges - element type indicators #}
  <div class="page-hero__badges">
    {% include 'api-reference/partials/badges.html' %}
  </div>

  {# Title - always qualified name for elements #}
  <h1 class="page-hero__title page-hero__title--code">
    <code>{{ element.qualified_name }}</code>
  </h1>

  {# Description from element #}
  {% if element.description %}
  <div class="page-hero__description">
    {{ element.description | markdownify | safe }}
  </div>
  {% endif %}

  {# Footer: Source link + stats #}
  <div class="page-hero__footer">
    {% if element.source_file and config %}
    <a href="{{ config.github_repo }}/blob/{{ config.github_branch | default('main') }}/{{ element.display_source_file or element.source_file }}{% if element.line_number %}#L{{ element.line_number }}{% endif %}"
       class="page-hero__source-link" target="_blank">
      {{ icon('file-code', size=14) }} View source
    </a>
    {% endif %}

    {# Stats from element.children #}
    {% set classes = element.children | selectattr('element_type', 'eq', 'class') | list %}
    {% set functions = element.children | selectattr('element_type', 'eq', 'function') | list %}
    {% if classes or functions %}
    <div class="page-hero__stats">
      {% if classes %}<span class="page-hero__stat">{{ classes | length }} Classes</span>{% endif %}
      {% if functions %}<span class="page-hero__stat">{{ functions | length }} Functions</span>{% endif %}
    </div>
    {% endif %}
  </div>
{% endcall %}
```

#### `page-hero/section.html`
**Receives**: `section` (Section), `page`, `site`, `config`  
**Contract**: `section` MUST be a Section object

```jinja
{# Section hero - for section-index pages #}
{% from 'partials/page-hero/_base.html' import hero_wrapper %}

{% call hero_wrapper(section.title) %}
  {# No badges for sections #}

  {# Title - section title #}
  <h1 class="page-hero__title">{{ section.title }}</h1>

  {# Description from section metadata (dict access) #}
  {% set desc = section.metadata.get('description', '') %}
  {% if desc %}
  <div class="page-hero__description">
    {{ desc | markdownify | safe }}
  </div>
  {% endif %}

  {# Footer: Stats from section children #}
  <div class="page-hero__footer">
    {% set subsection_count = section.sorted_subsections | length %}
    {% set page_count = section.sorted_pages | rejectattr('source_path', 'match', '.*_index.*') | list | length %}
    {% if subsection_count or page_count %}
    <div class="page-hero__stats">
      {% if subsection_count %}<span class="page-hero__stat">{{ subsection_count }} Packages</span>{% endif %}
      {% if page_count %}<span class="page-hero__stat">{{ page_count }} Modules</span>{% endif %}
    </div>
    {% endif %}
  </div>
{% endcall %}
```

### Migration Path

#### Phase 1: Create New Templates (Non-breaking)
1. Create `partials/page-hero/` directory
2. Implement `_base.html`, `element.html`, `section.html`
3. Keep `page-hero-api.html` unchanged

#### Phase 2: Update Consumers
1. Update `api-reference/module.html` to use `page-hero/element.html`
2. Update `api-reference/section-index.html` to use `page-hero/section.html`
3. Update `cli-reference/` templates similarly
4. Update `openapi-reference/` templates similarly

#### Phase 3: Deprecate Old Template
1. Add deprecation warning to `page-hero-api.html`
2. After one release cycle, remove it

---

## Design Decisions

### Decision 1: Separate vs. Unified Template

**Options**:
- A) Keep unified template, add more guards
- B) Separate templates with shared base

**Chosen**: B - Separate templates

**Rationale**:
- Each template has a clear contract
- No conditional access pattern mixing
- Errors are immediately traceable to specific template
- Follows single responsibility principle

### Decision 2: Macro vs. Include for Base

**Options**:
- A) Use `{% include %}` with block overrides
- B) Use `{% call %}` macro pattern

**Chosen**: B - Call macro pattern

**Rationale**:
- More explicit about what's customizable
- Better IDE support (macros show parameters)
- Cleaner composition than block inheritance for partials

### Decision 3: Where to Put the Logic

**Options**:
- A) Smart templates that detect context type
- B) Dumb templates, orchestrator chooses which to include
- C) View model pattern (normalize data before template)

**Chosen**: B - Orchestrator chooses template

**Rationale**:
- Templates stay simple
- Logic in Python is easier to test
- Can implement C later if needed

---

## Architecture Impact

### Affected Components

| Component | Change |
|-----------|--------|
| `partials/page-hero-api.html` | Deprecated, replaced |
| `api-reference/module.html` | Include path change |
| `api-reference/section-index.html` | Include path change |
| `cli-reference/*.html` | Include path change |
| `openapi-reference/*.html` | Include path change |

### New Files

```
bengal/themes/default/templates/partials/page-hero/
├── _base.html
├── _share-dropdown.html
├── element.html
└── section.html
```

### Backward Compatibility

- `page-hero-api.html` will be kept with a deprecation warning
- Site-level template overrides will continue to work
- No changes to rendering pipeline or context passing

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template override breakage | Medium | High | Keep old template as fallback |
| Missing edge cases | Low | Medium | Comprehensive testing |
| Performance (more includes) | Low | Low | Jinja caches compiled templates |

---

## Success Criteria

1. ✅ Zero template errors from data access mismatches
2. ✅ Each template file < 80 lines
3. ✅ No `is defined` checks needed for primary context objects
4. ✅ All existing autodoc pages render correctly
5. ✅ Site-level overrides still work

---

## Implementation Plan

### Phase 1: Foundation (Est. 2 hours)
- [ ] Create `partials/page-hero/` directory
- [ ] Implement `_base.html` with shared structure
- [ ] Implement `_share-dropdown.html` (extract from current)
- [ ] Implement `element.html`
- [ ] Implement `section.html`

### Phase 2: Migration (Est. 3 hours)
- [ ] Update `api-reference/module.html`
- [ ] Update `api-reference/section-index.html`
- [ ] Update `cli-reference/command.html`
- [ ] Update `cli-reference/command-group.html`
- [ ] Update `cli-reference/section-index.html`
- [ ] Update `openapi-reference/` templates

### Phase 3: Cleanup (Est. 1 hour)
- [ ] Add deprecation warning to `page-hero-api.html`
- [ ] Update documentation
- [ ] Add tests for template rendering

---

## Alternatives Considered

### Alternative 1: View Model Pattern

Normalize data in Python before passing to templates:

```python
@dataclass
class HeroContext:
    title: str
    description: str | None
    badges: list[str]
    stats: dict[str, int]
    source_link: str | None
```

**Pros**: Templates become trivial, data access is uniform  
**Cons**: More Python code, harder to customize in themes  
**Verdict**: Good idea for future, but higher effort

### Alternative 2: Make Section Have Same API as DocElement

Add properties to `Section` class:

```python
class Section:
    @property
    def element_type(self) -> str | None:
        return None

    @property
    def description(self) -> str | None:
        return self.metadata.get('description')
```

**Pros**: Templates don't need changes  
**Cons**: Pollutes `Section` API with unrelated concerns (we tried this - it's a hack)  
**Verdict**: Rejected - leaky abstraction

### Alternative 3: Template Helper Functions

Add Jinja functions for safe access:

```jinja
{{ get_description(element, section, page) }}
```

**Pros**: Centralizes access logic  
**Cons**: Still mixing concerns in one template, harder to understand  
**Verdict**: Partial solution, doesn't address root cause

---

## References

- Related bug fixes: Session 2025-01-11 (this conversation)
- Bengal architecture: `architecture/design-principles.md`
- Jinja best practices: https://jinja.palletsprojects.com/en/3.1.x/templates/

---

## Open Questions

1. Should `page-hero/simple.html` be created for non-API pages (docs, blog)?
2. Should the share dropdown be a separate component or inline in base?
3. Timeline for deprecating `page-hero-api.html`?
