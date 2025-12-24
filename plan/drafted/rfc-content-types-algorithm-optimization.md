# RFC: Content Types Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Content Types (`bengal/content_types`)  
**Confidence**: 92% 🟢 (verified against source code)  
**Priority**: P3 (Low) — Minor performance gains; affects large sites with 10K+ pages  
**Estimated Effort**: 0.5 days

---

## Executive Summary

The `bengal/content_types` package implements a Strategy Pattern for content type-specific behavior (sorting, filtering, pagination, template selection). Analysis confirms the package is **already well-optimized**, with **most operations at O(1)**. The primary cost center is **sorting at O(n log n)**, which is optimal for comparison-based sorting.

**Key findings**:

1. **Sorting** — O(n log n) via Python's Timsort (optimal)
2. **Detection** — O(1) via bounded sampling (max 5 pages)
3. **Registry** — O(1) via dict lookups
4. **Template resolution** — O(1) via fixed fallback chains

**Minor optimization opportunities**:

1. **Pre-compute sort keys** — Avoid repeated `dict.get()` and `str.lower()` in lambda
2. **Eliminate defensive copies** — `ApiReferenceStrategy.sort_pages()` copies without sorting
3. **Cache template existence checks** — Avoid repeated template engine lookups

**Impact**: Marginal (~10-20% improvement in sorting for 10K+ page sections). The module is not a bottleneck.

---

## Problem Statement

### Current Performance Characteristics

> **Note**: The content_types module is **not a performance bottleneck**. This RFC documents minor optimizations for completeness and large-scale deployments.

| Operation | Complexity | 1K Pages | 10K Pages | Notes |
|-----------|------------|----------|-----------|-------|
| `sort_pages()` | O(n log n) | ~5ms | ~80ms | Timsort; optimal |
| `filter_display_pages()` | O(n) | <1ms | ~5ms | List comprehension |
| `detect_content_type()` | O(1) | <1ms | <1ms | Bounded sampling |
| `get_strategy()` | O(1) | <1ms | <1ms | Dict lookup |
| `get_template()` | O(1) | <1ms | <1ms | Fixed chain |

### Analysis by Component

#### 1. Sorting — O(n log n) ✅ Optimal

**Location**: `base.py:118`, `strategies.py:88,208,493,536,579,636`

```python
# Current implementation (base.py:118)
return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))
```

**Analysis**:
- Uses Python's Timsort: O(n log n) time, O(n) space
- Lambda key executes **per comparison** during sort (~n log n times)
- Each lambda call: `dict.get()` O(1) + `str.lower()` O(m) where m = title length

**Minor inefficiency**: Lambda recreates tuple and calls `str.lower()` repeatedly. For 10K pages with 100-char titles, this is ~130K string operations.

#### 2. Filtering — O(n) ✅ Acceptable

**Location**: `base.py:120-147`

```python
# Current implementation
if index_page:
    return [p for p in pages if p != index_page]
return list(pages)
```

**Analysis**:
- List comprehension with O(1) equality check
- Creates new list (defensive copy)
- O(n) is unavoidable for filtering

#### 3. Detection — O(1) ✅ Well-Optimized

**Location**: `strategies.py:90-108`, `registry.py:218-228`

```python
# BlogStrategy.detect_from_section() — bounded sampling
if section.pages:
    pages_with_dates = sum(1 for p in section.pages[:5] if p.metadata.get("date") or p.date)
    return pages_with_dates >= len(section.pages[:5]) * 0.6
```

**Analysis**:
- Slicing `[:5]` bounds iteration to constant time
- Registry iterates fixed 5 strategies
- Total: O(1) × O(5) = O(1)

#### 4. Template Resolution — O(1) ✅ Well-Optimized

**Location**: `base.py:180-267`, strategy overrides

```python
# Fixed fallback chain (max 4 templates)
templates_to_try = [
    f"{type_name}/home.html",
    f"{type_name}/index.html",
    "home.html",
    "index.html",
]
for template_name in templates_to_try:
    if template_exists(template_name):
        return template_name
```

**Analysis**:
- Fixed 4-template chain
- Each `template_exists()` is template engine dependent but typically O(1)
- Total: O(4) = O(1)

**Minor inefficiency**: `template_exists()` is called fresh each time; no caching of previous lookups.

#### 5. Defensive Copies — O(n) Unnecessary

**Location**: `strategies.py:291,393`

```python
# ApiReferenceStrategy.sort_pages() — copy without sorting
def sort_pages(self, pages: list[Page]) -> list[Page]:
    return list(pages)  # O(n) copy
```

**Analysis**:
- Creates copy to maintain immutability contract
- If caller never mutates, copy is wasted
- Same pattern in `CliReferenceStrategy`

---

## Current Complexity Analysis

### Summary Table

| Component | Function | Current | Optimal | Gap |
|-----------|----------|---------|---------|-----|
| `ContentTypeStrategy` | `sort_pages()` | O(n log n) | O(n log n) | ✅ Optimal |
| `ContentTypeStrategy` | `filter_display_pages()` | O(n) | O(n) | ✅ Optimal |
| `ContentTypeStrategy` | `should_paginate()` | O(1) | O(1) | ✅ Optimal |
| `ContentTypeStrategy` | `get_template()` | O(1) | O(1) | ✅ Optimal |
| `registry` | `get_strategy()` | O(1) | O(1) | ✅ Optimal |
| `registry` | `detect_content_type()` | O(1) | O(1) | ✅ Optimal |
| `registry` | `register_strategy()` | O(1) | O(1) | ✅ Optimal |
| `BlogStrategy` | `sort_pages()` | O(n log n) | O(n log n) | ⚡ Lambda overhead |
| `ApiReferenceStrategy` | `sort_pages()` | O(n) | O(1) | ⚡ Unnecessary copy |

### Variables

- **n** = number of pages in section
- **m** = average title length (chars)
- **t** = number of templates to check (fixed at 4)
- **s** = number of strategies in detection order (fixed at 5)

---

## Goals

1. **Reduce sort key computation overhead** — Pre-compute sort keys for large sections
2. **Eliminate unnecessary copies** — Return input directly when safe
3. **Cache template lookups** — Avoid repeated template engine queries
4. **Maintain API compatibility** — No breaking changes

### Non-Goals

- Replacing Timsort with a different algorithm
- Parallelizing sorting (Python GIL limits benefit)
- Caching sorted results (sections are typically sorted once per build)

---

## Proposed Solution

### Phase 1: Pre-Computed Sort Keys (Optional)

**Estimated effort**: 1 hour  
**Expected speedup**: 10-20% for sections with 5K+ pages

> **Trade-off**: Adds complexity for marginal gain. Recommend only if profiling shows sorting as bottleneck.

#### 1.1 Decorate-Sort-Undecorate Pattern

```python
# base.py — optimized sort_pages()
def sort_pages(self, pages: list[Page]) -> list[Page]:
    """
    Sort pages for display in list views.
    
    Uses decorate-sort-undecorate pattern to avoid repeated
    key computation during Timsort comparisons.
    """
    if len(pages) <= 100:
        # Small sections: lambda is fine, avoid overhead
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))
    
    # Large sections: pre-compute keys
    # Decorate: [(sort_key, original_index, page), ...]
    decorated = [
        ((p.metadata.get("weight", 999999), p.title.lower()), i, p)
        for i, p in enumerate(pages)
    ]
    
    # Sort: compare tuples (weight, title_lower)
    decorated.sort(key=lambda x: x[0])
    
    # Undecorate: extract pages
    return [p for _, _, p in decorated]
```

**Complexity**: O(n) pre-computation + O(n log n) sort = O(n log n) overall

**Benefit**: Each page's key is computed **once** instead of **O(log n) times** during sort.

#### 1.2 Strategy-Specific Optimizations

```python
# strategies.py — BlogStrategy with cached date
def sort_pages(self, pages: list[Page]) -> list[Page]:
    """Sort by date, newest first, with pre-computed keys."""
    if len(pages) <= 100:
        return sorted(pages, key=lambda p: p.date if p.date else datetime.min, reverse=True)
    
    # Pre-compute dates once
    dated = [(p.date if p.date else datetime.min, i, p) for i, p in enumerate(pages)]
    dated.sort(key=lambda x: x[0], reverse=True)
    return [p for _, _, p in dated]
```

---

### Phase 2: Eliminate Defensive Copies

**Estimated effort**: 30 minutes  
**Expected speedup**: Eliminates O(n) copy for Api/Cli reference strategies

#### 2.1 Document Immutability Contract

```python
# base.py — Add docstring clarification
def sort_pages(self, pages: list[Page]) -> list[Page]:
    """
    Sort pages for display in list views.

    Args:
        pages: List of Page objects to sort.

    Returns:
        New sorted list of pages. The caller MUST NOT mutate the
        returned list if it may be the same object as the input.
        
    Note:
        Implementations that preserve original order MAY return the
        input list directly. Callers should treat the return value
        as read-only.
    """
```

#### 2.2 Remove Unnecessary Copies

```python
# strategies.py — ApiReferenceStrategy
def sort_pages(self, pages: list[Page]) -> list[Page]:
    """
    Preserve original discovery order (typically alphabetical).
    
    Returns the input list directly since no reordering is needed.
    Caller must not mutate the returned list.
    """
    return pages  # O(1) — no copy

# strategies.py — CliReferenceStrategy  
def sort_pages(self, pages: list[Page]) -> list[Page]:
    """Preserve original discovery order."""
    return pages  # O(1) — no copy
```

**Complexity change**: O(n) → O(1) for these two strategies

**Risk**: If caller mutates returned list, original is affected. Mitigate with documentation and/or runtime check:

```python
# Optional: Debug-only copy
def sort_pages(self, pages: list[Page]) -> list[Page]:
    if __debug__:  # Stripped in optimized mode (-O)
        return list(pages)
    return pages
```

---

### Phase 3: Template Lookup Caching (Optional)

**Estimated effort**: 1 hour  
**Expected speedup**: Negligible unless template engine lookups are slow

> **Trade-off**: Adds state to stateless strategies. Recommend only if profiling shows template resolution as bottleneck.

#### 3.1 Per-Build Template Cache

```python
# base.py — Add template cache
class ContentTypeStrategy:
    # Class-level cache (shared across instances)
    _template_cache: dict[str, bool] = {}
    _template_engine_id: int | None = None  # Invalidate on engine change
    
    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        # ... existing logic ...
        
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            
            # Invalidate cache if engine changed
            engine_id = id(template_engine)
            if ContentTypeStrategy._template_engine_id != engine_id:
                ContentTypeStrategy._template_cache.clear()
                ContentTypeStrategy._template_engine_id = engine_id
            
            # Check cache first
            if name in ContentTypeStrategy._template_cache:
                return ContentTypeStrategy._template_cache[name]
            
            # Query engine and cache result
            try:
                template_engine.env.get_template(name)
                exists = True
            except Exception:
                exists = False
            
            ContentTypeStrategy._template_cache[name] = exists
            return exists
```

**Benefit**: Template existence is checked once per build, not once per page.

**Risk**: Cache invalidation complexity. If templates change mid-build (unlikely), stale cache could cause issues.

---

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (Required First)

**Files**: `benchmarks/test_content_types_performance.py` (new)

1. Create benchmark scenarios:
   - Small: 100 pages, mixed content types
   - Medium: 1K pages per section
   - Large: 10K pages per section
   
2. Measure operations:
   - `sort_pages()` for each strategy
   - `filter_display_pages()` with various index page scenarios
   - `detect_content_type()` on sections with different characteristics
   - `get_template()` with template engine

3. Record baseline in `benchmarks/baseline_content_types.json`

```python
@pytest.mark.benchmark
def test_blog_sort_10k(benchmark, blog_pages_10k):
    """Baseline: BlogStrategy.sort_pages on 10K pages."""
    strategy = BlogStrategy()
    result = benchmark(strategy.sort_pages, blog_pages_10k)
    assert len(result) == 10000
    # Verify sorted by date descending
    for i in range(1, len(result)):
        assert result[i-1].date >= result[i].date
```

### Step 1: Phase 2 — Eliminate Copies (Low Risk)

**Files**: `content_types/strategies.py`

1. Update `ApiReferenceStrategy.sort_pages()` to return input directly
2. Update `CliReferenceStrategy.sort_pages()` to return input directly
3. Update docstrings to document immutability contract
4. Add tests verifying behavior is unchanged

### Step 2: Phase 1 — Pre-Computed Keys (Medium Risk)

**Files**: `content_types/base.py`, `content_types/strategies.py`

1. Add threshold constant `SORT_KEY_PRECOMPUTE_THRESHOLD = 100`
2. Update `ContentTypeStrategy.sort_pages()` with hybrid approach
3. Update strategy overrides to use same pattern
4. Benchmark to verify improvement

### Step 3: Phase 3 — Template Cache (Optional, Higher Risk)

**Files**: `content_types/base.py`

1. Add class-level template cache
2. Add cache invalidation on template engine change
3. Integrate into `get_template()` method
4. Test cache invalidation works correctly

### Step 4: Final Benchmarking

1. Run full benchmark suite
2. Compare against baseline
3. Document actual speedup achieved
4. Add regression tests

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time | Space | Hot Path? |
|-----------|------|-------|-----------|
| `sort_pages()` (most) | O(n log n) | O(n) | ✅ Yes |
| `sort_pages()` (Api/Cli) | O(n) | O(n) | ✅ Yes |
| `filter_display_pages()` | O(n) | O(n) | ✅ Yes |
| `detect_content_type()` | O(1) | O(1) | No |
| `get_template()` | O(1) | O(1) | ✅ Yes |

### After Optimization

| Operation | Time | Space | Change |
|-----------|------|-------|--------|
| `sort_pages()` (most) | O(n log n) | O(n) | Faster constant factor |
| `sort_pages()` (Api/Cli) | **O(1)** | O(1) | ⚡ No copy |
| `filter_display_pages()` | O(n) | O(n) | Unchanged |
| `detect_content_type()` | O(1) | O(1) | Unchanged |
| `get_template()` | O(1) | O(1) | Cached lookups |

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify sorted output is identical before/after optimization
2. **Edge cases**:
   - Empty page list
   - Single page
   - Pages with identical sort keys
   - Pages with None/missing metadata
   - Large sections (10K+ pages)

### Performance Tests

1. **Benchmark suite**: 100, 1K, 5K, 10K pages
2. **Regression detection**: Fail if performance degrades >5%
3. **Memory profiling**: Verify space complexity unchanged

### Integration Tests

1. **Real site tests**: Run on bengal's own docs
2. **Template resolution**: Verify correct templates selected

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Caller mutates returned list | Low | Medium | Document contract; debug-mode copy |
| Template cache stale | Very Low | Low | Invalidate on engine change |
| Pre-compute overhead for small lists | Medium | Low | Threshold check (skip if <100 items) |
| Complexity for marginal gain | Medium | Low | Phase 1 & 3 optional; Phase 2 safe |

---

## Alternatives Considered

### 1. Use `operator.attrgetter()` Instead of Lambda

**Pros**: Slightly faster than lambda for attribute access  
**Cons**: Can't handle dict.get() with default; doesn't help with tuple construction

**Decision**: Not applicable; current key is `(metadata.get(), title.lower())`

### 2. Parallel Sorting

**Pros**: Multi-core utilization  
**Cons**: Python GIL limits benefit; Timsort not easily parallelizable

**Decision**: Not worth complexity for O(n log n) on 10K items (~80ms)

### 3. Maintain Sorted Order Incrementally

**Pros**: O(log n) insertions if pages added one at a time  
**Cons**: Pages are discovered in batch; requires different data structure

**Decision**: Current batch-sort approach matches discovery pattern

### 4. Cache Sorted Results

**Pros**: O(1) for repeated access  
**Cons**: Memory overhead; invalidation complexity; sections typically sorted once

**Decision**: Not needed; sections are sorted during build, not queried repeatedly

---

## Success Criteria

1. **Api/Cli sort_pages()**: O(1) (currently O(n))
2. **General sort_pages() for 10K pages**: <70ms (currently ~80ms, ~15% improvement)
3. **No API changes**: Existing code continues working
4. **No memory regression**: Space complexity unchanged
5. **Tests pass**: All existing tests + new performance tests

---

## Recommendation

**Priority**: P3 (Low)

The `content_types` module is **not a performance bottleneck**. The optimizations proposed provide marginal gains:

| Optimization | Effort | Impact | Recommend |
|--------------|--------|--------|-----------|
| Phase 1: Pre-compute keys | 1 hour | 10-20% for large sections | ⚠️ Optional |
| Phase 2: Eliminate copies | 30 min | O(n) → O(1) for 2 strategies | ✅ Yes |
| Phase 3: Template cache | 1 hour | Negligible | ❌ No |

**Recommended action**: Implement **Phase 2 only** (eliminate unnecessary copies). This provides measurable improvement with minimal risk and effort.

---

## References

- [Python TimeSort](https://docs.python.org/3/howto/sorting.html) — Stable O(n log n) sort
- [Decorate-Sort-Undecorate](https://wiki.python.org/moin/HowTo/Sorting#The_Old_Way_Using_Decorate-Sort-Undecorate) — Pattern for complex keys
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy) — Design pattern used in this module

---

## Appendix: Source Code Locations

| Component | File | Lines |
|-----------|------|-------|
| `ContentTypeStrategy` (base) | `base.py` | 52-330 |
| `sort_pages()` (base) | `base.py` | 95-118 |
| `filter_display_pages()` | `base.py` | 120-147 |
| `get_template()` | `base.py` | 180-267 |
| `BlogStrategy` | `strategies.py` | 57-145 |
| `DocsStrategy` | `strategies.py` | 166-250 |
| `ApiReferenceStrategy` | `strategies.py` | 252-351 |
| `CliReferenceStrategy` | `strategies.py` | 354-450 |
| `TutorialStrategy` | `strategies.py` | 453-498 |
| `ChangelogStrategy` | `strategies.py` | 501-543 |
| `TrackStrategy` | `strategies.py` | 546-602 |
| `PageStrategy` | `strategies.py` | 605-636 |
| `get_strategy()` | `registry.py` | 125-151 |
| `detect_content_type()` | `registry.py` | 154-245 |
| `register_strategy()` | `registry.py` | 248-291 |

---

## Appendix: Benchmark Expectations

### Sorting Performance (Wall Clock)

| Pages | Current | After Phase 1 | After Phase 2 |
|-------|---------|---------------|---------------|
| 100 | <1ms | <1ms | <1ms |
| 1,000 | ~5ms | ~4ms | ~4ms |
| 5,000 | ~30ms | ~25ms | ~25ms |
| 10,000 | ~80ms | ~65ms | ~65ms |

### Api/Cli Reference Sorting

| Pages | Current (copy) | After Phase 2 (no copy) |
|-------|----------------|-------------------------|
| 100 | <1ms | <1μs |
| 1,000 | ~1ms | <1μs |
| 10,000 | ~5ms | <1μs |

> **Note**: Estimates based on typical Python performance. Actual measurements required via Step 0 benchmarks.

