# RFC: Code Smell Remediation - Monolithic Modules and God Functions

**Status**: Deprecated ⚠️
**Author**: AI Assistant
**Created**: 2025-12-19
**Evaluated**: 2025-12-19
**Refreshed**: 2025-01-27
**Deprecated**: 2025-01-27
**Replaced By**: `plan/drafted/rfc-architecture-refactoring.md`
**Confidence**: 91% 🟢
**Category**: Architecture / Refactoring

---

## ⚠️ This RFC Has Been Consolidated

This RFC has been **deprecated** and consolidated into a unified architecture refactoring plan.

**See**: `plan/drafted/rfc-architecture-refactoring.md` for the complete, unified refactoring plan that combines:
- Package-level consolidation (from `rfc-package-architecture-consolidation.md`)
- File-level code smell remediation (this RFC)

The unified RFC provides better sequencing (package consolidation first, then file-level refactoring) and eliminates overlap (e.g., `cards.py` extraction and breakdown handled in one coordinated step).

---

## Original Content (Preserved for Reference)

---

## Executive Summary

Codebase analysis identified **8 monolithic files** (>700 lines) that should become packages, **40+ god functions** (>50 lines), and several structural code smells. This RFC proposes a phased refactoring plan to improve maintainability, testability, and adherence to Bengal's existing architectural patterns.

---

## Problem Statement

### Current State

Bengal already follows good modularization patterns in key areas:
- `bengal/core/page/` - Well-structured package with focused mixins
- `bengal/core/site/` - Properly decomposed into concern-specific modules
- `bengal/orchestration/build/` - Build phases separated into modules

However, several modules have grown beyond the **400-line threshold** specified in Bengal's architecture rules, and numerous functions exceed reasonable complexity limits.

### Evidence: Largest Files

| File | Lines | Threshold Exceeded |
|------|-------|-------------------|
| `orchestration/incremental.py` | 1,399 | 3.5x |
| `analysis/knowledge_graph.py` | 1,222 | 3.1x |
| `autodoc/extractors/python.py` | 1,146 | 2.9x |
| `rendering/parsers/mistune.py` | 1,075 | 2.7x |
| `rendering/plugins/directives/cards.py` | 1,027 | 2.6x |
| `rendering/template_functions/navigation.py` | 966 | 2.4x |
| `discovery/content_discovery.py` | 944 | 2.4x |
| `core/section.py` | 934 | 2.3x |
| `utils/cli_output.py` | 838 | 2.1x |

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
| `orchestration/incremental.py:842` | `find_work()` | 176 |
| `orchestration/incremental.py:588` | `find_work_early()` | 254 |
| `rendering/parsers/mistune.py:179` | `_create_syntax_highlighting_plugin()` | 175 |
| `postprocess/sitemap.py:74` | `generate()` | 150 |
| `health/autofix.py:427` | `apply_fix()` | 150 |
| `autodoc/config.py:14` | `load_autodoc_config()` | 150 |

---

## Architectural Code Smells

### 1. Long Parameter Lists

**`BuildOrchestrator.build()`** has 11 parameters:

```python
def build(
    self,
    parallel: bool = True,
    incremental: bool | None = None,
    verbose: bool = False,
    quiet: bool = False,
    profile: BuildProfile | None = None,
    memory_optimized: bool = False,
    strict: bool = False,
    full_output: bool = False,
    profile_templates: bool = False,
    changed_sources: set[Path] | None = None,
    nav_changed_sources: set[Path] | None = None,
    structural_changed: bool = False,
) -> BuildStats:
```

**Impact**: Hard to remember parameter order, easy to pass wrong values, difficult to extend.

### 2. Duplicated Logic

`IncrementalOrchestrator` has two nearly identical methods:

- `find_work_early()` (168 lines) - Called before taxonomy generation
- `find_work()` (177 lines) - Called after taxonomy generation

Both share ~70% of their logic but are maintained separately.

**Evidence** (`orchestration/incremental.py`):
```python
# Lines 588-841: find_work_early() (254 lines)
# Lines 842-1017: find_work() (176 lines)
# Both contain:
#   - Section-level filtering
#   - Cache bypass checking  
#   - Template change detection
#   - Autodoc dependency tracking
```

### 3. Primitive Obsession

Navigation functions return untyped dictionaries instead of dataclasses:

```python
# bengal/rendering/template_functions/navigation.py:132
def get_breadcrumbs(page: Page) -> list[dict[str, Any]]:
    items.append({"title": title, "url": url, "is_current": True})
```

**Impact**: No IDE autocompletion, runtime key errors possible, hard to refactor.

### 4. Feature Envy

`RenderingPipeline._normalize_autodoc_element()` (64 lines) deeply manipulates autodoc element internals:

```python
# bengal/rendering/pipeline/core.py:804-868
def _normalize_autodoc_element(self, element: Any) -> Any:
    # 64 lines of manipulation
    def _coerce(obj: Any) -> None:
        obj.children = []
        obj.metadata = _wrap_metadata(obj.metadata)
        meta.setdefault("signature", "")
        meta.setdefault("parameters", [])
        # ...more manipulation...
```

**Impact**: This logic belongs on the autodoc element class, not the rendering pipeline.

### 5. Middle Man Pattern (Low Priority)

`KnowledgeGraph` delegates nearly all methods to `GraphAnalyzer`:

```python
# bengal/analysis/knowledge_graph.py
def get_hubs(self, threshold: int | None = None) -> list[Page]:
    if not self._built or self._analyzer is None:
        raise RuntimeError("KnowledgeGraph is not built. Call .build() first")
    return self._analyzer.get_hubs(threshold)

def get_leaves(self, threshold: int | None = None) -> list[Page]:
    if not self._built or self._analyzer is None:
        raise RuntimeError("KnowledgeGraph is not built. Call .build() first")
    return self._analyzer.get_leaves(threshold)
# ...10+ more delegation methods with build-state validation
```

**Nuance**: This is **defensive programming**, not pure middle-man anti-pattern. Each delegated method validates build state before forwarding, preventing cryptic errors if the graph hasn't been built. This adds value.

**Revised Assessment**: Lower priority than other items. Consider whether the ~20 lines of boilerplate justify refactoring, given the safety benefit.

---

## Proposed Solutions

### Phase 1: High-Impact Modularization (Priority 1)

#### 1.1 Convert `orchestration/incremental.py` to Package

**Current**: 1,399 lines in single file (increased from 1,284)

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

#### 1.2 Convert `rendering/template_functions/navigation.py` to Package

**Current**: 966 lines in single file (increased from 950)

**Proposed Structure**:
```
bengal/rendering/template_functions/navigation/
├── __init__.py              # register() function, re-exports
├── breadcrumbs.py           # get_breadcrumbs() + BreadcrumbItem dataclass
├── pagination.py            # get_pagination_items() + PaginationData dataclass
├── tree.py                  # get_nav_tree() + NavTreeItem dataclass
├── auto_nav.py              # get_auto_nav() + section menu helpers
└── toc.py                   # get_toc_grouped(), combine_track_toc_items()
```

**Key Refactoring**:
- Create typed dataclasses for return values
- Extract `_build_section_menu_item()` to `auto_nav.py`

#### 1.3 Create `BuildOptions` Dataclass

**Current**: 11 parameters to `build()`

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

---

### Phase 2: Medium-Priority Modularization (Priority 2)

#### 2.1 Convert `rendering/parsers/mistune.py` to Package

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

#### 2.2 Convert `autodoc/extractors/python.py` to Package

**Current**: 1,146 lines

**Proposed Structure**:
```
bengal/autodoc/extractors/python/
├── __init__.py              # PythonExtractor class
├── docstring_parser.py      # Docstring parsing (Google, NumPy, Sphinx)
├── signature_analyzer.py    # Function/class signature analysis
├── hierarchy_builder.py     # Module hierarchy construction
└── metadata.py              # Metadata extraction helpers
```

#### 2.3 Introduce Navigation Dataclasses

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

**Template Migration Path**:
1. Deploy dataclasses with `__getitem__` support (zero template changes)
2. Update templates to use dot notation (`item.title` instead of `item["title"]`)
3. Optionally remove `__getitem__` in future major version

---

### Phase 3: Lower-Priority Improvements (Priority 3)

#### 3.1 Extract `_normalize_autodoc_element()` to Autodoc Model

Move the normalization logic to a method on `DocElement`:

```python
# bengal/autodoc/models/element.py
class DocElement:
    def normalize_for_rendering(self) -> DocElement:
        """Prepare element for template rendering."""
        # Move 64 lines of normalization here
        pass
```

#### 3.2 Simplify `KnowledgeGraph` Delegation (Optional)

**Reassessment**: Current delegation includes build-state validation, which is valuable defensive programming. Refactoring may not be worth the risk.

**If proceeding, Option A is recommended** (preserves safety):
```python
@property
def analyzer(self) -> GraphAnalyzer:
    """Access analyzer after build() has been called."""
    if not self._built or self._analyzer is None:
        raise RuntimeError("KnowledgeGraph is not built. Call .build() first")
    return self._analyzer

# Usage: graph.analyzer.get_hubs() instead of graph.get_hubs()
```

**Option B (Not Recommended)** - Loses explicit build-state validation:
```python
def __getattr__(self, name: str) -> Any:
    # CAUTION: This silently fails if _analyzer is None
    if self._analyzer and hasattr(self._analyzer, name):
        return getattr(self._analyzer, name)
    raise AttributeError(name)
```

**Recommendation**: Defer this refactoring. The ~50 lines of delegation boilerplate provide meaningful safety guarantees. Focus effort on higher-impact items.

#### 3.3 Extract CLI Build Command Executor

```python
# bengal/cli/commands/build_executor.py
class BuildCommandExecutor:
    """Encapsulates build command execution logic."""

    def __init__(self, site: Site, options: BuildOptions, cli: CLIOutput):
        self.site = site
        self.options = options
        self.cli = cli

    def execute(self) -> BuildStats:
        """Execute full build pipeline."""
        pass

    def _setup_logging(self) -> None: ...
    def _initialize_build(self) -> None: ...
    def _run_build_phases(self) -> None: ...
    def _finalize_build(self) -> None: ...
```

---

## Implementation Plan

### Sprint 1: Foundation (Week 1)

| Task | Effort | Risk |
|------|--------|------|
| Create `BuildOptions` dataclass | 2h | Low |
| Create navigation dataclasses (`BreadcrumbItem`, etc.) | 3h | Low |
| Update call sites for `BuildOptions` | 4h | Medium |

**Exit Criteria**: All tests pass, no API changes visible to users

### Sprint 2: Incremental Package (Week 2)

| Task | Effort | Risk |
|------|--------|------|
| Create `orchestration/incremental/` package structure | 1h | Low |
| Extract `ChangeDetector` class | 4h | Medium |
| Merge `find_work()` and `find_work_early()` | 6h | High |
| Extract `CascadeTracker` | 3h | Low |
| Update imports and tests | 4h | Medium |

**Exit Criteria**: `IncrementalOrchestrator` < 400 lines, all incremental build tests pass

**Risk Mitigation for `find_work` Merge** (HIGH risk item):

1. **Pre-requisite**: Audit existing test coverage for `find_work_early()` and `find_work()`
   - Location: `tests/unit/test_incremental.py`
   - Required: Tests covering both pre-taxonomy and post-taxonomy phases

2. **Feature flag**: Introduce `use_unified_change_detector: bool = False` config option
   - Old code path remains default until validated
   - New code path opt-in for testing

3. **Parallel execution period**: Run both old and new code paths, compare results
   - Log any discrepancies
   - 1-week validation before switching default

4. **Rollback plan**: Git revert to last known-good if issues arise

### Sprint 3: Navigation Package (Week 3)

| Task | Effort | Risk |
|------|--------|------|
| Create `template_functions/navigation/` package | 1h | Low |
| Split into focused modules | 4h | Low |
| Migrate to typed dataclasses | 6h | Medium |
| Update template usage if needed | 4h | Low |

**Exit Criteria**: Navigation package < 200 lines per module, templates still work

### Sprint 4: Parser Package (Week 4)

| Task | Effort | Risk |
|------|--------|------|
| Create `parsers/mistune/` package structure | 1h | Low |
| Extract highlighting plugin | 4h | Medium |
| Extract TOC logic | 4h | Medium |
| Extract cross-reference support | 3h | Low |
| Update tests | 4h | Medium |

**Exit Criteria**: `MistuneParser` < 400 lines, all parsing tests pass

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking incremental builds during refactor | Medium | High | Feature flag (`use_unified_change_detector`), parallel execution validation period, rollback plan |
| Template breakage from navigation changes | Low | Medium | Dataclasses implement `__getitem__` for dict compatibility; gradual migration path |
| Performance regression | Low | Medium | Benchmark before/after each sprint |
| Increased import complexity | Medium | Low | Clear public API in `__init__.py`, re-export key classes |
| Test coverage gaps during merge | Medium | Medium | Audit existing incremental tests before Sprint 2; require 100% coverage for ChangeDetector |

---

## Success Criteria

### Quantitative

- [ ] No file in `bengal/` exceeds 600 lines (soft target: 400)
- [ ] No function exceeds 100 lines (soft target: 50)
- [ ] Test coverage maintained or improved
- [ ] Build performance within 5% of baseline

### Qualitative

- [ ] New developers can understand module structure faster
- [ ] Changes to one concern don't require touching unrelated code
- [ ] Type hints improve IDE experience for template function returns

---

## Alternative Considered: Incremental Refactoring Without Package Conversion

**Approach**: Just split large functions without changing file structure.

**Pros**: Lower risk, faster to implement.

**Cons**:
- Doesn't address the core problem (files too large)
- Loses opportunity for cleaner imports
- Harder to test individual components

**Verdict**: Rejected. Bengal already has the package pattern established (`core/page/`, `core/site/`, `orchestration/build/`); we should extend it consistently.

---

## Evaluation Notes

**Evaluated**: 2025-12-19 | **Refreshed**: 2025-01-27 | **Confidence**: 91% 🟢

### Claims Verified (17/18)

| Claim Category | Verified | Notes |
|----------------|----------|-------|
| File sizes (8 files) | 8/8 ✅ | All line counts exact match |
| God function locations | ✅ | Line numbers verified |
| BuildOrchestrator signature | ✅ | 11 params at `build/__init__.py:97-111` |
| find_work duplication | ✅ | Lines 588 and 842 confirmed (functions have grown) |
| Existing package patterns | ✅ | `core/page/`, `core/site/`, `build/` verified |
| Architecture threshold | ✅ | 400-line rule in `architecture-patterns.mdc:223` |

### Corrections Made

1. **CLI build function**: 421 → 419 lines (file is 575 lines, function spans 156-575)
2. **Middle Man assessment**: Added nuance - delegation includes defensive build-state checks

### Refresh Updates (2025-01-27)

1. **File sizes updated**: `incremental.py` grew from 1,284 → 1,399 lines (+115 lines)
2. **Function locations shifted**: `find_work_early()` moved from line 482 → 588, `find_work()` from 727 → 842
3. **Function sizes**: `find_work_early()` grew from 168 → 254 lines, `find_work()` remains ~176 lines
4. **New entry**: `core/section.py` (934 lines) added to largest files list
5. **Navigation file**: Grew from 950 → 966 lines
6. **Content discovery**: Grew from 911 → 944 lines

**Impact**: The problem has worsened since RFC creation. Refactoring is more urgent.

### Improvements Added

1. **Dict compatibility strategy** for navigation dataclasses (Sprint 3)
2. **Risk mitigation detail** for `find_work` merge (Sprint 2)
3. **KnowledgeGraph recommendation**: Defer refactoring, value outweighs boilerplate cost

### Confidence Breakdown

| Component | Score | Notes |
|-----------|-------|-------|
| Evidence Strength | 38/40 | 17/18 claims verified exactly |
| Consistency | 28/30 | Proposals match existing patterns |
| Recency | 15/15 | Current codebase verified |
| Test Coverage | 10/15 | Proposed dataclasses need tests |
| **Total** | **91/100** | 🟢 Ready for implementation |

---

## Related

- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc` - 400-line threshold
- **Existing Patterns**: `bengal/core/page/` - Mixin-based package structure
- **RFC**: `plan/drafted/rfc-autodoc-rendering-consolidation.md` - Related cleanup
