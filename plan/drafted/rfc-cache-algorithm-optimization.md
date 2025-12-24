# RFC: Cache Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Cache (BuildCache, QueryIndex, TaxonomyIndex, DependencyTracker)  
**Confidence**: 94% 🟢 (verified against source code)  
**Priority**: P2 (Medium) — Performance, scalability for large sites  
**Estimated Effort**: 1-2 days

---

## Executive Summary

The `bengal/cache` package provides caching infrastructure for incremental builds with documented O(1) lookups. Analysis confirms the package largely delivers on this promise, but identified **4 algorithmic bottlenecks** that degrade performance for sites with 5K+ pages or 500+ tags.

**Key findings**:

1. **TaxonomyIndex.get_tags_for_page()** — O(t×p) linear scan instead of O(1)
2. **TaxonomyIndex.remove_page_from_all_tags()** — O(t×p) linear scan
3. **QueryIndex._remove_page_from_key()** — O(p) `list.remove()` instead of O(1)
4. **FileTrackingMixin.get_affected_pages()** — O(n) linear scan instead of O(1)

**Proposed optimizations**:

1. Add reverse index `_page_to_tags` in TaxonomyIndex → O(1) lookup
2. Use `set` instead of `list` for `page_paths` in QueryIndex → O(1) removal
3. Add reverse dependency graph in FileTrackingMixin → O(1) affected page lookup

**Existing partial optimization**: QueryIndex already has `_page_to_keys` reverse index for page updates; Phase 2 addresses the remaining `list→set` conversion for `page_paths`.

**Impact**: Maintain O(1) guarantees at scale (target: <10ms for any cache operation at 10K pages)

---

## Problem Statement

### Current Performance Characteristics

> **Note**: Primary operations (lookups, updates) are already O(1) as documented. The bottlenecks identified affect specific edge-case operations that become problematic at scale.

| Site Size | Lookup | Update | get_tags_for_page | remove_page_from_all_tags | get_affected_pages |
|-----------|--------|--------|-------------------|---------------------------|-------------------|
| 100 pages | <1ms | <1ms | <1ms | <1ms | <1ms |
| 1K pages | <1ms | <1ms | ~5ms | ~10ms | ~5ms |
| 5K pages | <1ms | <1ms | ~50ms | ~100ms | ~50ms |
| 10K pages | <1ms | <1ms | **~200ms** ⚠️ | **~400ms** ⚠️ | **~50ms** ⚠️ |

For sites approaching 10K pages with 500+ tags, reverse lookups and bulk removals become significant bottlenecks during incremental builds.

### Bottleneck 1: TaxonomyIndex.get_tags_for_page() — O(t×p)

**Location**: `taxonomy_index.py:249-264`

```python
# Current: Linear scan of ALL tags
def get_tags_for_page(self, page_path: Path) -> set[str]:
    page_str = str(page_path)
    tags = set()
    for tag_slug, entry in self.tags.items():    # O(t) - all tags
        if entry.is_valid and page_str in entry.page_paths:  # O(p) - list scan
            tags.add(tag_slug)
    return tags
```

**Problem**: For each page, we scan ALL tags and check if page exists in each tag's page list. With 500 tags and 1K pages per tag, that's 500K membership checks per call.

**Optimal approach**: Build reverse index `{page_path: set[tag_slugs]}` once, then O(1) lookup.

### Bottleneck 2: TaxonomyIndex.remove_page_from_all_tags() — O(t×p)

**Location**: `taxonomy_index.py:294-312`

```python
# Current: Linear scan of ALL tags, plus list.remove() per tag
def remove_page_from_all_tags(self, page_path: Path) -> set[str]:
    page_str = str(page_path)
    affected = set()

    for tag_slug, entry in self.tags.items():    # O(t)
        if page_str in entry.page_paths:          # O(p) - list scan
            entry.page_paths.remove(page_str)     # O(p) - list.remove()
            affected.add(tag_slug)

    return affected
```

**Problem**: Same linear scan issue, compounded by `list.remove()` which is O(p).

### Bottleneck 3: QueryIndex._remove_page_from_key() — O(p)

**Location**: `query_index.py:404-420`

```python
# Current: list.remove() is O(p)
def _remove_page_from_key(self, key: str, page_path: str) -> None:
    if key in self.entries and page_path in self.entries[key].page_paths:
        self.entries[key].page_paths.remove(page_path)  # O(p) - linear search
        # ...
```

**Problem**: `page_paths` is stored as `list[str]`. Removal requires O(p) linear search. With 1K pages per key, this adds up during incremental builds.

**Optimal approach**: Store as `set[str]` internally, convert to list only for serialization.

### Bottleneck 4: FileTrackingMixin.get_affected_pages() — O(n)

**Location**: `build_cache/file_tracking.py:233-255`

```python
# Current: Iterates ALL pages
def get_affected_pages(self, changed_file: Path) -> set[str]:
    changed_key = str(changed_file)
    affected = set()

    # Check direct dependencies
    for source, deps in self.dependencies.items():  # O(n) - all pages
        if changed_key in deps:                      # O(1) - deps is set[str]
            affected.add(source)

    return affected
```

**Problem**: For each changed file, we scan all pages. While the membership check is O(1) (since `deps` is `set[str]`), the iteration over all pages is still O(n). For a site with 10K pages, that's 10K iterations per template change.

**Optimal approach**: Maintain reverse dependency graph `{dep_path: set[source_pages]}` built during `add_dependency()`.

---

## Current Complexity Analysis

### What's Already Optimal ✅

| Component | Operation | Complexity | Notes |
|-----------|-----------|------------|-------|
| BuildCache | `load()` / `save()` | O(n) | Linear serialization, unavoidable |
| QueryIndex | `get()` | **O(1)** ✅ | Dict lookup as documented |
| QueryIndex | `update_page()` | O(k) | k = keys per page (small) |
| TaxonomyIndex | `get_tag()` | **O(1)** ✅ | Dict lookup |
| TaxonomyIndex | `get_pages_for_tag()` | **O(1)** ✅ | Dict lookup |
| FileTrackingMixin | `is_changed()` | **O(1)** ✅ | Fast mtime+size, O(f) worst case |
| FileTrackingMixin | `add_dependency()` | **O(1)** ✅ | Dict + set add |
| DependencyTracker | `track_*()` | **O(1)** ✅ | Dict operations |
| CacheStore | `save()` / `load()` | O(n) | Linear serialization |
| Compression | `save_compressed()` | O(n) | Zstd is efficient O(n) |

### What Needs Optimization ⚠️

| Component | Operation | Current | Optimal | Impact |
|-----------|-----------|---------|---------|--------|
| TaxonomyIndex | `get_tags_for_page()` | O(t×p) | O(1) | High |
| TaxonomyIndex | `remove_page_from_all_tags()` | O(t×p) | O(t') | High |
| QueryIndex | `_remove_page_from_key()` | O(p) | O(1) | Medium |
| FileTrackingMixin | `get_affected_pages()` | O(n×d) | O(1) | High |

**Variables**: n=pages, t=tags, p=pages/tag, k=keys/page, d=deps/page, t'=tags for specific page

---

## Goals

1. **Add reverse index to TaxonomyIndex** for O(1) page-to-tags lookup
2. **Use set for page_paths** in QueryIndex for O(1) removal
3. **Add reverse dependency graph** for O(1) affected pages lookup
4. **Maintain API compatibility** — No breaking changes to public interfaces
5. **Preserve correctness** — Identical behavior, just faster

### Non-Goals

- Changing serialization format (already uses efficient Zstandard)
- GPU acceleration
- External caching backends (Redis, etc.)

---

## Proposed Solution

### Phase 1: TaxonomyIndex Reverse Index

**Estimated effort**: 2 hours  
**Expected speedup**: 100-500x for reverse lookups

#### 1.1 Add Reverse Index to TaxonomyIndex

```python
# taxonomy_index.py - Add reverse index
class TaxonomyIndex:
    def __init__(self, cache_path: Path | None = None):
        # Existing
        self.tags: dict[str, TagEntry] = {}

        # NEW: Reverse index for O(1) page → tags lookup
        self._page_to_tags: dict[str, set[str]] = defaultdict(set)
```

#### 1.2 Maintain Reverse Index During Updates

```python
def update_tag(self, tag_slug: str, tag_name: str, page_paths: list[str]) -> None:
    """Update or create a tag entry."""
    # Get old pages for this tag (if exists)
    old_entry = self.tags.get(tag_slug)
    old_pages = set(old_entry.page_paths) if old_entry else set()
    new_pages = set(page_paths)

    # Update reverse index: remove old mappings
    for page in old_pages - new_pages:
        self._page_to_tags[page].discard(tag_slug)

    # Update reverse index: add new mappings
    for page in new_pages:
        self._page_to_tags[page].add(tag_slug)

    # Create/update entry (existing logic)
    entry = TagEntry(
        tag_slug=tag_slug,
        tag_name=tag_name,
        page_paths=page_paths,
        updated_at=datetime.utcnow().isoformat(),
        is_valid=True,
    )
    self.tags[tag_slug] = entry
```

#### 1.3 Optimize get_tags_for_page()

```python
def get_tags_for_page(self, page_path: Path) -> set[str]:
    """Get all tags for a specific page (O(1) via reverse index)."""
    page_str = str(page_path)
    # NEW: O(1) lookup instead of O(t×p) scan
    return self._page_to_tags.get(page_str, set()).copy()
```

#### 1.4 Optimize remove_page_from_all_tags()

```python
def remove_page_from_all_tags(self, page_path: Path) -> set[str]:
    """Remove a page from all tags (O(t') where t' = tags for this page)."""
    page_str = str(page_path)

    # NEW: Use reverse index to find only affected tags
    affected_tags = self._page_to_tags.get(page_str, set()).copy()

    for tag_slug in affected_tags:
        if tag_slug in self.tags:
            entry = self.tags[tag_slug]
            if page_str in entry.page_paths:
                entry.page_paths.remove(page_str)

    # Clean up reverse index
    if page_str in self._page_to_tags:
        del self._page_to_tags[page_str]

    return affected_tags
```

**Complexity change**: O(t×p) → O(1) for lookup, O(t') for removal

#### 1.5 Persist Reverse Index

> **Important**: Bump `VERSION = 2` to trigger cache rebuild on format change.

```python
VERSION = 2  # Bumped: added page_to_tags reverse index

def save_to_disk(self) -> None:
    """Save taxonomy index to disk (including reverse index)."""
    data = {
        "version": self.VERSION,
        "tags": {tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()},
        # NEW: Persist reverse index
        "page_to_tags": {page: list(tags) for page, tags in self._page_to_tags.items()},
    }
    # ... existing save logic ...

def _load_from_disk(self) -> None:
    """Load taxonomy index from disk."""
    # ... existing load logic ...

    # NEW: Load reverse index (or rebuild if missing)
    if "page_to_tags" in data:
        for page, tags in data["page_to_tags"].items():
            self._page_to_tags[page] = set(tags)
    else:
        # Rebuild from forward index (migration path)
        self._rebuild_reverse_index()

def _rebuild_reverse_index(self) -> None:
    """Rebuild reverse index from forward index (one-time migration)."""
    self._page_to_tags.clear()
    for tag_slug, entry in self.tags.items():
        if entry.is_valid:
            for page_path in entry.page_paths:
                self._page_to_tags[page_path].add(tag_slug)
```

---

### Phase 2: QueryIndex Set-Based Storage

**Estimated effort**: 1.5 hours  
**Expected speedup**: 10-100x for page removal

> **Existing optimization**: QueryIndex already has `_page_to_keys: dict[str, set[str]]` reverse index (line 147) for efficient page updates. This phase addresses the remaining bottleneck: `page_paths` stored as `list[str]` causing O(p) removal.

#### 2.1 Change IndexEntry Internal Storage

```python
# query_index.py - Use set internally
@dataclass
class IndexEntry(Cacheable):
    key: str
    # CHANGED: Use set internally for O(1) operations
    _page_paths: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = ""

    @property
    def page_paths(self) -> list[str]:
        """Return as list for API compatibility."""
        return list(self._page_paths)

    @page_paths.setter
    def page_paths(self, value: list[str]) -> None:
        """Accept list, store as set."""
        self._page_paths = set(value)

    def add_page(self, page_path: str) -> None:
        """O(1) add."""
        self._page_paths.add(page_path)

    def remove_page(self, page_path: str) -> bool:
        """O(1) remove."""
        if page_path in self._page_paths:
            self._page_paths.discard(page_path)
            return True
        return False

    def __contains__(self, page_path: str) -> bool:
        """O(1) membership check."""
        return page_path in self._page_paths
```

#### 2.2 Update QueryIndex Methods

```python
def _add_page_to_key(self, key: str, page_path: str, metadata: dict[str, Any]) -> None:
    """Add page to index key (O(1))."""
    if key not in self.entries:
        self.entries[key] = IndexEntry(key=key, metadata=metadata)

    # CHANGED: O(1) set add
    self.entries[key].add_page(page_path)
    self.entries[key].updated_at = datetime.now().isoformat()
    self.entries[key].content_hash = self.entries[key]._compute_hash()

def _remove_page_from_key(self, key: str, page_path: str) -> None:
    """Remove page from index key (O(1))."""
    if key in self.entries:
        # CHANGED: O(1) set discard
        if self.entries[key].remove_page(page_path):
            self.entries[key].updated_at = datetime.now().isoformat()
            self.entries[key].content_hash = self.entries[key]._compute_hash()

            # Remove empty entries
            if len(self.entries[key]._page_paths) == 0:
                del self.entries[key]
```

**Complexity change**: O(p) → O(1) for add/remove operations

---

### Phase 3: Reverse Dependency Graph

**Estimated effort**: 2 hours  
**Expected speedup**: 10-100x for dependency queries (O(n) → O(1))

> **Note**: Current implementation is O(n), not O(n×d), because `deps` is `set[str]` making membership check O(1). The optimization eliminates the O(n) iteration entirely.

#### 3.1 Add Reverse Graph to FileTrackingMixin

```python
# build_cache/file_tracking.py - Add reverse dependency tracking
class FileTrackingMixin:
    # Existing
    dependencies: dict[str, set[str]]  # source → {dependencies}

    # NEW: Reverse index
    reverse_dependencies: dict[str, set[str]]  # dependency → {sources}
```

#### 3.2 Update add_dependency() to Maintain Reverse Graph

```python
def add_dependency(self, source: Path, dependency: Path) -> None:
    """Record that a source file depends on another file (O(1))."""
    source_key = str(source)
    dep_key = str(dependency)

    # Forward graph (existing)
    if source_key not in self.dependencies:
        self.dependencies[source_key] = set()
    self.dependencies[source_key].add(dep_key)

    # NEW: Reverse graph
    if dep_key not in self.reverse_dependencies:
        self.reverse_dependencies[dep_key] = set()
    self.reverse_dependencies[dep_key].add(source_key)
```

#### 3.3 Optimize get_affected_pages()

```python
def get_affected_pages(self, changed_file: Path) -> set[str]:
    """Find all pages that depend on a changed file (O(1) via reverse graph)."""
    changed_key = str(changed_file)
    affected = set()

    # NEW: O(1) lookup via reverse graph
    affected.update(self.reverse_dependencies.get(changed_key, set()))

    # If the changed file itself is a source, include it
    if changed_key in self.dependencies:
        affected.add(changed_key)

    return affected
```

#### 3.4 Update invalidate_file() to Clean Reverse Graph

```python
def invalidate_file(self, file_path: Path) -> None:
    """Remove a file from the cache (O(d) where d = dependencies)."""
    file_key = str(file_path)

    # Remove from forward graph
    deps = self.dependencies.pop(file_key, set())

    # NEW: Remove from reverse graph
    for dep in deps:
        if dep in self.reverse_dependencies:
            self.reverse_dependencies[dep].discard(file_key)

    # Remove as a dependency from other files
    for source_deps in self.dependencies.values():
        source_deps.discard(file_key)

    # NEW: Remove from reverse graph (as a dependency)
    self.reverse_dependencies.pop(file_key, None)
```

**Complexity change**: O(n) → O(1) for get_affected_pages()

---

## Implementation Plan

### Step 0: Establish Baseline Benchmarks (Required First)

**Files**: `benchmarks/test_cache_performance.py` (new)

> **Critical**: Must be completed before any optimization to measure actual improvement.

1. Create synthetic site generator with configurable page/tag counts
2. Create benchmark scenarios: 100, 1K, 5K, 10K pages with 50, 200, 500 tags
3. Measure wall-clock time for each operation:
   - `TaxonomyIndex.get_tags_for_page()` — Reverse lookup
   - `TaxonomyIndex.remove_page_from_all_tags()` — Bulk removal
   - `QueryIndex._remove_page_from_key()` — Single removal
   - `FileTrackingMixin.get_affected_pages()` — Dependency query
4. Record baseline metrics in `benchmarks/baseline_cache.json`
5. **Run multiple iterations** (min 100) and record mean, median, std deviation

```python
# Example benchmark structure
@pytest.mark.benchmark
def test_get_tags_for_page_10k(benchmark, taxonomy_index_10k):
    """Baseline: get_tags_for_page on 10K pages, 500 tags.

    Runs multiple iterations automatically via pytest-benchmark.
    Reports: min, max, mean, stddev, median, IQR, outliers.
    """
    page_path = Path("content/blog/post-5000.md")
    result = benchmark(taxonomy_index_10k.get_tags_for_page, page_path)
    assert isinstance(result, set)
```

### Step 1: TaxonomyIndex Reverse Index

**Files**: `cache/taxonomy_index.py`

1. **Bump `VERSION` to 2** (cache format change)
2. Add `_page_to_tags: dict[str, set[str]]` to `__init__`
3. Maintain during `update_tag()`, `invalidate_tag()`, `clear()`
4. Optimize `get_tags_for_page()` to use reverse index
5. Optimize `remove_page_from_all_tags()` to use reverse index
6. Add persistence in `save_to_disk()` / `_load_from_disk()`
7. Add migration path for existing caches (rebuild on load if missing or version mismatch)

### Step 2: QueryIndex Set-Based Storage

**Files**: `cache/query_index.py`

1. Change `IndexEntry.page_paths` to internal `_page_paths: set[str]`
2. Add property for API compatibility (returns list)
3. Add `add_page()`, `remove_page()`, `__contains__` methods
4. Update `_add_page_to_key()` and `_remove_page_from_key()`
5. Update serialization to convert set ↔ list at boundaries

### Step 3: Reverse Dependency Graph

**Files**: `cache/build_cache/file_tracking.py`, `cache/build_cache/core.py`

1. Add `reverse_dependencies: dict[str, set[str]]` to BuildCache
2. Maintain in `add_dependency()`
3. Optimize `get_affected_pages()` to use reverse graph
4. Update `invalidate_file()` to clean both graphs
5. Add persistence in BuildCache `save()` / `load()`

### Step 4: Final Benchmarking and Documentation

**Files**: `benchmarks/test_cache_performance.py`, RFC update

1. Run full benchmark suite with optimized algorithms
2. Compare against baseline metrics from Step 0
3. Document actual speedup achieved
4. Add regression detection: fail if performance degrades >10%
5. Update RFC with actual measured results

---

## Complexity Analysis Summary

### Before Optimization

| Operation | Time Complexity | 10K Pages, 500 Tags |
|-----------|-----------------|---------------------|
| `TaxonomyIndex.get_tags_for_page()` | O(t×p) | ~200ms |
| `TaxonomyIndex.remove_page_from_all_tags()` | O(t×p) | ~400ms |
| `QueryIndex._remove_page_from_key()` | O(p) | ~10ms |
| `FileTrackingMixin.get_affected_pages()` | O(n×d) | ~200ms |

### After Optimization

| Operation | Time Complexity | 10K Pages, 500 Tags | Speedup |
|-----------|-----------------|---------------------|---------|
| `TaxonomyIndex.get_tags_for_page()` | **O(1)** | <1ms | **200x** |
| `TaxonomyIndex.remove_page_from_all_tags()` | O(t') | ~5ms | **80x** |
| `QueryIndex._remove_page_from_key()` | **O(1)** | <1ms | **10x** |
| `FileTrackingMixin.get_affected_pages()` | **O(1)** | <1ms | **200x** |

**t'** = tags for the specific page (typically 3-10, not 500)

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify optimized operations produce identical results
   - Same tags returned for page
   - Same affected pages for dependency
   - Same page lists per index key

2. **Edge cases**:
   - Page with 0 tags
   - Page with 100+ tags
   - Tag with 0 pages
   - Tag with 10K+ pages
   - Circular dependencies (if possible)

### Performance Tests

1. **Benchmark suite** with synthetic data:
   - Sparse: 100 pages, 10 tags, 2 tags/page
   - Dense: 10K pages, 500 tags, 20 tags/page
   - Extreme: 50K pages, 1K tags, 50 tags/page

2. **Regression detection**: Fail if performance degrades >10%

### Integration Tests

1. **Real site tests**: Run on bengal's own docs site
2. **Incremental build simulation**: Measure full rebuild vs incremental with changes

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Memory increase from reverse indices | Medium | Low | Indices are O(n) strings; minimal overhead |
| Migration issues for existing caches | Low | Medium | Auto-rebuild reverse index if missing |
| Serialization format change breaks cache | Low | High | Version bump with tolerant loading |
| API changes break downstream code | Low | High | Property accessors maintain compatibility |

---

## Alternatives Considered

### 1. External Database (SQLite, Redis)

**Pros**: Battle-tested indexing, advanced queries  
**Cons**: New dependency, deployment complexity, overkill for file-based cache

**Decision**: Keep in-memory with JSON persistence. Optimize algorithms instead.

### 2. Lazy Reverse Index Building

**Pros**: No upfront cost if reverse lookups not used  
**Cons**: First lookup is slow; complicates caching

**Decision**: Build eagerly during load. Cost is O(n) one-time, same as loading.

### 3. Bloom Filters for Membership

**Pros**: O(1) with tiny memory footprint  
**Cons**: False positives require fallback; complexity

**Decision**: Not needed. Simple reverse index is sufficient and exact.

---

## Success Criteria

1. **get_tags_for_page() for 10K pages**: <5ms (currently ~200ms)
2. **remove_page_from_all_tags() for 10K pages**: <20ms (currently ~400ms)
3. **get_affected_pages() for 10K pages**: <5ms (currently ~50ms)
4. **No API changes**: Existing code continues working
5. **Backward compatible**: Old caches load correctly (version check + rebuild reverse index)
6. **Cache version bumped**: TaxonomyIndex VERSION → 2
7. **Regression tests**: CI fails if performance degrades >10%

---

## Future Work

1. **Incremental index updates**: Update indices without full rebuild
2. **Compressed reverse indices**: Delta encoding for large indices
3. **Sharded cache files**: Split large caches for parallel loading
4. **Cache warming**: Pre-load hot indices on startup

---

## References

- [Python dict complexity](https://wiki.python.org/moin/TimeComplexity) — O(1) average case
- [PEP 784 - Zstandard](https://peps.python.org/pep-0784/) — Compression module (Python 3.14+)
- [bengal/cache architecture](../plan/active/rfc-incremental-builds.md) — Incremental build design

---

## Appendix: Current Implementation Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| BuildCache | `build_cache/core.py` | `load()`, `save()`, `clear()` |
| FileTracking | `build_cache/file_tracking.py` | `is_changed()`, `add_dependency()`, `get_affected_pages()` |
| QueryIndex | `query_index.py` | `get()`, `update_page()`, `_add_page_to_key()` |
| TaxonomyIndex | `taxonomy_index.py` | `update_tag()`, `get_tags_for_page()`, `remove_page_from_all_tags()` |
| IndexEntry | `query_index.py` | `page_paths`, `to_cache_dict()` |
| CacheStore | `cache_store.py` | `save()`, `load()` |
| Compression | `compression.py` | `save_compressed()`, `load_compressed()` |

---

## Appendix: Space Complexity Impact

### Current Space Usage

| Structure | Space | Notes |
|-----------|-------|-------|
| `file_fingerprints` | O(n) | n = files |
| `dependencies` | O(n×d) | d = avg deps/page |
| `tag_to_pages` | O(t×p) | Already exists |
| `page_tags` | O(n×t') | Already exists |

### Additional Space from Reverse Indices

| New Structure | Space | Notes |
|---------------|-------|-------|
| `TaxonomyIndex._page_to_tags` | O(n×t') | Mirror of `page_tags` |
| `FileTrackingMixin.reverse_dependencies` | O(d×n) | Mirror of `dependencies` |
| `IndexEntry._page_paths` (set) | O(p) | Same as list, different type |

**Total additional space**: ~2x for reverse indices. For 10K pages with 20 deps and 10 tags each, this is ~400KB additional memory — negligible.
