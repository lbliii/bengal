# RFC: Cache Lifecycle Hardening

**Status**: Draft  
**Created**: 2025-12-30  
**Updated**: 2025-12-30  
**Author**: AI Assistant  
**Priority**: Medium  
**Affects**: `bengal/cache/`, `bengal/orchestration/`, `bengal/rendering/context/`  
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
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

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
_invalidation_log: list[tuple[str, InvalidationReason, float]] = []

def register_cache(
    name: str,
    clear_fn: Callable[[], None],
    invalidate_on: set[InvalidationReason] | None = None,
    depends_on: set[str] | None = None,
) -> None:
    """Register a cache with lifecycle metadata."""
    _registered_caches[name] = CacheEntry(
        name=name,
        clear_fn=clear_fn,
        invalidate_on=invalidate_on or {InvalidationReason.FULL_REBUILD},
        depends_on=depends_on or set(),
    )

def invalidate_for_reason(reason: InvalidationReason) -> list[str]:
    """
    Invalidate all caches that should be cleared for this reason.
    
    Returns list of invalidated cache names (for logging).
    """
    import time
    invalidated = []
    
    for name, entry in _registered_caches.items():
        if reason in entry.invalidate_on:
            entry.clear_fn()
            invalidated.append(name)
            _invalidation_log.append((name, reason, time.time()))
    
    return invalidated

def invalidate_with_dependents(cache_name: str, reason: InvalidationReason) -> list[str]:
    """
    Invalidate a specific cache and all caches that depend on it.
    
    Uses topological sort to ensure correct order.
    """
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
    for name in _topological_sort(to_invalidate):
        if name in _registered_caches:
            _registered_caches[name].clear_fn()
            invalidated.append(name)
    
    return invalidated

def get_invalidation_log() -> list[tuple[str, InvalidationReason, float]]:
    """Get log of recent invalidations (for debugging)."""
    return _invalidation_log[-100:]  # Keep last 100

def clear_invalidation_log() -> None:
    """Clear invalidation log."""
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

#### 2.1 Build Context as Cache Scope

```python
# utils/build_context.py (enhanced)
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class BuildContext:
    """Context for a single build execution."""
    site: Site
    stats: BuildStats
    build_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    
    # Build-scoped caches
    _context_cache: dict[str, Any] = field(default_factory=dict)
    
    def get_cached(self, key: str, factory: Callable[[], Any]) -> Any:
        """Get or create cached value for this build."""
        if key not in self._context_cache:
            self._context_cache[key] = factory()
        return self._context_cache[key]
    
    def __enter__(self) -> BuildContext:
        """Enter build scope - signal BUILD_START."""
        from bengal.utils.cache_registry import invalidate_for_reason, InvalidationReason
        invalidate_for_reason(InvalidationReason.BUILD_START)
        return self
    
    def __exit__(self, *args) -> None:
        """Exit build scope - signal BUILD_END."""
        from bengal.utils.cache_registry import invalidate_for_reason, InvalidationReason
        invalidate_for_reason(InvalidationReason.BUILD_END)
        self._context_cache.clear()
```

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

_active_renders = threading.atomic.AtomicInteger(0)  # Python 3.13+
# Or for compatibility:
_active_render_count: int = 0
_active_render_lock = threading.Lock()

def _increment_active_renders() -> None:
    global _active_render_count
    with _active_render_lock:
        _active_render_count += 1

def _decrement_active_renders() -> None:
    global _active_render_count
    with _active_render_lock:
        _active_render_count -= 1

def clear_thread_local_pipelines() -> None:
    """
    Invalidate thread-local pipeline caches across all threads.
    
    IMPORTANT: Must not be called while renders are active.
    """
    with _active_render_lock:
        if _active_render_count > 0:
            logger.warning(
                "clear_pipelines_during_active_render",
                active_count=_active_render_count,
            )
            # In strict mode, could raise here
    
    global _build_generation
    with _generation_lock:
        _build_generation += 1
```

---

## Migration Plan

### Phase 1: Cache Registry (Week 1-2)

1. Enhance `utils/cache_registry.py` with metadata and dependency tracking
2. Update all existing `register_cache()` calls with `invalidate_on` metadata
3. Replace scattered invalidation calls with `invalidate_for_reason()`
4. Add tests for invalidation cascades

### Phase 2: Build-Scoped Context (Week 2-3)

1. Enhance `BuildContext` with scoped caching
2. Update `build_page_context()` to accept optional `build_context`
3. Gradually migrate from global cache to build-scoped
4. Add tests for cross-build isolation

### Phase 3: Invariant Checks (Week 3)

1. Add `_check_invariants()` to TaxonomyIndex and QueryIndex
2. Call during save (debug mode only initially)
3. Add tests that verify invariants hold after various operations
4. Consider enabling in CI as regression protection

### Phase 4: Thread-Local Guards (Week 4)

1. Add active render tracking
2. Add guards to `clear_thread_local_pipelines()`
3. Add tests for concurrent build scenarios

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

1. **No scattered invalidation calls**: All cache invalidation goes through registry
2. **Dependency tracking works**: Adding new cache with dependency auto-cascades
3. **Build isolation verified**: Concurrent builds don't interfere
4. **Invariant checks pass**: Two-layer caches stay in sync
5. **No regressions**: Existing tests continue to pass
6. **Performance neutral**: No measurable slowdown in builds

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Over-invalidation (clearing too much) | Medium | Low (slower builds) | Log invalidations, tune `invalidate_on` |
| Under-invalidation (missing clears) | Low | High (stale data) | Integration tests, invariant checks |
| Dependency cycles | Low | Medium | Validate no cycles at registration |
| Migration breaks existing code | Medium | Medium | Gradual migration, feature flags |

---

## Open Questions

1. **Should invariant checks be enabled in production?** Currently proposed for debug-only. Could catch issues earlier if always-on with sampling.

2. **How to handle cache versioning?** When cache format changes, need coordinated migration. Registry could track versions.

3. **Should we add cache hit/miss metrics?** Would help identify optimization opportunities but adds overhead.

---

## References

- `rfc-cache-invalidation-fixes.md`: Related fixes for file fingerprint timing
- `bengal/utils/cache_registry.py`: Existing (basic) cache registry
- `bengal/core/nav_tree.py`: NavTreeCache implementation
- `bengal/rendering/context/__init__.py`: Global context caching

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Initial draft |

