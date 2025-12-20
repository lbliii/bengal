# RFC: Architecture Refactoring - Package Consolidation and Code Smell Remediation

**Status**: Draft
**Author**: AI Assistant
**Created**: 2025-01-27
**Consolidates**: `rfc-code-smell-remediation.md`, `rfc-package-architecture-consolidation.md`
**Confidence**: 91% 🟢
**Category**: Architecture / Refactoring

---

## Executive Summary

Comprehensive architecture analysis identified **package-level structural issues** (oversized packages, grab-bag utils, overlapping validation) and **file-level code smells** (8+ monolithic files >700 lines, 40+ god functions >50 lines). This unified RFC proposes a coordinated refactoring plan addressing both levels: first consolidate packages for better structure, then break down large files within the improved architecture.

**Key Insight**: Package consolidation must happen **before** file-level refactoring to avoid moving code twice. For example, `rendering/plugins/directives/cards.py` (1,027 lines) should be extracted to `bengal/directives/cards/` AND broken into a package in one coordinated step.

---

## Problem Statement

### Current State

Bengal's architecture has grown organically, introducing structural drift at both package and file levels:

**Package-Level Issues**:
- `rendering/` package: 107 files (too large, contains 30+ directive plugins)
- `utils/` package: 25 files (grab-bag with domain-specific code)
- Overlapping validation: Duplicate logic in `health/` and `rendering/`
- Inconsistent patterns: `autodoc/orchestration/` breaks main orchestration pattern

**File-Level Issues**:
- 8+ monolithic files exceeding 700 lines (3.5x the 400-line threshold)
- 40+ god functions exceeding 50 lines
- Duplicated logic (e.g., `find_work()` and `find_work_early()` share 70% code)
- Primitive obsession (dict returns instead of typed dataclasses)

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
cli/                 14 files
discovery/            8 files
```

### Evidence: Largest Files

| File | Lines | Threshold Exceeded | Package Issue |
|------|-------|-------------------|--------------|
| `orchestration/incremental.py` | 1,399 | 3.5x | File-level only |
| `analysis/knowledge_graph.py` | 1,222 | 3.1x | File-level only |
| `autodoc/extractors/python.py` | 1,146 | 2.9x | File-level only |
| `rendering/parsers/mistune.py` | 1,075 | 2.7x | File-level only |
| `rendering/plugins/directives/cards.py` | 1,027 | 2.6x | **Both** - extract AND break up |
| `rendering/template_functions/navigation.py` | 966 | 2.4x | File-level only |
| `discovery/content_discovery.py` | 944 | 2.4x | File-level only |
| `core/section.py` | 934 | 2.3x | File-level only |
| `utils/cli_output.py` | 838 | 2.1x | **Both** - relocate AND break up |

### Evidence: God Functions (Top 15)

| Location | Function | Lines |
|----------|----------|-------|
| `cli/commands/build.py:156` | `build()` | 419 |
| `analysis/graph_visualizer.py:290` | `generate_html()` | 409 |
| `health/validators/connectivity.py:152` | `_safe_get_metrics()` | 280 |
| `orchestration/build/__init__.py:97` | `BuildOrchestrator.build()` | 274 |
| `health/linkcheck/async_checker.py:33` | `__init__()` | 269 |
| `orchestration/streaming.py:48` | `process()` | 235 |
| `rendering/renderer.py:117` | `render_page()` | 215 |
| `rendering/template_engine/environment.py:132` | `create_jinja_environment()` | 203 |
| `rendering/template_functions/navigation.py:132` | `get_breadcrumbs()` | 196 |
| `orchestration/incremental.py:588` | `find_work_early()` | 254 |
| `orchestration/incremental.py:842` | `find_work()` | 176 |
| `rendering/parsers/mistune.py:179` | `_create_syntax_highlighting_plugin()` | 175 |
| `postprocess/sitemap.py:74` | `generate()` | 150 |
| `health/autofix.py:427` | `apply_fix()` | 150 |
| `autodoc/config.py:14` | `load_autodoc_config()` | 150 |

### Evidence: Utils Grab-Bag

`bengal/utils/` contains domain-specific modules that violate single-responsibility:

| File | Lines | Belongs In |
|------|-------|------------|
| `theme_resolution.py` | 245 | `core/theme/resolution.py` |
| `theme_registry.py` | 180 | `core/theme/registry.py` |
| `build_stats.py` | 156 | `orchestration/stats.py` |
| `build_summary.py` | 142 | `orchestration/summary.py` |
| `build_badge.py` | 89 | `orchestration/badge.py` |
| `page_initializer.py` | 234 | `discovery/page_factory.py` |
| `sections.py` | 178 | `core/section.py` (merge) |
| `cli_output.py` | 838 | `cli/output.py` (relocate AND break up) |

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
- `link_transformer.py` - Link processing (keep - transforms links)
- `validator.py` - Template validation

**Impact**:
- Same bug may need fixing in two places
- Inconsistent behavior between build-time and health-check validation
- Confusion about which validator to use

### Evidence: Duplicated Logic

`IncrementalOrchestrator` has two nearly identical methods:
- `find_work_early()` (254 lines) - Called before taxonomy generation
- `find_work()` (176 lines) - Called after taxonomy generation

Both share ~70% of their logic but are maintained separately.

---

## Proposed Solutions

### Strategy: Package Consolidation First, Then File-Level Refactoring

**Rationale**: Package structure changes affect where files should be broken up. For example:
- `cards.py` (1,027 lines) should be extracted to `bengal/directives/cards/` AND broken into a package in one step
- `navigation.py` should be broken up within `rendering/template_functions/` (no package move needed)
- `utils/cli_output.py` should be relocated to `cli/output.py` AND broken up

**Sequence**:
1. **Phase 1-3**: Package consolidation (extract directives, relocate utils, consolidate validation)
2. **Phase 4-7**: File-level refactoring (break up large files within improved structure)

---

## Phase 1: Extract Directives Package (Priority 1)

**Problem**: `rendering/plugins/directives/` is 30+ files that could be independent, including `cards.py` (1,027 lines) that needs both extraction AND breakdown.

**Current Structure**:
```
rendering/plugins/directives/
├── __init__.py
├── admonitions.py
├── cards.py (1,027 lines!)  # 🔴 Extract AND break up
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

**Proposed**: Extract to `bengal/directives/` AND break up `cards.py`:

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
- `cards.py` broken into focused modules (<400 lines each)
- Directives become independently testable
- Clearer ownership and contribution path
- Enables future plugin system

**Migration**:
1. Create `bengal/directives/` with re-exports
2. Move files incrementally (except `cards.py`)
3. Break `cards.py` into `directives/cards/` package during move
4. Update imports in `rendering/plugins/__init__.py`
5. Deprecate old location with import redirects

---

## Phase 2: Relocate Domain Utils (Priority 1)

**Problem**: `utils/` contains domain-specific code that belongs in domain packages.

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
| `utils/cli_output.py` | `cli/output.py` | CLI output belongs with CLI package (will break up in Phase 6) |

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

## Phase 3: Consolidate Validation (Priority 2)

**Problem**: Overlapping validation in `health/` and `rendering/`.

**Proposed**: Consolidate all validation in `health/`:

```
health/
├── validators/
│   ├── links.py          # Merge rendering/link_validator.py
│   ├── templates.py     # Merge rendering/validator.py
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

## Phase 4: Foundation - Dataclasses (Priority 1)

**Goal**: Create foundational dataclasses for type safety. Low risk, high value.

### 4.1 Create `BuildOptions` Dataclass

**Current**: 11 parameters to `BuildOrchestrator.build()`

**Proposed**:
```python
@dataclass
class BuildOptions:
    """Configuration options for site builds."""
    parallel: bool = True
    incremental: bool | None = None
    verbose: bool = False
    quiet: bool = False
    profile: BuildProfile | None = None
    memory_optimized: bool = False
    strict: bool = False
    full_output: bool = False
    profile_templates: bool = False
    changed_sources: set[Path] = field(default_factory=set)
    nav_changed_sources: set[Path] = field(default_factory=set)
    structural_changed: bool = False
```

**New Signature**:
```python
def build(self, options: BuildOptions | None = None) -> BuildStats:
```

### 4.2 Create Navigation Dataclasses

**Proposed**:
```python
# bengal/rendering/template_functions/navigation/models.py

@dataclass
class BreadcrumbItem:
    """Single breadcrumb in navigation trail."""
    title: str
    url: str
    is_current: bool = False

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        return getattr(self, key)

    def keys(self) -> list[str]:
        """Support dict(item) conversion."""
        return ["title", "url", "is_current"]

@dataclass  
class PaginationItem:
    """Single page in pagination."""
    num: int | None
    url: str | None
    is_current: bool = False
    is_ellipsis: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

@dataclass
class NavTreeItem:
    """Item in navigation tree."""
    title: str
    url: str
    is_current: bool = False
    is_in_active_trail: bool = False
    is_section: bool = False
    depth: int = 0
    children: list[NavTreeItem] = field(default_factory=list)
    has_children: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
```

**Dict Compatibility Strategy**: Dataclasses implement `__getitem__` for backward compatibility with templates using `item["key"]` syntax. This allows gradual migration without breaking existing templates.

---

## Phase 5: Break Up Incremental Package (Priority 1) ⚠️ HIGH RISK

**Problem**: `orchestration/incremental.py` is 1,399 lines with duplicated logic.

**Current**: 1,399 lines in single file

**Proposed Structure**:
```
bengal/orchestration/incremental/
├── __init__.py              # Public API (IncrementalOrchestrator)
├── change_detector.py       # Unified change detection logic
├── cache_manager.py         # Cache initialization and persistence  
├── rebuild_filter.py        # Pages/assets filtering logic
├── cascade_tracker.py       # Cascade and navigation dependencies
└── cleanup.py               # Deleted file cleanup
```

**Key Refactoring**:
- Merge `find_work()` and `find_work_early()` into `ChangeDetector` with a `phase` parameter
- Extract `_apply_cascade_rebuilds()`, `_apply_nav_frontmatter_section_rebuilds()`, etc. into `CascadeTracker`

**Estimated Impact**: -400 lines of duplication, improved testability

**Risk Mitigation** (CRITICAL):
1. **Pre-requisite**: Audit existing test coverage for `find_work_early()` and `find_work()`
2. **Feature flag**: Introduce `use_unified_change_detector: bool = False` config option
3. **Parallel execution period**: Run both old and new code paths, compare results
4. **Rollback plan**: Git revert to last known-good if issues arise

---

## Phase 6: Break Up Navigation Package (Priority 2)

**Problem**: `rendering/template_functions/navigation.py` is 966 lines.

**Current**: 966 lines in single file

**Proposed Structure**:
```
bengal/rendering/template_functions/navigation/
├── __init__.py              # register() function, re-exports
├── models.py                 # BreadcrumbItem, PaginationItem, NavTreeItem dataclasses
├── breadcrumbs.py            # get_breadcrumbs() function
├── pagination.py             # get_pagination_items() function
├── tree.py                   # get_nav_tree() function
├── auto_nav.py               # get_auto_nav() + section menu helpers
└── toc.py                    # get_toc_grouped(), combine_track_toc_items()
```

**Key Refactoring**:
- Migrate to typed dataclasses (created in Phase 4)
- Extract `_build_section_menu_item()` to `auto_nav.py`
- Each module < 200 lines

---

## Phase 7: Break Up Remaining Large Files (Priority 2)

### 7.1 Convert `rendering/parsers/mistune.py` to Package

**Current**: 1,075 lines

**Proposed Structure**:
```
bengal/rendering/parsers/mistune/
├── __init__.py              # MistuneParser class
├── highlighting.py          # Syntax highlighting plugin
├── toc.py                   # TOC extraction and anchor injection
├── cross_refs.py            # Cross-reference support
└── ast.py                   # AST parsing and rendering
```

### 7.2 Convert `autodoc/extractors/python.py` to Package

**Current**: 1,146 lines

**Proposed Structure**:
```
bengal/autodoc/extractors/python/
├── __init__.py              # PythonExtractor class
├── docstring_parser.py      # Docstring parsing (Google, NumPy, Sphinx)
├── signature_analyzer.py   # Function/class signature analysis
├── hierarchy_builder.py     # Module hierarchy construction
└── metadata.py              # Metadata extraction helpers
```

### 7.3 Break Up `cli/output.py` (relocated from `utils/cli_output.py`)

**Current**: 838 lines (after relocation in Phase 2)

**Proposed Structure**:
```
bengal/cli/output/
├── __init__.py              # CLIOutput class, public API
├── formatter.py             # Output formatting logic
├── progress.py              # Progress indicators
├── stats.py                 # Build stats display
└── colors.py                # Color/ANSI utilities
```

### 7.4 Standardize Autodoc Orchestration (Priority 2)

**Problem**: `autodoc/orchestration/` duplicates main orchestration pattern.

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

---

## Implementation Plan

### Sprint 1: Package Consolidation Foundation (Week 1-2)

**Goal**: Extract directives package and relocate domain utils.

| Task | Effort | Risk |
|------|--------|------|
| Create `bengal/directives/` package structure | 2h | Low |
| Move base directive classes | 2h | Low |
| Move directive implementations (29 files) | 8h | Medium |
| Break `cards.py` into `directives/cards/` package (1,027 lines) | 4h | Medium |
| Create `core/theme/` package | 1h | Low |
| Move theme_resolution.py, theme_registry.py | 2h | Low |
| Move build_*.py to orchestration/ | 2h | Low |
| Move page_initializer.py to discovery/ | 2h | Low |
| Merge sections.py into core/section.py | 3h | Medium |
| Move cli_output.py to cli/output.py | 2h | Low |
| Add deprecation warnings to old locations | 2h | Low |
| Update imports | 8h | Medium |
| Update tests | 6h | Medium |

**Exit Criteria**:
- `rendering/` file count < 80
- `utils/` contains only generic utilities
- `cards.py` broken into focused modules
- All tests pass

---

### Sprint 2: Validation Consolidation & Foundation Dataclasses (Week 3)

**Goal**: Consolidate validation and create foundational dataclasses.

| Task | Effort | Risk |
|------|--------|------|
| Audit overlap between health/ and rendering/ validators | 4h | Low |
| Merge link validation logic | 6h | Medium |
| Merge template validation logic | 4h | Medium |
| Update rendering pipeline to use health validators | 4h | Medium |
| Remove duplicated code | 2h | Low |
| Create `BuildOptions` dataclass | 2h | Low |
| Create navigation dataclasses | 3h | Low |
| Update call sites for `BuildOptions` | 4h | Medium |
| Update tests | 4h | Medium |

**Exit Criteria**:
- Single source of truth for each validator
- `BuildOptions` and navigation dataclasses created
- All tests pass

---

### Sprint 3: Incremental Package Refactoring (Week 4-5) ⚠️ HIGH RISK

**Goal**: Break up `incremental.py` (1,399 lines) into focused package.

| Task | Effort | Risk |
|------|--------|------|
| Create `orchestration/incremental/` package structure | 1h | Low |
| Extract `ChangeDetector` class | 4h | Medium |
| Merge `find_work()` and `find_work_early()` | 6h | **High** |
| Extract `CascadeTracker` | 3h | Low |
| Update imports and tests | 4h | Medium |
| Feature flag validation (1-week parallel execution) | 8h | Medium |

**Exit Criteria**:
- `IncrementalOrchestrator` < 400 lines
- `find_work()` and `find_work_early()` merged
- Feature flag validated
- All incremental build tests pass

**Risk Mitigation**:
- Feature flag: `use_unified_change_detector: bool = False`
- Parallel execution validation period
- Rollback plan

---

### Sprint 4: Navigation & Parser Packages (Week 6-7)

**Goal**: Break up navigation and mistune parser.

| Task | Effort | Risk |
|------|--------|------|
| Create `template_functions/navigation/` package | 1h | Low |
| Split navigation into focused modules | 4h | Low |
| Migrate to typed dataclasses | 6h | Medium |
| Create `parsers/mistune/` package structure | 1h | Low |
| Extract highlighting plugin | 4h | Medium |
| Extract TOC logic | 4h | Medium |
| Extract cross-reference support | 3h | Low |
| Update tests | 6h | Medium |

**Exit Criteria**:
- Navigation package < 200 lines per module
- `MistuneParser` < 400 lines
- All tests pass

---

### Sprint 5: Remaining Large Files (Week 8)

**Goal**: Break up remaining large files.

| Task | Effort | Risk |
|------|--------|------|
| Break up `cli/output.py` (relocated) | 4h | Medium |
| Convert `autodoc/extractors/python.py` to package | 6h | Medium |
| Rename autodoc/orchestration/ to orchestrators/ | 2h | Low |
| Update imports and tests | 4h | Medium |

**Exit Criteria**:
- All files < 600 lines (soft target: 400)
- All tests pass

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking incremental builds during refactor | Medium | High | Feature flag (`use_unified_change_detector`), parallel execution validation period, rollback plan |
| Import breakage for external users | Low | High | Deprecation warnings + re-exports for 1 release |
| Template breakage from navigation changes | Low | Medium | Dataclasses implement `__getitem__` for dict compatibility; gradual migration path |
| Circular imports after relocation | Medium | Medium | Careful dependency analysis before moving |
| Performance regression | Low | Medium | Benchmark before/after each sprint |
| Test coverage gaps | Medium | Medium | Run full test suite after each file move; audit incremental tests before Sprint 3 |

---

## Success Criteria

### Quantitative

- [ ] `rendering/` has < 80 files (from 107)
- [ ] `utils/` has < 15 files (from 25)
- [ ] No file in `bengal/` exceeds 600 lines (soft target: 400)
- [ ] No function exceeds 100 lines (soft target: 50)
- [ ] No validation logic duplicated between packages
- [ ] Test coverage maintained or improved
- [ ] Build performance within 5% of baseline

### Qualitative

- [ ] New developers can find code by domain concept
- [ ] Single source of truth for each concern
- [ ] Clear package boundaries with minimal overlap
- [ ] Changes to one concern don't require touching unrelated code
- [ ] Type hints improve IDE experience for template function returns

---

## Alternatives Considered

### Alternative 1: File-Level First, Package-Level Later

**Approach**: Break up large files first, then reorganize packages.

**Pros**: Addresses immediate pain points faster.

**Cons**:
- Risk of moving code twice (e.g., break up `cards.py`, then move to `directives/`)
- Package structure affects where files should be broken up
- More coordination overhead

**Verdict**: Rejected. Package structure should be established first.

### Alternative 2: Separate RFCs

**Approach**: Keep package consolidation and code smell remediation as separate RFCs.

**Pros**: Smaller scope per RFC, easier to review.

**Cons**:
- Coordination overhead
- Risk of conflicting changes
- Overlap in work (e.g., `cards.py` needs both)

**Verdict**: Rejected. Unified approach prevents double work and ensures optimal sequencing.

---

## Related

- **Deprecated RFCs**: 
  - `plan/drafted/rfc-code-smell-remediation.md` (consolidated into this RFC)
  - `plan/drafted/rfc-package-architecture-consolidation.md` (consolidated into this RFC)
- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc` - 400-line threshold
- **Existing Patterns**: `bengal/core/page/`, `bengal/core/site/` - Well-structured packages

