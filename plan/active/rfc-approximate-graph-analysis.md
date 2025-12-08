---
Title: Approximate Betweenness Centrality for Large Sites
Author: AI Assistant
Date: 2025-12-08
Status: Draft
Confidence: 95%
---

# RFC: Approximate Betweenness Centrality

**Proposal**: Replace the $O(N^2)$ exact Brandes' algorithm in `PathAnalyzer` with a pivot-based approximation ($O(k \cdot N)$) to enable scalable graph analysis for large sites.

---

## 1. Problem Statement

### Current State

The current `PathAnalyzer.analyze()` method uses Brandes' algorithm to compute betweenness centrality. This algorithm runs a Breadth-First Search (BFS) from **every single page** in the graph to count how many shortest paths pass through each node.

**Evidence**:

- `bengal/analysis/path_analysis.py:211`: `for source in pages: ...` (Iterates all pages)
- `bengal/analysis/path_analysis.py:222`: `while queue: ...` (BFS traversal)

### Pain Points

- **Complexity**: The complexity is $O(N \cdot E)$, which for sparse graphs is roughly $O(N^2)$.
- **Scalability**: For a site with 10,000 pages, this requires 10,000 BFS runs. If one BFS takes 10ms, the total analysis takes ~100 seconds. For 100k pages, it takes hours.
- **User Impact**: Users with large sites cannot use `::analyze` or graph insights features without acceptable delays.

---

## 2. Goals & Non-Goals

**Goals**:

- Reduce time complexity of betweenness centrality to $O(k \cdot N)$, where $k \ll N$.
- Maintain sufficient accuracy to identify "top bridge pages" correctly.
- Ensure deterministic results by seeding the random pivot selection.

**Non-Goals**:

- We are **not** trying to get *exact* centrality values (relative ranking is sufficient for insights).
- We are not changing Closeness Centrality at this time (though similar techniques apply).

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Analysis** (`bengal/analysis/`):
  - `path_analysis.py`: Implementation of `_compute_betweenness_centrality`.
  - `knowledge_graph.py`: Consumer of these metrics.

**Integration Points**:

- `KnowledgeGraph.analyze_paths()` calls `PathAnalyzer.analyze()`.
- No impact on core build or rendering (analysis is optional).

---

## 4. Design Options

### Option A: Pivot-Based Approximation (Recommended)

Run Brandes' algorithm from a small subset of $k$ random nodes (pivots) and extrapolate.

- **Description**: Select $k$ (e.g., 50-100) pivot pages. Run BFS only from these pivots. Accumulate dependencies.
- **Pros**:
  - Linear scalability with site size (for fixed $k$).
  - Drastically faster for $N > 1000$.
  - Tunable accuracy via $k$.
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

### API Changes

Update `PathAnalyzer` to accept approximation parameters.

```python
# bengal/analysis/path_analysis.py

class PathAnalyzer:
    def __init__(self, graph: KnowledgeGraph, k_pivots: int = 100, seed: int = 42):
        self.graph = graph
        self.k_pivots = k_pivots
        self.seed = seed

    def _compute_betweenness_centrality(self, pages: list[Page]) -> dict[Page, float]:
        # Select pivots
        import random
        random.seed(self.seed)
        
        # If N < k, use exact (all pages)
        if len(pages) <= self.k_pivots:
            sources = pages
        else:
            sources = random.sample(pages, self.k_pivots)
            
        # Run Brandes' only for sources...
```

### Normalization

The normalization factor for exact betweenness is $(N-1)(N-2)$. For approximated, we extrapolate based on the ratio of pivots to total nodes:
$$ \text{Score} \approx \text{RawScore} \times \frac{N}{k} $$
(Or simply use raw scores for ranking, as relative order matters most).

### Configuration

Add configuration to `bengal.toml` (optional):

```toml
[analysis]
approximate_centrality = true
pivot_count = 100
```

---

## 6. Tradeoffs & Risks

**Tradeoffs**:

- **Accuracy vs Speed**: We lose precision in the 4th/5th decimal place but gain massive speed.
- **Stability**: Top 10 lists might fluctuate slightly with different seeds.

**Risks**:

- **Risk 1**: Missing a critical bridge page that isn't reached by pivots.
  - **Likelihood**: Low for well-connected graphs.
  - **Mitigation**: Ensure $k$ is large enough (e.g., 100 covers most structures).
- **Risk 2**: Determinism issues breaking tests.
  - **Mitigation**: Fix random seed in tests and default config.

---

## 7. Performance Impact

- **Time**: $O(k \cdot N)$ vs $O(N^2)$.
  - For $N=10,000, k=100$: $100 \cdot 10,000 = 10^6$ ops vs $10^8$ ops (100x speedup).
- **Memory**: No change (uses existing graph structure).

---

## 8. Open Questions

- [ ] **Q1**: What is the optimal default $k$? (Proposed: 100 based on literature).
- [ ] **Q2**: Should we automatically switch to exact for small sites ($N < 500$)? (Yes, design includes this).
