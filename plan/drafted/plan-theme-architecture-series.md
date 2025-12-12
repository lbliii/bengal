# Implementation Plan: Theme Architecture Modernization

**RFC Series**: `rfc-theme-architecture-series.md`  
**Status**: Draft  
**Created**: 2024-12-08  
**Timeline**: 6 weeks  

---

## Executive Summary

This plan converts the RFC Theme Architecture Series into actionable, atomic tasks grouped by phase. Total effort: ~6 weeks across 3 RFCs + parallel documentation.

**Key Dependencies**:
- RFC-002 (CSS) → Independent
- RFC-001 (Config) → Independent  
- RFC-003 (Autodoc) → Soft dependency on RFC-001 (can proceed in parallel)
- DOC-001 → Parallel throughout

---

## Phase 1: Theme Configuration (RFC-001)

**Timeline**: Week 1-2  
**Priority**: High  
**Dependencies**: None  

### 1.1 Core Infrastructure

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1.1.1 | Create `ThemeConfig` dataclass with nested config models | `bengal/themes/config.py` (new) | `themes: add ThemeConfig dataclass with FeatureFlags, AppearanceConfig, IconConfig models` |
| 1.1.2 | Add YAML schema validation using Pydantic or dataclass validation | `bengal/themes/config.py` | `themes(config): add theme.yaml schema validation with helpful error messages` |
| 1.1.3 | Create `theme.yaml` loader in `ThemeConfig.load()` | `bengal/themes/config.py` | `themes(config): add ThemeConfig.load() to parse theme.yaml files` |
| 1.1.4 | Integrate with existing `Theme` class in `bengal/core/theme.py` | `bengal/core/theme.py` | `core(theme): integrate ThemeConfig loading; extend Theme.from_config()` |

### 1.2 Template Integration

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1.2.1 | Inject `theme` object into Jinja2 context | `bengal/rendering/environment.py` | `rendering: inject ThemeConfig as 'theme' in template context` |
| 1.2.2 | Create `feature_enabled` Jinja2 filter | `bengal/rendering/filters.py` | `rendering(filters): add feature_enabled filter for template feature checks` |
| 1.2.3 | Update `base.html` to use `theme.features` checks | `bengal/themes/default/templates/base.html` | `themes(default): adopt theme.features checks in base.html` |

### 1.3 Migration Tooling

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1.3.1 | Create migration script to convert `features.py` → `theme.yaml` | `bengal/cli/commands/theme_migrate.py` (new) | `cli(theme): add 'bengal theme migrate-config' command` |
| 1.3.2 | Add deprecation warning when `features.py` is loaded | `bengal/themes/default/__init__.py` | `themes(default): add deprecation warning for features.py usage` |
| 1.3.3 | Create `theme.yaml` for default theme | `bengal/themes/default/theme.yaml` (new) | `themes(default): add theme.yaml with all feature flags and config` |

### 1.4 Icon Configuration (Merged from RFC-006)

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1.4.1 | Move `ICON_MAP` aliases from Python to `theme.yaml` | `bengal/themes/default/theme.yaml`, `bengal/rendering/_icons.py` | `themes: move ICON_MAP aliases to theme.yaml; update icon loader` |
| 1.4.2 | Add icon configuration loading to `ThemeConfig` | `bengal/themes/config.py` | `themes(config): add IconConfig model with library, aliases, defaults` |

### Phase 1 Deliverables

```yaml
# themes/default/theme.yaml (target)
name: default
version: 2.0.0
parent: null

features:
  navigation:
    breadcrumbs: true
    toc_sidebar: true
    back_to_top: true
  content:
    lightbox: true
    code_copy: true
  accessibility:
    skip_link: true

appearance:
  default_mode: system
  default_palette: ""

icons:
  library: phosphor
  aliases:
    search: magnifying-glass
    menu: list
    close: x
```

---

## Phase 2: CSS Organization & Pattern Extraction (RFC-002)

**Timeline**: Week 3-4  
**Priority**: Medium  
**Dependencies**: None (can run in parallel with Phase 1)  
**Status**: ✅ **Approach Revised** - Keep modular structure, extract common patterns

### Decision: Modular CSS is Optimal

**Analysis:** Consolidating 45 component files would create files of 1,200-3,200 lines each, which is **worse** than the current modular approach.

**New Approach:** Keep modular structure, extract common patterns into reusable utilities.

**Documentation:**
- [MODULAR_CSS_RATIONALE.md](../../bengal/themes/default/assets/css/MODULAR_CSS_RATIONALE.md) - Why modular CSS is better
- [CSS_ARCHITECTURE_EVALUATION.md](../../bengal/themes/default/assets/css/CSS_ARCHITECTURE_EVALUATION.md) - Evaluation of alternatives

### 2.1 Common Pattern Extraction ✅

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 2.1.1 | Extract common interactive patterns (focus, hover, transitions) | `bengal/themes/default/assets/css/base/interactive-patterns.css` | `themes(css): extract common interactive patterns to base/interactive-patterns.css` |
| 2.1.2 | Update style.css to import interactive-patterns | `bengal/themes/default/assets/css/style.css` | `themes(css): add interactive-patterns.css import` |

### 2.2 Documentation ✅

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 2.2.1 | Document modular CSS rationale | `bengal/themes/default/assets/css/MODULAR_CSS_RATIONALE.md` | `themes(css): add MODULAR_CSS_RATIONALE.md` |
| 2.2.2 | Evaluate CSS architecture alternatives | `bengal/themes/default/assets/css/CSS_ARCHITECTURE_EVALUATION.md` | `themes(css): add CSS_ARCHITECTURE_EVALUATION.md` |
| 2.2.3 | Update README with modular CSS link | `bengal/themes/default/assets/css/README.md` | `themes(css): update README with modular CSS rationale link` |

### 2.3 Future Improvements (Optional)

| Task | Description | Status |
|------|-------------|--------|
| 2.3.1 | Expand utility classes if needed | Optional |
| 2.3.2 | Use native CSS nesting when widely supported | Future |
| 2.3.3 | Better token usage documentation | Optional |

### Component Grouping Reference

```yaml
navigation.css:
  - header.css
  - mobile-nav.css (nav-action-buttons.css)
  - docs-nav.css
  - breadcrumbs.css (from navigation.css)
  - toc.css
  - back-to-top.css (from action-bar.css)

content.css:
  - prose.css (from multiple)
  - headings.css
  - tables.css (data-table.css)
  - hero.css, page-hero.css

interactive.css:
  - buttons.css
  - forms.css
  - tabs.css
  - dropdowns.css
  - accordion/details (from interactive.css)
  - tooltip.css

feedback.css:
  - admonitions.css
  - alerts.css
  - badges.css
  - empty-state.css

media.css:
  - lightbox (from interactive.css)
  - embeds
  - figures
  - icons.css

code.css:
  - code.css
  - syntax highlighting
  - copy button
```

---

## Phase 3: Autodoc Theme Integration (RFC-003)

**Timeline**: Week 5-6  
**Priority**: Medium  
**Dependencies**: Soft dependency on RFC-001 (theme config for template resolution)  

### 3.1 Theme Template Creation

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 3.1.1 | Create `api-reference/module.html` in theme | `bengal/themes/default/templates/api-reference/module.html` | `themes(api-reference): add module.html template for Python modules` |
| 3.1.2 | Create `api-reference/section-index.html` | `bengal/themes/default/templates/api-reference/section-index.html` | `themes(api-reference): add section-index.html for package indexes` |

### 3.2 Partials Creation

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 3.2.1 | Create `class-card.html` partial | `bengal/themes/default/templates/api-reference/partials/class-card.html` | `themes(api-reference): add class-card.html partial` |
| 3.2.2 | Create `function-card.html` partial | `bengal/themes/default/templates/api-reference/partials/function-card.html` | `themes(api-reference): add function-card.html partial` |
| 3.2.3 | Create `method-item.html` partial | `bengal/themes/default/templates/api-reference/partials/method-item.html` | `themes(api-reference): add method-item.html partial` |
| 3.2.4 | Create `parameters-table.html` partial | `bengal/themes/default/templates/api-reference/partials/parameters-table.html` | `themes(api-reference): add parameters-table.html partial` |
| 3.2.5 | Create `attributes-table.html` partial | `bengal/themes/default/templates/api-reference/partials/attributes-table.html` | `themes(api-reference): add attributes-table.html partial` |
| 3.2.6 | Create `signature.html` partial | `bengal/themes/default/templates/api-reference/partials/signature.html` | `themes(api-reference): add signature.html partial` |
| 3.2.7 | Create `badges.html` partial | `bengal/themes/default/templates/api-reference/partials/badges.html` | `themes(api-reference): add badges.html partial for type/status badges` |
| 3.2.8 | Create `returns-section.html` partial | `bengal/themes/default/templates/api-reference/partials/returns-section.html` | `themes(api-reference): add returns-section.html partial` |
| 3.2.9 | Create `raises-list.html` partial | `bengal/themes/default/templates/api-reference/partials/raises-list.html` | `themes(api-reference): add raises-list.html partial` |

### 3.3 Orchestrator Updates

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 3.3.1 | Update `virtual_orchestrator.py` to prefer theme templates | `bengal/autodoc/virtual_orchestrator.py` | `autodoc: prefer theme templates over built-in; add fallback chain` |
| 3.3.2 | Update template rendering to pass element data | `bengal/autodoc/virtual_orchestrator.py` | `autodoc: pass DocElement data to theme templates for rendering` |
| 3.3.3 | Add fallback to minimal templates when theme lacks them | `bengal/autodoc/virtual_orchestrator.py` | `autodoc: add graceful fallback to minimal templates` |

### 3.4 Fallback Templates

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 3.4.1 | Create `autodoc/fallback/` directory structure | `bengal/autodoc/fallback/` (new) | `autodoc: create fallback/ directory for minimal templates` |
| 3.4.2 | Create minimal `module.html` fallback | `bengal/autodoc/fallback/module.html` | `autodoc(fallback): add minimal module.html without styling` |
| 3.4.3 | Create minimal `section.html` fallback | `bengal/autodoc/fallback/section.html` | `autodoc(fallback): add minimal section.html without styling` |

### 3.5 Cleanup

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 3.5.1 | Move existing `html_templates/` to fallback | `bengal/autodoc/html_templates/` → `bengal/autodoc/fallback/` | `autodoc: move html_templates/ to fallback/; deprecate location` |
| 3.5.2 | Add deprecation notice to markdown templates | `bengal/autodoc/templates/` | `autodoc: add deprecation notice to markdown templates` |
| 3.5.3 | Clean up untracked `templates/html/` directory | `bengal/autodoc/templates/html/` (delete) | `autodoc: remove untracked templates/html/ directory` |

---

## Documentation (DOC-001) — Parallel

**Timeline**: Throughout (parallel with all phases)  
**Priority**: High  
**Dependencies**: None  

### DOC-001: Theme Customization Guide

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| D.1 | Document theme inheritance system | `site/content/docs/themes/inheritance.md` | `docs(themes): add theme inheritance guide` |
| D.2 | Document swizzle workflow | `site/content/docs/themes/swizzle.md` | `docs(themes): add swizzle workflow guide` |
| D.3 | Create inheritance vs swizzle decision tree | `site/content/docs/themes/customization.md` | `docs(themes): add customization decision guide` |
| D.4 | Add common customization examples | `site/content/docs/themes/examples.md` | `docs(themes): add common customization examples` |
| D.5 | Document `theme.yaml` schema | `site/content/docs/themes/configuration.md` | `docs(themes): add theme.yaml configuration reference` |
| D.6 | Document CSS architecture (post-consolidation) | `site/content/docs/themes/css.md` | `docs(themes): add CSS architecture guide` |

---

## Task Summary by Phase

| Phase | Tasks | Est. Hours | Dependencies | Status |
|-------|-------|------------|--------------|--------|
| **Phase 1: Config** | 11 tasks | 20-25h | None | ✅ Complete |
| **Phase 2: CSS** | 3 tasks | 2-3h | None | ✅ Complete (revised approach) |
| **Phase 3: Autodoc** | 17 tasks | 20-25h | Soft dep on Phase 1 | ⏳ Pending |
| **DOC-001** | 6 tasks | 10-15h | Parallel | ⏳ Pending |
| **Total** | **37 tasks** | **52-68h** | | |

---

## Verification Checklist

### Phase 1 Complete When:
- [ ] `theme.yaml` exists for default theme
- [ ] `features.py` shows deprecation warning
- [ ] `theme.features.X` works in templates
- [ ] `{{ 'feature.name' | feature_enabled }}` filter works
- [ ] Icon aliases load from `theme.yaml`
- [ ] All existing tests pass

### Phase 2 Complete When:
- [x] Common patterns extracted to `base/interactive-patterns.css`
- [x] Modular CSS rationale documented
- [x] CSS architecture evaluation completed
- [x] README updated with rationale links
- [ ] Components can use common patterns (optional migration)

### Phase 3 Complete When:
- [ ] API docs render using theme templates
- [ ] Theme templates match site design
- [ ] Fallback templates work for themeless sites
- [ ] `html_templates/` moved to `fallback/`
- [ ] No regressions in autodoc output

### Documentation Complete When:
- [ ] Theme inheritance documented
- [ ] Swizzle workflow documented
- [ ] `theme.yaml` schema documented
- [ ] CSS architecture documented
- [ ] Decision tree for customization exists

---

## Execution Order

**Recommended parallel execution**:

```
Week 1-2:
  [Phase 1: 1.1-1.4] ──────────────────────┐
  [DOC: D.1-D.2] ─────────────────────────┤
                                          │
Week 3-4:                                 │
  [Phase 2: 2.1-2.5] ─────────────────────┤
  [DOC: D.3-D.4] ─────────────────────────┤
                                          │
Week 5-6:                                 │
  [Phase 3: 3.1-3.5] ─────────────────────┤
  [DOC: D.5-D.6] ─────────────────────────┘
```

**Critical path**: Phase 1 (config) → Phase 3 (autodoc template loading uses theme config)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CSS consolidation causes visual regressions | Manual visual review + screenshot comparison |
| Breaking existing themes | All changes backwards-compatible; deprecation warnings |
| Template resolution conflicts | Clear fallback chain: theme → fallback → error |
| Large merge conflicts | Small, atomic commits; frequent integration |

---

## Success Criteria (from RFC)

- [x] ~~Theme inheritance works~~ (already done)
- [x] ~~Swizzle system with provenance~~ (already done)
- [x] ~~Theme CLI (`new --extends`, swizzle commands)~~ (already done)
- [ ] Single `theme.yaml` for all theme config → **Phase 1**
- [ ] CSS file count: 45 → ~15 → **Phase 2**
- [ ] Autodoc templates in theme (not separate) → **Phase 3**
- [ ] Theme customization documented → **DOC-001**

---

## Related Documents

- [rfc-theme-architecture-series.md](rfc-theme-architecture-series.md) - RFC series overview
- [rfc-theme-001-configuration.md](rfc-theme-001-configuration.md) - Configuration RFC
- [rfc-theme-002-css-consolidation.md](rfc-theme-002-css-consolidation.md) - CSS RFC
- [rfc-theme-003-autodoc-integration.md](rfc-theme-003-autodoc-integration.md) - Autodoc RFC
