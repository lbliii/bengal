# Implementation Plan: Template Context Redesign

**RFC:** `rfc-template-context-redesign.md`  
**Status:** Draft  
**Estimated Effort:** ~4 days (32 hours)  
**Priority:** P0 (Core DX improvement)

---

## Executive Summary

This plan implements a unified template context system that eliminates defensive coding patterns in templates. The changes are primarily **wiring fixes**—the wrapper infrastructure exists but isn't connected.

### Key Metrics to Eliminate

| Pattern | Current Count | Target |
|---------|---------------|--------|
| `.get()` calls in templates | 776 | 0 |
| `is defined` checks | 104 | 0 |
| `or {}` patterns | 3 | 0 |

---

## Phase 1: Jinja2 Safe Access Configuration

**Duration:** 2 hours  
**Risk:** Low  
**Files:** `bengal/rendering/template_engine/environment.py`

### Tasks

- [ ] **1.1** Import `ChainableUndefined` from jinja2 (line 17-24)
- [ ] **1.2** Replace `StrictUndefined` with `ChainableUndefined` in Environment creation (line 377-380)
- [ ] **1.3** Add `finalize` function to convert `None` to empty string
- [ ] **1.4** Remove `strict_mode` conditional from env_kwargs

### Code Changes

```python
# Line 17: Add to imports
from jinja2 import ChainableUndefined

# Line 380: Replace environment creation
env = Environment(
    **env_kwargs,
    undefined=ChainableUndefined,
    finalize=lambda x: '' if x is None else x,
)
```

### Validation

- [ ] Run `pytest tests/rendering/` - all pass
- [ ] Build site docs - no UndefinedError
- [ ] Verify `{{ missing.nested.key }}` returns empty string

---

## Phase 2: Wire Wrappers into Environment Globals

**Duration:** 2 hours  
**Risk:** Medium  
**Files:** `bengal/rendering/template_engine/environment.py`

### Tasks

- [ ] **2.1** Import context wrappers from `bengal.rendering.context`
- [ ] **2.2** Wrap `site` global with `SiteContext`
- [ ] **2.3** Wrap `config` global with `ConfigContext`
- [ ] **2.4** Wrap `theme` global with `ThemeContext`

### Code Changes

```python
# Line 29: Add import
from bengal.rendering.context import SiteContext, ConfigContext, ThemeContext

# Lines 388-391: Wrap globals
env.globals["site"] = SiteContext(site)
env.globals["config"] = ConfigContext(site.config)
env.globals["theme"] = ThemeContext(site.theme_config) if site.theme_config else ThemeContext._empty()
```

### Validation

- [ ] Verify `{{ site.title }}` works in templates
- [ ] Verify `{{ config.baseurl }}` works
- [ ] Verify `{{ theme.appearance }}` works

---

## Phase 3: Add site.params Property

**Duration:** 1 hour  
**Risk:** Low  
**Files:** `bengal/core/site/properties.py`

### Tasks

- [ ] **3.1** Add `params` property to `SitePropertiesMixin`
- [ ] **3.2** Add `logo` property with fallback chain
- [ ] **3.3** Add unit tests for new properties

### Code Changes

```python
@property
def params(self) -> dict[str, Any]:
    """
    Site-level custom parameters from [params] config section.

    Template usage:
        {{ site.params.repo_url }}
        {{ site.params.author }}
    """
    return self.config.get('params', {})

@property
def logo(self) -> str:
    """Logo URL from config (checks multiple locations)."""
    cfg = self.config
    return (
        cfg.get('logo_image', '') or
        cfg.get('site', {}).get('logo_image', '') or
        ''
    )
```

### Validation

- [ ] Unit test: `site.params` returns dict
- [ ] Unit test: `site.params.missing` doesn't error
- [ ] Unit test: `site.logo` fallback chain works

---

## Phase 4: Enhance Wrapper Classes

**Duration:** 4 hours  
**Risk:** Medium  
**Files:** `bengal/rendering/context.py`

### Tasks

#### 4.1 ParamsContext Enhancements

- [ ] **4.1.1** Add recursive `ParamsContext` wrapping for nested dicts
- [ ] **4.1.2** Add `__iter__` method for iteration
- [ ] **4.1.3** Add `keys()`, `values()`, `items()` methods
- [ ] **4.1.4** Ensure `None` returns `''` not `None`

#### 4.2 SectionContext Enhancements

- [ ] **4.2.1** Add `href` property for section URL
- [ ] **4.2.2** Verify all properties return safe defaults when `_section` is None
- [ ] **4.2.3** Add `params` property returning `ParamsContext`

#### 4.3 ThemeContext Enhancements

- [ ] **4.3.1** Add `config` property returning `ParamsContext`
- [ ] **4.3.2** Ensure `has()` handles None features list

### Code Changes

See RFC Phase 5 for complete implementation.

### Validation

- [ ] Unit test: `ParamsContext({'a': {'b': 'c'}}).a.b` returns `'c'`
- [ ] Unit test: `SectionContext(None).title` returns `''`
- [ ] Unit test: `ThemeContext(theme).has('feature')` works

---

## Phase 5: Update build_page_context()

**Duration:** 2 hours  
**Risk:** Medium  
**Files:** `bengal/rendering/context.py`

### Tasks

- [ ] **5.1** Add `posts` parameter for page lists
- [ ] **5.2** Add `subsections` parameter
- [ ] **5.3** Add pagination context handling
- [ ] **5.4** Handle tag/archive page types
- [ ] **5.5** Ensure all page types get consistent context

### Code Changes

See RFC Phase 6 for complete `build_page_context()` implementation.

### Validation

- [ ] Integration test: Regular page context correct
- [ ] Integration test: Section index page has `posts`
- [ ] Integration test: Tag page has `tag`, `posts`
- [ ] Integration test: Autodoc page has `element`

---

## Phase 6: Refactor Renderer

**Duration:** 4 hours  
**Risk:** High  
**Files:** `bengal/rendering/renderer.py`

### Tasks

- [ ] **6.1** Import `build_page_context` from context.py
- [ ] **6.2** Replace lines 165-178 (manual context dict) with `build_page_context()` call
- [ ] **6.3** Move generated page logic into `build_page_context()`
- [ ] **6.4** Delete `_add_generated_page_context()` (lines 328-358)
- [ ] **6.5** Delete `_add_archive_like_generated_page_context()` (lines 359-398)
- [ ] **6.6** Delete `_add_tag_generated_page_context()` (lines 400-581)
- [ ] **6.7** Delete `_add_tag_index_generated_page_context()` (lines 583-603)
- [ ] **6.8** Delete section context handling (lines 199-268)

### Before/After

```python
# BEFORE (lines 165-178):
context = {
    "page": page,
    "content": Markup(content),
    "title": page.title,
    "metadata": page.metadata,
    "params": page.metadata,
    ...
}

# AFTER:
from bengal.rendering.context import build_page_context

context = build_page_context(
    page=page,
    site=self.site,
    content=content,
)
```

### Validation

- [ ] All template tests pass
- [ ] Build Bengal docs site
- [ ] Verify tag pages render correctly
- [ ] Verify archive pages render correctly
- [ ] Verify autodoc pages render correctly

---

## Phase 7: Update Pipeline Context

**Duration:** 2 hours  
**Risk:** Medium  
**Files:** `bengal/rendering/pipeline/core.py`

### Tasks

- [ ] **7.1** Replace `_build_variable_context()` anonymous class with `SectionContext`
- [ ] **7.2** Use wrappers from context.py instead of inline class

### Code Changes

```python
# Replace lines 739-773
def _build_variable_context(self, page: Page) -> dict[str, Any]:
    from bengal.rendering.context import (
        ParamsContext, SectionContext, ConfigContext
    )

    section = getattr(page, "_section", None)

    return {
        "page": page,
        "site": self.site,
        "config": ConfigContext(self.site.config),
        "params": ParamsContext(page.metadata if hasattr(page, "metadata") else {}),
        "section": SectionContext(section),
    }
```

### Validation

- [ ] Variable substitution in markdown works
- [ ] `{{ section.title }}` works in content

---

## Phase 8: Delete Dead Code

**Duration:** 2 hours  
**Risk:** Low  
**Files:** Multiple

### Tasks

- [ ] **8.1** Remove `SmartDict` class from context.py (if replaced)
- [ ] **8.2** Verify no remaining usages of deleted code
- [ ] **8.3** Update imports in any files that referenced deleted code

### Validation

- [ ] `grep -r "SmartDict" bengal/` returns no runtime usages
- [ ] All tests pass
- [ ] No import errors

---

## Phase 9: Implement Data Cascade

**Duration:** 4 hours  
**Risk:** Medium  
**Files:** `bengal/rendering/context.py`

### Tasks

- [ ] **9.1** Create `CascadingParamsContext` class
- [ ] **9.2** Implement cascade lookup: page → section → site
- [ ] **9.3** Handle nested dict cascading
- [ ] **9.4** Update `build_page_context()` to use `CascadingParamsContext`
- [ ] **9.5** Add documentation for cascade behavior

### Code Changes

See RFC Phase 8 for complete `CascadingParamsContext` implementation.

### Validation

- [ ] Unit test: Page params override section params
- [ ] Unit test: Section params override site params
- [ ] Unit test: Nested dict cascading works
- [ ] Integration test: `{{ params.author }}` shows page author, falls back to section, then site

---

## Phase 10: Migrate Templates

**Duration:** 8 hours  
**Risk:** High  
**Files:** `bengal/themes/default/templates/**/*.html`

### Migration Patterns

| Before | After | Regex Find |
|--------|-------|------------|
| `params.get('x', '')` | `params.x` | `params\.get\(['"](\w+)['"],\s*['"]?['"]?\)` |
| `params.get('x')` | `params.x` | `params\.get\(['"](\w+)['"]\)` |
| `config.get('x')` | `config.x` | `config\.get\(['"](\w+)['"]\)` |
| `{% if x is defined %}` | `{% if x %}` | `if (\w+) is defined` |
| `x is defined and x` | `x` | `(\w+) is defined and \1` |
| `(x or {}).get('y')` | `x.y` | `\((\w+) or \{\}\)\.get` |
| `theme.config.get('x')` | `theme.x` | `theme\.config\.get\(['"](\w+)['"]\)` |

### Files by Priority

**Priority 1 (Core templates):**
- [ ] `base.html` (37 .get(), 3 is defined)
- [ ] `page.html` (1 .get())
- [ ] `index.html` (11 .get(), 5 is defined)

**Priority 2 (Partials):**
- [ ] `partials/content-components.html` (26 .get(), 4 is defined)
- [ ] `partials/page-hero.html` (2 .get(), 6 is defined)
- [ ] `partials/nav-menu.html` (3 .get(), 1 is defined)
- [ ] `partials/action-bar.html` (7 .get(), 1 is defined)
- [ ] `partials/navigation-components.html` (7 .get(), 1 is defined)

**Priority 3 (Section templates):**
- [ ] `blog/home.html`, `blog/list.html`, `blog/single.html`
- [ ] `doc/home.html`, `doc/list.html`, `doc/single.html`
- [ ] `tutorial/single.html`, `tutorial/list.html`
- [ ] `changelog/single.html`, `changelog/list.html`

**Priority 4 (Autodoc templates):**
- [ ] `autodoc/python/*.html`
- [ ] `autodoc/cli/*.html`
- [ ] `autodoc/openapi/*.html`
- [ ] `autodoc/partials/*.html`

**Priority 5 (Specialized):**
- [ ] `resume/*.html`
- [ ] `author/*.html`
- [ ] `archive*.html`
- [ ] Remaining files

### Validation (per batch)

- [ ] Visual diff of rendered output
- [ ] No Jinja2 errors during build
- [ ] No missing content

---

## Testing Plan

### Unit Tests

```
tests/rendering/test_context.py
├── test_params_context_nested_access
├── test_params_context_missing_returns_empty
├── test_section_context_none_section
├── test_section_context_with_section
├── test_theme_context_has_feature
├── test_cascading_params_page_overrides_section
├── test_cascading_params_section_overrides_site
└── test_cascading_params_nested_dicts
```

### Integration Tests

```
tests/rendering/test_build_page_context.py
├── test_regular_page_context
├── test_section_index_context
├── test_tag_page_context
├── test_archive_page_context
├── test_autodoc_page_context
└── test_special_page_context
```

### Smoke Tests

- [ ] Build Bengal docs site: `bengal build site/`
- [ ] Build example blog: `bengal build example-sites/milos-blog/`
- [ ] Dev server: `bengal serve site/` - navigate all pages

---

## Rollback Plan

If issues arise during deployment:

1. **Phase 1-2 rollback:** Revert environment.py changes
2. **Phase 3 rollback:** Remove site.params property
3. **Phase 4-9 rollback:** Keep old context building path, add feature flag
4. **Phase 10 rollback:** Git revert template changes by batch

---

## Success Criteria

- [ ] `rg "\.get\(" bengal/themes/default/templates/ | wc -l` returns 0
- [ ] `rg "is defined" bengal/themes/default/templates/ | wc -l` returns 0
- [ ] `rg "or {}" bengal/themes/default/templates/ | wc -l` returns 0
- [ ] All existing tests pass
- [ ] Bengal docs site builds without error
- [ ] No visual regressions in rendered output
- [ ] Template authors guide updated

---

## Commit Strategy

Follow atomic commits per phase:

```
feat(context): configure Jinja2 ChainableUndefined
feat(context): wire SiteContext/ThemeContext/ConfigContext into globals
feat(site): add params and logo properties
feat(context): enhance ParamsContext with recursive wrapping
feat(context): enhance SectionContext with safe defaults
feat(context): enhance ThemeContext with config access
feat(context): update build_page_context as single source of truth
refactor(renderer): use build_page_context instead of manual dict
refactor(pipeline): use SectionContext in variable context
chore(context): remove SmartDict and dead code
feat(context): implement CascadingParamsContext for data cascade
refactor(templates): migrate base.html to safe access patterns
refactor(templates): migrate partials to safe access patterns
refactor(templates): migrate blog templates to safe access patterns
refactor(templates): migrate doc templates to safe access patterns
refactor(templates): migrate autodoc templates to safe access patterns
refactor(templates): migrate remaining templates to safe access patterns
docs: update template authors guide with new patterns
```

---

## Dependencies

None external. All changes are internal to Bengal.

---

## Post-Implementation

1. **Documentation:** Update `TEMPLATE-CONTEXT.md` and `SAFE_PATTERNS.md`
2. **Announcement:** Add to CHANGELOG.md under "Developer Experience"
3. **Monitoring:** Watch for UndefinedError reports in first week
