# RFC: Page Hero Template Separation

**Status**: Draft  
**Created**: 2025-01-11  
**Author**: AI Assistant  
**Subsystems**: Rendering, Templates, Autodoc  
**Confidence**: 85% 🟢

---

## Executive Summary

The `page-hero-api.html` template (265 lines) serves two incompatible data contracts: DocElement pages (attribute access) and Section-index pages (dict access). This causes fragile conditional chains and repeated bugs. This RFC proposes separating it into focused templates with a shared include, using established Bengal template patterns.

**Key Changes from v1**:
- Added Phase 0 (regression tests) before refactoring
- Switched from `{% call %}` macro to `{% include %}` + `{% block %}` pattern (established in codebase)
- Added explicit context variable for CLI detection
- Revised time estimates (8-10 hours total)
- Resolved open questions

---

## Problem Statement

### Current State

The `partials/page-hero-api.html` template handles both:
1. **DocElement pages** (modules, classes, functions) - receive `element` with rich dataclass properties
2. **Section-index pages** - receive only `section`, with `element=None`

**Evidence** (`page-hero-api.html:146-148`):
```jinja
{# Complex conditional chains #}
{% set description = element.description if (element and element.description) else
  (page.metadata.get('description', '') if page.metadata.get('description', '') else
   (section.metadata.get('description', '') if section else '')) %}
```

### Problems Identified

1. **Template Overloading**: Single template serves two different contracts
   - Evidence: Lines 21-29 handle `element.children`, lines 231-261 handle `section`

2. **Inconsistent Data Access**:
   - `DocElement.description` is a dataclass attribute (`autodoc/base.py:42`)
   - `Section.metadata` is `dict[str, Any]` (`core/section.py:90`)

3. **Fragile Conditionals**: Multiple fallback chains are error-prone
   - Evidence: 5 separate `{% if element %}` blocks in current template

4. **Magic String Detection**: CLI sections detected via URL sniffing (`page-hero-api.html:236`):
   ```jinja
   {% set is_cli_section = page.url is defined and '/cli' in page.url %}
   ```

5. **Jinja Gotchas**: `is defined` returns `True` for `None`, causing unexpected behavior

### Scope

**7 templates** include `page-hero-api.html`:
- `api-reference/module.html`
- `api-reference/section-index.html`  
- `cli-reference/command.html`
- `cli-reference/command-group.html`
- `cli-reference/section-index.html`
- `api-reference/partials/badges.html` (indirect)
- `partials/page-hero.html`

**0 tests** currently cover these templates.

---

## Goals

1. **Single Responsibility**: Each template handles one use case
2. **Clear Contracts**: Templates document what context they expect
3. **Consistent Access**: No mixing attribute/dict access within a template
4. **Easier Debugging**: Errors point to specific templates, not conditional branches
5. **DRY**: Share common elements (breadcrumbs, actions) via include
6. **Testable**: Regression tests validate behavior before/after migration

## Non-Goals

- Changing the `Section` or `DocElement` data models
- Modifying the rendering pipeline's context passing
- Full template refactoring beyond page hero components
- Introducing new template patterns not established in Bengal

---

## Proposed Solution

### Template Structure

```
themes/default/templates/partials/
├── page-hero/
│   ├── _wrapper.html       # Shared wrapper (breadcrumbs, share dropdown)
│   ├── _share-dropdown.html # Extracted share dropdown component
│   ├── element.html        # For DocElement pages (modules, classes, functions)
│   └── section.html        # For section-index pages (API + CLI)
└── page-hero-api.html      # DEPRECATED: Redirects to appropriate sub-template
```

### Template Contracts

#### `page-hero/_wrapper.html`
**Receives**: `page`, `site`, `config`  
**Renders**: Opening wrapper, breadcrumbs, share dropdown  
**Pattern**: Uses `{% include %}` composition (established pattern in Bengal)

```jinja
{#
  Page Hero Wrapper - shared structure for all API hero variants

  Usage:
    {% include 'partials/page-hero/_wrapper.html' %}
    {# Your badges, title, description, footer here #}
    </div>  {# Close .page-hero #}
#}
{% from 'partials/navigation-components.html' import breadcrumbs with context %}

<div class="page-hero page-hero--api">
  {# Top row: Breadcrumbs (left) + Actions (right) #}
  <div class="page-hero__top">
    <nav class="page-hero__eyebrow" aria-label="Breadcrumb">
      {% set breadcrumb_items = get_breadcrumbs(page) %}
      {% if breadcrumb_items and breadcrumb_items | length > 1 %}
      <ol class="page-hero__breadcrumbs">
        {% for item in breadcrumb_items[:-1] %}
        <li>
          <a href="{{ item.url | absolute_url }}" class="page-hero__breadcrumb-link">{{ item.title }}</a>
        </li>
        {% endfor %}
      </ol>
      {% endif %}
    </nav>

    {# Share dropdown - extracted component #}
    {% include 'partials/page-hero/_share-dropdown.html' %}
  </div>
```

#### `page-hero/element.html`
**Receives**: `element` (DocElement), `page`, `section`, `site`, `config`  
**Contract**: `element` MUST be a DocElement (not None)  
**Lines**: ~60 (target: <80)

```jinja
{#
  Element Hero - for DocElement pages (modules, classes, functions, commands)

  Contract:
    - element: DocElement instance (REQUIRED, not None)
    - page: Page instance
    - section: Section instance (may be None)
    - site: Site instance  
    - config: Autodoc config dict

  Data access: All via element.attribute (dataclass properties)
#}

{# Include shared wrapper (opens .page-hero div) #}
{% include 'partials/page-hero/_wrapper.html' %}

  {# Badges - element type indicators #}
  <div class="page-hero__badges">
    {% include 'api-reference/partials/badges.html' %}
  </div>

  {# Title - qualified name for elements #}
  <h1 class="page-hero__title page-hero__title--code">
    <code>{{ element.qualified_name }}</code>
  </h1>

  {# Description from element (attribute access) #}
  {% if element.description %}
  <div class="page-hero__description page-hero__description--prose">
    {{ element.description | markdownify | safe }}
  </div>
  {% endif %}

  {# Footer: Source link + stats #}
  <div class="page-hero__footer">
    {# Source link #}
    {% if element.source_file and config %}
    <a href="{{ config.github_repo }}/blob/{{ config.github_branch | default('main') }}/{{ element.display_source_file or element.source_file }}{% if element.line_number %}#L{{ element.line_number }}{% endif %}"
       class="page-hero__source-link" target="_blank" rel="noopener">
      {{ icon('file-code', size=14) }}
      <span>View source</span>
    </a>
    {% endif %}

    {# Stats computed from element.children #}
    {% set children = element.children | default([]) %}
    {% include 'partials/page-hero/_element-stats.html' %}
  </div>
</div>
```

#### `page-hero/section.html`
**Receives**: `section` (Section), `page`, `site`, `config`, `hero_context` (optional)  
**Contract**: `section` MUST be a Section object  
**Lines**: ~55 (target: <80)

```jinja
{#
  Section Hero - for section-index pages (API packages, CLI groups)

  Contract:
    - section: Section instance (REQUIRED)
    - page: Page instance
    - site: Site instance
    - config: Autodoc config dict
    - hero_context: Optional dict with explicit flags:
        - is_cli: bool - True if CLI section (explicit, no URL sniffing)

  Data access: All via section.metadata.get() (dict access)
#}

{# Determine section type from explicit context or page type #}
{% set is_cli = hero_context.is_cli if (hero_context and hero_context.is_cli is defined) else (page.type == 'cli-reference') %}

{# Include shared wrapper (opens .page-hero div) #}
{% include 'partials/page-hero/_wrapper.html' %}

  {# No badges for sections #}

  {# Title - section title #}
  <h1 class="page-hero__title">{{ section.title }}</h1>

  {# Description from section metadata (dict access) #}
  {% set desc = section.metadata.get('description', '') %}
  {% if desc %}
  <div class="page-hero__description page-hero__description--prose">
    {{ desc | markdownify | safe }}
  </div>
  {% endif %}

  {# Footer: Stats from section children #}
  <div class="page-hero__footer">
    {% set subsection_count = section.sorted_subsections | length %}
    {% set page_count = section.sorted_pages | rejectattr('source_path', 'match', '.*_index.*') | list | length %}
    {% if subsection_count or page_count %}
    <div class="page-hero__stats">
      {% if subsection_count %}
      <span class="page-hero__stat">
        <span class="page-hero__stat-value">{{ subsection_count }}</span>
        <span class="page-hero__stat-label">{{ 'Group' if is_cli else 'Package' }}{{ 's' if subsection_count != 1 else '' }}</span>
      </span>
      {% endif %}
      {% if page_count %}
      <span class="page-hero__stat">
        <span class="page-hero__stat-value">{{ page_count }}</span>
        <span class="page-hero__stat-label">{{ 'Command' if is_cli else 'Module' }}{{ 's' if page_count != 1 else '' }}</span>
      </span>
      {% endif %}
    </div>
    {% endif %}
  </div>
</div>
```

### Migration Path

#### Phase 0: Regression Tests (Est. 2 hours) - NEW
1. Add snapshot tests for current `page-hero-api.html` output
2. Test API module page rendering (element with children)
3. Test API section-index rendering (section, no element)
4. Test CLI command page rendering (element)
5. Test CLI section-index rendering (section, CLI labels)

**Why**: Currently 0 tests cover these templates. Must establish baseline before refactoring.

#### Phase 1: Create New Templates (Est. 2 hours)
1. Create `partials/page-hero/` directory
2. Extract `_share-dropdown.html` from current template (~70 lines)
3. Implement `_wrapper.html` with shared structure
4. Implement `_element-stats.html` for element children stats
5. Implement `element.html`
6. Implement `section.html`
7. Verify new templates pass Phase 0 tests individually

#### Phase 2: Migration (Est. 4-5 hours)
**API Reference** (1.5 hours):
1. Update `api-reference/module.html` → `page-hero/element.html`
2. Update `api-reference/section-index.html` → `page-hero/section.html`
3. Run Phase 0 tests, verify no regression

**CLI Reference** (2 hours):
1. Update `cli-reference/command.html` → `page-hero/element.html`
2. Update `cli-reference/command-group.html` → `page-hero/element.html`
3. Update `cli-reference/section-index.html` → `page-hero/section.html` with `hero_context.is_cli=true`
4. Run Phase 0 tests, verify no regression

**OpenAPI Reference** (1 hour):
1. Update `openapi-reference/` templates similarly
2. Run Phase 0 tests, verify no regression

#### Phase 3: Cleanup (Est. 1 hour)
1. Add deprecation warning to `page-hero-api.html`
2. Update theme customization documentation
3. Remove unused code paths from deprecated template

**Total Estimate**: 9-10 hours (was 6 hours)

---

## Design Decisions

### Decision 1: Separate vs. Unified Template

**Options**:
- A) Keep unified template, add more guards
- B) Separate templates with shared include

**Chosen**: B - Separate templates

**Rationale**:
- Each template has a clear contract
- No conditional access pattern mixing
- Errors are immediately traceable to specific template
- Follows single responsibility principle

### Decision 2: Include vs. Macro for Base

**Options**:
- A) Use `{% include %}` composition (established pattern)
- B) Use `{% call %}` macro pattern (new pattern)

**Chosen**: A - Include composition

**Rationale**:
- **Established pattern**: `{% include %}` is used throughout Bengal templates
- **Evidence**: `grep 'call.*macro'` found 0 uses in `/themes/default/templates/`
- **Theme compatibility**: Theme customizers already understand include pattern
- **Simpler**: No macro import syntax needed
- **Trade-off**: Slightly less explicit about caller-provided content, but comments document contract

**Pattern**:
```jinja
{# wrapper opens div #}
{% include 'partials/page-hero/_wrapper.html' %}
  {# variant-specific content #}
</div>  {# wrapper expects caller to close #}
```

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

### Decision 4: CLI Detection

**Options**:
- A) URL sniffing (`'/cli' in page.url`) - current approach
- B) Explicit context variable (`hero_context.is_cli`)
- C) Page type check (`page.type == 'cli-reference'`)

**Chosen**: B + C - Explicit context with page type fallback

**Rationale**:
- Magic string detection is fragile (what if URL changes?)
- Explicit `hero_context.is_cli` passed from orchestrator is clearest
- `page.type` fallback provides sensible default
- No URL string matching needed

---

## Architecture Impact

### Affected Components

| Component | Change |
|-----------|--------|
| `partials/page-hero-api.html` | Deprecated, kept as fallback |
| `api-reference/module.html` | Include path change |
| `api-reference/section-index.html` | Include path change |
| `cli-reference/command.html` | Include path change |
| `cli-reference/command-group.html` | Include path change |
| `cli-reference/section-index.html` | Include path change + `hero_context` |
| `openapi-reference/*.html` | Include path change |

### New Files

```
bengal/themes/default/templates/partials/page-hero/
├── _wrapper.html           # Shared wrapper structure (~40 lines)
├── _share-dropdown.html    # Extracted share component (~70 lines)
├── _element-stats.html     # Element children stats (~30 lines)
├── element.html            # DocElement pages (~60 lines)
└── section.html            # Section-index pages (~55 lines)
```

### New Test Files

```
tests/unit/rendering/
└── test_page_hero_templates.py  # Phase 0 regression tests
```

### Backward Compatibility

- `page-hero-api.html` will be kept with a deprecation warning
- Site-level template overrides will continue to work
- No changes to rendering pipeline or context passing
- Existing sites using `page-hero-api.html` will see deprecation warning in dev mode

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template override breakage | Medium | High | Keep old template as fallback for 1 release |
| Missing edge cases | Low | Medium | Phase 0 regression tests before migration |
| CLI label regression | Medium | Medium | Explicit `hero_context.is_cli` + tests |
| Stats display differences | Low | Low | Extract `_element-stats.html` for reuse |
| Performance (more includes) | Low | Low | Jinja caches compiled templates |

---

## Success Criteria

1. ✅ Zero template errors from data access mismatches
2. ✅ Each template file < 80 lines
3. ✅ No `is defined` checks needed for primary context objects
4. ✅ All existing autodoc pages render correctly (verified by Phase 0 tests)
5. ✅ Site-level overrides still work
6. ✅ CLI sections show correct labels (Groups/Commands vs Packages/Modules)
7. ✅ No magic string URL detection

---

## Implementation Plan

### Phase 0: Regression Tests (Est. 2 hours)
- [ ] Create `tests/unit/rendering/test_page_hero_templates.py`
- [ ] Test: API module page with `element` (classes, functions)
- [ ] Test: API section-index page with `section` (packages, modules labels)
- [ ] Test: CLI command page with `element` (options, arguments)
- [ ] Test: CLI section-index page with `section` (groups, commands labels)
- [ ] Snapshot current HTML output for each case

### Phase 1: Foundation (Est. 2 hours)
- [ ] Create `partials/page-hero/` directory
- [ ] Extract `_share-dropdown.html` from current template
- [ ] Implement `_wrapper.html` with shared structure
- [ ] Implement `_element-stats.html` for element children stats
- [ ] Implement `element.html`
- [ ] Implement `section.html`

### Phase 2: Migration (Est. 4-5 hours)

**API Reference** (1.5 hours):
- [ ] Update `api-reference/module.html` → `page-hero/element.html`
- [ ] Update `api-reference/section-index.html` → `page-hero/section.html`
- [ ] Run Phase 0 tests, verify no regression

**CLI Reference** (2 hours):
- [ ] Update `cli-reference/command.html` → `page-hero/element.html`
- [ ] Update `cli-reference/command-group.html` → `page-hero/element.html`
- [ ] Update `cli-reference/section-index.html` → `page-hero/section.html`
- [ ] Pass `hero_context={'is_cli': true}` to section template
- [ ] Run Phase 0 tests, verify no regression

**OpenAPI Reference** (1 hour):
- [ ] Audit `openapi-reference/` templates for page-hero usage
- [ ] Update as needed
- [ ] Run Phase 0 tests, verify no regression

### Phase 3: Cleanup (Est. 1 hour)
- [ ] Add deprecation warning to `page-hero-api.html`
- [ ] Update theme customization documentation
- [ ] Document `hero_context` pattern for CLI sections

**Total**: ~9-10 hours

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

**Code Evidence**:
- `bengal/themes/default/templates/partials/page-hero-api.html` - Current 265-line template
- `bengal/autodoc/base.py:40-51` - DocElement dataclass definition
- `bengal/core/section.py:90` - Section.metadata is `dict[str, Any]`

**Related Files**:
- `bengal/themes/default/templates/api-reference/module.html:34` - Uses page-hero-api
- `bengal/themes/default/templates/cli-reference/command.html:29` - Uses page-hero-api

**Documentation**:
- Bengal architecture: `architecture/design-principles.md`
- Jinja best practices: https://jinja.palletsprojects.com/en/3.1.x/templates/

---

## Resolved Questions

1. **Should `page-hero/simple.html` be created for non-API pages?**
   - **Answer**: No. Non-API pages already use `page-hero.html`, `page-hero-editorial.html`, etc.
   - **Rationale**: This RFC focuses on fixing the API template, not expanding scope.

2. **Should the share dropdown be a separate component?**
   - **Answer**: Yes. Extract to `_share-dropdown.html` (~70 lines).
   - **Rationale**: Reusable, testable, reduces template size.

3. **Timeline for deprecating `page-hero-api.html`?**
   - **Answer**: Keep for 1 release cycle with deprecation warning.
   - **Rationale**: Allows site-level overrides to migrate. Remove after 2-3 months.

---

## Evaluation Summary

**v2 Changes** (from initial draft):
- ✅ Added Phase 0 (regression tests) - addresses 0 existing test coverage
- ✅ Switched from `{% call %}` macro to `{% include %}` pattern - established in codebase
- ✅ Added explicit `hero_context.is_cli` - replaces URL string sniffing
- ✅ Revised time estimate: 9-10 hours (was 6 hours)
- ✅ Resolved all open questions
- ✅ Added code evidence references

**Confidence**: 85% 🟢 (was 78% 🟡)

**Ready for**: Move to `evaluated/` after Phase 0 test plan review
