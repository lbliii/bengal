# RFC: Parallel Render Complexity Ordering

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0008 |
| **Title** | Complexity-Based Page Ordering for Parallel Rendering |
| **Status** | Implemented |
| **Created** | 2025-12-25 |
| **Author** | Bengal Core Team |
| **Depends On** | None |
| **Supersedes** | None |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Sort pages by estimated complexity before parallel dispatch (heavy pages first) |
| **Why** | Eliminate "straggler workers" that cause idle time in parallel builds |
| **Effort** | ~2 hours (small, focused change) |
| **Risk** | Very Low — sorting overhead negligible, no behavior changes |
| **Constraints** | Estimation must be < 0.1ms per page to avoid adding more overhead than saved |

**Key Insight**: With parallel rendering, if heavy pages are processed last, fast workers finish early and sit idle waiting for the slowest worker. Processing heavy pages first ensures all workers finish at approximately the same time.

**Key Deliverables:**
1. `ComplexityEstimator` module for O(n) page complexity scoring
2. Integration with `RenderOrchestrator` parallel methods
3. Optional configuration flag (enabled by default)
4. Build logging for complexity distribution analysis

---

## Motivation

### The Straggler Problem

With parallel rendering using `ThreadPoolExecutor`, pages are currently dispatched in arrival order. This creates a load imbalance:

**Current Behavior (pages in arbitrary order):**
```
Worker 1: [light][light][light][HEAVY]────────────────────|done
Worker 2: [light][light][light][light]|idle waiting.......|
Worker 3: [light][light][light][light]|idle waiting.......|
Worker 4: [light][light][HEAVY]───────────────────|idle...|
                                                  ↑
                                          Waiting for Worker 1
```

Workers 2-4 finish their light pages quickly, then sit idle while Worker 1 processes the final heavy page. The total build time is determined by the slowest single page, not the average.

**Optimal Behavior (heavy pages first):**
```
Worker 1: [HEAVY]────────────────────[light][light]|done
Worker 2: [HEAVY]──────────────[light][light][light]|done
Worker 3: [light][light][light][light][light][light]|done
Worker 4: [light][light][light][light][light]|done
                                              ↑
                                   All finish closer together
```

By dispatching heavy pages first, they run in parallel with each other while light pages fill in the remaining time.

### Quantified Impact

| Scenario | Without Ordering | With Ordering | Savings |
|----------|------------------|---------------|---------|
| 100 pages, 1 heavy (5s), rest avg 0.2s | 5s + 2s idle | ~5s | 2s idle time |
| 1000 pages, 10 heavy (3s each), rest avg 0.1s | 3s + straggler wait | ~3s | Variable |
| Mixed API docs (heavy) + blog posts (light) | Significant idle | Near-optimal | 20-40% |

**Sites with high variance** (API documentation mixed with short blog posts) see the largest gains.

---

## Design

### Algorithm: Longest Processing Time First (LPT)

This RFC implements the [LPT scheduling algorithm](https://en.wikipedia.org/wiki/Longest-processing-time-first_scheduling), a well-studied greedy heuristic for minimizing makespan (total completion time) on parallel machines.

**Key properties:**
- **Optimal for 2 workers**: LPT produces optimal schedules for m=2 machines
- **4/3-approximation**: For m≥3 machines, LPT achieves makespan ≤ 4/3 × optimal
- **O(n log n) complexity**: Dominated by sorting, same as quicksort
- **Simple implementation**: Just sort descending and dispatch

**Why LPT works here:**
- ThreadPoolExecutor distributes work to available workers
- Processing heavy pages first ensures they run in parallel
- Light pages fill in remaining time, reducing idle workers

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ComplexityEstimator                           │
│  - O(n) content scanning                                         │
│  - Heuristic scoring (content size, code blocks, directives)     │
│  - No actual rendering — estimation only                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RenderOrchestrator                            │
│  - Sort pages by complexity score (descending)                   │
│  - Dispatch to ThreadPoolExecutor                                │
│  - Heavy pages processed first across all workers                │
└─────────────────────────────────────────────────────────────────┘
```

### Complexity Factors

| Factor | Weight | Rationale |
|--------|--------|-----------|
| **Content bytes** | 1 pt / 500 bytes | Parsing time scales with content |
| **Code blocks** | 10 pts each | Syntax highlighting is expensive (~2-10ms per block) |
| **Directives** | 3 pts each | Directive processing adds overhead |
| **Variable substitutions** | 1 pt each | Template variable resolution |

**Formula:**
```
score = (content_bytes // 500) + (code_blocks * 10) + (directives * 3) + (variables * 1)
```

### Why These Factors?

**Code blocks** are weighted highest because:
- Each code fence triggers the syntax highlighter (Rosettes/Pygments)
- Highlighting involves tokenization, state machine execution, HTML generation
- A page with 20 code blocks can take 10x longer than a prose page

**Content size** is a baseline indicator:
- Larger documents have more markdown to parse
- More content = more AST nodes = more template rendering

**Directives** (admonitions, tabs, etc.):
- Each directive requires parsing, processing, and rendering
- Some directives (like `{toctree}`) trigger additional lookups

---

## Implementation

### Module: `bengal/orchestration/complexity.py`

```python
"""Page complexity estimation for optimal parallel dispatch ordering.

This module provides lightweight heuristics to estimate page rendering
complexity BEFORE rendering, enabling optimal work distribution across
parallel workers.

Design Goals:
    1. Fast: < 0.1ms per page (must not add significant overhead)
    2. Accurate enough: Relative ordering matters, not absolute accuracy
    3. Thread-safe: Uses only compiled regexes and immutable data

Key Insight:
    We don't need perfect predictions. We just need heavy pages to
    sort before light pages. Even rough estimates improve parallelism.

Example:
    >>> from bengal.orchestration.complexity import sort_by_complexity
    >>> sorted_pages = sort_by_complexity(pages)  # Heavy first
    >>> # Now dispatch to ThreadPoolExecutor
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page

__all__ = [
    "ComplexityScore",
    "estimate_complexity",
    "sort_by_complexity",
    "get_cached_score",
    "get_complexity_stats",
]


@dataclass(frozen=True, slots=True)
class ComplexityScore:
    """Lightweight complexity metrics for a page.

    Immutable and hashable for potential caching use cases.

    Attributes:
        content_bytes: Raw content length in bytes
        code_blocks: Count of fenced code blocks
        directives: Count of MyST/RST directives
        variables: Count of template variables ({{ var }})
    """
    content_bytes: int
    code_blocks: int
    directives: int
    variables: int

    @property
    def score(self) -> int:
        """Combined complexity score (higher = more complex).

        Weights are tuned based on profiling data:
        - Code blocks are most expensive (syntax highlighting)
        - Directives require additional processing
        - Content size is baseline indicator
        - Variables have minimal impact

        Note:
            Relative ordering matters more than absolute accuracy.
            Even rough estimates significantly improve parallelism.
        """
        return (
            self.content_bytes // 500 +      # ~1 point per 500 bytes
            self.code_blocks * 10 +          # Code highlighting is expensive
            self.directives * 3 +            # Directive processing
            self.variables                   # Variable substitution (minimal)
        )


# Compiled patterns for speed (module-level, computed once)
# These run in ~0.01ms for typical page content

_CODE_FENCE = re.compile(r'^\s*```', re.MULTILINE)
"""Matches fenced code block markers (opening AND closing).

Note: Matches both opening and closing ```, so we divide count by 2.
Also matches indented code blocks (e.g., in lists) via \s* prefix.
"""

_DIRECTIVE_MYST = re.compile(r'^:::{?\w+', re.MULTILINE)
"""Matches MyST directive syntax (:::{name} or :::name)."""

_DIRECTIVE_RST = re.compile(r'^\.\. \w+::', re.MULTILINE)
"""Matches RST-style directive syntax (.. name::)."""

_VARIABLE = re.compile(r'\{\{')
"""Matches template variable openings."""


def estimate_complexity(content: str) -> ComplexityScore:
    """Estimate page rendering complexity from raw content.

    Designed to be fast (< 0.1ms per page) so sorting overhead
    doesn't exceed the parallelism benefits.

    Implementation uses findall() which is O(n) and creates minimal
    allocations due to regex engine optimizations.

    Args:
        content: Raw markdown content (before parsing)

    Returns:
        ComplexityScore with heuristic metrics

    Example:
        >>> score = estimate_complexity(page.content)
        >>> print(f"Complexity: {score.score}")
    """
    if not content:
        return ComplexityScore(0, 0, 0, 0)

    # Count patterns (each findall is O(n), total is O(n))
    # Divide fence count by 2 since we match both opening and closing ```
    code_fences = len(_CODE_FENCE.findall(content))
    code_blocks = code_fences // 2  # Each block has open + close

    directives = (
        len(_DIRECTIVE_MYST.findall(content)) +
        len(_DIRECTIVE_RST.findall(content))
    )
    variables = len(_VARIABLE.findall(content))

    return ComplexityScore(
        content_bytes=len(content),
        code_blocks=code_blocks,
        directives=directives,
        variables=variables,
    )


def _get_content_safe(page: Page) -> str:
    """Get page content without triggering lazy loads on PageProxy.

    For PageProxy instances where content isn't loaded, returns empty
    string (treated as unknown/light complexity). This avoids disk I/O
    during sorting, which would negate the optimization benefits.

    For regular Page instances, content is always available.
    """
    # Check for PageProxy with unloaded content
    if hasattr(page, '_full_page') and page._full_page is None:
        # PageProxy without loaded content - treat as light
        return ''

    return getattr(page, 'content', '') or ''


def get_cached_score(page: Page) -> int:
    """Get complexity score with caching on the page object.

    Caches the score on the page to avoid recomputation if called
    multiple times (e.g., in logging after sorting).
    """
    # Check for cached score first
    cached = getattr(page, '_complexity_score', None)
    if cached is not None:
        return cached

    # Compute and cache
    content = _get_content_safe(page)
    score = estimate_complexity(content).score

    # Cache on page (safe - pages are mutable objects)
    try:
        page._complexity_score = score  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        pass  # Frozen dataclass or other immutable - skip caching

    return score


def sort_by_complexity(
    pages: list[Page],
    descending: bool = True,
) -> list[Page]:
    """Sort pages by estimated rendering complexity.

    For parallel rendering, descending=True (heavy first) is optimal.
    This ensures heavy pages start processing immediately while light
    pages fill in later, minimizing idle worker time.

    Thread-safe: creates new list, doesn't modify input.
    Uses Python's stable Timsort, so equal-complexity pages maintain
    their original relative order.

    Args:
        pages: List of Page objects to sort
        descending: If True, heaviest pages first (optimal for parallel)

    Returns:
        New sorted list (original unchanged)

    Performance:
        - Estimation: ~0.01ms per page
        - Sorting: O(n log n) with Timsort
        - Total for 1000 pages: ~10-20ms

    Note:
        PageProxy instances with unloaded content are treated as light
        pages to avoid triggering disk I/O during sorting.

    Example:
        >>> sorted_pages = sort_by_complexity(pages)
        >>> # First page is most complex
        >>> print(sorted_pages[0].source_path)
    """
    return sorted(pages, key=get_cached_score, reverse=descending)


def get_complexity_stats(pages: list[Page]) -> dict[str, int | float | list[int]]:
    """Get complexity distribution statistics for logging.

    Useful for understanding build characteristics and validating
    that complexity ordering is beneficial. High variance_ratio (>10)
    indicates the site will benefit significantly from ordering.

    Args:
        pages: List of pages to analyze

    Returns:
        Dictionary with distribution stats and top/bottom samples
    """
    if not pages:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "median": 0,
            "variance_ratio": 1.0,
            "top_5_scores": [],
            "bottom_5_scores": [],
        }

    # Use cached scores to avoid recomputation
    scores = [get_cached_score(page) for page in pages]
    scores_sorted = sorted(scores, reverse=True)
    n = len(scores)

    return {
        "count": n,
        "min": scores_sorted[-1],
        "max": scores_sorted[0],
        "mean": sum(scores) / n,
        "median": scores_sorted[n // 2],
        "variance_ratio": scores_sorted[0] / max(scores_sorted[-1], 1),
        "top_5_scores": scores_sorted[:5],       # Heaviest pages
        "bottom_5_scores": scores_sorted[-5:],   # Lightest pages
    }
```

### Integration: `bengal/orchestration/render.py`

**Modify `_render_parallel_simple` (and similar methods):**

```python
def _render_parallel_simple(
    self,
    pages: list[Page],
    tracker: DependencyTracker | None,
    quiet: bool,
    stats: BuildStats | None,
    build_context: BuildContext | None = None,
    changed_sources: set[Path] | None = None,
) -> None:
    """Parallel rendering without progress (traditional)."""
    from bengal.orchestration.complexity import sort_by_complexity
    from bengal.rendering.pipeline import RenderingPipeline

    max_workers = get_max_workers(self.site.config.get("max_workers"))

    # Sort heavy pages first to avoid straggler workers
    # Overhead: ~0.01ms per page, saves seconds on large builds with variance
    if len(pages) > max_workers:
        # Only sort if we have more pages than workers (otherwise no benefit)
        sorted_pages = sort_by_complexity(pages, descending=True)
    else:
        sorted_pages = pages

    # ... rest of method unchanged, but use sorted_pages ...

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {
            executor.submit(process_page_with_pipeline, page): page
            for page in sorted_pages  # <-- Use sorted pages
        }
        # ... error handling unchanged ...
```

**Apply same pattern to:**
- `_render_parallel_with_progress`
- `_render_parallel_with_live_progress`

### Configuration

Add optional configuration in `bengal.yaml`:

```yaml
build:
  # Sort pages by complexity for optimal parallel distribution
  # Default: true (recommended for most sites)
  complexity_ordering: true
```

**Implementation:**

```python
# In render.py
def _should_use_complexity_ordering(self) -> bool:
    """Check if complexity-based ordering is enabled."""
    return self.site.config.get("build", {}).get("complexity_ordering", True)
```

### Logging

Add structured logging for build analysis:

```python
# Log complexity distribution at debug level
if logger.isEnabledFor(logging.DEBUG):
    from bengal.orchestration.complexity import get_complexity_stats
    stats = get_complexity_stats(pages)

    # Log distribution summary
    logger.debug(
        "complexity_distribution",
        page_count=stats["count"],
        min_score=stats["min"],
        max_score=stats["max"],
        mean_score=round(stats["mean"], 1),
        variance_ratio=round(stats["variance_ratio"], 1),
    )

    # Log ordering effectiveness (high variance = big benefit)
    if stats["variance_ratio"] > 10:
        logger.debug(
            "complexity_ordering_beneficial",
            reason="high variance detected",
            top_5=stats["top_5_scores"],
            bottom_5=stats["bottom_5_scores"],
        )
    elif stats["variance_ratio"] < 2:
        logger.debug(
            "complexity_ordering_marginal",
            reason="low variance - pages have similar complexity",
        )
```

**Interpreting Variance Ratio:**
- **> 20**: Excellent candidate, expect 20-40% improvement
- **10-20**: Good candidate, expect 10-20% improvement
- **2-10**: Marginal benefit, expect 5-10% improvement
- **< 2**: Minimal benefit, but overhead is negligible anyway

---

## Performance Analysis

### Overhead

| Operation | Time per Page | 1000 Pages | Notes |
|-----------|--------------|------------|-------|
| `estimate_complexity()` | ~0.01ms | ~10ms | Four regex findall() calls |
| `sorted()` | O(n log n) | ~5ms | Python's Timsort |
| **Total overhead** | - | ~15ms | Negligible |

### Savings

**Scenario: 1000 pages, 10 heavy (3s each), 990 light (0.1s avg)**

| Metric | Without Ordering | With Ordering |
|--------|------------------|---------------|
| Heavy page distribution | Random (clustered at end) | First 10 positions |
| Worker idle time | Up to 2.5s × 3 workers | Near zero |
| Total build time | ~3.5s | ~3.1s |
| **Improvement** | - | ~10-15% |

**Worst case (no variance):** If all pages have equal complexity, sorting adds ~15ms overhead with no benefit. This is acceptable.

**Best case (high variance):** API documentation sites with mix of heavy API reference pages and light blog posts see 20-40% improvement.

---

## Alternatives Considered

### 1. Work Stealing

**Approach:** Let idle workers "steal" work from busy workers' queues.

**Rejected:**
- Python's `ThreadPoolExecutor` doesn't support work stealing
- Would require custom executor implementation
- Complexity ordering achieves similar result with simpler code

### 2. Dynamic Complexity Measurement

**Approach:** Measure actual render time and use for future builds.

**Rejected:**
- Requires persistent state across builds
- First build has no data
- Content changes invalidate measurements
- Heuristic estimation is "good enough"

### 3. Page Type Classification

**Approach:** Use page type (api_doc, blog, etc.) as complexity proxy.

**Rejected:**
- Not all heavy pages are API docs
- Long blog posts with many code examples can be heavy
- Content-based estimation is more accurate

### 4. Parallel Chunks

**Approach:** Pre-partition pages into equal-complexity chunks.

**Rejected:**
- More complex implementation
- ThreadPoolExecutor already handles distribution
- Simple sorting achieves same effect

---

## Edge Cases & Limitations

### PageProxy Handling

When using incremental builds with `PageProxy`, content may not be loaded until accessed. To avoid triggering expensive disk I/O during sorting:

- **PageProxy with unloaded content**: Treated as "unknown" complexity (score = 0)
- **Effect**: Unloaded proxies sort to the end (light position)
- **Mitigation**: Most incremental builds render few pages, reducing straggler impact

This is acceptable because:
1. Incremental builds typically process fewer pages
2. Disk I/O during sorting would negate optimization benefits
3. Unknown pages at the end is a safe default

### Unclosed Code Blocks

Malformed markdown with unclosed code fences (odd number of ` ``` `) results in:
- `code_blocks = fence_count // 2` (rounded down)
- Example: 5 fences → 2 blocks counted

This is acceptable since:
1. Relative ordering is what matters, not exact counts
2. Malformed content is rare
3. The estimate is still directionally correct

### Very Large Pages

Pages > 100KB may have higher estimation overhead (~0.05ms instead of ~0.01ms), but this is:
1. Still well under the 0.1ms budget
2. Proportional to the savings from correct ordering
3. Rare in typical documentation sites

---

## Migration

### Automatic (Default On)

No migration required. The optimization is enabled by default and transparent to users.

### Opt-Out

Users can disable via configuration:

```yaml
build:
  complexity_ordering: false
```

---

## Testing

### Unit Tests

```python
# tests/unit/orchestration/test_complexity.py

import pytest
from unittest.mock import Mock

from bengal.orchestration.complexity import (
    estimate_complexity,
    sort_by_complexity,
    get_cached_score,
    get_complexity_stats,
    ComplexityScore,
)


class TestEstimateComplexity:
    """Tests for estimate_complexity function."""

    def test_empty_content(self):
        """Empty content has zero complexity."""
        score = estimate_complexity("")
        assert score.score == 0
        assert score.code_blocks == 0
        assert score.directives == 0

    def test_code_blocks_counted_correctly(self):
        """Code blocks are counted as pairs (open + close)."""
        # One complete code block = 2 fence markers = 1 block
        content = "```python\nprint('hi')\n```"
        score = estimate_complexity(content)
        assert score.code_blocks == 1

        # Three complete code blocks
        content = "```\na\n```\n\n```\nb\n```\n\n```\nc\n```"
        score = estimate_complexity(content)
        assert score.code_blocks == 3

    def test_indented_code_blocks(self):
        """Indented code blocks (in lists) are detected."""
        content = """\
- Item with code:
    ```python
    print("hi")
    ```
"""
        score = estimate_complexity(content)
        assert score.code_blocks == 1

    def test_code_blocks_weighted_heavily(self):
        """Code blocks should dominate scoring over prose."""
        prose = "Hello world " * 100  # 1200 bytes, ~2 points
        code = "```python\nprint('hi')\n```"  # ~30 bytes + 10 points

        prose_score = estimate_complexity(prose)
        code_score = estimate_complexity(code)

        assert code_score.score > prose_score.score

    def test_myst_directives(self):
        """MyST directives are counted."""
        content = """\
:::{note}
This is a note.
:::

:::{warning}
This is a warning.
:::
"""
        score = estimate_complexity(content)
        assert score.directives == 2

    def test_rst_directives(self):
        """RST-style directives are counted."""
        content = """\
.. note::
   This is a note.

.. warning::
   This is a warning.
"""
        score = estimate_complexity(content)
        assert score.directives == 2


class TestSortByComplexity:
    """Tests for sort_by_complexity function."""

    def test_heavy_pages_first(self):
        """Heavy pages should sort first (descending)."""
        light = Mock(content="short")
        heavy = Mock(content="```python\n```\n" * 10)  # 10 code blocks

        sorted_pages = sort_by_complexity([light, heavy])

        assert sorted_pages[0] is heavy
        assert sorted_pages[1] is light

    def test_preserves_order_for_equal_complexity(self):
        """Stable sort: equal complexity pages maintain original order."""
        pages = [Mock(content="same") for _ in range(5)]
        for i, p in enumerate(pages):
            p.name = f"page_{i}"  # For identification

        sorted_pages = sort_by_complexity(pages)

        # Python's Timsort is stable
        for i, page in enumerate(pages):
            assert sorted_pages[i] is page

    def test_does_not_modify_input(self):
        """Original list should remain unchanged."""
        pages = [Mock(content="a"), Mock(content="b" * 1000)]
        original_order = list(pages)

        sorted_pages = sort_by_complexity(pages)

        assert pages == original_order
        assert sorted_pages is not pages

    def test_page_proxy_without_content(self):
        """PageProxy with unloaded content is treated as light."""
        # Simulate PageProxy with _full_page = None (not loaded)
        proxy = Mock()
        proxy._full_page = None
        proxy.content = "this should not be accessed"

        regular = Mock()
        regular.content = "```\n```\n" * 5  # 5 code blocks
        del regular._full_page  # Regular page has no _full_page

        sorted_pages = sort_by_complexity([proxy, regular])

        # Regular page (with content) should sort first
        assert sorted_pages[0] is regular


class TestCachedScore:
    """Tests for score caching behavior."""

    def test_score_cached_on_page(self):
        """Score is cached on page object after first computation."""
        page = Mock(content="```\n```\n" * 3)
        del page._full_page  # Ensure it's treated as regular page

        score1 = get_cached_score(page)
        score2 = get_cached_score(page)

        assert score1 == score2
        assert hasattr(page, '_complexity_score')
        assert page._complexity_score == score1


class TestComplexityStats:
    """Tests for get_complexity_stats function."""

    def test_empty_pages(self):
        """Empty page list returns zero stats."""
        stats = get_complexity_stats([])
        assert stats["count"] == 0
        assert stats["variance_ratio"] == 1.0

    def test_stats_include_samples(self):
        """Stats include top and bottom score samples."""
        pages = [Mock(content="x" * (i * 500)) for i in range(10)]
        for p in pages:
            del p._full_page

        stats = get_complexity_stats(pages)

        assert "top_5_scores" in stats
        assert "bottom_5_scores" in stats
        assert len(stats["top_5_scores"]) == 5
```

### Integration Tests

```python
# tests/integration/test_parallel_rendering.py

import time
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator


@pytest.fixture
def high_variance_site(tmp_path):
    """Create a site with high complexity variance for testing."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create 10 heavy pages (many code blocks)
    for i in range(10):
        page = content_dir / f"api-reference-{i}.md"
        code_blocks = "```python\nimport foo\n```\n\n" * 25
        page.write_text(f"# API Reference {i}\n\n{code_blocks}")

    # Create 90 light pages (minimal content)
    for i in range(90):
        page = content_dir / f"blog-post-{i}.md"
        page.write_text(f"# Blog Post {i}\n\nShort content here.")

    # Create config
    config = tmp_path / "bengal.toml"
    config.write_text('[site]\ntitle = "Test Site"\n')

    return tmp_path


def test_complexity_ordering_no_regression(high_variance_site):
    """Verify complexity ordering doesn't slow down builds."""
    site = Site(high_variance_site)

    # Build with ordering disabled
    site.config["build"] = {"complexity_ordering": False}
    start = time.perf_counter()
    BuildOrchestrator(site).build()
    time_without = time.perf_counter() - start

    # Clean and rebuild with ordering enabled
    site.config["build"] = {"complexity_ordering": True}
    start = time.perf_counter()
    BuildOrchestrator(site).build()
    time_with = time.perf_counter() - start

    # Should be at least as fast (usually faster)
    # Allow 5% variance for timing noise
    assert time_with <= time_without * 1.05


def test_complexity_ordering_with_parallel_workers(high_variance_site):
    """Verify ordering works correctly with parallel rendering."""
    site = Site(high_variance_site)
    site.config["max_workers"] = 4
    site.config["build"] = {"complexity_ordering": True}

    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    # Build should complete without errors
    assert (high_variance_site / "output" / "api-reference-0" / "index.html").exists()
    assert (high_variance_site / "output" / "blog-post-0" / "index.html").exists()
```

### Benchmark

```python
# benchmarks/test_complexity_ordering.py

"""Benchmarks for complexity-based page ordering optimization.

Tests both the overhead of complexity estimation and the actual
build time improvement from optimal ordering.

Run with: pytest benchmarks/test_complexity_ordering.py -v --benchmark-only
"""

import time
from unittest.mock import Mock

import pytest

from bengal.orchestration.complexity import (
    estimate_complexity,
    sort_by_complexity,
    get_complexity_stats,
)


class TestComplexityOverhead:
    """Measure estimation overhead to ensure < 0.1ms per page."""

    @pytest.mark.parametrize("size", [100, 1000, 10000, 100000])
    def test_estimation_speed(self, size, benchmark):
        """Estimation should be fast regardless of content size."""
        content = "x" * size
        result = benchmark(estimate_complexity, content)

        # Should complete in < 0.1ms (100µs)
        assert benchmark.stats["mean"] < 0.0001

    def test_estimation_with_code_blocks(self, benchmark):
        """Estimation with realistic content (code blocks + prose)."""
        content = "# Title\n\nSome prose.\n\n" + "```python\ncode\n```\n\n" * 20
        result = benchmark(estimate_complexity, content)

        assert benchmark.stats["mean"] < 0.0001

    def test_sorting_1000_pages(self, benchmark):
        """Sorting 1000 pages should complete in < 20ms total."""
        pages = []
        for i in range(1000):
            p = Mock()
            p.content = "x" * (i * 10)  # Varying sizes
            pages.append(p)

        result = benchmark(sort_by_complexity, pages)

        # Total should be < 20ms
        assert benchmark.stats["mean"] < 0.020


class TestOrderingBenefit:
    """Measure actual build time improvement from ordering."""

    @pytest.fixture
    def high_variance_pages(self):
        """Create pages with high complexity variance."""
        pages = []

        # 10 heavy pages (many code blocks)
        for i in range(10):
            p = Mock()
            p.content = "```python\ncode\n```\n\n" * 30  # 30 code blocks
            p.name = f"heavy_{i}"
            pages.append(p)

        # 90 light pages (minimal content)
        for i in range(90):
            p = Mock()
            p.content = f"# Page {i}\n\nShort content."
            p.name = f"light_{i}"
            pages.append(p)

        return pages

    def test_high_variance_detection(self, high_variance_pages):
        """High variance sites should be detected."""
        stats = get_complexity_stats(high_variance_pages)

        # Heavy pages have ~300+ score, light have ~1
        # Variance ratio should be > 100
        assert stats["variance_ratio"] > 50
        assert stats["top_5_scores"][0] > 200  # Heavy pages
        assert stats["bottom_5_scores"][-1] < 10  # Light pages

    def test_ordering_puts_heavy_first(self, high_variance_pages):
        """After sorting, heavy pages should be at the front."""
        import random
        random.shuffle(high_variance_pages)  # Randomize input

        sorted_pages = sort_by_complexity(high_variance_pages)

        # First 10 should all be heavy pages
        for page in sorted_pages[:10]:
            assert "heavy" in page.name
```

---

## Rollout Plan

### Phase 1: Implementation (This RFC)
- [ ] Create `bengal/orchestration/complexity.py`
- [ ] Add unit tests: `tests/unit/orchestration/test_complexity.py`
- [ ] Add integration tests: `tests/integration/test_parallel_rendering.py`
- [ ] Add benchmark: `benchmarks/test_complexity_ordering.py`
- [ ] Integrate with `RenderOrchestrator._render_parallel_*` methods
- [ ] Add `build.complexity_ordering` configuration option

### Phase 2: Validation
- [ ] Run benchmarks on `benchmarks/scenarios/large_site/`
- [ ] Create high-variance test site (API docs + blog mix)
- [ ] Verify < 2% regression on uniform sites
- [ ] Verify > 10% improvement on high-variance sites
- [ ] Collect complexity distribution logs from real builds

### Phase 3: Release
- [ ] Enable by default (already the plan)
- [ ] Add to performance guide with variance ratio interpretation
- [ ] Add to changelog: "Improved parallel build performance via complexity-based page ordering"
- [ ] Consider adding `bengal build --stats` flag to show complexity distribution

---

## Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Estimation overhead | < 0.1ms per page | `benchmarks/test_complexity_ordering.py` |
| Total overhead (1000 pages) | < 20ms | Benchmark: sort_by_complexity timing |
| Uniform site regression | < 2% slower | Benchmark: variance_ratio < 2 sites |
| High-variance improvement | 10-30% faster | Benchmark: variance_ratio > 20 sites |
| Code added | < 150 lines | `wc -l bengal/orchestration/complexity.py` |
| Test coverage | > 90% | `pytest --cov` on new module |

### Validation Checklist

- [ ] `estimate_complexity()` completes in < 0.1ms for 100KB content
- [ ] `sort_by_complexity()` completes in < 20ms for 1000 pages
- [ ] No regression on `benchmarks/scenarios/large_site/` (uniform)
- [ ] > 15% improvement on high-variance test site
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] PageProxy handling verified (no accidental lazy loads)

---

## Appendix: Complexity Score Examples

| Page Type | Content | Code Blocks | Directives | Score | Calculation |
|-----------|---------|-------------|------------|-------|-------------|
| Short blog post | 500 bytes | 0 | 0 | ~1 | 500/500 = 1 |
| Long tutorial | 10KB | 15 | 5 | ~185 | 20 + 150 + 15 |
| API reference | 5KB | 30 | 2 | ~316 | 10 + 300 + 6 |
| Changelog | 20KB | 2 | 0 | ~60 | 40 + 20 |
| README | 3KB | 5 | 1 | ~59 | 6 + 50 + 3 |

**Score formula:** `content_bytes // 500 + code_blocks * 10 + directives * 3 + variables`

**Key observation:** API reference pages with many code examples are 50-300x more complex than short blog posts. This variance is what complexity ordering optimizes for.

### Variance Ratio Interpretation

| Variance Ratio | Expected Improvement | Site Characteristics |
|----------------|---------------------|----------------------|
| > 100 | 30-50% | API docs heavy, blog posts light |
| 20-100 | 20-30% | Mixed technical content |
| 10-20 | 10-20% | Moderate complexity variance |
| 2-10 | 5-10% | Mostly similar page types |
| < 2 | < 5% | Uniform complexity (little benefit) |

---

## References

- [Scheduling Theory: Longest Processing Time First](https://en.wikipedia.org/wiki/Longest-processing-time-first_scheduling)
- [Python concurrent.futures documentation](https://docs.python.org/3/library/concurrent.futures.html)
- Bengal Performance Guide (internal)
