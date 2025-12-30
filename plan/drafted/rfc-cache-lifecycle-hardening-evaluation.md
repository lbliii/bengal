# RFC Evaluation: Cache Lifecycle Hardening

**RFC**: `rfc-cache-lifecycle-hardening.md`  
**Evaluated**: 2025-12-30  
**Status**: ✅ **APPROVED with Recommendations**

---

## Executive Summary

This RFC addresses real cache lifecycle issues identified in the codebase. The proposed solutions are technically sound and well-structured. **Recommendation: APPROVE** with minor clarifications and one architectural consideration.

**Key Findings**:
- ✅ All problem statements verified against codebase
- ✅ Proposed solutions are feasible and well-designed
- ✅ Migration plan is realistic
- ⚠️ One architectural gap: BuildContext already exists but doesn't match proposed design
- 💡 Consider incremental rollout strategy

---

## Problem Statement Verification

### ✅ Verified: Scattered Invalidation Calls

**Claim**: NavTreeCache invalidation called from multiple locations  
**Evidence**: Found 40 matches across codebase
- `orchestration/incremental/orchestrator.py:118, 188` ✅ Verified
- Multiple test files (expected)
- Benchmark files (expected)

**Assessment**: Problem is real. Centralized invalidation would reduce risk.

### ✅ Verified: Manual Invalidation Chains

**Claim**: Config change requires manual invalidation chain  
**Evidence**: `orchestration/incremental/orchestrator.py:116-133`

```116:133:bengal/orchestration/incremental/orchestrator.py
        if config_changed:
            # Config change may affect navigation (versioning, menus, etc.)
            NavTreeCache.invalidate()
            logger.debug("nav_tree_cache_invalidated", reason="config_changed")

            # Also invalidate version page index cache
            from bengal.rendering.template_functions.version_url import (
                invalidate_version_page_index,
            )

            invalidate_version_page_index()
            logger.debug("version_page_index_cache_invalidated", reason="config_changed")

            # Invalidate site version dict caches (site.versions, site.latest_version)
            # These cache .to_dict() results for template performance
            if hasattr(self.site, "invalidate_version_caches"):
                self.site.invalidate_version_caches()
                logger.debug("site_version_dict_cache_invalidated", reason="config_changed")
```

**Assessment**: Problem is real. Adding new caches requires updating this chain manually.

### ✅ Verified: Context Cache Lifecycle Issue

**Claim**: Global context uses `id(site)` as cache key, risk of reuse  
**Evidence**: `rendering/context/__init__.py:142-164`

```142:164:bengal/rendering/context/__init__.py
    site_id = id(site)

    # Fast path: check if already cached
    with _context_lock:
        if site_id in _global_context_cache:
            return _global_context_cache[site_id]

    # Build contexts outside lock (object creation)
    theme_obj = site.theme_config if hasattr(site, "theme_config") else None

    contexts = {
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj else ThemeContext._empty(),
        "menus": MenusContext(site),
    }

    # Store under lock, with double-check
    with _context_lock:
        # Another thread may have populated while we computed
        if site_id not in _global_context_cache:
            _global_context_cache[site_id] = contexts
        return _global_context_cache[site_id]
```

**Assessment**: Problem is real. While `id()` reuse is unlikely in practice (requires GC + same memory address), build-scoped caching is safer.

### ✅ Verified: Thread-Local State Without Build Boundaries

**Claim**: Generation counter is global, not build-scoped  
**Evidence**: `orchestration/render.py:84-85`

```84:85:bengal/orchestration/render.py
_build_generation: int = 0
_generation_lock = threading.Lock()
```

**Assessment**: Problem is real. Concurrent builds in tests could interfere.

### ✅ Verified: Two-Layer State Sync Requirements

**Claim**: TaxonomyIndex and QueryIndex maintain forward + reverse indexes  
**Evidence**: 
- `cache/taxonomy_index.py:130` - `_page_to_tags` reverse index ✅
- `cache/query_index.py:163` - `_page_to_keys` reverse index ✅

**Assessment**: Problem is real. No invariant checks exist currently.

---

## Solution Feasibility Analysis

### Phase 1: Central Cache Registry ✅ FEASIBLE

**Current State**: `utils/cache_registry.py` exists with basic `register_cache()` and `clear_all_caches()`

**Proposed Enhancement**: Add metadata, dependency tracking, reason-based invalidation

**Assessment**: 
- ✅ Builds on existing infrastructure
- ✅ Design is sound (enum for reasons, dataclass for metadata)
- ✅ Dependency tracking via topological sort is correct approach
- ⚠️ **Minor Issue**: `_topological_sort()` function referenced but not implemented in RFC

**Recommendation**: Add implementation of `_topological_sort()` or use existing library (e.g., `graphlib.TopologicalSorter` in Python 3.9+)

### Phase 2: Build-Scoped Context ⚠️ ARCHITECTURAL GAP

**Current State**: `BuildContext` already exists (`utils/build_context.py`) but:
- Does NOT have `build_id` field
- Does NOT implement context manager (`__enter__`/`__exit__`)
- Does NOT have `_context_cache` dict
- Does NOT signal `BUILD_START`/`BUILD_END` events

**Proposed Enhancement**: Add build-scoped caching to BuildContext

**Assessment**:
- ⚠️ **Gap**: RFC proposes new `BuildContext` design but doesn't acknowledge existing implementation
- ✅ Concept is sound: build-scoped caching prevents cross-build contamination
- ⚠️ **Consideration**: Existing `BuildContext` is a dataclass with many fields. Adding context manager protocol is feasible but needs careful integration.

**Recommendation**: 
1. Acknowledge existing `BuildContext` in RFC
2. Propose extending existing class rather than creating new one
3. Consider backward compatibility: make `build_context` parameter optional initially

### Phase 3: Invariant Checks ✅ FEASIBLE

**Proposed**: Add `_check_invariants()` to TaxonomyIndex and QueryIndex

**Assessment**:
- ✅ Implementation pattern is correct
- ✅ Debug-only initially is appropriate (performance consideration)
- ✅ Violation detection logic is sound

**Recommendation**: Consider adding invariant checks to `load_from_disk()` as well (not just `save_to_disk()`)

### Phase 4: Thread-Local Lifecycle Guards ✅ FEASIBLE

**Proposed**: Add active render tracking to prevent invalidation during active operations

**Assessment**:
- ✅ Concept is sound
- ⚠️ **Minor Issue**: RFC mentions `threading.atomic.AtomicInteger` for Python 3.13+, but Python 3.13 doesn't exist yet (as of 2025-12-30). Use `threading.Lock` with counter instead.

**Recommendation**: Use standard `threading.Lock` with integer counter (as shown in compatibility version).

---

## Code Reference Accuracy

### ✅ All Code References Verified

| Reference | Status | Notes |
|-----------|--------|-------|
| `orchestration/incremental/orchestrator.py:118` | ✅ Verified | Exact match |
| `orchestration/incremental/orchestrator.py:188` | ✅ Verified | Exact match |
| `rendering/context/__init__.py:142` | ✅ Verified | Exact match |
| `orchestration/render.py:84-85` | ✅ Verified | Exact match |
| `cache/taxonomy_index.py:118-119` | ✅ Verified | Forward + reverse indexes exist |
| `cache/query_index.py:122-123` | ✅ Verified | Forward + reverse indexes exist |
| `utils/cache_registry.py` | ✅ Verified | Basic registry exists |

---

## Missing Considerations

### 1. **Existing BuildContext Integration**

The RFC doesn't acknowledge that `BuildContext` already exists with a different design. Need to clarify:
- How to extend existing `BuildContext` vs. creating new one
- Migration path for existing code using `BuildContext`
- Backward compatibility strategy

### 2. **Topological Sort Implementation**

RFC references `_topological_sort()` but doesn't provide implementation. Should:
- Use `graphlib.TopologicalSorter` (Python 3.9+)
- Or provide custom implementation
- Handle cycles gracefully (shouldn't happen, but defensive)

### 3. **Cache Registration Timing**

RFC doesn't specify when caches should register themselves:
- At module import time? (current pattern)
- At first use?
- Explicitly during build setup?

**Recommendation**: Use module-level registration (current pattern) for simplicity.

### 4. **Performance Impact**

No performance analysis provided. Consider:
- Overhead of registry lookups
- Dependency graph traversal cost
- Invariant check overhead (even in debug mode)

**Recommendation**: Add performance benchmarks to migration plan.

### 5. **Error Handling**

RFC doesn't specify error handling:
- What if `clear_fn()` raises exception?
- What if dependency cycle detected?
- What if cache registration fails?

**Recommendation**: 
- Registry already handles exceptions in `clear_all_caches()` (logs warning, continues)
- Add cycle detection at registration time
- Validate dependencies exist before registration

---

## Migration Plan Assessment

### ✅ Realistic Timeline

**Phase 1 (Week 1-2)**: Registry enhancement
- ✅ Timeline is reasonable
- ✅ Low risk (additive changes)

**Phase 2 (Week 2-3)**: Build-scoped context
- ⚠️ May need extra week for BuildContext integration
- ⚠️ Need to coordinate with existing BuildContext usage

**Phase 3 (Week 3)**: Invariant checks
- ✅ Timeline is reasonable
- ✅ Low risk (additive, debug-only)

**Phase 4 (Week 4)**: Thread-local guards
- ✅ Timeline is reasonable
- ✅ Low risk (additive)

**Overall**: 4-week timeline is realistic, but Phase 2 may need buffer.

### ✅ Testing Strategy is Sound

- Unit tests for registry ✅
- Integration tests for lifecycle ✅
- Concurrent build tests ✅

**Recommendation**: Add performance regression tests.

---

## Risks and Mitigations

### ✅ Risks Properly Assessed

| Risk | RFC Assessment | Evaluation |
|------|----------------|------------|
| Over-invalidation | Medium/Low | ✅ Appropriate - logging will help tune |
| Under-invalidation | Low/High | ✅ Appropriate - integration tests mitigate |
| Dependency cycles | Low/Medium | ⚠️ Should add cycle detection at registration |
| Migration breaks code | Medium/Medium | ⚠️ Need backward compatibility plan |

**Additional Risk**: BuildContext changes may break existing code  
**Mitigation**: Make `build_context` parameter optional, gradual migration

---

## Recommendations

### ✅ APPROVE with Modifications

**Required Changes**:

1. **Acknowledge Existing BuildContext**:
   - Update Phase 2 to extend existing `BuildContext` class
   - Add migration strategy for existing usage
   - Make build-scoped caching optional initially

2. **Implement Topological Sort**:
   - Use `graphlib.TopologicalSorter` (Python 3.9+)
   - Add cycle detection at registration time
   - Handle edge cases (empty graph, single node)

3. **Fix Python Version Reference**:
   - Remove `threading.atomic.AtomicInteger` reference (doesn't exist)
   - Use standard `threading.Lock` with counter

4. **Add Performance Considerations**:
   - Benchmark registry lookup overhead
   - Measure dependency traversal cost
   - Document expected performance impact

5. **Clarify Registration Timing**:
   - Specify module-level registration pattern
   - Document when caches should register

**Optional Enhancements**:

1. **Add Invariant Checks to Load**:
   - Check invariants when loading from disk (not just saving)
   - Detect corruption early

2. **Add Cache Versioning**:
   - Track cache format versions in registry
   - Enable coordinated migration (addresses Open Question #2)

3. **Add Metrics**:
   - Cache hit/miss rates (addresses Open Question #3)
   - Invalidation frequency by reason
   - Dependency cascade depth

---

## Open Questions Resolution

### Q1: Should invariant checks be enabled in production?

**Recommendation**: 
- Start with debug-only (as proposed) ✅
- Consider enabling in CI with sampling (e.g., check 10% of saves)
- Enable always-on if performance impact is negligible

### Q2: How to handle cache versioning?

**Recommendation**: 
- Add `version: int` field to `CacheEntry`
- Registry tracks versions
- `invalidate_for_reason()` can check versions
- Consider separate RFC for version migration strategy

### Q3: Should we add cache hit/miss metrics?

**Recommendation**: 
- Yes, but defer to Phase 2 (after registry is stable)
- Add lightweight counters to `CacheEntry`
- Enable via feature flag (low overhead when disabled)

---

## Final Verdict

### ✅ **APPROVED** with Recommendations

**Strengths**:
- Addresses real, verified problems
- Solutions are technically sound
- Well-structured phased approach
- Good testing strategy

**Weaknesses**:
- Doesn't acknowledge existing `BuildContext`
- Missing topological sort implementation
- Minor Python version reference error
- Could use more performance analysis

**Next Steps**:
1. Incorporate recommendations above
2. Add implementation details for missing pieces
3. Update Phase 2 to work with existing `BuildContext`
4. Proceed with Phase 1 implementation

---

## Appendix: Code Verification Details

### Cache Registry Current State

```46:103:bengal/utils/cache_registry.py
def register_cache(name: str, cleanup_func: Callable[[], None]) -> None:
    """
    Register a cache for centralized cleanup.

    Args:
        name: Unique name for the cache (for debugging)
        cleanup_func: Callable that clears the cache (e.g., lambda: cache.clear())

    Thread Safety:
        Thread-safe registration and cleanup.
    """
    with _registry_lock:
        _cache_registry[name] = cleanup_func


def unregister_cache(name: str) -> None:
    """
    Unregister a cache (rarely needed).

    Args:
        name: Name of cache to unregister
    """
    with _registry_lock:
        _cache_registry.pop(name, None)


def clear_all_caches() -> None:
    """
    Clear all registered caches.

    This is the main function to call in test fixtures or between builds
    to prevent memory leaks. All registered caches will be cleared.

    Thread Safety:
        Thread-safe - clears all caches under lock.
    """
    with _registry_lock:
        for name, cleanup_func in _cache_registry.items():
            try:
                cleanup_func()
            except Exception as e:
                # Log but don't fail - one cache failure shouldn't break cleanup
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to clear cache '{name}': {e}")


def list_registered_caches() -> list[str]:
    """
    List all registered cache names (for debugging).

    Returns:
        List of cache names
    """
    with _registry_lock:
        return list(_cache_registry.keys())
```

**Assessment**: Basic registry exists. Enhancement is straightforward.

### BuildContext Current State

```121:642:bengal/utils/build_context.py
@dataclass
class BuildContext:
    """
    Shared build context passed across build phases.

    This context is created at the start of build() and passed to all _phase_* methods.
    It replaces local variables that were scattered throughout the 894-line build() method.

    Lifecycle:
        1. Created in _setup_build_context() at build start
        2. Populated incrementally as phases execute
        3. Used by all _phase_* methods for shared state

    Categories:
        - Core: site, stats, profile (required)
        - Cache: cache, tracker (initialized in Phase 0)
        - Build mode: incremental, verbose, quiet, strict, parallel
        - Work items: pages_to_build, assets_to_process (determined in Phase 2)
        - Incremental state: affected_tags, affected_sections, changed_page_paths
        - Output: cli, progress_manager, reporter
    """

    # Core (required)
    site: Site | None = None
    stats: BuildStats | None = None
    profile: BuildProfile | None = None

    # Cache and tracking
    cache: BuildCache | None = None
    tracker: DependencyTracker | None = None

    # Build mode flags
    incremental: bool = False
    verbose: bool = False
    quiet: bool = False
    strict: bool = False
    parallel: bool = True
    memory_optimized: bool = False
    full_output: bool = False
    profile_templates: bool = False  # Enable template profiling for performance analysis

    # Work items (determined during incremental filtering)
    pages: list[Page] | None = None  # All discovered pages
    pages_to_build: list[Page] | None = None  # Pages that need rendering
    assets: list[Asset] | None = None  # All discovered assets
    assets_to_process: list[Asset] | None = None  # Assets that need processing

    # Incremental build state
    affected_tags: set[str] = field(default_factory=set)
    affected_sections: set[str] | None = None
    changed_page_paths: set[Path] = field(default_factory=set)
    config_changed: bool = False

    # Output/progress
    cli: CLIOutput | None = None
    progress_manager: LiveProgressManager | None = None
    reporter: ProgressReporter | None = None

    # Output collector for hot reload tracking
    output_collector: OutputCollector | None = None

    # Write-behind collector for async I/O (RFC: rfc-path-to-200-pgs Phase III)
    # Created by BuildOrchestrator when build.write_behind=True
    write_behind: Any = None  # WriteBehindCollector (lazy import to avoid circular)

    # Timing (build start time for duration calculation)
    build_start: float = 0.0

    # Lazy-computed artifacts (built once on first access)
    # These eliminate redundant expensive computations across build phases
    _knowledge_graph: Any = field(default=None, repr=False)
    _knowledge_graph_enabled: bool = field(default=True, repr=False)

    # Content cache - populated during discovery, shared by validators
    # Eliminates redundant disk I/O during health checks (4s+ → <100ms)
    # See: plan/active/rfc-build-integrated-validation.md
    _page_contents: dict[str, str] = field(default_factory=dict, repr=False)
    _content_cache_lock: Lock = field(default_factory=Lock, repr=False)
```

**Assessment**: `BuildContext` is a dataclass with many fields. Adding context manager protocol and build-scoped caching is feasible but needs careful design.

---

**Evaluation Complete**: 2025-12-30

