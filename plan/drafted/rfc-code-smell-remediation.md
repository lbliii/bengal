# RFC: Code Smell Remediation - Monolithic Modules and God Functions

**Status**: Draft
**Author**: AI Assistant
**Created**: 2025-12-19
**Category**: Architecture / Refactoring

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
| `orchestration/incremental.py` | 1,284 | 3.2x |
| `analysis/knowledge_graph.py` | 1,222 | 3.1x |
| `autodoc/extractors/python.py` | 1,146 | 2.9x |
| `rendering/parsers/mistune.py` | 1,075 | 2.7x |
| `rendering/plugins/directives/cards.py` | 1,027 | 2.6x |
| `rendering/template_functions/navigation.py` | 950 | 2.4x |
| `discovery/content_discovery.py` | 911 | 2.3x |
| `utils/cli_output.py` | 838 | 2.1x |

### Evidence: God Functions (Top 15)

| Location | Function | Lines |
|----------|----------|-------|
| `cli/commands/build.py:156` | `build()` | 421 |
| `analysis/graph_visualizer.py:290` | `generate_html()` | 409 |
| `health/validators/connectivity.py:152` | `_safe_get_metrics()` | 280 |
| `orchestration/build/__init__.py:97` | `BuildOrchestrator.build()` | 274 |
| `health/linkcheck/async_checker.py:33` | `__init__()` | 269 |
| `orchestration/streaming.py:48` | `process()` | 235 |
| `rendering/renderer.py:117` | `render_page()` | 215 |
| `rendering/template_engine/environment.py:132` | `create_jinja_environment()` | 203 |
| `rendering/template_functions/navigation.py:132` | `get_breadcrumbs()` | 196 |
| `orchestration/incremental.py:727` | `find_work()` | 177 |
| `orchestration/incremental.py:482` | `find_work_early()` | 168 |
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
# Lines 482-725: find_work_early()
# Lines 727-902: find_work()
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

### 5. Middle Man Pattern

`KnowledgeGraph` delegates nearly all methods to `GraphAnalyzer`:

```python
# bengal/analysis/knowledge_graph.py
def get_hubs(self, threshold: int | None = None) -> list[Page]:
    return self._analyzer.get_hubs(threshold)

def get_leaves(self, threshold: int | None = None) -> list[Page]:
    return self._analyzer.get_leaves(threshold)

def get_orphans(self) -> list[Page]:
    return self._analyzer.get_orphans()
# ...10+ more delegation methods
```

---

## Proposed Solutions

### Phase 1: High-Impact Modularization (Priority 1)

#### 1.1 Convert `orchestration/incremental.py` to Package

**Current**: 1,284 lines in single file

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

**Current**: 950 lines in single file

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

@dataclass  
class PaginationItem:
    """Single page in pagination."""
    num: int | None
    url: str | None
    is_current: bool = False
    is_ellipsis: bool = False

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
```

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

#### 3.2 Simplify `KnowledgeGraph` Delegation

Option A: Expose analyzer directly
```python
@property
def analyzer(self) -> GraphAnalyzer:
    if not self._built:
        raise RuntimeError("Call build() first")
    return self._analyzer
```

Option B: Use `__getattr__` delegation
```python
def __getattr__(self, name: str) -> Any:
    if self._analyzer and hasattr(self._analyzer, name):
        return getattr(self._analyzer, name)
    raise AttributeError(name)
```

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
| Breaking incremental builds during refactor | Medium | High | Feature flag for new ChangeDetector |
| Template breakage from navigation changes | Low | Medium | Keep dict compatibility during transition |
| Performance regression | Low | Medium | Benchmark before/after |
| Increased import complexity | Medium | Low | Clear public API in `__init__.py` |

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

## Related

- **Architecture Rule**: `bengal/.cursor/rules/architecture-patterns.mdc` - 400-line threshold
- **Existing Patterns**: `bengal/core/page/` - Mixin-based package structure
- **RFC**: `plan/drafted/rfc-autodoc-rendering-consolidation.md` - Related cleanup
