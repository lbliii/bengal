# RFC: Code Health Improvements - Modularization & Complexity Reduction

**Status**: Draft  
**Created**: 2026-01-13  
**Updated**: 2026-01-13  
**Priority**: Medium  
**Tracking**: `plan/rfc-code-health-improvements.md`

---

## Executive Summary

A codebase audit identified several monolithic files and high-complexity modules in Bengal's core systems. This RFC proposes targeted refactoring to improve maintainability, testability, and cognitive load for contributors. Focus areas: rendering errors, HTML renderer, page proxy, and orchestration modules.

**Key Changes**:
- Split 5 monolithic files into focused modules
- Complete adoption of existing `_lazy_property` pattern in PageProxy
- Decompose HtmlRenderer using composition pattern
- Isolate threading complexity in orchestration layer

**Scope**: Patitas-based code only (Mistune deprecation tracked separately)

---

## Problem Statement

### Audit Findings

| Category | Files Identified | Impact |
|----------|-----------------|--------|
| Monolithic (>800 LOC) | 25 files | Hard to navigate, test, modify |
| High function count (>25) | 15 files | Low cohesion, multiple responsibilities |
| God objects | 3 files | Too much in one class |

### Top Priority Files

| File | LOC | Functions | Issue |
|------|-----|-----------|-------|
| `rendering/errors.py` | 1,246 | 23 | Error handling + formatting + deduplication |
| `rendering/parsers/patitas/renderers/html.py` | 1,114 | 47 | Single class renders all node types |
| `orchestration/render.py` | 1,078 | 22 | Threading + rendering + caching |
| `health/report.py` | 952 | 39 | Data models + formatting + serialization |
| `core/page/proxy.py` | 861 | 80 | Lazy delegation for every property |

---

## Proposed Improvements

### 1. Split `rendering/errors.py` (1,246 → ~4 × 300 LOC)

**Current Structure**:
```
rendering/errors.py
├── TemplateErrorContext (dataclass)
├── InclusionChain (dataclass)  
├── ErrorDeduplicator (class)
├── TemplateRenderError (exception)
└── display_template_error() + helpers (functions)
```

**Proposed Structure**:
```
rendering/errors/
├── __init__.py          # Public API re-exports
├── context.py           # TemplateErrorContext, InclusionChain
├── deduplication.py     # ErrorDeduplicator
├── exceptions.py        # TemplateRenderError
└── display.py           # display_template_error(), formatting helpers
```

**Benefits**:
- Focused modules with single responsibility
- Easier to test deduplication logic in isolation
- Display formatting can evolve independently

**Migration**:
```python
# Before
from bengal.rendering.errors import TemplateRenderError, display_template_error

# After (same API via __init__.py re-exports)
from bengal.rendering.errors import TemplateRenderError, display_template_error
```

---

### 2. Decompose `HtmlRenderer` (1,114 → ~3 × 350 LOC)

**Current**: Single 1,114-line class with 29 class methods + 18 node-type dispatch handlers (47 total render paths) handling all node types.

**Method Breakdown**:
- 29 class methods (direct `def` statements)
- 18 node-type handlers registered via dispatch table
- All node types (block, inline, directive) in one file

**Proposed Structure**:
```
rendering/parsers/patitas/renderers/
├── __init__.py          # HtmlRenderer facade
├── html.py              # Core HtmlRenderer (composition root)
├── blocks.py            # Block-level rendering (paragraphs, lists, quotes)
├── inline.py            # Inline rendering (emphasis, links, code)
└── directives.py        # Directive dispatch and rendering
```

**Implementation Approach**:
```python
# html.py - Composition over monolith
class HtmlRenderer:
    def __init__(self):
        self._blocks = BlockRenderer()
        self._inline = InlineRenderer()
        self._directives = DirectiveRenderer()
    
    def render_node(self, node: Node, sb: StringBuilder) -> None:
        match node:
            case Paragraph() | List() | Quote():
                self._blocks.render(node, sb)
            case Emphasis() | Link() | Code():
                self._inline.render(node, sb)
            case Directive():
                self._directives.render(node, sb)
```

**Benefits**:
- Each renderer module under 400 LOC
- Block/inline/directive logic can be tested independently
- New node types don't bloat single file

**Performance Consideration**: This is a hot path (~15% of render time). Benchmark required before/after to ensure composition overhead stays < 3%.

---

### 3. Complete `PageProxy` Pattern Adoption (861 LOC, 80 functions)

**Current State**: The `_lazy_property` helper already exists (`proxy.py:40-55`) but is only used for 2 properties. The remaining 78 properties use manual delegation.

**Existing Pattern** (already in codebase):
```python
# proxy.py:40-55 - Already implemented!
def _lazy_property(attr_name: str, default: Any = None, doc: str | None = None):
    """Create a lazy property that delegates to _full_page."""
    def getter(self: PageProxy) -> Any:
        self._ensure_loaded()
        return getattr(self._full_page, attr_name, default) if self._full_page else default
    getter.__doc__ = doc or f"Get {attr_name} (lazy-loaded from full page)."
    return property(getter)
```

**Current Problem**: Pattern exists but adoption is incomplete.
- ✅ 2 properties use `_lazy_property`
- ❌ 78 properties use manual delegation

**Proposed Change**: Complete pattern migration.

```python
# Before: 78 manual properties like this
@property
def title(self) -> str:
    self._ensure_loaded()
    return self._full_page.title if self._full_page else ""

# After: Compact declarations using existing helper
title = _lazy_property('title', '')
description = _lazy_property('description', '')
content = _lazy_property('content', '')
# ... 75 more one-liners
```

**Benefits**:
- Reduces LOC from 861 to ~300 (65% reduction)
- Maintains IDE autocomplete (explicit property declarations)
- No new patterns to introduce—just complete existing migration
- Lower risk since helper is already tested in production

**Effort Reduction**: Originally estimated 3 hours → now 1.5 hours (pattern exists)

---

### 4. Modularize `orchestration/render.py` (1,078 LOC)

**Current**: Threading management + rendering + active render tracking + generation counting all in one file.

**Proposed Structure**:
```
orchestration/render/
├── __init__.py          # Public API: render_pages()
├── orchestrator.py      # RenderOrchestrator class
├── parallel.py          # ThreadPoolExecutor logic, worker management
├── tracking.py          # Active render counting, generation tracking
└── pipeline.py          # Per-page render pipeline (thread-local)
```

**Benefits**:
- Threading complexity isolated in `parallel.py`
- Lifecycle tracking in dedicated `tracking.py`
- Core orchestrator stays focused on coordination

---

### 5. Split `health/report.py` (952 LOC)

**Current**: Data models + console formatting + JSON export + quality scoring.

**Proposed Structure**:
```
health/report/
├── __init__.py          # Public API
├── models.py            # CheckStatus, CheckResult, ValidatorStats, etc.
├── formatting.py        # Console output, Rich integration
├── serialization.py     # JSON export, CI integration formats
└── scoring.py           # Quality scoring algorithms
```

---

## Implementation Plan

### Phase 0: Baseline Capture (Required First)

| Task | Effort | Output |
|------|--------|--------|
| Capture complexity metrics | 30 min | `reports/complexity-baseline.json` |
| Capture render benchmarks | 30 min | `reports/render-baseline.json` |
| Document import graph | 30 min | List of files importing each target |

**Gate**: Phase 1 cannot start until baselines are captured.

### Phase 1: Low-Risk Splits (No API Changes)

| File | Target | Effort | Risk | Importers |
|------|--------|--------|------|-----------|
| `rendering/errors.py` | 4 modules | 2 hours | Low | 13 files |
| `health/report.py` | 4 modules | 2 hours | Low | ~5 files |

These are pure organizational changes with re-exports maintaining backward compatibility.

**Validation**: `uv run pytest tests/ -v` must pass after each split.

### Phase 2: Structural Improvements

| File | Target | Effort | Risk | Notes |
|------|--------|--------|------|-------|
| `core/page/proxy.py` | Complete `_lazy_property` adoption | 1.5 hours | Low | Pattern already exists |
| `orchestration/render.py` | 4 modules | 4 hours | Medium | Thread-safety critical |

**PageProxy**: Lower effort since `_lazy_property` helper already implemented.

**Render Orchestrator**: Requires new thread-safety tests before merge.

### Phase 3: Renderer Decomposition (Performance-Gated)

| File | Target | Effort | Risk | Gate |
|------|--------|--------|------|------|
| `renderers/html.py` | 4 modules | 6 hours | Medium | < 5% perf regression |

**Pre-requisite**: Benchmark baseline captured in Phase 0.

**Gate Criteria**: 
- `benchmark_render.py` shows < 5% regression
- 1000-page build shows < 3% regression

Most complex change—affects hot path. Do not merge without passing performance gate.

---

## Success Metrics

### Code Organization

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Files > 800 LOC | 25 | < 15 | `find bengal -name "*.py" \| xargs wc -l \| awk '$1>800'` |
| Files > 40 functions | 4 | 0 | `radon raw -s bengal \| grep -E "^[^ ].*functions: [4-9][0-9]"` |
| Max file size (target files) | 1,246 LOC | < 600 LOC | Per-file `wc -l` |

### Cognitive Complexity (via `radon`)

| File | Current CC | Target CC |
|------|------------|-----------|
| `rendering/errors.py` | Measure baseline | < 5 average |
| `renderers/html.py` | Measure baseline | < 5 average |
| `core/page/proxy.py` | Measure baseline | < 3 average |
| `orchestration/render.py` | Measure baseline | < 5 average |

**Baseline Command**:
```bash
uv run radon cc bengal/rendering/errors.py -a -s
uv run radon cc bengal/rendering/parsers/patitas/renderers/html.py -a -s
```

### Performance (Phase 3 Gate)

| Benchmark | Baseline | Max Regression |
|-----------|----------|----------------|
| `benchmarks/benchmark_render.py` | Capture before | < 5% slower |
| 1000-page warm build | Capture before | < 3% slower |

**Benchmark Commands**:
```bash
# Render performance
uv run python benchmarks/benchmark_render.py --iterations 100

# Build performance  
uv run bengal build site/ --profile --quiet
```

---

## Testing Strategy

### Phase 1: Baseline Capture (Before Any Changes)

```bash
# 1. Run existing test suite
uv run pytest tests/ -v --tb=short

# 2. Capture complexity baseline
uv run radon cc bengal/rendering/errors.py bengal/orchestration/render.py -a -j > reports/complexity-baseline.json

# 3. Capture performance baseline
uv run python benchmarks/benchmark_render.py --output reports/render-baseline.json
```

### Phase 2: During Refactoring

- All existing tests must pass after each commit
- No new test files until split is complete (avoid test-code drift)

### Phase 3: Post-Refactoring Validation

**New Unit Tests for Isolated Modules**:

```python
# tests/unit/rendering/errors/test_deduplication.py
def test_error_deduplicator_tracks_unique_errors():
    """Test ErrorDeduplicator in isolation."""

# tests/unit/rendering/errors/test_display.py  
def test_display_template_error_formats_correctly():
    """Test display formatting without template engine."""
```

**Thread-Safety Tests for `orchestration/render/parallel.py`**:

```python
# tests/integration/test_render_parallel.py
import threading

def test_parallel_render_no_shared_state():
    """Verify worker threads don't share mutable state."""
    results = []
    errors = []
    
    def worker(page_id: int):
        try:
            # Each worker should have isolated state
            result = render_page_isolated(page_id)
            results.append((page_id, result))
        except Exception as e:
            errors.append((page_id, e))
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 10

def test_generation_counter_thread_safe():
    """Verify generation tracking is atomic under contention."""
```

**Performance Regression Tests**:

```python
# tests/integration/test_render_performance.py
import pytest

@pytest.mark.benchmark
def test_html_renderer_no_regression(benchmark_baseline):
    """HtmlRenderer composition must not exceed 5% overhead."""
    result = run_render_benchmark()
    assert result.time_ms < benchmark_baseline * 1.05
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Verification |
|------|------------|--------|------------|--------------|
| Import path breakage | Low | Medium | Re-export from `__init__.py` | `grep -r "from bengal.rendering.errors import"` returns same results |
| Performance regression (HtmlRenderer) | Medium | High | Phase 3 performance gate | Benchmark < 5% regression |
| Thread-safety regression | Low | High | New thread-safety tests | `test_parallel_render_no_shared_state` passes |
| Incomplete migration | Medium | Low | Phase incrementally | Each phase has completion checklist |
| IDE autocomplete loss (PageProxy) | Low | Low | Use explicit property declarations | Manual IDE testing |

### Rollback Plan

Each phase is independently revertible:

```bash
# If Phase 1 fails
git revert <phase-1-commits>

# If Phase 3 performance gate fails
# Don't merge - iterate on composition pattern locally
```

---

## Dependencies

### Tooling Requirements

| Tool | Purpose | Installation |
|------|---------|--------------|
| `radon` | Cognitive complexity measurement | `uv add --dev radon` |
| `pytest-benchmark` | Performance regression testing | Already in dev deps |

### Pre-Existing Infrastructure

| Component | Status | Used For |
|-----------|--------|----------|
| `_lazy_property` helper | ✅ Exists (`proxy.py:40`) | PageProxy migration |
| `benchmarks/benchmark_render.py` | ✅ Exists | HtmlRenderer gate |
| Parallel build tests | ✅ Exist | Thread-safety validation |

---

## Out of Scope

- Mistune deprecation (separate RFC: `rfc-mistune-deprecation.md`)
- New features
- API changes (all changes are internal organization)

---

## Execution Checklists

### Phase 0 Checklist
- [ ] Install radon: `uv add --dev radon`
- [ ] Capture complexity baseline: `uv run radon cc bengal/rendering/errors.py -a -j > reports/complexity-baseline.json`
- [ ] Capture render baseline: `uv run python benchmarks/benchmark_render.py --output reports/render-baseline.json`
- [ ] Document current import graph for target files
- [ ] Commit baselines to repo

### Phase 1 Checklist
- [ ] Split `rendering/errors.py` → `rendering/errors/`
- [ ] Verify: `grep -r "from bengal.rendering.errors import"` still works
- [ ] Run: `uv run pytest tests/unit/rendering/test_template_errors.py -v`
- [ ] Split `health/report.py` → `health/report/`
- [ ] Run: `uv run pytest tests/ -v`
- [ ] Commit with message: `refactor(rendering): split errors.py into focused modules`

### Phase 2 Checklist
- [ ] Migrate 78 PageProxy properties to `_lazy_property`
- [ ] Verify IDE autocomplete works
- [ ] Run: `uv run pytest tests/unit/core/test_page_proxy.py -v`
- [ ] Split `orchestration/render.py` → `orchestration/render/`
- [ ] Add thread-safety test: `test_parallel_render_no_shared_state`
- [ ] Run: `uv run pytest tests/integration/warm_build/ -v`
- [ ] Commit with message: `refactor(core): complete _lazy_property adoption in PageProxy`

### Phase 3 Checklist
- [ ] Create branch: `refactor/html-renderer-decomposition`
- [ ] Implement composition pattern
- [ ] Run benchmark: `uv run python benchmarks/benchmark_render.py`
- [ ] Compare to baseline: must be < 5% slower
- [ ] If gate fails: iterate locally, do not merge
- [ ] If gate passes: merge and commit: `refactor(rendering): decompose HtmlRenderer into block/inline/directive modules`

---

## Appendix: Full Audit Results

<details>
<summary>All files > 600 LOC</summary>

```
1,246 lines | rendering/errors.py
1,114 lines | rendering/parsers/patitas/renderers/html.py
1,078 lines | orchestration/render.py
  977 lines | health/autofix.py
  958 lines | orchestration/taxonomy.py
  956 lines | orchestration/menu.py
  954 lines | analysis/knowledge_graph.py
  952 lines | health/report.py
  939 lines | server/build_trigger.py
  898 lines | autodoc/extractors/python/extractor.py
  891 lines | orchestration/content.py
  885 lines | postprocess/social_cards.py
  883 lines | orchestration/build/initialization.py
  867 lines | rendering/template_functions/autodoc.py
  861 lines | core/page/proxy.py
  845 lines | rendering/template_functions/openapi.py
  845 lines | autodoc/utils.py
  844 lines | output/core.py
  840 lines | server/dev_server.py
  840 lines | cli/dashboard/screens.py
  838 lines | core/page/metadata.py
  837 lines | orchestration/asset.py
  833 lines | orchestration/build/__init__.py
  829 lines | cli/commands/build.py
  827 lines | debug/content_migrator.py
  819 lines | rendering/renderer.py
  817 lines | utils/logger.py
  815 lines | cli/commands/theme.py
  814 lines | rendering/parsers/patitas/directives/builtins/code_tabs.py
```

</details>

<details>
<summary>Files with > 25 functions</summary>

```
80 functions | core/page/proxy.py
47 functions | rendering/parsers/patitas/renderers/html.py
39 functions | health/report.py
38 functions | core/nav_tree.py
36 functions | core/page/metadata.py
35 functions | config/accessor.py
34 functions | cli/dashboard/screens.py
32 functions | rendering/context/data_wrappers.py
30 functions | utils/logger.py
30 functions | rendering/context/site_wrappers.py
30 functions | protocols/core.py
29 functions | core/site/properties.py
29 functions | utils/build_context.py
28 functions | output/core.py
28 functions | core/page/bundle.py
```

</details>

<details>
<summary>Outstanding TODOs</summary>

```
bengal/directives/marimo.py:143:        # TODO: Implement caching
bengal/directives/marimo.py:170:            # TODO: Store in cache
bengal/cli/dashboard/base.py:120:        # TODO: Implement help screen in Phase 7
bengal/cli/commands/debug.py:421:    _redirect_format: str | None,  # TODO: implement redirect generation
bengal/orchestration/incremental/data_detector.py:229:  # TODO: smarter heuristic
```

</details>
