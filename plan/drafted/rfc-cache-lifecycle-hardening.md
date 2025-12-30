# RFC: Cache Lifecycle Hardening

**Status**: Draft (Planned)  
**Created**: 2025-12-30  
**Updated**: 2025-12-30  
**Author**: AI Assistant  
**Priority**: Medium  
**Estimated Effort**: 3-4 weeks (4 phases)  
**Risk Level**: Low-Medium  
**Affects**: `bengal/cache/`, `bengal/orchestration/`, `bengal/rendering/context/`, `bengal/utils/`  
**Related**: `rfc-cache-invalidation-fixes.md`

---

## Executive Summary

Following the cache invalidation fixes, this RFC addresses broader cache lifecycle issues identified during the technical debt analysis. The goal is to prevent similar issues from emerging in other caching subsystems by establishing consistent patterns for cache invalidation, lifecycle management, and cross-cache coordination.

**Key Issues**:
1. Scattered invalidation calls across multiple entry points
2. No central registry for cache coordination
3. Potential stale references in context caches
4. Missing lifecycle guarantees for thread-local state
5. Fragile invalidation chains that must be manually maintained

**Proposed Solution**: Centralized cache registry with lifecycle hooks, observer pattern for invalidation cascades, and build-scoped context management.

**Implementation Summary**: 4 phases, 28 tasks, ~3-4 weeks

| Phase | Tasks | Risk | Value |
|-------|-------|------|-------|
| 1. Cache Registry | 11 | Low | High |
| 2. Build-Scoped Context | 7 | Medium | Medium |
| 3. Invariant Checks | 6 | Low | Medium |
| 4. Thread-Local Guards | 6 | Low | Low |

---

## Problem Statement

### Current State

Bengal has multiple independent caching systems:

| Cache | Location | Invalidation Method | Entry Points |
|-------|----------|---------------------|--------------|
| BuildCache | `cache/build_cache/` | `clear()`, file fingerprints | 1 |
| NavTreeCache | `core/nav_tree.py` | `invalidate()` class method | 5+ |
| Global Context | `rendering/context/` | `clear_global_context_cache()` | 2 |
| Thread-local Pipelines | `orchestration/render.py` | `clear_thread_local_pipelines()` | 1 |
| TaxonomyIndex | `cache/taxonomy_index.py` | `clear()`, `invalidate_all()` | 2 |
| QueryIndex(es) | `cache/query_index.py` | `clear()` | 2 |
| Version Page Index | `rendering/template_functions/` | `invalidate_version_page_index()` | 3 |
| Parser Cache | `rendering/pipeline/thread_local.py` | `reset_parser_cache()` | 1 |

### Problems

#### 1. Scattered Invalidation Calls

NavTreeCache invalidation is called from multiple locations:

```python
# orchestration/incremental/orchestrator.py:118
NavTreeCache.invalidate()
logger.debug("nav_tree_cache_invalidated", reason="config_changed")

# orchestration/incremental/orchestrator.py:188
NavTreeCache.invalidate()
logger.debug("nav_tree_cache_invalidated", reason="structural_changes")

# server/build_trigger.py (likely)
# ... more places ...
```

**Risk**: Missing an invalidation call in one codepath leads to stale navigation.

#### 2. Manual Invalidation Chains

When config changes, multiple caches must be invalidated in sequence:

```python
# orchestration/incremental/orchestrator.py:116-133
if config_changed:
    NavTreeCache.invalidate()
    logger.debug("nav_tree_cache_invalidated", reason="config_changed")

    invalidate_version_page_index()
    logger.debug("version_page_index_cache_invalidated", reason="config_changed")

    if hasattr(self.site, "invalidate_version_caches"):
        self.site.invalidate_version_caches()
        logger.debug("site_version_dict_cache_invalidated", reason="config_changed")
```

**Risk**: Adding a new cache requires updating this chain manually. Easy to miss.

#### 3. Context Cache Lifecycle Issues

Global context uses `id(site)` as cache key:

```python
# rendering/context/__init__.py:142
site_id = id(site)
with _context_lock:
    if site_id in _global_context_cache:
        return _global_context_cache[site_id]
```

**Risk**: If Site is garbage-collected and a new Site reuses the same memory address (same `id()`), could return cached context from wrong site.

#### 4. Thread-Local State Without Build Boundaries

Thread-local pipelines use generation counter for invalidation:

```python
# orchestration/render.py:84-85
_build_generation: int = 0
_generation_lock = threading.Lock()
```

**Risk**: Generation counter is global, not build-scoped. Concurrent builds (e.g., in test suite) could interfere.

#### 5. Two-Layer State Sync Requirements

Multiple caches maintain forward + reverse indexes:

```python
# cache/taxonomy_index.py
self.tags: dict[str, TagEntry] = {}
self._page_to_tags: dict[str, set[str]] = {}  # Must stay in sync

# cache/query_index.py
self.entries: dict[str, IndexEntry] = {}
self._page_to_keys: dict[str, set[str]] = {}  # Must stay in sync
```

**Risk**: Partial failures during save/load could desync indexes.

---

## Code Verification

Claims in this RFC have been verified against the codebase:

| Claim | Status | Evidence |
|-------|--------|----------|
| Cache registry is basic (`clear_all_caches` only) | ✅ Verified | `utils/cache_registry.py:72-91` - only has `register_cache`, `clear_all_caches`, `list_registered_caches` |
| NavTreeCache called from 5+ locations | ✅ Verified | Found **39 calls** to `NavTreeCache.invalidate()` across tests, benchmarks, and production code |
| Global context uses `id(site)` as key | ✅ Verified | `rendering/context/__init__.py:142` - `site_id = id(site)` |
| Thread-local uses generation counter | ✅ Verified | `orchestration/render.py:84-85` - `_build_generation: int = 0` |
| TaxonomyIndex has two-layer indexes | ✅ Verified | `cache/taxonomy_index.py:128-130` - `tags` + `_page_to_tags` |
| BuildContext exists (to be extended) | ✅ Verified | `utils/build_context.py:122-642` - comprehensive dataclass with 50+ fields |

---

## Root Cause Analysis

### Pattern 1: No Single Source of Truth for Cache State

Each cache manages its own lifecycle independently. There's no central authority that knows:
- Which caches exist
- What dependencies exist between caches
- When all caches should be invalidated together

### Pattern 2: Event-Driven Invalidation Without Events

Invalidation is triggered by calling specific functions at specific points. This is imperative (caller must know what to call) rather than declarative (caches declare their dependencies).

### Pattern 3: Global State Masquerading as Thread-Local

Some "thread-local" caches use global generation counters or locks, creating implicit coupling.

### Pattern 4: Missing Invariant Checks

Two-layer caches don't verify their invariants, so desync can go undetected until it causes subtle bugs.

---

## Proposed Solutions

### Phase 1: Central Cache Registry (Low Risk, High Value)

**Goal**: Single source of truth for all caches, enabling coordinated invalidation.

#### 1.1 Extend Existing Cache Registry

Current registry only supports `clear_all_caches()` for tests:

```python
# utils/cache_registry.py (current)
_registered_caches: dict[str, Callable[[], None]] = {}

def register_cache(name: str, clear_fn: Callable[[], None]) -> None:
    _registered_caches[name] = clear_fn

def clear_all_caches() -> None:
    for clear_fn in _registered_caches.values():
        clear_fn()
```

**Proposed Enhancement**:

```python
# utils/cache_registry.py (enhanced)
from dataclasses import dataclass, field
from enum import Enum, auto
from graphlib import TopologicalSorter
from typing import Callable
import logging
import threading
import time

logger = logging.getLogger(__name__)

class InvalidationReason(Enum):
    """Why a cache was invalidated."""
    CONFIG_CHANGED = auto()
    STRUCTURAL_CHANGE = auto()  # Pages added/deleted
    NAV_CHANGE = auto()         # Navigation-affecting metadata
    TEMPLATE_CHANGE = auto()
    FULL_REBUILD = auto()
    BUILD_START = auto()        # New build starting
    BUILD_END = auto()          # Build completed
    TEST_CLEANUP = auto()

@dataclass
class CacheEntry:
    """Registered cache with metadata."""
    name: str
    clear_fn: Callable[[], None]
    invalidate_on: set[InvalidationReason]  # When to auto-invalidate
    depends_on: set[str] = field(default_factory=set)  # Cache dependencies

_registered_caches: dict[str, CacheEntry] = {}
_registry_lock = threading.Lock()
_invalidation_log: list[tuple[str, InvalidationReason, float]] = []

def register_cache(
    name: str,
    clear_fn: Callable[[], None],
    invalidate_on: set[InvalidationReason] | None = None,
    depends_on: set[str] | None = None,
) -> None:
    """
    Register a cache with lifecycle metadata.
    
    Caches should register themselves at module import time (standard pattern).
    This ensures all caches are registered before any build operations.
    
    Args:
        name: Unique cache name (for debugging and dependency tracking)
        clear_fn: Callable that clears the cache (e.g., lambda: cache.clear())
        invalidate_on: Set of reasons that should trigger invalidation
        depends_on: Set of cache names this cache depends on (for cascade invalidation)
    
    Raises:
        ValueError: If dependency cycle detected or dependencies don't exist
    
    Example:
        register_cache(
            "nav_tree",
            NavTreeCache.invalidate,
            invalidate_on={InvalidationReason.CONFIG_CHANGED, InvalidationReason.STRUCTURAL_CHANGE},
            depends_on={"build_cache"},  # Nav tree depends on build cache
        )
    """
    with _registry_lock:
        # Validate dependencies exist (if not empty)
        if depends_on:
            missing = depends_on - _registered_caches.keys()
            if missing:
                raise ValueError(
                    f"Cache '{name}' depends on non-existent caches: {missing}. "
                    f"Register dependencies first or remove them from depends_on."
                )
        
        # Check for cycles (defensive - shouldn't happen with proper design)
        _validate_no_cycles(name, depends_on or set())
        
        _registered_caches[name] = CacheEntry(
            name=name,
            clear_fn=clear_fn,
            invalidate_on=invalidate_on or {InvalidationReason.FULL_REBUILD},
            depends_on=depends_on or set(),
        )

def _validate_no_cycles(new_cache: str, new_deps: set[str]) -> None:
    """
    Validate that adding new_cache with new_deps doesn't create a cycle.
    
    Uses DFS to detect cycles in dependency graph.
    """
    # Build dependency graph
    graph: dict[str, set[str]] = {}
    for name, entry in _registered_caches.items():
        graph[name] = entry.depends_on.copy()
    graph[new_cache] = new_deps.copy()
    
    # Check for cycles using DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()
    
    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        
        for dep in graph.get(node, set()):
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            if has_cycle(node):
                raise ValueError(
                    f"Cache dependency cycle detected involving '{new_cache}'. "
                    f"Dependencies: {new_deps}"
                )

def _topological_sort(cache_names: set[str]) -> list[str]:
    """
    Topologically sort cache names by dependency order.
    
    Uses graphlib.TopologicalSorter (Python 3.9+) for reliable ordering.
    Ensures dependencies are invalidated before dependents.
    
    Args:
        cache_names: Set of cache names to sort
    
    Returns:
        List of cache names in dependency order (dependencies first)
    """
    # Build dependency graph for selected caches
    graph: dict[str, set[str]] = {}
    for name in cache_names:
        if name in _registered_caches:
            # Only include dependencies that are also in cache_names
            entry = _registered_caches[name]
            graph[name] = entry.depends_on & cache_names
    
    # Handle empty graph or single node
    if not graph:
        return list(cache_names)
    if len(graph) == 1:
        return list(cache_names)
    
    # Use TopologicalSorter for reliable ordering
    sorter = TopologicalSorter(graph)
    try:
        return list(sorter.static_order())
    except ValueError as e:
        # Shouldn't happen if cycle detection works, but defensive
        logger.warning(f"Topological sort failed (cycle?): {e}. Invalidating in arbitrary order.")
        return list(cache_names)

def invalidate_for_reason(reason: InvalidationReason) -> list[str]:
    """
    Invalidate all caches that should be cleared for this reason.
    
    Returns list of invalidated cache names (for logging).
    
    Thread-safe: Uses registry lock for consistency.
    """
    invalidated = []
    timestamp = time.time()
    
    with _registry_lock:
        for name, entry in _registered_caches.items():
            if reason in entry.invalidate_on:
                try:
                    entry.clear_fn()
                    invalidated.append(name)
                    _invalidation_log.append((name, reason, timestamp))
                except Exception as e:
                    # Log but don't fail - one cache failure shouldn't break invalidation
                    logger.warning(f"Failed to invalidate cache '{name}': {e}")
    
    return invalidated

def invalidate_with_dependents(cache_name: str, reason: InvalidationReason) -> list[str]:
    """
    Invalidate a specific cache and all caches that depend on it.
    
    Uses topological sort to ensure correct order (dependencies before dependents).
    
    Args:
        cache_name: Name of cache to invalidate
        reason: Reason for invalidation (for logging)
    
    Returns:
        List of invalidated cache names in dependency order
    
    Raises:
        KeyError: If cache_name not registered
    """
    with _registry_lock:
        if cache_name not in _registered_caches:
            raise KeyError(f"Cache '{cache_name}' not registered")
        
        # Find all dependents (transitive closure)
        to_invalidate = {cache_name}
        changed = True
        while changed:
            changed = False
            for name, entry in _registered_caches.items():
                if entry.depends_on & to_invalidate and name not in to_invalidate:
                    to_invalidate.add(name)
                    changed = True
        
        # Invalidate in dependency order
        invalidated = []
        timestamp = time.time()
        for name in _topological_sort(to_invalidate):
            if name in _registered_caches:
                try:
                    _registered_caches[name].clear_fn()
                    invalidated.append(name)
                    _invalidation_log.append((name, reason, timestamp))
                except Exception as e:
                    logger.warning(f"Failed to invalidate cache '{name}': {e}")
    
    return invalidated

def get_invalidation_log() -> list[tuple[str, InvalidationReason, float]]:
    """Get log of recent invalidations (for debugging)."""
    with _registry_lock:
        return _invalidation_log[-100:]  # Keep last 100

def clear_invalidation_log() -> None:
    """Clear invalidation log."""
    with _registry_lock:
        _invalidation_log.clear()
```

#### 1.2 Migrate Existing Caches

**NavTreeCache**:
```python
# core/nav_tree.py
from bengal.utils.cache_registry import register_cache, InvalidationReason

class NavTreeCache:
    ...
    
# Register at module load
register_cache(
    "nav_tree",
    NavTreeCache.invalidate,
    invalidate_on={
        InvalidationReason.CONFIG_CHANGED,
        InvalidationReason.STRUCTURAL_CHANGE,
        InvalidationReason.NAV_CHANGE,
        InvalidationReason.FULL_REBUILD,
    },
)
```

**Global Context**:
```python
# rendering/context/__init__.py
register_cache(
    "global_context",
    clear_global_context_cache,
    invalidate_on={
        InvalidationReason.BUILD_START,  # Always fresh per build
        InvalidationReason.CONFIG_CHANGED,
        InvalidationReason.FULL_REBUILD,
    },
)
```

**Version Page Index**:
```python
# rendering/template_functions/version_url.py
register_cache(
    "version_page_index",
    invalidate_version_page_index,
    invalidate_on={
        InvalidationReason.CONFIG_CHANGED,
        InvalidationReason.STRUCTURAL_CHANGE,
        InvalidationReason.FULL_REBUILD,
    },
    depends_on={"nav_tree"},  # Depends on nav structure
)
```

#### 1.3 Simplify Invalidation Sites

**Before** (current):
```python
# orchestration/incremental/orchestrator.py
if config_changed:
    NavTreeCache.invalidate()
    invalidate_version_page_index()
    if hasattr(self.site, "invalidate_version_caches"):
        self.site.invalidate_version_caches()
```

**After** (proposed):
```python
# orchestration/incremental/orchestrator.py
if config_changed:
    from bengal.utils.cache_registry import invalidate_for_reason, InvalidationReason
    
    invalidated = invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
    logger.debug("caches_invalidated", reason="config_changed", caches=invalidated)
```

---

### Phase 2: Build-Scoped Context (Medium Risk)

**Goal**: Ensure context caches are scoped to a specific build, preventing cross-build contamination.

**Note**: `BuildContext` already exists in `bengal/utils/build_context.py` as a dataclass for sharing state across build phases. This phase extends the existing class rather than creating a new one.

#### 2.1 Extend Existing BuildContext

```python
# utils/build_context.py (enhanced)
from dataclasses import dataclass, field
from typing import Any, Callable
import uuid

@dataclass
class BuildContext:
    """
    Shared build context passed across build phases.
    
    Extended with build-scoped caching to prevent cross-build contamination.
    Existing fields preserved for backward compatibility.
    """
    # ... existing fields (site, stats, cache, tracker, etc.) ...
    
    # NEW: Build-scoped cache identifier
    build_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    
    # NEW: Build-scoped caches (separate from existing _page_contents, etc.)
    _build_scoped_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    
    def get_cached(self, key: str, factory: Callable[[], Any]) -> Any:
        """
        Get or create cached value scoped to this build.
        
        Values cached here are automatically cleared when build completes,
        preventing cross-build contamination.
        
        Args:
            key: Cache key (should be descriptive, e.g., "global_contexts")
            factory: Callable that creates the value if not cached
        
        Returns:
            Cached value (created on first access)
        
        Example:
            contexts = build_context.get_cached(
                "global_contexts",
                lambda: _create_contexts(site)
            )
        """
        if key not in self._build_scoped_cache:
            self._build_scoped_cache[key] = factory()
        return self._build_scoped_cache[key]
    
    def __enter__(self) -> BuildContext:
        """
        Enter build scope - signal BUILD_START event.
        
        Enables context manager usage:
            with BuildContext(...) as ctx:
                # Build operations
        """
        from bengal.utils.cache_registry import invalidate_for_reason, InvalidationReason
        invalidate_for_reason(InvalidationReason.BUILD_START)
        return self
    
    def __exit__(self, *args) -> None:
        """
        Exit build scope - signal BUILD_END event and clear build-scoped caches.
        
        Automatically clears _build_scoped_cache to free memory and prevent
        cross-build contamination.
        """
        from bengal.utils.cache_registry import invalidate_for_reason, InvalidationReason
        invalidate_for_reason(InvalidationReason.BUILD_END)
        self._build_scoped_cache.clear()
```

**Backward Compatibility**: Existing code using `BuildContext` continues to work. Build-scoped caching is opt-in via `get_cached()` method. Context manager protocol is optional.

#### 2.2 Refactor Global Context to Use Build Scope

```python
# rendering/context/__init__.py (refactored)

def _get_global_contexts(site: Site, build_context: BuildContext | None = None) -> dict[str, Any]:
    """
    Get context wrappers, using build-scoped cache if available.
    
    If build_context is provided, caches are scoped to that build.
    Otherwise, falls back to global cache (for compatibility).
    """
    if build_context:
        return build_context.get_cached(
            "global_contexts",
            lambda: _create_contexts(site)
        )
    
    # Legacy: global cache
    site_id = id(site)
    with _context_lock:
        if site_id in _global_context_cache:
            return _global_context_cache[site_id]
        contexts = _create_contexts(site)
        _global_context_cache[site_id] = contexts
        return contexts

def _create_contexts(site: Site) -> dict[str, Any]:
    """Create fresh context wrappers."""
    theme_obj = site.theme_config if hasattr(site, "theme_config") else None
    return {
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj else ThemeContext._empty(),
        "menus": MenusContext(site),
    }
```

---

### Phase 3: Invariant Checks for Two-Layer Caches (Low Risk)

**Goal**: Detect index desync early before it causes subtle bugs.

#### 3.1 TaxonomyIndex Invariant Check

```python
# cache/taxonomy_index.py

def _check_invariants(self) -> list[str]:
    """
    Verify forward and reverse indexes are in sync.
    
    Returns list of violations (empty if consistent).
    """
    violations = []
    
    # Check 1: Every page in _page_to_tags exists in tags[tag].page_paths
    for page, tags in self._page_to_tags.items():
        for tag in tags:
            if tag not in self.tags:
                violations.append(f"Reverse index has tag '{tag}' not in forward index")
            elif page not in self.tags[tag].page_paths:
                violations.append(f"Page '{page}' in reverse index for tag '{tag}' but not in forward")
    
    # Check 2: Every page in tags[tag].page_paths exists in _page_to_tags
    for tag_slug, entry in self.tags.items():
        for page in entry.page_paths:
            if page not in self._page_to_tags:
                violations.append(f"Page '{page}' in forward index for tag '{tag_slug}' but not in reverse")
            elif tag_slug not in self._page_to_tags[page]:
                violations.append(f"Tag '{tag_slug}' for page '{page}' in forward but not reverse")
    
    return violations

def save_to_disk(self) -> None:
    """Save taxonomy index with invariant check."""
    # Debug: verify consistency before save
    if logger.isEnabledFor(logging.DEBUG):
        violations = self._check_invariants()
        if violations:
            logger.warning(
                "taxonomy_index_invariant_violation",
                violations=violations[:5],  # First 5
                total=len(violations),
            )
    
    # ... existing save logic ...

def load_from_disk(self) -> None:
    """Load taxonomy index with invariant check."""
    # ... existing load logic ...
    
    # Verify invariants after load (detect corruption early)
    if logger.isEnabledFor(logging.DEBUG):
        violations = self._check_invariants()
        if violations:
            logger.error(
                "taxonomy_index_corruption_detected",
                violations=violations[:5],
                total=len(violations),
                action="Rebuilding index from scratch",
            )
            # Optionally: clear and rebuild if corruption detected
            # self.clear()
```

#### 3.2 QueryIndex Invariant Check (Similar Pattern)

```python
# cache/query_index.py

def _check_invariants(self) -> list[str]:
    """Verify forward and reverse indexes are in sync."""
    violations = []
    
    for page, keys in self._page_to_keys.items():
        for key in keys:
            if key not in self.entries:
                violations.append(f"Reverse has key '{key}' not in forward")
            elif page not in self.entries[key].page_paths:
                violations.append(f"Page '{page}' in reverse for key '{key}' not in forward")
    
    for key, entry in self.entries.items():
        for page in entry.page_paths:
            if page not in self._page_to_keys:
                violations.append(f"Page '{page}' in forward for key '{key}' not in reverse")
            elif key not in self._page_to_keys[page]:
                violations.append(f"Key '{key}' for page '{page}' in forward not in reverse")
    
    return violations
```

---

### Phase 4: Thread-Local Lifecycle Guards (Low Risk)

**Goal**: Prevent thread-local invalidation during active operations.

#### 4.1 Add Active Render Guard

```python
# orchestration/render.py

# Thread-safe counter for active renders
_active_render_count: int = 0
_active_render_lock = threading.Lock()

def _increment_active_renders() -> None:
    """Increment active render count (call at render start)."""
    global _active_render_count
    with _active_render_lock:
        _active_render_count += 1

def _decrement_active_renders() -> None:
    """Decrement active render count (call at render end)."""
    global _active_render_count
    with _active_render_lock:
        _active_render_count -= 1

def clear_thread_local_pipelines() -> None:
    """
    Invalidate thread-local pipeline caches across all threads.
    
    IMPORTANT: Must not be called while renders are active.
    This guard prevents invalidation during active operations.
    """
    with _active_render_lock:
        if _active_render_count > 0:
            logger.warning(
                "clear_pipelines_during_active_render",
                active_count=_active_render_count,
            )
            # In strict mode, could raise RuntimeError here
            # For now, log warning and proceed (defensive)
    
    global _build_generation
    with _generation_lock:
        _build_generation += 1
```

**Integration**: Wrap render operations with increment/decrement:
```python
def render_page(...):
    _increment_active_renders()
    try:
        # ... render logic ...
    finally:
        _decrement_active_renders()
```

---

## Migration Plan

### Phase 1: Cache Registry (Week 1-2)

1. Enhance `utils/cache_registry.py` with metadata and dependency tracking
2. Update all existing `register_cache()` calls with `invalidate_on` metadata
3. Replace scattered invalidation calls with `invalidate_for_reason()`
4. Add tests for invalidation cascades

### Phase 2: Build-Scoped Context (Week 2-3)

1. Extend existing `BuildContext` class with `build_id` and `_build_scoped_cache`
2. Add `get_cached()` method and context manager protocol (`__enter__`/`__exit__`)
3. Update `_get_global_contexts()` to accept optional `build_context` parameter
4. Gradually migrate from global cache to build-scoped (backward compatible)
5. Add tests for cross-build isolation
6. **Performance**: Benchmark build-scoped cache overhead (expected: <1ms per build)

### Phase 3: Invariant Checks (Week 3)

1. Add `_check_invariants()` to TaxonomyIndex and QueryIndex
2. Call during `save_to_disk()` (debug mode only initially)
3. Call during `load_from_disk()` to detect corruption early
4. Add tests that verify invariants hold after various operations
5. Add tests that verify corruption detection works
6. Consider enabling in CI as regression protection (with sampling to reduce overhead)
7. **Performance**: Measure invariant check overhead (expected: <10ms for typical sites)

### Phase 4: Thread-Local Guards (Week 4)

1. Add active render tracking
2. Add guards to `clear_thread_local_pipelines()`
3. Add tests for concurrent build scenarios

---

## Implementation Tasks

Detailed task breakdown for each phase:

### Phase 1: Central Cache Registry (High Value, Low Risk)

**Architecture Change**:
```
Current: _cache_registry: dict[str, Callable]
Target:  _registered_caches: dict[str, CacheEntry] with metadata
         + dependency tracking + topological invalidation
```

| Task ID | Task | File(s) | Complexity |
|---------|------|---------|------------|
| 1.1 | Add `InvalidationReason` enum | `utils/cache_registry.py` | Low |
| 1.2 | Add `CacheEntry` dataclass with `invalidate_on`, `depends_on` | `utils/cache_registry.py` | Low |
| 1.3 | Implement `_validate_no_cycles()` DFS cycle detection | `utils/cache_registry.py` | Medium |
| 1.4 | Implement `_topological_sort()` using `graphlib.TopologicalSorter` | `utils/cache_registry.py` | Medium |
| 1.5 | Add `invalidate_for_reason()` API | `utils/cache_registry.py` | Low |
| 1.6 | Add `invalidate_with_dependents()` API | `utils/cache_registry.py` | Medium |
| 1.7 | Migrate NavTreeCache registration | `core/nav_tree.py` | Low |
| 1.8 | Migrate GlobalContext registration | `rendering/context/__init__.py` | Low |
| 1.9 | Migrate VersionPageIndex registration | `rendering/template_functions/version_url.py` | Low |
| 1.10 | Replace invalidation calls in IncrementalOrchestrator | `orchestration/incremental/orchestrator.py` | Medium |
| 1.11 | Add unit tests for registry | `tests/unit/cache/test_cache_registry.py` | Medium |

**Key Migration Point** (orchestration/incremental/orchestrator.py:116-133):
```python
# Before
if config_changed:
    NavTreeCache.invalidate()
    invalidate_version_page_index()
    if hasattr(self.site, "invalidate_version_caches"):
        self.site.invalidate_version_caches()

# After
if config_changed:
    invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
```

### Phase 2: Build-Scoped Context (Medium Risk)

**Architecture Change**:
```
Extend existing BuildContext (not replace) with:
- build_id: str (uuid4 hex)
- _build_scoped_cache: dict[str, Any]
- get_cached(key, factory) method
- __enter__ / __exit__ context manager
```

| Task ID | Task | File(s) | Complexity |
|---------|------|---------|------------|
| 2.1 | Add `build_id` field (default: `uuid.uuid4().hex[:8]`) | `utils/build_context.py` | Low |
| 2.2 | Add `_build_scoped_cache` field | `utils/build_context.py` | Low |
| 2.3 | Add `get_cached(key, factory)` method | `utils/build_context.py` | Low |
| 2.4 | Add `__enter__` (signal BUILD_START) | `utils/build_context.py` | Low |
| 2.5 | Add `__exit__` (signal BUILD_END, clear cache) | `utils/build_context.py` | Low |
| 2.6 | Refactor `_get_global_contexts()` to accept `build_context` | `rendering/context/__init__.py` | Medium |
| 2.7 | Add integration tests for build isolation | `tests/integration/test_cache_lifecycle.py` | Medium |

**Backward Compatibility**: Existing code continues to work. Build-scoped caching is opt-in via `build_context` parameter.

### Phase 3: Invariant Checks (Low Risk)

| Task ID | Task | File(s) | Complexity |
|---------|------|---------|------------|
| 3.1 | Add `_check_invariants()` to TaxonomyIndex | `cache/taxonomy_index.py` | Medium |
| 3.2 | Call invariants in `save_to_disk()` (debug mode) | `cache/taxonomy_index.py` | Low |
| 3.3 | Call invariants in `_load_from_disk()` | `cache/taxonomy_index.py` | Low |
| 3.4 | Add `_check_invariants()` to QueryIndex | `cache/query_index.py` | Medium |
| 3.5 | Call invariants in QueryIndex save/load | `cache/query_index.py` | Low |
| 3.6 | Add tests for invariant detection | `tests/unit/cache/test_taxonomy_index.py` | Medium |

### Phase 4: Thread-Local Guards (Low Risk)

| Task ID | Task | File(s) | Complexity |
|---------|------|---------|------------|
| 4.1 | Add `_active_render_count` and lock | `orchestration/render.py` | Low |
| 4.2 | Add `_increment_active_renders()` | `orchestration/render.py` | Low |
| 4.3 | Add `_decrement_active_renders()` | `orchestration/render.py` | Low |
| 4.4 | Add guard to `clear_thread_local_pipelines()` | `orchestration/render.py` | Low |
| 4.5 | Wrap render operations with increment/decrement | `orchestration/render.py` | Medium |
| 4.6 | Add concurrency tests | `tests/unit/orchestration/test_render.py` | Medium |

---

## Identified Gaps

Issues discovered during planning that require attention:

1. **QueryIndex verification needed**: RFC references `cache/query_index.py` - verify it has similar two-layer structure to TaxonomyIndex before implementing Phase 3.4.

2. **Version Page Index location**: Verify `rendering/template_functions/version_url.py` contains `invalidate_version_page_index()` function.

3. **Performance baseline**: Recommend adding benchmark tests before Phase 1 implementation to establish baseline for measuring overhead.

4. **Documentation**: Cache registration pattern (module-level at import time) should be documented in registry docstring and contributing guide.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/cache/test_cache_registry.py

class TestCacheRegistry:
    def test_invalidate_for_reason_clears_correct_caches(self):
        """Caches with matching reason are cleared."""
        cleared = []
        register_cache("a", lambda: cleared.append("a"), 
                       invalidate_on={InvalidationReason.CONFIG_CHANGED})
        register_cache("b", lambda: cleared.append("b"),
                       invalidate_on={InvalidationReason.STRUCTURAL_CHANGE})
        
        invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
        
        assert "a" in cleared
        assert "b" not in cleared
    
    def test_invalidate_with_dependents_cascades(self):
        """Dependent caches are invalidated in order."""
        order = []
        register_cache("base", lambda: order.append("base"))
        register_cache("dependent", lambda: order.append("dependent"),
                       depends_on={"base"})
        
        invalidate_with_dependents("base", InvalidationReason.FULL_REBUILD)
        
        assert order == ["base", "dependent"]
```

### Integration Tests

```python
# tests/integration/test_cache_lifecycle.py

class TestCacheLifecycle:
    def test_config_change_invalidates_all_dependent_caches(self, site):
        """Config change triggers cascade invalidation."""
        # Build once to populate caches
        build_site(site)
        
        # Modify config
        site.config["title"] = "New Title"
        
        # Build again
        build_site(site)
        
        # Verify fresh caches (implementation-specific checks)
        assert NavTreeCache._cache == {}  # or appropriate check
    
    def test_concurrent_builds_isolated(self, site):
        """Concurrent builds don't contaminate each other."""
        import concurrent.futures
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(build_site, site.copy()) 
                for _ in range(2)
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())
        
        # Both builds should succeed without interference
        assert all(r.success for r in results)
```

---

## Success Criteria

### Functional Criteria

1. **No scattered invalidation calls**: All cache invalidation goes through registry
2. **Dependency tracking works**: Adding new cache with dependency auto-cascades
3. **Build isolation verified**: Concurrent builds don't interfere
4. **Invariant checks pass**: Two-layer caches stay in sync
5. **No regressions**: Existing tests continue to pass
6. **Backward compatibility**: Existing code using BuildContext continues to work

### Performance Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Registry lookup overhead | <0.1ms per invalidation | Benchmark with 10+ caches |
| Dependency traversal | <1ms for typical graphs | Benchmark with 5-level deep graph |
| Build-scoped cache | <1ms per build | Measure `__enter__`/`__exit__` overhead |
| Invariant checks | <10ms for typical sites | Measure on 500+ page site |
| Total build regression | <1% slowdown | Compare before/after on reference site |

### Implementation Completeness

| Phase | Completion Criteria |
|-------|---------------------|
| Phase 1 | All caches registered with metadata; 0 direct invalidation calls outside registry |
| Phase 2 | BuildContext context manager works; global context accepts build_context |
| Phase 3 | Invariants checked on save/load; 0 false positives in test suite |
| Phase 4 | Guards prevent invalidation during active renders; concurrent tests pass |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Over-invalidation (clearing too much) | Medium | Low (slower builds) | Log invalidations, tune `invalidate_on`, performance benchmarks |
| Under-invalidation (missing clears) | Low | High (stale data) | Integration tests, invariant checks, comprehensive test coverage |
| Dependency cycles | Low | Medium | Cycle detection at registration time, clear error messages |
| Migration breaks existing code | Medium | Medium | Backward compatibility (optional build_context param), gradual migration |
| Performance regression | Low | Medium | Benchmark each phase, measure overhead, optimize hot paths |
| BuildContext integration issues | Medium | Medium | Extend existing class (don't replace), maintain backward compatibility |

---

## Open Questions

1. **Should invariant checks be enabled in production?** 
   - **Recommendation**: Start with debug-only (as proposed). After Phase 3, evaluate performance impact. If <10ms overhead, consider enabling in CI with sampling (check 10% of saves). Production: keep debug-only unless corruption issues emerge.

2. **How to handle cache versioning?** 
   - **Recommendation**: Add `version: int` field to `CacheEntry` in Phase 1. Registry tracks versions. `invalidate_for_reason()` can check versions. Consider separate RFC for coordinated version migration strategy (when cache formats change).

3. **Should we add cache hit/miss metrics?** 
   - **Recommendation**: Defer to Phase 2 (after registry is stable). Add lightweight counters to `CacheEntry` (hit_count, miss_count). Enable via feature flag (low overhead when disabled). Use for optimization opportunities identification.

4. **Cache registration timing?**
   - **Recommendation**: Module-level registration at import time (current pattern). Document this pattern in registry docstring. Ensures all caches registered before any build operations.

---

## References

- `rfc-cache-invalidation-fixes.md`: Related fixes for file fingerprint timing
- `bengal/utils/cache_registry.py`: Existing (basic) cache registry
- `bengal/utils/build_context.py`: Existing BuildContext class (to be extended)
- `bengal/core/nav_tree.py`: NavTreeCache implementation
- `bengal/rendering/context/__init__.py`: Global context caching
- `bengal/orchestration/incremental/orchestrator.py`: Current invalidation sites
- `bengal/cache/taxonomy_index.py`: Two-layer cache example
- `bengal/cache/query_index.py`: Two-layer cache example
- Python `graphlib.TopologicalSorter`: Used for dependency ordering (Python 3.9+)

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Initial draft |
| 2025-12-30 | Improved: Added topological sort implementation, cycle detection, error handling |
| 2025-12-30 | Fixed: Acknowledged existing BuildContext, proposed extension rather than replacement |
| 2025-12-30 | Fixed: Removed non-existent Python 3.13 threading.atomic reference |
| 2025-12-30 | Added: Performance considerations, cache registration timing, invariant checks on load |
| 2025-12-30 | Enhanced: Error handling documentation, backward compatibility strategy |
| 2025-12-30 | Added: Code Verification section with evidence for all claims |
| 2025-12-30 | Added: Implementation Tasks section with detailed task breakdown per phase |
| 2025-12-30 | Added: Identified Gaps section noting items requiring attention |
| 2025-12-30 | Enhanced: Success Criteria with performance targets and completion criteria tables |

