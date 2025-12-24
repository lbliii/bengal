# RFC: Analysis Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Analysis (Knowledge Graph, PageRank, Path Analysis, Link Suggestions)  
**Confidence**: 92% 🟢 (verified against source code)  
**Priority**: P2 (Medium) — Performance, scalability for large sites  
**Estimated Effort**: 2-3 days

---

## Executive Summary

The `bengal/analysis` package provides site analysis capabilities (PageRank, community detection, centrality metrics, link suggestions), but several algorithms have suboptimal Big O complexity that creates performance bottlenecks for sites with 5K+ pages.

**Key findings**:

1. **PageRank** — O(I × N²) instead of optimal O(I × E) due to inner loop design
2. **Link Suggestions** — O(N² × T) brute-force comparison of all page pairs
3. **No incremental updates** — Full recomputation required for any change

**Proposed optimizations**:

1. Build reverse adjacency list for PageRank → 10-100x speedup for 10K pages
2. Inverted tag index for link suggestions → Skip 90%+ of comparisons
3. Optional: NetworkX/igraph integration for very large sites (50K+)

**Impact**: Enable real-time analysis for 10K+ page sites (current: ~10min → target: <30s)

---

## Problem Statement

### Current Performance Characteristics

> **Note**: These are theoretical projections based on complexity analysis. Actual baseline measurements should be captured before optimization (see Step 0 in Implementation Plan).

| Site Size | Graph Build | PageRank | Path Analysis | Link Suggestions |
|-----------|-------------|----------|---------------|------------------|
| 100 pages | <1s | <1s | <1s | <1s |
| 1K pages | ~2s | ~5s | ~10s | ~10s |
| 5K pages | ~10s | ~2min | ~30s (approx) | ~5min |
| 10K pages | ~20s | **~8min** ⚠️ | ~1min (approx) | **~20min** ⚠️ |

For sites approaching 10K pages, PageRank and link suggestions become the primary bottlenecks, making iterative content development painful.

### Bottleneck 1: PageRank Inner Loop — O(I × N²)

**Location**: `page_rank.py:235-243`

```python
# Current: O(N) inner loop per page per iteration
for page in pages:                          # O(N)
    for source_page in pages:               # O(N) - INEFFICIENT
        outgoing_links = self.graph.outgoing_refs.get(source_page, set())
        if page in outgoing_links:          # O(1)
            link_score += scores[source_page] / len(outgoing_links)
```

**Problem**: For each target page, we iterate ALL pages to find those linking to it. With 10K pages, that's 100M iterations per PageRank iteration (typical 20-50 iterations → 2-5 billion operations).

**Optimal approach**: Build `incoming_edges[page] = [source_pages]` once, then iterate only incoming edges → O(E) per iteration.

### Bottleneck 2: Link Suggestions — O(N² × T)

**Location**: `link_suggestions.py:223-236`

```python
# Current: Compare every page pair
for source_page in pages:                   # O(N)
    for target in all_pages:                # O(N)
        if target == source or target in existing_links:
            continue
        score, reasons = self._calculate_link_score(...)  # O(T) tag comparison
```

**Problem**: For 10K pages, we perform 100M comparisons. Most comparisons yield score=0 (no shared tags), but we still compute them.

**Optimal approach**: Build inverted tag index `tag → [pages]`, only compare pages with shared tags → typically 90%+ reduction.

### Bottleneck 3: No Incremental Updates

All analysis methods recompute from scratch:

```python
# Adding one page forces full recomputation
graph.build()              # Reanalyzes all N pages
graph.compute_pagerank()   # Recomputes all scores
graph.suggest_links()      # Regenerates all suggestions
```

For iterative development (edit → preview → edit), this creates significant latency.

---

## Goals

1. **Reduce PageRank complexity** from O(I × N²) to O(I × E)
2. **Reduce link suggestions complexity** from O(N² × T) to O(N × overlap)
3. **Maintain API compatibility** — No breaking changes to public interfaces
4. **Preserve accuracy** — Identical results, just faster
5. **Optional**: Add incremental update support for common operations

### Non-Goals

- Replacing algorithms with external libraries (NetworkX/igraph) — separate RFC
- Approximate PageRank (current implementation is already iterative)
- GPU acceleration

---

## Proposed Solution

### Existing Infrastructure

> **Note**: `GraphBuilder` already implements parallel page analysis using `ThreadPoolExecutor` (see `graph_builder.py:166-285`). This pattern can potentially be extended to PageRank iteration for additional parallelism gains on multi-core machines, especially with Python 3.13t+ free-threading.

### Phase 1: PageRank Adjacency List Optimization

**Estimated effort**: 4 hours  
**Expected speedup**: 10-100x for large sites

#### 1.1 Add Reverse Adjacency List to GraphBuilder

```python
# graph_builder.py - Add to data structures
class GraphBuilder:
    def __init__(self, ...):
        # Existing
        self.outgoing_refs: dict[Page, set[Page]] = defaultdict(set)

        # NEW: Reverse index for efficient incoming edge iteration
        self.incoming_edges: dict[Page, list[Page]] = defaultdict(list)
```

Build during graph construction:

```python
def _analyze_cross_references(self) -> None:
    for page in analysis_pages:
        for link in getattr(page, "links", []):
            target = self._resolve_link(link)
            if target and target != page and target in analysis_pages_set:
                self.incoming_refs[target] += 1
                self.outgoing_refs[page].add(target)
                # NEW: Also record reverse edge
                self.incoming_edges[target].append(page)
```

#### 1.2 Update PageRank to Use Incoming Edges

```python
# page_rank.py - Optimized inner loop
def compute(self, ...) -> PageRankResults:
    # Build incoming edges index once
    incoming_edges: dict[Page, list[Page]] = defaultdict(list)
    for source_page in pages:
        for target in self.graph.outgoing_refs.get(source_page, set()):
            if target in pages:
                incoming_edges[target].append(source_page)

    for iteration in range(self.max_iterations):
        for page in pages:
            base_score = (1 - self.damping) / N
            link_score = 0.0

            # NEW: Iterate only incoming edges - O(degree) instead of O(N)
            for source_page in incoming_edges[page]:
                outgoing_count = len(self.graph.outgoing_refs.get(source_page, set()))
                if outgoing_count > 0:
                    link_score += scores[source_page] / outgoing_count

            new_scores[page] = base_score + self.damping * link_score
```

**Complexity change**: O(I × N²) → O(I × E) where E << N² for typical site graphs

### Phase 2: Link Suggestions Inverted Index

**Estimated effort**: 4 hours  
**Expected speedup**: 5-20x for typical sites

#### 2.1 Build Inverted Tag and Category Indices

```python
# link_suggestions.py - Add inverted indices
def _build_inverted_tag_index(self, pages: list[Page]) -> dict[str, set[Page]]:
    """Build tag -> pages mapping for efficient candidate filtering."""
    tag_to_pages: dict[str, set[Page]] = defaultdict(set)
    for page in pages:
        tags = getattr(page, "tags", []) or []
        for tag in tags:
            normalized = tag.lower().replace(" ", "-")
            tag_to_pages[normalized].add(page)
    return tag_to_pages

def _build_inverted_category_index(self, pages: list[Page]) -> dict[str, set[Page]]:
    """Build category -> pages mapping for efficient candidate filtering."""
    category_to_pages: dict[str, set[Page]] = defaultdict(set)
    for page in pages:
        category = getattr(page, "category", None)
        if category:
            normalized = category.lower().replace(" ", "-")
            category_to_pages[normalized].add(page)
        categories = getattr(page, "categories", []) or []
        for cat in categories:
            normalized = cat.lower().replace(" ", "-")
            category_to_pages[normalized].add(page)
    return category_to_pages
```

#### 2.2 Filter Candidates Before Scoring

```python
def _generate_suggestions_for_page(self, source: Page, ...) -> list[LinkSuggestion]:
    existing_links = self.graph.outgoing_refs.get(source, set())
    source_tags = page_tags.get(source, set())

    # NEW: Only consider pages with shared tags
    candidate_pages: set[Page] = set()
    for tag in source_tags:
        candidate_pages.update(tag_to_pages.get(tag, set()))

    # Also include pages in same category
    source_cats = page_categories.get(source, set())
    for cat in source_cats:
        candidate_pages.update(category_to_pages.get(cat, set()))

    # Include underlinked pages (orphan bonus applies regardless of tags)
    for page in underlinked_pages:  # Pre-computed: pages with < 3 incoming refs
        candidate_pages.add(page)

    # Score only candidates with potential overlap
    candidates: list[tuple[Page, float, list[str]]] = []
    for target in candidate_pages:
        if target == source or target in existing_links:
            continue
        score, reasons = self._calculate_link_score(...)
        if score >= self.min_score:
            candidates.append((target, score, reasons))
```

> **Note**: Underlinked pages (orphans and pages with < 3 incoming refs) are always included as candidates because they receive the underlinked bonus regardless of tag/category overlap. This preserves the current behavior of suggesting links to orphan pages.

**Complexity change**: O(N² × T) → O(N × avg_overlap × T) where avg_overlap << N

### Phase 3: Optional Incremental Updates

**Estimated effort**: 1 day  
**Scope**: Future enhancement, not required for initial optimization

Add lightweight update methods for common operations:

```python
class KnowledgeGraph:
    def update_page(self, page: Page) -> None:
        """Incrementally update graph for a single page change."""
        # Remove old edges for this page
        self._remove_page_edges(page)
        # Re-extract and add new edges
        self._add_page_edges(page)
        # Invalidate caches that depend on this page
        self._invalidate_caches()

    def _invalidate_caches(self) -> None:
        """Clear cached results, forcing lazy recomputation."""
        self._pagerank_results = None
        self._community_results = None
        self._path_results = None
        self._link_suggestions = None
```

---

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (Required First)

**Files**: `benchmarks/test_analysis_performance.py` (new)

> **Critical**: Must be completed before any optimization to measure actual improvement.

1. Create synthetic site generator with configurable page count and link density
2. Create benchmark scenarios: 100, 1K, 5K, 10K synthetic pages
3. Measure wall-clock time for each operation:
   - `graph.build()` — Graph construction
   - `graph.compute_pagerank()` — PageRank computation
   - `graph.suggest_links()` — Link suggestion generation
4. Record baseline metrics in `benchmarks/baseline_analysis.json`
5. Verify theoretical projections match actual performance

```python
# Example benchmark structure
@pytest.mark.benchmark
def test_pagerank_10k_pages(benchmark, synthetic_10k_site):
    """Baseline: PageRank on 10K pages."""
    graph = KnowledgeGraph(synthetic_10k_site)
    graph.build()
    result = benchmark(graph.compute_pagerank)
    assert result.converged
```

### Step 1: Add Incoming Edges to GraphBuilder

**Files**: `graph_builder.py`

1. Add `incoming_edges: dict[Page, list[Page]]` to `__init__`
2. Populate in `_analyze_cross_references()`, `_analyze_related_posts()`, etc.
3. Update parallel path (`_build_parallel`) to also build reverse edges
4. Expose via `KnowledgeGraph.incoming_edges` property
5. Update tests to verify reverse index correctness

### Step 2: Optimize PageRank

**Files**: `page_rank.py`

1. Use `self.graph.incoming_edges` (preferred) or build locally if not available
2. Replace inner loop with edge iteration
3. Run benchmark comparing old vs new implementation
4. Verify identical results with tolerance for floating point (1e-6)
5. Update baseline metrics with optimized performance

### Step 3: Optimize Link Suggestions

**Files**: `link_suggestions.py`

1. Add `_build_inverted_tag_index()` and `_build_inverted_category_index()`
2. Update `generate_suggestions()` to build indices at start
3. Update `_generate_suggestions_for_page()` to filter candidates
4. Run benchmark comparing old vs new implementation
5. Verify identical suggestions (order may differ due to float comparison)
6. Update baseline metrics with optimized performance

### Step 4: Final Benchmarking and Documentation

**Files**: `benchmarks/test_analysis_performance.py`, `README.md`

1. Run full benchmark suite with optimized algorithms
2. Compare against baseline metrics from Step 0
3. Document actual speedup achieved (target: 10x+ for PageRank, 5x+ for suggestions)
4. Add regression detection: fail if performance degrades >10% from optimized baseline
5. Update RFC with actual measured results

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | 10K Pages (projected) |
|-----------|-----------------|-----------|
| Graph Build | O(N × L) | ~20s |
| PageRank | O(I × N²) | ~8min |
| Community | O(N × E × log N) | ~1min |
| Paths (approx) | O(k × N) | ~1min |
| Link Suggestions | O(N² × T) | ~20min |

> **Note**: Time estimates are projections based on complexity analysis. Actual baseline measurements will be captured in Step 0.

### After Optimization

| Operation | Time Complexity | 10K Pages (projected) | Expected Speedup |
|-----------|-----------------|-----------|------------------|
| Graph Build | O(N × L) | ~20s (unchanged) | 1x |
| PageRank | O(I × E) | **~5s** | **10-100x** |
| Community | O(N × E × log N) | ~1min (unchanged) | 1x |
| Paths (approx) | O(k × N) | ~1min (unchanged) | 1x |
| Link Suggestions | O(N × overlap × T) | **~1min** | **5-20x** |

**Projected total analysis time for 10K pages**: ~30min → ~3min

### Complexity Variables

- **N**: Number of pages
- **E**: Number of edges (links between pages)
- **I**: PageRank iterations (typically 20-50)
- **L**: Average links per page
- **T**: Average tags per page
- **overlap**: Average number of pages sharing tags with a given page (typically << N)

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized algorithms produce identical results
   - PageRank scores within floating-point tolerance (1e-6)
   - Link suggestions contain same (source, target) pairs

2. **Edge cases**:
   - Empty graph (0 pages)
   - Single page (no edges)
   - Fully connected graph (all pages link to all)
   - Disconnected components

### Performance Tests

1. **Benchmark suite** with synthetic graphs:
   - Sparse graphs (avg degree 5)
   - Dense graphs (avg degree 50)
   - Power-law degree distribution (realistic)

2. **Regression detection**: Fail if performance degrades >10%

### Integration Tests

1. **Real site tests**: Run on bengal's own docs site
2. **Large site simulation**: 10K synthetic pages with realistic structure

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Floating-point differences in PageRank | Medium | Low | Use tolerance comparison, document precision |
| Memory increase from reverse index | Low | Low | Index is O(E), same as existing structures |
| Inverted index misses edge cases | Low | Medium | Comprehensive test coverage |
| Performance regression in small sites | Low | Low | Benchmark small sites explicitly |

---

## Alternatives Considered

### 1. Use NetworkX/igraph

**Pros**: Battle-tested C implementations, 10-100x faster  
**Cons**: New dependency, different API, harder to customize

**Decision**: Defer to separate RFC for very large sites (50K+). Current Python implementation is sufficient for typical Bengal sites after optimization.

### 2. Approximate PageRank

**Pros**: O(k) complexity with random sampling  
**Cons**: Non-deterministic, accuracy trade-off

**Decision**: Not needed. Optimized exact algorithm is fast enough for 10K pages.

### 3. Lazy Computation

**Pros**: Only compute what's requested  
**Cons**: Already implemented (caching). Core algorithms still need optimization.

**Decision**: Already in place. This RFC addresses the algorithms themselves.

---

## Success Criteria

1. **PageRank for 10K pages**: ≥10x speedup vs baseline (target: < 30 seconds)
2. **Link suggestions for 10K pages**: ≥5x speedup vs baseline (target: < 2 minutes)
3. **Baseline established**: Step 0 benchmarks captured before optimization
4. **No accuracy regression**: Results identical within tolerance (1e-6 for PageRank)
5. **No API changes**: Existing code continues working
6. **Regression tests**: CI fails if performance degrades >10% from optimized baseline

---

## Future Work

1. **Incremental updates**: Update graph without full rebuild
2. **Streaming analysis**: Analyze pages as they're processed
3. **NetworkX integration**: Optional backend for 50K+ sites
4. **Parallel PageRank**: Extend existing `GraphBuilder` ThreadPoolExecutor pattern to PageRank iteration (already free-threading ready via `graph_builder.py:166-285`)
5. **Lazy index building**: Build inverted indices only when `suggest_links()` is first called, not on every graph build

---

## References

- [Brandes' Algorithm](https://www.tandfonline.com/doi/abs/10.1080/0022250X.2001.9990249) — Fast betweenness centrality (already used for path analysis)
- [PageRank Paper](http://ilpubs.stanford.edu:8090/422/) — Original algorithm description
- [Louvain Method](https://arxiv.org/abs/0803.0476) — Community detection (already implemented efficiently)

---

## Appendix: Current Implementation Locations

| Algorithm | File | Key Functions |
|-----------|------|---------------|
| Graph Build | `graph_builder.py` | `build()`, `_analyze_*()` |
| PageRank | `page_rank.py` | `PageRankCalculator.compute()` |
| Community | `community_detection.py` | `LouvainCommunityDetector.detect()` |
| Path Analysis | `path_analysis.py` | `PathAnalyzer.analyze()` |
| Link Suggestions | `link_suggestions.py` | `LinkSuggestionEngine.generate_suggestions()` |
| Metrics | `graph_metrics.py` | `MetricsCalculator.compute_metrics()` |
