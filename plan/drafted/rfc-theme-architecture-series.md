# RFC Series: Theme Architecture Modernization (v2)

**Status**: Draft (Revised)  
**Created**: 2024-12-08  
**Priority**: P2 (Medium)  
**Revised**: 2024-12-08 (Post-Investigation)  
**Scope**: Bengal Theme System  

---

## Executive Summary

Investigation revealed Bengal's theme system is **more complete than initially assumed**. This revised series focuses on **actual gaps** rather than reimplementing existing features.

### What Already Works (No RFC Needed)

| Feature | Status | Evidence |
|---------|--------|----------|
| Theme inheritance | ✅ Complete | `resolve_theme_chain()` in `environment.py:28-57` |
| Swizzle system | ✅ Complete | `utils/swizzle.py` (325 lines) with provenance tracking |
| Theme CLI | ✅ Complete | `bengal theme new --extends`, `swizzle`, `swizzle-list`, `swizzle-update` |
| Icon system | ✅ Complete | LRU cache, preloading, ICON_MAP aliases |
| Feature registry | ✅ Complete | 18 features in `features.py` |

### What Actually Needs Work

| Gap | Impact | Solution |
|-----|--------|----------|
| Configuration scattered | High - hard to discover settings | RFC-001: `theme.yaml` |
| 45 CSS component files | Medium - maintenance burden | RFC-002: Consolidate to ~15 |
| Autodoc templates separate | Medium - inconsistent styling | RFC-003: Move to theme |
| Features undocumented | High - users don't know they exist | DOC-001: Documentation |

---

## Revised RFC Index

| RFC | Title | Priority | Status |
|-----|-------|----------|--------|
| [001](rfc-theme-001-configuration.md) | Theme Configuration (`theme.yaml`) | High | Keep |
| [002](rfc-theme-002-css-consolidation.md) | CSS Architecture Simplification | Medium | Keep (was 005) |
| [003](rfc-theme-003-autodoc-integration.md) | Autodoc Theme Integration | Medium | Keep (was 007) |

### Dropped/Deferred RFCs

| Original | Decision | Rationale |
|----------|----------|-----------|
| RFC-002 (Templates) | **Dropped** | Cosmetic renaming (`single.html` → `article.html`) creates churn with no functional benefit. Current structure works. |
| RFC-003 (Inheritance) | **→ Documentation** | Feature already exists. Write docs, not code. |
| RFC-004 (Macros) | **Deferred** | Nice-to-have. Current partials work. Can be done incrementally without RFC. |
| RFC-006 (Icons) | **Merged into 001** | Just moves `ICON_MAP` to config. Not RFC-worthy on its own. |

---

## Implementation Plan

### Phase 1: Configuration (Week 1-2)

**RFC-001: Theme Configuration**
- Create `theme.yaml` schema
- Migrate `features.py` registry to YAML
- Move `ICON_MAP` aliases to config
- Add `theme.yaml` loader to `Theme.from_config()`

**Deliverables**:
```yaml
# themes/default/theme.yaml
name: default
version: 2.0.0
parent: null

features:
  navigation:
    breadcrumbs: { enabled: true, description: "..." }
    toc: { enabled: true, description: "..." }
  content:
    lightbox: { enabled: true, description: "..." }

icons:
  aliases:
    search: magnifying-glass
    menu: list
    close: x
```

### Phase 2: CSS Cleanup (Week 3-4)

**RFC-002: CSS Consolidation**
- Consolidate 45 component files → ~15 domain-grouped files
- Keep token structure (already reasonable)
- Create migration script

**Before → After**:
```
components/           →  components/
├── action-bar.css        ├── navigation.css (7 files merged)
├── admonitions.css       ├── content.css (6 files merged)
├── alerts.css            ├── interactive.css (8 files merged)
├── ... (42 more)         ├── feedback.css (5 files merged)
                          ├── code.css (3 files merged)
                          ├── api-explorer.css (kept separate)
                          └── ... (~9 more)
```

### Phase 3: Autodoc Integration (Week 5-6)

**RFC-003: Autodoc Theme Integration**
- Move autodoc HTML templates to `themes/default/templates/api-reference/`
- Create partials for class, function, method rendering
- Update `virtual_orchestrator.py` to prefer theme templates

### Documentation (Parallel)

**DOC-001: Theme Customization Guide**
- Document existing inheritance system
- Document swizzle workflow
- Show inheritance vs swizzle decision tree
- Add examples for common customizations

---

## Success Criteria (Revised)

- [x] ~~Theme inheritance works~~ (already done)
- [x] ~~Swizzle system with provenance~~ (already done)
- [x] ~~Theme CLI (`new --extends`, swizzle commands)~~ (already done)
- [ ] Single `theme.yaml` for all theme config
- [ ] CSS file count: 45 → ~15
- [ ] Autodoc templates in theme (not separate)
- [ ] Theme customization documented

---

## Target Theme Structure (Simplified)

```
themes/my-theme/
├── theme.yaml              # RFC-001: All config in one file
├── theme.toml              # (Already supported for extends)
├── assets/
│   ├── css/
│   │   ├── tokens/         # Keep current structure
│   │   ├── base/           # Keep current structure
│   │   ├── components/     # RFC-002: Consolidated (45→15)
│   │   └── style.css
│   └── icons/              # Custom icons only
├── templates/
│   ├── base.html           # Keep current naming
│   ├── page.html           # Keep current naming
│   ├── partials/           # Keep current structure
│   ├── api-reference/      # RFC-003: Autodoc templates here
│   │   ├── module.html
│   │   ├── partials/
│   │   └── ...
│   └── [content-types]/    # Keep current structure
└── README.md
```

**Note**: No template renaming. `single.html`/`list.html` conventions kept.

---

## Migration Path

### For Users

1. **No action required** - Existing themes continue to work
2. **Optional**: Create `theme.yaml` for new config format
3. **Optional**: Run `bengal theme migrate-css` for CSS consolidation

### Deprecation Timeline

| Version | Status |
|---------|--------|
| v1.x | `features.py` works, `theme.yaml` available |
| v2.0 | `features.py` deprecated (warning), `theme.yaml` preferred |
| v3.0 | `features.py` removed |

---

## Evidence Summary

**Investigation Date**: 2024-12-08

| Finding | Impact on RFCs |
|---------|----------------|
| `resolve_theme_chain()` exists | RFC-003 (inheritance) → Documentation only |
| Swizzle system complete | RFC-003 (inheritance) → Documentation only |
| `bengal theme new --extends` exists | CLI work already done |
| Icon system well-designed | RFC-006 → Merge into RFC-001 (config only) |
| 45 CSS files verified | RFC-005 → RFC-002 (keep, real gap) |
| Template structure functional | RFC-002 (templates) → Drop (no value) |

---

## Archived RFCs

The following RFCs are archived but preserved for reference:

- `rfc-theme-002-templates.md` → Archived (template renaming dropped)
- `rfc-theme-003-inheritance.md` → Converted to documentation task
- `rfc-theme-004-components.md` → Archived (deferred, do incrementally)
- `rfc-theme-005-css.md` → Renamed to `rfc-theme-002-css-consolidation.md`
- `rfc-theme-006-icons.md` → Merged into RFC-001
- `rfc-autodoc-theme-integration.md` → Renamed to `rfc-theme-003-autodoc-integration.md`

---

## Related Documents

- [architecture/themes.md](../../architecture/themes.md) - Current theme architecture
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Theme contribution guidelines

---

## Appendix: What We're NOT Doing (And Why)

### Template Renaming (Original RFC-002)

**Proposed**: Rename `single.html` → `article.html`, `list.html` → `feed.html`

**Why Dropped**:
- Creates migration burden for existing themes
- Hugo naming is familiar to many users
- No functional improvement, just cosmetic
- Template resolution already works fine

### Macro System (Original RFC-004)

**Proposed**: Formal macro library with component registry

**Why Deferred**:
- Current partials work well
- Can add macros incrementally without RFC
- Component registry is over-engineering for current needs
- Users can create macros now if they want them

### Separate Icon RFC (Original RFC-006)

**Proposed**: Full icon system overhaul

**Why Merged**:
- Icon system is already well-designed (caching, preloading, aliases)
- Only gap is moving `ICON_MAP` to config
- Single config change doesn't need its own RFC
