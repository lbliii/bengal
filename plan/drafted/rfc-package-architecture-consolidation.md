# RFC: Package Architecture Consolidation

**Status**: Draft
**Author**: AI Assistant
**Created**: 2025-12-20
**Category**: Architecture / Refactoring

---

## Executive Summary

Systematic package analysis identified **4 high-priority architectural issues**: an oversized `rendering/` package (107 files), a "grab-bag" `utils/` with domain-specific code, overlapping validation subsystems, and an inconsistent `autodoc/` orchestration pattern. This RFC proposes targeted consolidation to improve cohesion, reduce cognitive load, and align with Bengal's established architectural patterns.

**Relationship to Other RFCs**: This RFC complements `rfc-code-smell-remediation.md` (which addresses file-level issues). This RFC addresses **package-level** structural concerns.

---

## Problem Statement

### Current State

Bengal's package structure is generally well-organized, but growth has introduced structural drift:

| Package | Files | Issue |
|---------|-------|-------|
| `rendering/` | 107 | Too large; contains 30+ directive plugins as subpackage |
| `utils/` | 25 | Grab-bag with domain-specific code that belongs elsewhere |
| `health/` + `rendering/` | - | Overlapping link/template validation |
| `autodoc/` | 18 | Private `orchestration/` subpackage breaks main pattern |

### Evidence: Package Sizes

```bash
# File counts per package (excluding __pycache__)
rendering/          107 files  # 🔴 Needs extraction
utils/               25 files  # 🟡 Needs relocation
autodoc/             18 files
cache/               17 files
orchestration/       16 files
health/              16 files
core/                15 files
cli/                 14 files  # Includes templates/
discovery/            8 files
debug/                8 files
postprocess/          7 files
server/               7 files
content_layer/        7 files
config/               6 files
analysis/             5 files
collections/          4 files
content_types/        4 files
assets/               3 files  # 🟡 Consider merge
fonts/                3 files  # 🟡 Consider merge
services/             2 files  # 🟡 Underdeveloped
```

### Evidence: Utils Grab-Bag

`bengal/utils/` contains domain-specific modules that violate single-responsibility:

| File | Lines | Belongs In |
|------|-------|------------|
| `theme_resolution.py` | 245 | `themes/` or `core/theme.py` |
| `theme_registry.py` | 180 | `themes/` or `core/theme.py` |
| `build_stats.py` | 156 | `orchestration/` |
| `build_summary.py` | 142 | `orchestration/` |
| `build_badge.py` | 89 | `orchestration/` |
| `page_initializer.py` | 234 | `core/` or `discovery/` |
| `sections.py` | 178 | `core/section.py` |

**Impact**:
- Developers search multiple locations for related code
- Circular import risks when domain packages import from utils
- Unclear ownership for bug fixes

### Evidence: Overlapping Validation

Two validation subsystems exist with overlapping scope:

**In `health/`**:
- `validators/links.py` - Link validation during health check
- `validators/rendering.py` - Template validation
- `linkcheck/` - Async link checking

**In `rendering/`**:
- `link_validator.py` - Link validation during render
- `link_transformer.py` - Link processing
- `validator.py` - Template validation

**Impact**:
- Same bug may need fixing in two places
- Inconsistent behavior between build-time and health-check validation
- Confusion about which validator to use

### Evidence: Autodoc Orchestration

`bengal/autodoc/` has a private `orchestration/` subpackage:

```
bengal/autodoc/
├── orchestration/           # 🔴 Private subpackage
│   ├── __init__.py
│   ├── base.py
│   └── python_orchestrator.py
├── virtual_orchestrator.py  # Different pattern than above
└── ...
```

**Impact**:
- Inconsistent with main `bengal/orchestration/` pattern
- Confusing import structure
- Duplicates orchestration concepts

---

## Proposed Solutions

### Phase 1: Extract Directives Package (Priority 1)

**Problem**: `rendering/plugins/directives/` is 30+ files that could be independent.

**Current Structure**:
```
rendering/plugins/directives/
├── __init__.py
├── admonitions.py
├── cards.py (1,027 lines!)
├── code_blocks.py
├── diagrams.py
├── dropdowns.py
├── grids.py
├── image.py
├── tabs.py
├── toc.py
├── youtube.py
└── ... (20+ more)
```

**Proposed**: Extract to `bengal/directives/`

```
bengal/directives/
├── __init__.py              # register_all(), registry
├── registry.py              # Directive registration system
├── base.py                  # BaseDirective class
├── admonitions.py
├── cards/                   # Package for 1,000+ line module
│   ├── __init__.py
│   ├── simple.py
│   ├── linked.py
│   └── grid.py
├── code_blocks.py
├── diagrams.py
├── dropdowns.py
├── grids.py
├── image.py
├── tabs.py
├── toc.py
└── youtube.py
```

**Benefits**:
- `rendering/` drops from 107 to ~75 files
- Directives become independently testable
- Clearer ownership and contribution path
- Enables future plugin system

**Migration**:
1. Create `bengal/directives/` with re-exports
2. Move files incrementally
3. Update imports in `rendering/plugins/__init__.py`
4. Deprecate old location with import redirects

---

### Phase 2: Relocate Domain Utils (Priority 1)

**Problem**: `utils/` contains domain-specific code.

**Proposed Relocations**:

| Current Location | New Location | Rationale |
|------------------|--------------|-----------|
| `utils/theme_resolution.py` | `core/theme/resolution.py` | Theme logic belongs with core models |
| `utils/theme_registry.py` | `core/theme/registry.py` | Theme logic belongs with core models |
| `utils/build_stats.py` | `orchestration/stats.py` | Build artifacts belong with orchestration |
| `utils/build_summary.py` | `orchestration/summary.py` | Build artifacts belong with orchestration |
| `utils/build_badge.py` | `orchestration/badge.py` | Build artifacts belong with orchestration |
| `utils/page_initializer.py` | `discovery/page_factory.py` | Page creation is discovery concern |
| `utils/sections.py` | `core/section.py` (merge) | Section logic belongs with Section class |

**What Remains in `utils/`** (generic utilities only):
```
utils/
├── async_compat.py      # Async utilities
├── dates.py             # Date parsing/formatting
├── file_io.py           # File operations
├── hashing.py           # Hash utilities
├── retry.py             # Retry decorators
├── text.py              # Text utilities
├── thread_local.py      # Thread-local storage
├── paths.py             # Path resolution (generic)
└── paginator.py         # Generic pagination
```

**Migration Strategy**:
1. Create new modules at target locations
2. Add deprecation warnings to old locations
3. Update internal imports
4. Remove old modules after 1 release cycle

---

### Phase 3: Consolidate Validation (Priority 2)

**Problem**: Overlapping validation in `health/` and `rendering/`.

**Proposed**: Consolidate all validation in `health/`:

```
health/
├── validators/
│   ├── links.py          # Merge rendering/link_validator.py
│   ├── templates.py      # Merge rendering/validator.py
│   └── ...
├── linkcheck/            # Async link checking (keep)
└── ...
```

**Rendering Package Changes**:
```
rendering/
├── link_transformer.py   # Keep - transforms links during render
├── link_validator.py     # REMOVE - delegate to health/
├── validator.py          # REMOVE - delegate to health/
└── ...
```

**New Pattern**:
```python
# bengal/rendering/pipeline/core.py
from bengal.health.validators import validate_links, validate_templates

# During render, call health validators
def _validate_output(self, page: Page) -> list[ValidationError]:
    return validate_links(page) + validate_templates(page)
```

**Benefits**:
- Single source of truth for validation logic
- Consistent behavior across build and health check
- Clearer testing boundaries

---

### Phase 4: Standardize Autodoc Orchestration (Priority 2)

**Problem**: `autodoc/orchestration/` duplicates main orchestration pattern.

**Proposed**: Flatten autodoc orchestration, follow main pattern:

**Current**:
```
autodoc/
├── orchestration/
│   ├── __init__.py
│   ├── base.py
│   └── python_orchestrator.py
├── virtual_orchestrator.py
└── ...
```

**Proposed**:
```
autodoc/
├── orchestrators/              # Rename, plural for consistency
│   ├── __init__.py
│   ├── base.py
│   └── python.py              # Rename from python_orchestrator.py
├── virtual.py                  # Rename from virtual_orchestrator.py
└── ...
```

**Or, if tighter integration desired**:
```
orchestration/
├── autodoc.py                  # Move VirtualAutodocOrchestrator here
└── ...

autodoc/
├── extractors/                 # Keep extraction logic
└── models/                     # Keep data models
```

**Recommendation**: First option (rename to `orchestrators/`) is lower risk. Second option (merge with main orchestration) requires more analysis.

---

### Phase 5: Merge Micro-Packages (Priority 3)

**Problem**: Several packages are too small to justify separate directories.

**Proposed Merges**:

| Package | Files | Merge Into | Rationale |
|---------|-------|------------|-----------|
| `assets/` | 3 | `orchestration/` | Asset processing is orchestration concern |
| `fonts/` | 3 | `assets/` → `orchestration/` | Font downloading is asset concern |
| `services/` | 2 | `rendering/` or remove | Only has template validation service |
| `content_types/` | 4 | `core/` or `collections/` | Content type strategy is core concept |

**Alternative**: Keep as-is if growth is expected. Document decision.

---

## Implementation Plan

### Sprint 1: Directives Extraction (Week 1-2)

| Task | Effort | Risk |
|------|--------|------|
| Create `bengal/directives/` package structure | 2h | Low |
| Move base directive classes | 2h | Low |
| Move directive implementations (30 files) | 8h | Medium |
| Convert `cards.py` to package (1,027 lines) | 4h | Medium |
| Update imports in `rendering/plugins/` | 4h | Low |
| Add deprecation redirects | 2h | Low |
| Update tests | 4h | Medium |

**Exit Criteria**:
- All directive imports work from `bengal.directives`
- `rendering/` file count < 80
- All tests pass

### Sprint 2: Utils Relocation (Week 2-3)

| Task | Effort | Risk |
|------|--------|------|
| Create `core/theme/` package | 1h | Low |
| Move theme_resolution.py, theme_registry.py | 2h | Low |
| Move build_*.py to orchestration/ | 2h | Low |
| Merge sections.py into core/section.py | 3h | Medium |
| Move page_initializer.py to discovery/ | 2h | Low |
| Add deprecation warnings to old locations | 2h | Low |
| Update all internal imports | 6h | Medium |
| Update tests | 4h | Medium |

**Exit Criteria**:
- `utils/` contains only generic utilities
- No domain-specific code in utils
- All tests pass

### Sprint 3: Validation Consolidation (Week 3-4)

| Task | Effort | Risk |
|------|--------|------|
| Audit overlap between health/ and rendering/ validators | 4h | Low |
| Merge link validation logic | 6h | Medium |
| Merge template validation logic | 4h | Medium |
| Update rendering pipeline to use health validators | 4h | Medium |
| Remove duplicated code | 2h | Low |
| Update tests | 4h | Medium |

**Exit Criteria**:
- Single source of truth for each validator
- rendering/ delegates to health/ for validation
- All tests pass

### Sprint 4: Autodoc & Micro-Packages (Week 4-5)

| Task | Effort | Risk |
|------|--------|------|
| Rename autodoc/orchestration/ to orchestrators/ | 2h | Low |
| Rename files for consistency | 2h | Low |
| Evaluate micro-package merges | 2h | Low |
| Execute approved merges | 4h | Low |
| Update imports and tests | 4h | Medium |

**Exit Criteria**:
- Autodoc follows consistent naming
- Micro-package decisions documented
- All tests pass

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import breakage for external users | Low | High | Deprecation warnings + re-exports for 1 release |
| Circular imports after relocation | Medium | Medium | Careful dependency analysis before moving |
| Test coverage gaps | Medium | Medium | Run full test suite after each file move |
| Performance regression | Low | Low | No logic changes, only file locations |

---

## Success Criteria

### Quantitative

- [ ] `rendering/` has < 80 files (from 107)
- [ ] `utils/` has < 15 files (from 25)
- [ ] No validation logic duplicated between packages
- [ ] All packages follow consistent orchestration pattern

### Qualitative

- [ ] New developers can find code by domain concept
- [ ] Single source of truth for each concern
- [ ] Clear package boundaries with minimal overlap

---

## Alternatives Considered

### Alternative 1: No Structural Changes

**Approach**: Accept current structure, only address file-level issues.

**Pros**: Zero risk, no migration needed.

**Cons**:
- Doesn't solve package-level confusion
- Technical debt continues to accumulate
- New developers still struggle with code location

**Verdict**: Rejected. Package structure issues compound over time.

### Alternative 2: Aggressive Restructuring

**Approach**: Complete package reorganization with new top-level structure.

**Pros**: Clean slate, optimal structure.

**Cons**:
- Very high risk
- Massive import changes
- Long stabilization period

**Verdict**: Rejected. Incremental approach preferred.

---

## Appendix: Package Responsibility Matrix

| Package | Core Concept | Dependencies | Dependents |
|---------|--------------|--------------|------------|
| `core/` | Data models | None | All |
| `config/` | Configuration | None | orchestration, cli |
| `discovery/` | Content finding | core, config | orchestration |
| `cache/` | Build caching | core | orchestration |
| `orchestration/` | Build coordination | core, discovery, cache, rendering | cli, server |
| `rendering/` | Content rendering | core | orchestration |
| `directives/` (NEW) | Template directives | rendering | rendering |
| `health/` | Validation | core, rendering | cli, orchestration |
| `postprocess/` | Post-build | core | orchestration |
| `cli/` | User interface | orchestration | None |
| `server/` | Dev server | orchestration | cli |
| `autodoc/` | API docs | core, rendering | orchestration |
| `content_layer/` | Content sources | core | discovery |
| `collections/` | Schema validation | core | discovery |
| `utils/` | Generic utilities | None | All |

---

## Related

- **Complementary RFC**: `plan/drafted/rfc-code-smell-remediation.md` - File-level refactoring
- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc` - Package patterns
- **Existing Patterns**: `bengal/core/page/`, `bengal/core/site/` - Well-structured packages
