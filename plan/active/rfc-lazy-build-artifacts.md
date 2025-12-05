# RFC: Lazy-Computed Build Artifacts

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: AI-assisted analysis  
**Related**: `bengal/utils/build_context.py`, `bengal/analysis/knowledge_graph.py`

---

## Summary

Introduce lazy-computed build artifacts in BuildContext to eliminate redundant expensive computations. The knowledge graph is currently built 3 times per build (~600-1500ms wasted). This RFC proposes centralizing expensive computations as lazy properties on BuildContext.

**Immediate Impact**: ~400-1000ms faster builds  
**Foundation For**: Parallel validators, streaming builds, better incremental support

---

## Problem Statement

### Current State: Redundant Computation

The knowledge graph is built **3 times** during a single build:

| Consumer | Location | Purpose |
|----------|----------|---------|
| Post-processing | `postprocess.py:318-319` | Graph connections in JSON output |
| Special Pages | `special_pages.py:314-315` | Graph visualization page |
| Health Check | `connectivity.py:86-97` | Connectivity analysis |

Each consumer independently builds what it needs:

```python
# Pattern repeated 3 times
graph = KnowledgeGraph(site)
graph.build()  # Expensive! O(pages × links)
```

### Evidence

```
bengal/orchestration/postprocess.py:318-319
    graph = KnowledgeGraph(self.site)
    graph.build()

bengal/postprocess/special_pages.py:314-315
    graph = KnowledgeGraph(self.site)
    graph.build()

bengal/health/validators/connectivity.py:86-97
    graph = KnowledgeGraph(site)
    graph.build()
```

### Why This Matters

- **773 pages**: Each graph build takes ~200-500ms
- **3 builds**: ~600-1500ms total wasted
- **Sequential**: Can't parallelize when each builds its own
- **Memory**: 3 copies of graph data in memory

---

## Proposed Solution

### Design: Lazy Properties on BuildContext

Add expensive computations as lazy-cached properties on BuildContext:

```python
# bengal/utils/build_context.py
@dataclass
class BuildContext:
    """Build context with lazy-computed artifacts."""
    
    site: Site
    pages: list[Page]
    tracker: DependencyTracker | None = None
    stats: BuildStats | None = None
    profile: BuildProfile | None = None
    progress_manager: Any = None
    reporter: Any = None
    
    # Lazy-computed artifacts (built once on first access)
    _knowledge_graph: KnowledgeGraph | None = field(default=None, repr=False)
    _knowledge_graph_enabled: bool = field(default=True, repr=False)
    
    @property
    def knowledge_graph(self) -> KnowledgeGraph | None:
        """
        Get knowledge graph (built lazily, cached for build duration).
        
        Returns:
            Built KnowledgeGraph instance, or None if disabled/unavailable
            
        Example:
            # First access builds the graph
            graph = ctx.knowledge_graph
            
            # Subsequent accesses reuse cached instance
            graph2 = ctx.knowledge_graph  # Same instance, no rebuild
        """
        if not self._knowledge_graph_enabled:
            return None
            
        if self._knowledge_graph is None:
            self._knowledge_graph = self._build_knowledge_graph()
        return self._knowledge_graph
    
    def _build_knowledge_graph(self) -> KnowledgeGraph | None:
        """Build and cache knowledge graph."""
        try:
            from bengal.analysis.knowledge_graph import KnowledgeGraph
            from bengal.config.defaults import is_feature_enabled
            
            # Check if graph feature is enabled
            if not is_feature_enabled(self.site.config, "graph"):
                self._knowledge_graph_enabled = False
                return None
            
            graph = KnowledgeGraph(self.site)
            graph.build()
            return graph
        except ImportError:
            self._knowledge_graph_enabled = False
            return None
```

### Consumer Updates

Each consumer changes from building to accessing:

**Before (3 separate builds):**
```python
# postprocess.py
graph = KnowledgeGraph(self.site)
graph.build()

# special_pages.py  
graph = KnowledgeGraph(self.site)
graph.build()

# connectivity.py
graph = KnowledgeGraph(site)
graph.build()
```

**After (shared lazy computation):**
```python
# postprocess.py
graph = build_context.knowledge_graph

# special_pages.py
graph = build_context.knowledge_graph

# connectivity.py  
graph = build_context.knowledge_graph  # Need to pass context
```

---

## Implementation Plan

### Phase 1: Add Lazy Property to BuildContext

**File**: `bengal/utils/build_context.py`

1. Add `_knowledge_graph` field with `field(default=None)`
2. Add `knowledge_graph` property with lazy build logic
3. Add `_build_knowledge_graph()` helper method

**Effort**: ~30 minutes

### Phase 2: Update Post-Processing

**File**: `bengal/orchestration/postprocess.py`

1. Remove `_build_graph_data()` method (moves to BuildContext)
2. Use `build_context.knowledge_graph` in `_generate_output_formats()`
3. Pass `build_context` to `OutputFormatsGenerator`

**Effort**: ~30 minutes

### Phase 3: Update Special Pages

**File**: `bengal/postprocess/special_pages.py`

1. Accept `build_context` parameter in `generate()` method
2. Use `build_context.knowledge_graph` instead of building
3. Update caller in `PostprocessOrchestrator`

**Effort**: ~20 minutes

### Phase 4: Update Health Check

**File**: `bengal/health/validators/connectivity.py`

This is trickier because health check runs after post-processing and may not have BuildContext.

**Options**:
- A) Pass BuildContext to health check (clean, requires signature changes)
- B) Cache graph on Site temporarily (less clean, minimal changes)
- C) Health check builds if not cached (fallback behavior)

**Recommended**: Option A with Option C as fallback

```python
# connectivity.py
def validate(self, site: Site, build_context: BuildContext | None = None) -> list[CheckResult]:
    # Try build context first
    if build_context and build_context.knowledge_graph:
        graph = build_context.knowledge_graph
    else:
        # Fallback: build our own (for standalone health check)
        graph = KnowledgeGraph(site)
        graph.build()
```

**Effort**: ~45 minutes

### Phase 5: Update Health Check Orchestration

**File**: `bengal/orchestration/build/finalization.py`

1. Pass `build_context` to `run_health_check()`
2. Health check passes context to validators

**Effort**: ~30 minutes

---

## Future Extensions

Once BuildContext has lazy artifacts, we can add more:

```python
@dataclass
class BuildContext:
    # Existing
    _knowledge_graph: KnowledgeGraph | None = None
    
    # Future lazy artifacts
    _search_index: SearchIndex | None = None      # For search functionality
    _link_map: dict[str, list[str]] | None = None  # For link validation
    _toc_cache: dict[str, str] | None = None       # For cross-page TOC
```

### Parallel Validators (Phase 2 Optimization)

With shared artifacts, validators become embarrassingly parallel:

```python
# health_check.py
def run(self, build_context: BuildContext, ...) -> HealthReport:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(v.validate, self.site, build_context): v 
            for v in self.validators
        }
        for future in as_completed(futures):
            results = future.result()
            # ... collect results
```

### Streaming Builds (Phase 3 Optimization)

Lazy artifacts enable streaming:
- Build graph incrementally as pages render
- Update graph when pages change
- Never rebuild entire graph for small changes

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| BuildContext not available everywhere | Medium | Fallback to building locally |
| Thread safety of lazy properties | Low | Graph is read-only after build |
| Memory: keeping graph alive longer | Low | Clear `_knowledge_graph = None` at build end |
| Signature changes to validators | Medium | Optional parameter with fallback |

---

## Success Criteria

- [ ] Knowledge graph built at most once per build
- [ ] Post-processing uses cached graph
- [ ] Special pages use cached graph  
- [ ] Health check uses cached graph (or fallback)
- [ ] ~400-1000ms reduction in build time
- [ ] No functional regression (same outputs)
- [ ] All tests pass

---

## Metrics

**Before** (773 pages):
- Post-process: ~1300ms (includes 3 graph builds)
- Health check: ~800ms (includes graph build)

**After**:
- Post-process: ~900ms (1 graph build, shared)
- Health check: ~400ms (reuses graph)

**Expected Savings**: ~400-800ms per build

---

## Alternatives Considered

### 1. Cache on Site Object

```python
if not hasattr(site, '_knowledge_graph'):
    site._knowledge_graph = KnowledgeGraph(site)
    site._knowledge_graph.build()
graph = site._knowledge_graph
```

**Rejected**: Pollutes Site model with build artifacts. Site should be a data container, not a cache.

### 2. Global Singleton

```python
_graph_cache: dict[int, KnowledgeGraph] = {}

def get_knowledge_graph(site: Site) -> KnowledgeGraph:
    site_id = id(site)
    if site_id not in _graph_cache:
        _graph_cache[site_id] = KnowledgeGraph(site)
        _graph_cache[site_id].build()
    return _graph_cache[site_id]
```

**Rejected**: Global state, thread-unsafe, hard to clear between builds.

### 3. Pass Graph Through All Functions

```python
def run_postprocess(site, graph=None):
    if graph is None:
        graph = KnowledgeGraph(site)
        graph.build()
    # ...
```

**Rejected**: Requires changing many function signatures. BuildContext already exists for this purpose.

---

## Related Files

- `bengal/utils/build_context.py` - BuildContext dataclass
- `bengal/analysis/knowledge_graph.py` - KnowledgeGraph implementation
- `bengal/orchestration/postprocess.py` - Post-processing orchestrator
- `bengal/postprocess/special_pages.py` - Graph visualization page
- `bengal/health/validators/connectivity.py` - Connectivity validator
- `bengal/health/health_check.py` - Health check orchestrator

---

## Questions for Review

1. Should we add timing instrumentation to measure actual savings?
2. Should the graph be cleared at build end to free memory?
3. Should health check require BuildContext or keep fallback forever?
4. Are there other expensive computations that should be lazy artifacts?

