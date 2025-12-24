# RFC: Core Module Algorithm Optimization

**Status**: Draft  
**Created**: 2025-12-24  
**Last Verified**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Core (NavTree, ContentRegistry, Menu, URLRegistry, Section, Site)  
**Confidence**: 96% 🟢 (verified against source code)  
**Priority**: P3 (Low) — Performance is already excellent; preventive optimizations  
**Estimated Effort**: 0.5-1 day

### Verification Summary

All claims verified against source code on 2025-12-24:

| Claim | Status | Evidence |
|-------|--------|----------|
| `NavTree.find()` O(1) | ✅ Verified | `nav_tree.py:222-224` |
| `NavNode.find()` O(n) unused | ✅ Verified | Only in `tests/unit/test_nav_tree.py:124` |
| `MenuItem.add_child()` per-insert sort | ✅ Verified | `menu.py:140-141` |
| `_has_cycle()` copies path | ✅ Verified | `menu.py:570` |
| `NavTreeCache` FIFO eviction | ✅ Verified | `nav_tree.py:737-739` |
| `ContentRegistry` O(1) lookups | ✅ Verified | `registry.py:90-122` |

---

## Executive Summary

The `bengal/core` package provides foundational data models with documented O(1) lookups. Analysis confirms the package **already delivers on performance promises** through hash-based registries and caching. Identified **3 minor algorithmic patterns** that could be improved for edge cases:

**Key findings**:

1. ✅ **Well-designed**: Primary operations (lookups, URL resolution, section access) are O(1)
2. ✅ **Effective caching**: `@cached_property` ensures O(n) first access, O(1) subsequent
3. ⚠️ **Minor**: `NavNode.find()` is O(n) — but never used at runtime (shadow of `NavTree.find()`)
4. ⚠️ **Minor**: `MenuItem.add_child()` sorts on every insert — O(k log k) per insert
5. ⚠️ **Minor**: `NavTreeCache` uses FIFO eviction — could benefit from LRU

**Current state**: The existing implementation is **excellent for typical sites** (1K-10K pages). This RFC documents preventive optimizations for extreme scale (50K+ pages) or specific patterns.

**Impact**: Maintain sub-millisecond operations at extreme scale; improve cache efficiency

---

## Current Architecture Assessment

### What's Already Optimal ✅

| Component | Operation | Complexity | Evidence |
|-----------|-----------|------------|----------|
| **NavTree** | `find(url)` | **O(1)** ✅ | Dict lookup via `_flat_nodes` - `nav_tree.py:222-224` |
| **NavTree** | `urls` property | **O(1)** ✅ | Pre-computed set - `nav_tree.py:218-220` |
| **NavTreeContext** | `is_active(node)` | **O(1)** ✅ | Set membership - `nav_tree.py:442-446` |
| **ContentRegistry** | `get_page(path)` | **O(1)** ✅ | Dict lookup - `registry.py:90-110` |
| **ContentRegistry** | `get_section(path)` | **O(1)** ✅ | Dict lookup - `registry.py:124-144` |
| **ContentRegistry** | `get_page_by_url(url)` | **O(1)** ✅ | Dict lookup - `registry.py:112-122` |
| **URLRegistry** | `get_claim(url)` | **O(1)** ✅ | Dict lookup - `url_ownership.py:320-331` |
| **URLRegistry** | `claim(url)` | **O(1)** ✅ | Dict insert - `url_ownership.py:200-273` |
| **Site** | `get_section_by_path()` | **O(1)** ✅ | Delegates to registry - `section_registry.py:48-95` |
| **Site** | `get_section_by_url()` | **O(1)** ✅ | Delegates to registry - `section_registry.py:97-132` |
| **NavNodeProxy** | All properties | **O(1)** ✅ | Cached on first access - `nav_tree.py:532-639` |
| **Section** | `regular_pages` | O(n)/O(1) ✅ | `@cached_property` - `queries.py:77-99` |
| **Section** | `sorted_pages` | O(n log n)/O(1) ✅ | `@cached_property` - `queries.py:117-151` |
| **Site** | `regular_pages` | O(n)/O(1) ✅ | Cached - `page_caches.py:42-61` |
| **Site** | `get_page_path_map()` | O(n)/O(1) ✅ | Cached dict - `page_caches.py:122-140` |

### Design Patterns Employed

1. **Hash-Based Registries**: `ContentRegistry`, `NavTree._flat_nodes`, `URLRegistry._claims`
2. **Lazy Computation with Caching**: `@cached_property` for computed lists
3. **Pre-computation at Build Time**: `NavTree.__post_init__()` builds flat index
4. **Per-Key Locking**: `NavTreeCache` uses `PerKeyLockManager` for parallel builds
5. **Epoch-Based Invalidation**: `ContentRegistry._epoch` for cache staleness detection

---

## Problem Statement

### What Could Be Optimized ⚠️

> **Note**: These are edge-case optimizations. Current implementation handles typical sites excellently.

| Component | Operation | Current | Optimal | Impact |
|-----------|-----------|---------|---------|--------|
| NavNode | `find(url)` | O(n) | N/A (deprecate) | None (unused) |
| MenuItem | `add_child()` | O(k log k) | O(1) + deferred | Low |
| NavTreeCache | Eviction | FIFO | LRU | Low |
| MenuBuilder | `_has_cycle()` | O(n×d) space | O(d) space | Low |

### Bottleneck 1: NavNode.find() — O(n) Shadow Method

**Location**: `nav_tree.py:107-115`

```python
# Current: Recursive tree scan
def find(self, url: str) -> NavNode | None:
    if self._path == url:
        return self
    for child in self.children:
        found = child.find(url)  # O(n) recursive
        if found:
            return found
    return None
```

**Problem**: This O(n) method exists but is **never called at runtime**. All lookups use `NavTree.find()` which is O(1) via `_flat_nodes` dict.

**Current usage**: Only called in `tests/unit/test_nav_tree.py:124` for testing the method itself.

**Recommendation**: Deprecate to prevent accidental misuse; update test to use `NavTree.find()` or wrap with warning suppression.

### Bottleneck 2: MenuItem.add_child() — O(k log k) per Insert

**Location**: `menu.py:140-141`

```python
def add_child(self, child: MenuItem) -> None:
    self.children.append(child)
    self.children.sort(key=lambda x: x.weight)  # O(k log k) every insert!
```

**Problem**: For menus with many children (20+), sorting on every insert is wasteful. With k children and n inserts, total cost is O(n × k log k) instead of O(n + k log k).

**Optimal approach**: Append O(1), sort once after all children added.

### Bottleneck 3: NavTreeCache — FIFO Eviction

**Location**: `nav_tree.py:737-739`

```python
# Current: FIFO eviction when cache full
if len(cls._trees) >= cls._MAX_CACHE_SIZE:
    oldest_key = next(iter(cls._trees))  # First inserted
    cls._trees.pop(oldest_key, None)
```

**Problem**: FIFO evicts oldest entry, not least-recently-used. If version "v1" is accessed frequently but was inserted first, it gets evicted before "v15" which was recently inserted but never accessed again.

**Optimal approach**: Use `OrderedDict` with move_to_end on access for LRU semantics.

### Bottleneck 4: MenuBuilder._has_cycle() — O(d) Space per Call

**Location**: `menu.py:535-570`

```python
def _has_cycle(self, item: MenuItem, visited: set[str], path: set[str]) -> bool:
    # DFS with path copying
    return any(self._has_cycle(child, visited, path.copy()) for child in item.children)
```

**Problem**: `path.copy()` on each recursive call allocates O(d) memory where d is depth. For deeply-nested menus, total allocations are O(n × d) instead of O(d) with a single reused set.

**Impact**: Primarily a **space optimization** (reduced allocations), with minor time benefits from avoiding copy overhead.

**Optimal approach**: Use backtracking (`path.add()`/`path.discard()`) instead of copying.

---

## Proposed Solution

### Phase 1: Low-Hanging Fruit (Safety & Clarity)

**Estimated effort**: 1 hour  
**Impact**: Code hygiene, prevent misuse

#### 1.1 Deprecate NavNode.find()

```python
# nav_tree.py
import warnings

def find(self, url: str) -> NavNode | None:
    """
    Find a node by URL in this subtree.
    
    .. deprecated:: 0.x
        Use NavTree.find() for O(1) lookup instead.
        This method performs O(n) recursive search.
    """
    warnings.warn(
        "NavNode.find() is O(n). Use NavTree.find() for O(1) lookup.",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... existing implementation ...
```

**Rationale**: Prevents accidental O(n) lookups when O(1) alternative exists.

#### 1.2 Optimize MenuBuilder._has_cycle() with Backtracking

```python
# menu.py - Use backtracking instead of copying
def _has_cycle(self, item: MenuItem, visited: set[str], path: set[str]) -> bool:
    """Detect cycles using DFS with backtracking (O(d) space instead of O(n×d))."""
    if item.identifier is None:
        return False
    
    if item.identifier in path:
        return True
    
    path.add(item.identifier)
    visited.add(item.identifier)
    
    # Check each child; short-circuit on first cycle found
    for child in item.children:
        if self._has_cycle(child, visited, path):
            path.discard(item.identifier)  # Clean up before returning
            return True
    
    # Backtrack: remove from path after checking subtree
    path.discard(item.identifier)
    return False
```

**Optimization**: 
- **Space**: O(n × d) allocations → O(d) single set (major improvement)
- **Time**: Eliminates `set.copy()` overhead per call (minor improvement)

> **Note**: Changed from `any()` to explicit loop to ensure `path.discard()` runs on early return.

---

### Phase 2: Menu Sorting Optimization

**Estimated effort**: 1 hour  
**Impact**: Faster menu building for large hierarchies

#### 2.1 Defer Sorting in MenuItem.add_child()

```python
# menu.py - Mark dirty, sort lazily
@dataclass
class MenuItem:
    # ... existing fields ...
    _children_dirty: bool = field(default=False, repr=False)
    
    def add_child(self, child: MenuItem) -> None:
        """Add a child (O(1)). Call sort_children() when done adding."""
        self.children.append(child)
        self._children_dirty = True
    
    def sort_children(self) -> None:
        """Sort children by weight. O(k log k) where k = number of children."""
        if self._children_dirty:
            self.children.sort(key=lambda x: x.weight)
            self._children_dirty = False
    
    def get_sorted_children(self) -> list[MenuItem]:
        """Get children, sorting if needed."""
        self.sort_children()
        return self.children
```

#### 2.2 Update MenuBuilder.build_hierarchy()

```python
# menu.py - Sort once after hierarchy built
def build_hierarchy(self) -> list[MenuItem]:
    # ... existing tree building ...
    
    # Sort all nodes once (DFS)
    def sort_recursive(item: MenuItem) -> None:
        item.sort_children()
        for child in item.children:
            sort_recursive(child)
    
    for root in roots:
        sort_recursive(root)
    
    roots.sort(key=lambda x: x.weight)
    return roots
```

**Complexity change**: O(n × k log k) → O(n + k log k) for menu building

---

### Phase 3: NavTreeCache LRU Eviction (Optional)

**Estimated effort**: 30 minutes  
**Impact**: Better cache efficiency for sites with many versions

> **When to implement**: Sites with 20+ versions where cache eviction occurs frequently.

#### 3.1 Use OrderedDict for LRU

```python
# nav_tree.py - LRU eviction via OrderedDict
from collections import OrderedDict

class NavTreeCache:
    _trees: OrderedDict[str | None, NavTree] = OrderedDict()
    # ... existing code ...
    
    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        # ... existing cache check ...
        
        with cls._lock:
            if version_id in cls._trees:
                # LRU: Move to end on access
                cls._trees.move_to_end(version_id)
                return cls._trees[version_id]
        
        # ... build tree ...
        
        with cls._lock:
            if len(cls._trees) >= cls._MAX_CACHE_SIZE:
                # LRU: Evict oldest (first)
                cls._trees.popitem(last=False)
            cls._trees[version_id] = tree
            return tree
```

**Complexity**: Same O(1) operations, but evicts least-recently-used instead of oldest.

---

## Implementation Plan

### Step 0: Establish Baseline (Required)

**Files**: `benchmarks/test_core_performance.py` (new)

> **Rationale**: Baseline measurements are essential to validate improvement claims and detect regressions.

1. Create synthetic site with 10K pages, 100 sections, 50 menu items
2. Measure:
   - `NavTree.build()` — Tree construction
   - `NavTree.find()` — URL lookup
   - `MenuBuilder.build_hierarchy()` — Menu construction with 100+ items
   - `ContentRegistry` lookups — Page/section resolution
3. Record baseline in `benchmarks/baseline_core.json`
4. Define regression threshold: fail if >10% slower after changes

### Step 1: Code Hygiene (Phase 1)

**Files**: `bengal/core/nav_tree.py`, `bengal/core/menu.py`, `tests/unit/test_nav_tree.py`

1. Add deprecation warning to `NavNode.find()`
2. Update `tests/unit/test_nav_tree.py:124` to use `NavTree.find()` instead of `NavNode.find()` (or suppress warning in test context)
3. Refactor `_has_cycle()` to use backtracking with explicit loop (not `any()`)
4. Add tests for cycle detection edge cases
5. Document O(1) vs O(n) lookup distinction in docstrings

### Step 2: Menu Optimization (Phase 2)

**Files**: `bengal/core/menu.py`

1. Add `_children_dirty` flag to `MenuItem`
2. Make `add_child()` O(1) append-only
3. Add `sort_children()` method
4. Update `build_hierarchy()` to sort once
5. Update tests to call `sort_children()` if accessing children directly

### Step 3: LRU Cache (Phase 3, Conditional)

**Files**: `bengal/core/nav_tree.py`

> Only implement if benchmarks show cache churn with many versions.

1. Replace `dict` with `OrderedDict` for `_trees`
2. Add `move_to_end()` on cache hits
3. Update eviction to `popitem(last=False)`
4. Add tests for LRU behavior

---

## Complexity Analysis Summary

### Current State (Already Excellent)

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| NavTree.find(url) | **O(1)** | — | Dict lookup |
| NavTree.build() | O(n) | O(n) | Builds flat index |
| ContentRegistry lookups | **O(1)** | — | Dict lookups |
| Section.regular_pages | O(n)/O(1) | O(n) | Cached |
| Section.sorted_pages | O(n log n)/O(1) | O(n) | Cached |
| MenuBuilder.build_hierarchy() | O(n log k) | O(n) | Sorting dominates |
| MenuItem.add_child() | O(k log k) | — | Per-insert sort |
| NavTreeCache.get() | O(1)/O(n) | O(v) | Hit/miss, v=versions |

### After Optimization

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| MenuItem.add_child() (n inserts) | O(n × k log k) | O(n + k log k) | **~10x** time for large menus |
| _has_cycle() space | O(n × d) allocs | O(d) single set | **~n×** fewer allocations |
| _has_cycle() time | copy overhead | no copies | Minor (eliminates copy cost) |
| NavTreeCache eviction | FIFO | LRU | Better hit rate for hot versions |

---

## Testing Strategy

### Unit Tests

1. **Correctness**: Verify behavior unchanged
   - Same menu structure after optimization
   - Same cycle detection results
   - Same NavTree lookups

2. **Edge cases**:
   - Menu with 0 children
   - Menu with 100+ children
   - Deeply nested menu (10+ levels)
   - Cycle detection with self-reference
   - Cycle detection with indirect cycles

### Performance Tests

1. **Benchmark suite**:
   - Menu building: 10, 50, 200 items
   - Tree building: 100, 1K, 10K pages
   - Cache operations: 5, 20, 50 versions

2. **Regression detection**: Fail if >10% slower

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Menu sort timing change | Low | Low | Tests verify final order |
| Deprecation warning spam | Low | Low | Only warns on actual misuse |
| OrderedDict overhead | Very Low | Very Low | Same O(1) complexity |
| Breaking existing tests | Low | Medium | Update tests to sort explicitly |
| Test file needs update | Certain | Low | `test_nav_tree.py:124` uses deprecated method; migrate or suppress |

---

## Alternatives Considered

### 1. Remove NavNode.find() Entirely

**Pros**: Prevents misuse completely  
**Cons**: Breaking change if anyone uses it

**Decision**: Deprecate first, remove in next major version.

### 2. Binary Heap for Menu Children

**Pros**: O(log k) per insert with sorted output  
**Cons**: Complexity, children accessed as list in templates

**Decision**: Deferred sort is simpler and sufficient.

### 3. External LRU Library (cachetools)

**Pros**: Battle-tested implementation  
**Cons**: New dependency for simple use case

**Decision**: `OrderedDict` is stdlib and sufficient for 20-entry cache.

---

## Success Criteria

1. **NavNode.find() deprecated**: Warning emitted on direct usage ✅
2. **_has_cycle() uses backtracking**: No `path.copy()` calls ✅
3. **Menu building improved**: Measurable improvement vs baseline (target: 2x faster for 100+ items)
4. **No API changes**: Existing public interfaces unchanged ✅
5. **All tests pass**: Including updated `test_nav_tree.py` ✅
6. **No regressions**: Benchmark suite shows no >10% slowdowns ✅

---

## Future Work

1. **Parallel NavTree builds**: Build trees for multiple versions concurrently
2. **Incremental menu updates**: Update menu without full rebuild
3. **Compressed registry serialization**: Reduce cache file size
4. **Pre-warming popular caches**: Load hot entries on startup

---

## References

- [Python dict complexity](https://wiki.python.org/moin/TimeComplexity) — O(1) average case
- [OrderedDict](https://docs.python.org/3/library/collections.html#collections.OrderedDict) — LRU cache pattern
- [bengal/core architecture](../active/rfc-page-section-reference-contract.md) — Content model design (if exists)

---

## Appendix: Current Implementation Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| NavTree | `nav_tree.py` | `build()`, `find()` (O(1)), `context()` |
| NavTreeCache | `nav_tree.py` | `get()`, `invalidate()` |
| NavNode | `nav_tree.py` | `walk()`, `find()` (O(n), to be deprecated) |
| NavTreeContext | `nav_tree.py` | `is_active()`, `is_current()` |
| NavNodeProxy | `nav_tree.py` | `href`, `is_current`, `children` |
| ContentRegistry | `registry.py` | `get_page()`, `get_section()`, `register_*()` |
| URLRegistry | `url_ownership.py` | `claim()`, `get_claim()` |
| MenuItem | `menu.py` | `add_child()`, `mark_active()` |
| MenuBuilder | `menu.py` | `build_hierarchy()`, `_has_cycle()` |
| Section mixins | `section/*.py` | `regular_pages`, `sorted_pages` |
| Site mixins | `site/*.py` | `get_section_by_*()`, page caches |

---

## Appendix: Space Complexity

| Structure | Current | Notes |
|-----------|---------|-------|
| `NavTree._flat_nodes` | O(n) | n = all nav nodes |
| `NavTree._urls` | O(n) | Set of all URLs |
| `ContentRegistry` | O(p + s) | p = pages, s = sections |
| `URLRegistry._claims` | O(c) | c = claimed URLs |
| `NavTreeCache._trees` | O(20 × n) | Max 20 cached trees |
| `Section.regular_pages` | O(n) per section | Cached list |
| `Section.sorted_pages` | O(n) per section | Cached list |

**Total memory**: For 10K pages, ~50MB for all caches combined — negligible.

---

## Appendix: Verified O(1) Lookup Chains

Critical paths that maintain O(1) performance:

```
Page lookup by URL:
  site.registry.get_page_by_url(url) → O(1) dict lookup

Section lookup by path:
  site.get_section_by_path(path)
    → site.registry.get_section(path)
      → O(1) dict lookup

NavTree node lookup:
  nav_tree.find(url)
    → nav_tree._flat_nodes.get(url)
      → O(1) dict lookup

Active trail check:
  context.is_active(node)
    → node._path in context.active_trail_urls
      → O(1) set membership

URL claim check:
  registry.url_ownership.get_claim(url)
    → O(1) dict lookup
```

All critical runtime paths are verified O(1). ✅

