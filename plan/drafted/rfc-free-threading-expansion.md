# RFC: Free-Threading Expansion for CPU-Bound Build Phases

**Status**: Implemented  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `bengal/orchestration/render.py`, `bengal/utils/gil.py`, PEP 703  
**Confidence**: 72% 🟢

---

## Executive Summary

Bengal already has excellent free-threading support for page rendering (the primary CPU bottleneck). This RFC proposes expanding free-threading to additional CPU-bound phases: **knowledge graph building** and **autodoc extraction**.

**Key Insight**: With Python 3.13t/3.14t and `PYTHON_GIL=0`, Bengal's `ThreadPoolExecutor` usage achieves true parallelism. Currently, only page rendering and related posts leverage this. Other CPU-bound phases remain sequential, leaving performance on the table.

**Primary Use Case**: Sites with 500+ pages or autodoc enabled. Knowledge graph analysis is enabled by default and scales poorly with page count—making it a high-value parallelization target.

---

## Current State: What Bengal Already Does Well

### Existing Free-Threading Infrastructure

Bengal has robust free-threading support in place:

| Component | Location | Status |
|-----------|----------|--------|
| **GIL Detection** | `bengal/utils/gil.py` | ✅ Full detection + user tips |
| **Page Rendering** | `bengal/orchestration/render.py` | ✅ ThreadPoolExecutor with GIL detection |
| **Asset Processing** | `bengal/orchestration/asset.py` | ✅ Parallel CSS/JS/images |
| **Related Posts** | `bengal/orchestration/related_posts.py` | ✅ Parallel for 100+ pages |
| **Content Discovery** | `bengal/discovery/content_discovery.py` | ✅ Parallel frontmatter parsing |
| **Per-Key Locking** | `bengal/utils/concurrent_locks.py` | ✅ Thread-safe resource patterns |
| **Thread-Local Caching** | `bengal/rendering/pipeline/thread_local.py` | ✅ Parser instance caching |

### Existing GIL Detection (Excellent)

```python
# bengal/utils/gil.py:22-55
def is_gil_disabled() -> bool:
    """Check if running on free-threaded Python (GIL disabled)."""
    if hasattr(sys, "_is_gil_enabled"):
        try:
            return not sys._is_gil_enabled()
        except (AttributeError, TypeError):
            pass
    # Fallback: check sysconfig for Py_GIL_DISABLED
    try:
        import sysconfig
        return sysconfig.get_config_var("Py_GIL_DISABLED") == 1
    except (ImportError, AttributeError):
        pass
    return False
```

### Existing Parallel Rendering (Excellent)

```python
# bengal/orchestration/render.py:319-340
def _render_parallel(self, pages, ...):
    """
    Build pages in parallel for better performance.

    Free-Threaded Python Support (PEP 703):
        - Automatically detects Python 3.13t+ with GIL disabled
        - ThreadPoolExecutor gets true parallelism (no GIL contention)
        - ~1.5-2x faster rendering on multi-core machines
        - No code changes needed - works automatically
    """
```

---

## Problem Statement

### Sequential Bottlenecks Remain

While page rendering is parallel, two significant CPU-bound phases remain sequential:

| Phase | Current | CPU Profile | Parallelizable? |
|-------|---------|-------------|-----------------|
| **Knowledge Graph Building** | Sequential | High (link resolution, metrics) | ✅ Yes |
| **Autodoc Extraction** | Sequential | High (Python AST parsing) | ✅ Yes |
| Related Posts Calculation | ✅ Already parallel | Medium | N/A (done) |
| Social Card Generation | Sequential (intentional) | High | ❌ No (Pillow not thread-safe) |
| Search Index Building | Sequential | Low-Medium | Future RFC |

**Note**: Social card generation uses Pillow, whose C extensions are NOT thread-safe in free-threading Python. The current sequential implementation is intentional to prevent segfaults. Related posts already supports parallel processing via `RelatedPostsOrchestrator._build_parallel()`.

### Evidence: Knowledge Graph is CPU-Bound

```python
# bengal/analysis/graph_builder.py:90-116 (sequential)
def build(self) -> None:
    """Build the knowledge graph by analyzing all page connections."""
    self._ensure_links_extracted()      # CPU: Parse all pages
    self._analyze_cross_references()    # CPU: Resolve all links
    self._analyze_taxonomies()          # CPU: Group pages
    self._analyze_related_posts()       # CPU: Compute relationships
    self._analyze_menus()               # CPU: Menu traversal
    self._analyze_section_hierarchy()   # CPU: Tree traversal
    self._analyze_navigation_links()    # CPU: Sequential links
    self._build_link_metrics()          # CPU: Aggregate metrics
```

Each of these methods iterates over all pages. With 1000+ pages, this becomes a significant bottleneck.

### Why Knowledge Graph is High Priority

The knowledge graph is **enabled by default** — it runs on every build regardless of whether the site uses graph visualization features. This makes it a high-value target:

| Feature | Default State | Sites Affected |
|---------|--------------|----------------|
| Knowledge Graph | ✅ Enabled | All sites |
| Autodoc | ❌ Opt-in | Sites with Python APIs |
| Related Posts | ✅ Enabled (already parallel) | Sites with tags |

Parallelizing graph building benefits **all Bengal sites** with 100+ pages, not just those using specific features.

### Evidence: Autodoc Extraction is CPU-Bound

```python
# bengal/autodoc/orchestration/orchestrator.py
# Each module is parsed independently via Python AST
def extract_python(site, config) -> list[DocElement]:
    for module_path in config["paths"]:
        ast.parse(module_path.read_text())  # CPU-bound
        extract_classes(ast)                 # CPU-bound
        extract_functions(ast)               # CPU-bound
```

### Why Social Cards Cannot Be Parallelized

Social cards use Pillow for image generation. Pillow's C extensions are **not thread-safe** in free-threading Python, causing segfaults under parallel execution. The existing sequential implementation is intentional:

```python
# bengal/postprocess/social_cards.py:35-39
# Thread Safety Note:
#     Pillow's C extensions are NOT thread-safe in free-threading Python (3.13+).
#     Social card generation uses sequential mode to avoid segfaults.
```

This is acceptable since social cards are only generated for production builds, not during dev server operation.

---

## Goals

1. **Parallel Knowledge Graph Building** — Partition graph analysis across threads
2. **Parallel Autodoc Extraction** — Extract modules concurrently  
3. **Unified Parallel Pattern** — Consistent approach matching existing patterns

## Non-Goals

- Changing the existing page rendering architecture (already excellent)
- Parallelizing social card generation (Pillow C extensions not thread-safe)
- Parallelizing related posts (already implemented)
- Adding process-level parallelism (covered in `rfc-build-sharding.md`)
- Distributed builds (future RFC)

---

## Design

### Core Principle: Partition-Map-Reduce

All CPU-bound phases follow the same pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                     Partition Phase                          │
│  Split work into independent chunks (pages, modules, etc.)  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │Thread 1 │          │Thread 2 │          │Thread N │
   │ Map fn  │          │ Map fn  │          │ Map fn  │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Reduce Phase                            │
│  Merge thread-local results into global data structures     │
└─────────────────────────────────────────────────────────────┘
```

### Proposed: Parallel Graph Builder

```python
# bengal/analysis/graph_builder.py (proposed changes)

from concurrent.futures import ThreadPoolExecutor, as_completed
from bengal.config.defaults import get_max_workers
from bengal.utils.gil import is_gil_disabled
import threading

class GraphBuilder:
    """Builds the knowledge graph with optional parallel analysis."""

    def __init__(self, site, exclude_autodoc=True, parallel=True):
        self.site = site
        self.exclude_autodoc = exclude_autodoc
        self.parallel = parallel and len(site.pages) >= 100

        # Thread-safe accumulators for parallel mode
        self._lock = threading.Lock()

    def build(self) -> None:
        """Build the knowledge graph."""
        self._ensure_links_extracted()

        if self.parallel:
            self._build_parallel()
        else:
            self._build_sequential()

        # Final aggregation (always sequential)
        self._build_link_metrics()

    def _build_parallel(self) -> None:
        """Build graph with parallel page analysis."""
        max_workers = get_max_workers(self.site.config.get("max_workers"))
        pages = self.get_analysis_pages()

        # Thread-local accumulators
        thread_local = threading.local()

        def analyze_page(page):
            """Analyze a single page's connections."""
            # Initialize thread-local storage
            if not hasattr(thread_local, "incoming"):
                thread_local.incoming = defaultdict(float)
                thread_local.outgoing = defaultdict(set)
                thread_local.link_types = {}

            # Cross-references
            for link in getattr(page, "links", []):
                target = self._resolve_link(link)
                if target and target != page:
                    thread_local.incoming[target] += 1
                    thread_local.outgoing[page].add(target)
                    thread_local.link_types[(page, target)] = LinkType.EXPLICIT

            # Related posts (per-page, embarrassingly parallel)
            for related in getattr(page, "related_posts", []):
                if related != page:
                    thread_local.incoming[related] += 1
                    thread_local.outgoing[page].add(related)
                    thread_local.link_types[(page, related)] = LinkType.RELATED

            return thread_local

        # Parallel execution
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_page, p): p for p in pages}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.warning("graph_page_analysis_failed", error=str(e))

        # Reduce: merge thread-local results
        for tl in results:
            with self._lock:
                for page, count in tl.incoming.items():
                    self.incoming_refs[page] += count
                for page, targets in tl.outgoing.items():
                    self.outgoing_refs[page].update(targets)
                self.link_types.update(tl.link_types)

        # Taxonomy and menu analysis (global data, keep sequential)
        self._analyze_taxonomies()
        self._analyze_menus()
        self._analyze_section_hierarchy()
        self._analyze_navigation_links()
```

### Proposed: Parallel Autodoc Extraction

```python
# bengal/autodoc/orchestration/extractors.py (proposed changes)

from concurrent.futures import ThreadPoolExecutor, as_completed
from bengal.config.defaults import get_max_workers

def extract_python_parallel(site, config) -> list[DocElement]:
    """Extract Python documentation elements in parallel."""
    paths = config.get("paths", [])
    if not paths:
        return []

    max_workers = get_max_workers(site.config.get("max_workers"))

    def extract_module(module_path: Path) -> list[DocElement]:
        """Extract elements from a single module (thread-safe)."""
        try:
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            elements = []
            elements.extend(extract_module_docstring(tree, module_path))
            elements.extend(extract_classes(tree, module_path))
            elements.extend(extract_functions(tree, module_path))
            return elements
        except Exception as e:
            logger.warning("autodoc_module_extraction_failed",
                           module=str(module_path), error=str(e))
            return []

    # Parallel extraction
    all_elements = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_module, p): p for p in paths}
        for future in as_completed(futures):
            all_elements.extend(future.result())

    return all_elements
```

---

## Performance Estimates

> **Note**: These are projected estimates based on algorithmic analysis. Actual benchmarks should be run after implementation to validate.

### Current Baseline (GIL-Limited Threading)

| Phase | 500 Pages | 1000 Pages | 2000 Pages |
|-------|-----------|------------|------------|
| Graph Building | ~800ms | ~1.8s | ~4s |
| Autodoc (200 modules) | ~2s | ~2s | ~2s |

### With Free-Threading (Python 3.14t, PYTHON_GIL=0)

| Phase | 500 Pages | 1000 Pages | 2000 Pages | Est. Speedup |
|-------|-----------|------------|------------|---------|
| Graph Building | ~200ms | ~450ms | ~1s | **3-4x** |
| Autodoc (200 modules) | ~500ms | ~500ms | ~500ms | **4x** |

### Combined Impact on Full Build

| Site Size | Current | With Parallel Phases | Est. Improvement |
|-----------|---------|---------------------|-------------|
| 500 pages | 25s | 22s | ~12% faster |
| 1000 pages | 45s | 38s | ~16% faster |
| 2000 pages | 90s | 72s | ~20% faster |

**Note**: Page rendering is already parallel, so these gains are *additional* to existing parallelism. The knowledge graph is enabled by default, making this optimization broadly applicable.

---

## Implementation Plan

### Phase 1: Parallel Knowledge Graph (Highest Impact)

**Priority**: High — Graph building is enabled by default and scales poorly with page count.

**Why This Matters**: Unlike optional features, the knowledge graph runs on every build. Sites with 500+ pages spend significant time in sequential graph analysis. This is the highest-value parallelization target.

**Changes**:
1. Add parallel mode to `GraphBuilder`
2. Partition pages across threads for cross-reference analysis
3. Use thread-local accumulators for incoming/outgoing refs
4. Merge results with minimal locking
5. Keep taxonomy/menu analysis sequential (requires global state)

**Estimated effort**: 3-4 days

**Testing**:
```python
def test_parallel_graph_matches_sequential():
    """Parallel graph produces identical results to sequential."""

def test_parallel_graph_performance():
    """Parallel graph is faster for 500+ pages."""

def test_parallel_graph_thread_safety():
    """No race conditions in merge phase."""
```

### Phase 2: Parallel Autodoc Extraction

**Priority**: Medium — Benefits sites with large Python APIs.

**Why This Matters**: Autodoc parses Python source files via AST. Each file is independent, making this embarrassingly parallel. Sites documenting large codebases (100+ modules) will see significant improvement.

**Changes**:
1. Parallelize module extraction in `extract_python()`
2. Each module extracted independently (no shared state)
3. Collect `DocElement` lists after all complete

**Estimated effort**: 2 days

**Testing**:
```python
def test_parallel_autodoc_matches_sequential():
    """Parallel extraction produces identical elements."""

def test_parallel_autodoc_error_isolation():
    """One module failure doesn't affect others."""
```

### Phase 3: Documentation

**Priority**: Medium — Users need to understand parallel config options.

**Changes**:
1. Update `UV_QUICK_REFERENCE.md` with parallel config
2. Add troubleshooting for `--no-parallel` debugging
3. Document free-threading benefits with benchmarks

**Estimated effort**: 1 day

---

## Thread Safety Considerations

### Safe Patterns (Already Used)

Bengal already uses these patterns effectively:

1. **Thread-Local Storage** (`threading.local()`)
   - Used for parser caching in `thread_local.py`
   - Extend to graph accumulators

2. **Per-Key Locking** (`PerKeyLockManager`)
   - Used for template compilation
   - Available for any keyed resource

3. **Atomic Operations**
   - `ThreadSafeSet.add_if_new()` for directory tracking
   - Extend pattern for other accumulators

### New Patterns Needed

1. **Thread-Local Accumulators + Merge**
   ```python
   thread_local = threading.local()

   def worker(item):
       if not hasattr(thread_local, "results"):
           thread_local.results = []
       thread_local.results.append(process(item))
       return thread_local

   # After all workers complete
   all_results = []
   for tl in completed_thread_locals:
       all_results.extend(tl.results)
   ```

2. **Minimal Lock Scope**
   ```python
   # Bad: Lock entire operation
   with lock:
       result = expensive_compute()
       shared_dict[key] = result

   # Good: Lock only the update
   result = expensive_compute()  # Outside lock
   with lock:
       shared_dict[key] = result
   ```

---

## Risks and Mitigations

### Risk 1: Thread Safety Bugs in Merge Phase

**Problem**: Merging thread-local accumulators into shared data structures can cause race conditions.

**Mitigation**:
- Use thread-local storage for per-thread accumulators (no sharing during work)
- Single-threaded merge after all workers complete
- Minimal lock scope during merge (lock only the update, not computation)
- Comprehensive testing comparing parallel vs sequential results
- Follow `RelatedPostsOrchestrator._build_parallel()` as reference implementation

### Risk 2: Memory Overhead from Thread-Local Accumulators

**Problem**: Each thread maintains its own copy of accumulators (incoming_refs, outgoing_refs, link_types).

**Mitigation**:
- Only store per-page results in thread-local storage (not full graph)
- For 2000 pages with 8 workers: ~8x memory during parallel phase, then freed
- Add memory profiling to benchmarks
- Document expected memory growth in performance notes

### Risk 3: Debugging Complexity

**Problem**: Parallel bugs are harder to reproduce and debug.

**Mitigation**:
- Add `BENGAL_NO_PARALLEL=1` environment variable for debugging
- Structured logging includes thread IDs
- Deterministic test cases that verify parallel == sequential
- Default to sequential for small workloads (<100 pages)

### Risk 4: GIL Still Limits Standard Python

**Problem**: Without free-threading, ThreadPoolExecutor provides limited speedup for CPU-bound work.

**Mitigation**:
- Code works correctly on both GIL and free-threaded Python
- Standard Python still benefits from reduced memory pressure (work batching)
- Clear documentation about `PYTHON_GIL=0` for full benefits
- No performance regression on standard Python

---

## Configuration

### Proposed Config Options

```toml
# bengal.toml
[build]
# Existing
max_workers = 8

# New
parallel_graph = true      # Enable parallel graph building (default: true for 100+ pages)
parallel_autodoc = true    # Enable parallel autodoc extraction (default: true)
```

### Environment Variables

```bash
# Existing (documented in UV_QUICK_REFERENCE.md)
export PYTHON_GIL=0  # Enable free-threading

# New (debugging)
export BENGAL_NO_PARALLEL=1  # Disable all parallel phases (useful for debugging)
```

### Automatic Thresholds

Parallel processing is automatically disabled for small workloads to avoid thread pool overhead:

| Phase | Minimum for Parallel |
|-------|---------------------|
| Knowledge Graph | 100 pages |
| Autodoc | 10 modules |

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/analysis/test_graph_builder_parallel.py

def test_parallel_graph_matches_sequential():
    """Parallel graph produces identical results."""

def test_parallel_graph_thread_safety():
    """No race conditions with multiple threads."""

def test_parallel_graph_empty_site():
    """Handles empty site gracefully."""

def test_parallel_graph_single_page():
    """Falls back to sequential for small sites."""

def test_parallel_graph_merge_correctness():
    """Thread-local accumulators merge correctly."""
```

### Integration Tests

```python
# tests/integration/test_parallel_phases.py

def test_full_build_with_parallel_graph():
    """Full build produces correct output with parallel graph."""

def test_parallel_autodoc_extraction():
    """Autodoc elements extracted correctly in parallel."""

def test_parallel_with_no_parallel_flag():
    """BENGAL_NO_PARALLEL=1 disables parallel phases."""
```

### Performance Tests

```python
# benchmarks/test_parallel_performance.py

def test_parallel_graph_faster_for_large_sites():
    """Parallel graph is faster for 500+ pages."""

def test_parallel_autodoc_faster():
    """Parallel autodoc is faster for 50+ modules."""

def test_free_threading_speedup():
    """Free-threaded Python shows expected speedup."""

def test_memory_overhead_acceptable():
    """Thread-local accumulators don't cause memory bloat."""
```

---

## Implementation Checklist

### Phase 1: Parallel Knowledge Graph ✅

- [x] Add `parallel` parameter to `GraphBuilder.__init__`
- [x] Implement `_build_parallel()` method
- [x] Use per-page accumulators (not thread-local, to avoid accumulation bugs)
- [x] Implement merge phase with minimal locking
- [x] Add threshold check (skip parallel for <100 pages)
- [x] Add `parallel_graph` config option
- [x] Add `BENGAL_NO_PARALLEL` env var support
- [x] Add unit tests for thread safety
- [x] Add unit tests for merge correctness
- [ ] Add performance benchmarks
- [x] Update documentation

### Phase 2: Parallel Autodoc ✅

- [x] Modify `_extract_directory()` in PythonExtractor
- [x] Add `_extract_files_parallel()` method
- [x] Collect `DocElement` lists from workers
- [x] Add `parallel_autodoc` config option
- [x] Add threshold check (skip parallel for <10 modules)
- [x] Add tests for correctness and error isolation

### Phase 3: Documentation & Polish ✅

- [x] Update `UV_QUICK_REFERENCE.md` with parallel config
- [x] Add "Parallel Builds" section explaining behavior
- [x] Document `BENGAL_NO_PARALLEL` debugging flag
- [ ] Run benchmarks and update performance tables with real data
- [ ] Add performance comparison table to docs

---

## References

- **PEP 703**: [Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- **Python 3.13t/3.14t**: Free-threaded builds with `--disable-gil`
- **Bengal codebase**:
  - `bengal/utils/gil.py` — GIL detection utilities
  - `bengal/orchestration/render.py` — Existing parallel rendering
  - `bengal/orchestration/related_posts.py` — Existing parallel related posts (reference implementation)
  - `bengal/analysis/graph_builder.py` — Graph building (target for parallelization)
  - `bengal/autodoc/orchestration/extractors.py` — Autodoc extraction (target for parallelization)
  - `bengal/utils/concurrent_locks.py` — Thread-safe lock patterns
  - `bengal/rendering/pipeline/thread_local.py` — Thread-local caching patterns
- **Related RFCs**:
  - `plan/drafted/rfc-build-sharding.md` — Process-level parallelism

---

## Appendix: Free-Threading Quick Start

### Installing Free-Threaded Python

```bash
# macOS with Homebrew
brew install python@3.13 --enable-framework

# Using pyenv (recommended)
pyenv install 3.13t
pyenv local 3.13t

# Using uv
uv python install 3.13t
```

### Enabling Free-Threading

```bash
# Enable GIL-disabled mode
export PYTHON_GIL=0

# Verify
python -c "import sys; print(sys._is_gil_enabled())"
# Output: False
```

### Bengal with Free-Threading

```bash
# Full build with free-threading
PYTHON_GIL=0 bengal build

# Dev server with free-threading
PYTHON_GIL=0 bengal serve
```

---

## Changelog

- 2025-12-23: Revised after evaluation
  - Removed social card parallelization (Pillow not thread-safe in free-threading Python)
  - Removed related posts parallelization (already implemented in codebase)
  - Focused scope on knowledge graph and autodoc extraction
  - Added automatic thresholds for small workloads
  - Marked performance estimates as projections pending benchmarks
  - Added memory overhead testing requirement

- 2025-12-23: Initial draft
  - Analyzed existing free-threading support
  - Identified parallel opportunities in graph, autodoc, social cards
  - Proposed partition-map-reduce pattern
  - Added implementation plan and testing strategy
