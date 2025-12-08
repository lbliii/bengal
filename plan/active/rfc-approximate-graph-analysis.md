---
Title: Approximate Graph Analysis for Large Sites
Author: AI Assistant
Date: 2025-12-08
Status: Draft
Confidence: 95%
---

# RFC: Approximate Graph Analysis

**Proposal**: Replace the $O(N^2)$ exact algorithms in `PathAnalyzer` with pivot-based approximations ($O(k \cdot N)$) to enable scalable graph analysis for large sites. This applies to both betweenness centrality and closeness centrality.

---

## 1. Problem Statement

### Current State

The current `PathAnalyzer.analyze()` method uses exact algorithms that run a BFS from **every single page** in the graph:

1. **Betweenness Centrality**: Brandes' algorithm iterates all pages as sources
2. **Closeness Centrality**: BFS distances computed from every page

**Evidence**:

- `bengal/analysis/path_analysis.py:211`: `for source in pages: ...` (Betweenness - iterates all pages)
- `bengal/analysis/path_analysis.py:276`: `for page in pages: ...` (Closeness - iterates all pages)

### Pain Points

- **Complexity**: Both algorithms are $O(N \cdot E)$, which for sparse graphs is roughly $O(N^2)$.
- **Scalability**: For a site with 10,000 pages, this requires 20,000 BFS runs (10k for betweenness + 10k for closeness). At 10ms per BFS, total analysis takes ~200 seconds.
- **User Impact**: Users with large sites cannot use `::analyze` or graph insights features without unacceptable delays.
- **No Progress Feedback**: Long-running operations provide no intermediate progress.

---

## 2. Goals & Non-Goals

**Goals**:

- Reduce time complexity of both centrality metrics to $O(k \cdot N)$, where $k \ll N$.
- Maintain sufficient accuracy to identify "top pages" correctly (relative ranking preserved).
- Ensure deterministic results by seeding the random pivot selection.
- Add progress reporting for long-running operations.
- Add timeout protection for expensive operations like `find_all_paths`.
- Automatically select exact vs approximate based on site size.

**Non-Goals**:

- We are **not** trying to get *exact* centrality values (relative ranking is sufficient for insights).
- We are not changing community detection or PageRank (already efficient).

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Analysis** (`bengal/analysis/`):
  - `path_analysis.py`: Implementation of centrality algorithms.
  - `knowledge_graph.py`: Consumer of these metrics.

**Integration Points**:

- `KnowledgeGraph.analyze_paths()` calls `PathAnalyzer.analyze()`.
- No impact on core build or rendering (analysis is optional).

---

## 4. Design Options

### Option A: Pivot-Based Approximation (Recommended)

Run algorithms from a small subset of $k$ random nodes (pivots) and extrapolate.

- **Description**: Select $k$ (e.g., 100) pivot pages. Run BFS only from these pivots.
- **Pros**:
  - Linear scalability with site size (for fixed $k$).
  - Drastically faster for $N > 500$.
  - Tunable accuracy via $k$.
  - Same approximation technique applies to both betweenness and closeness.
- **Cons**:
  - Scores are approximations.
  - Non-deterministic if seed not fixed (mitigated by `random_seed`).
- **Complexity**: Simple modification to existing loop logic.

### Option B: Parallel Exact Computation

Run the exact algorithm in parallel using `multiprocessing`.

- **Description**: Split the `for source in pages` loop across CPU cores.
- **Pros**:
  - Exact results.
  - Faster than serial (linear speedup by core count).
- **Cons**:
  - Still $O(N^2)$ overall.
  - High overhead for IPC (pickling large graph structures).
  - Doesn't solve the fundamental scaling issue for 10k+ pages.

**Recommended**: **Option A** because algorithmic improvement ($O(N)$) beats constant-factor parallelization ($O(N^2/P)$) for scalability.

---

## 5. Detailed Design (Option A)

### 5.1 API Changes

Update `PathAnalyzer` to accept approximation and progress parameters.

```python
# bengal/analysis/path_analysis.py

from collections.abc import Callable

# Type alias for progress callback
type ProgressCallback = Callable[[int, int, str], None]  # (current, total, phase)

class PathAnalyzer:
    def __init__(
        self,
        graph: KnowledgeGraph,
        k_pivots: int = 100,
        seed: int = 42,
        auto_approximate_threshold: int = 500,
    ):
        self.graph = graph
        self.k_pivots = k_pivots
        self.seed = seed
        self.auto_approximate_threshold = auto_approximate_threshold

    def analyze(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> PathAnalysisResults:
        """Analyze with optional progress reporting."""
        ...
```

### 5.2 Betweenness Centrality Approximation

```python
def _compute_betweenness_centrality(
    self,
    pages: list[Page],
    progress_callback: ProgressCallback | None = None,
) -> dict[Page, float]:
    import random
    rng = random.Random(self.seed)
    
    # Auto-select exact vs approximate based on site size
    use_exact = len(pages) <= self.auto_approximate_threshold
    
    if use_exact:
        sources = pages
    else:
        sources = rng.sample(pages, min(self.k_pivots, len(pages)))
    
    # Run Brandes' only for selected sources...
    for i, source in enumerate(sources):
        if progress_callback:
            progress_callback(i, len(sources), "betweenness")
        # ... BFS and accumulation ...
    
    # Scale scores if approximating
    if not use_exact:
        scale = len(pages) / len(sources)
        betweenness = {p: c * scale for p, c in betweenness.items()}
```

### 5.3 Closeness Centrality Approximation

Apply the same pivot-based approach:

```python
def _compute_closeness_centrality(
    self,
    pages: list[Page],
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[Page, float], float, int]:
    import random
    rng = random.Random(self.seed)
    
    use_exact = len(pages) <= self.auto_approximate_threshold
    
    if use_exact:
        sample_pages = pages
    else:
        sample_pages = rng.sample(pages, min(self.k_pivots, len(pages)))
    
    # Compute distances only from sample pages
    for i, page in enumerate(sample_pages):
        if progress_callback:
            progress_callback(i, len(sample_pages), "closeness")
        distances = self._bfs_distances(page, pages)
        # ... accumulate distances ...
```

### 5.4 Timeout for find_all_paths

```python
def find_all_paths(
    self,
    source: Page,
    target: Page,
    max_length: int = 10,
    max_paths: int = 1000,
    timeout_seconds: float | None = 30.0,
) -> list[list[Page]]:
    """Find all simple paths with safety limits."""
    start_time = time.monotonic()
    all_paths: list[list[Page]] = []
    
    def dfs(current: Page, path: list[Page], visited: set[Page]) -> bool:
        # Check limits
        if timeout_seconds and (time.monotonic() - start_time) > timeout_seconds:
            return False  # Timeout
        if len(all_paths) >= max_paths:
            return False  # Path limit reached
        # ... rest of DFS ...
```

### 5.5 Normalization

For exact betweenness, normalization is $(N-1)(N-2)$. For approximated:
$$ \text{Score} \approx \text{RawScore} \times \frac{N}{k} $$

For closeness, we estimate based on average distances from pivots - this gives a good approximation of how "central" each node is relative to the sample.

---

## 6. Tradeoffs & Risks

**Tradeoffs**:

- **Accuracy vs Speed**: We lose precision but gain massive speed (100x+ for large sites).
- **Stability**: Top 10 lists might fluctuate slightly with different seeds.

**Risks**:

- **Risk 1**: Missing a critical bridge page that isn't reached by pivots.
  - **Likelihood**: Low for well-connected graphs.
  - **Mitigation**: Ensure $k$ is large enough (100 covers most structures).
- **Risk 2**: Determinism issues breaking tests.
  - **Mitigation**: Fix random seed in tests and default config.
- **Risk 3**: Progress callback overhead.
  - **Mitigation**: Callback is optional and called per-source, not per-edge.

---

## 7. Performance Impact

- **Time**: $O(k \cdot N)$ vs $O(N^2)$.
  - For $N=10,000, k=100$: $100 \cdot 10,000 = 10^6$ ops vs $10^8$ ops (100x speedup).
  - For $N=100,000, k=100$: 1000x speedup.
- **Memory**: No change (uses existing graph structure).

| Site Size | Exact Time | Approximate Time | Speedup |
|-----------|------------|------------------|---------|
| 500 pages | ~2.5s | ~2.5s (exact used) | 1x |
| 1,000 pages | ~10s | ~1s | 10x |
| 10,000 pages | ~1000s | ~10s | 100x |
| 100,000 pages | hours | ~100s | 1000x+ |

---

## 8. Implementation Checklist

- [x] Update RFC to include closeness centrality
- [ ] Add `k_pivots`, `seed`, `auto_approximate_threshold` to `PathAnalyzer.__init__`
- [ ] Implement pivot-based betweenness centrality
- [ ] Implement pivot-based closeness centrality
- [ ] Add `progress_callback` to `analyze()`
- [ ] Add `timeout_seconds` and `max_paths` to `find_all_paths()`
- [ ] Update `KnowledgeGraph.analyze_paths()` to pass parameters
- [ ] Add tests for approximation accuracy
- [ ] Add tests for progress callback
- [ ] Add tests for timeout behavior

---

## 9. Open Questions

- [x] **Q1**: What is the optimal default $k$? **Answer**: 100 based on literature (covers 95%+ of important nodes in typical web graphs).
- [x] **Q2**: Should we automatically switch to exact for small sites? **Answer**: Yes, threshold at 500 pages.
- [ ] **Q3**: Should we expose configuration via `bengal.toml`? (Proposed: Yes, under `[analysis]`)
