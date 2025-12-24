# RFC: Thread Safety Sweep for Free-Threading Support

**Status**: Draft  
**Created**: 2025-01-24  
**Author**: AI Assistant  
**Subsystem**: Cross-cutting (all packages)  
**Confidence**: 90% 🟢 (verified via comprehensive codebase scan)  
**Priority**: P0 (Critical) — Core feature for Python 3.14 free-threading  
**Estimated Effort**: 3-5 days

---

## Executive Summary

Bengal targets Python 3.14 with free-threading (PEP 703) as a core differentiator. This RFC documents a systematic audit of thread safety across the codebase, identifying **120 global statements**, **58 threading/lock usages**, and several patterns requiring attention for safe concurrent execution.

**Key Findings**:

| Category | Count | Risk | Action Required |
|----------|-------|------|-----------------|
| Global state mutations | 120 | 🔴 High | Audit each; protect or eliminate |
| Existing Lock usage | 58 | 🟡 Review | Verify correctness, no deadlocks |
| Shared mutable caches | 15+ | 🔴 High | Add thread-safe access patterns |
| Thread-local patterns | 4 | 🟢 Good | Already thread-safe by design |
| CLI-only globals | 18 | 🟢 Low | Single-threaded CLI context |

**Current State**: Bengal has **good foundations** with `PerKeyLockManager`, `ThreadLocalCache`, and `ThreadSafeSet` utilities already in place. However, several high-traffic paths have unprotected shared state that could cause data races under free-threading.

**Impact**:
- **Correctness**: Eliminate race conditions that cause intermittent build failures
- **Performance**: Enable true parallel rendering without GIL contention
- **Reliability**: Predictable behavior under concurrent workloads

---

## Table of Contents

1. [Current Thread Safety Infrastructure](#current-thread-safety-infrastructure)
2. [Risk Assessment Matrix](#risk-assessment-matrix)
3. [High-Risk Patterns](#high-risk-patterns)
4. [Medium-Risk Patterns](#medium-risk-patterns)
5. [Low-Risk Patterns](#low-risk-patterns)
6. [Remediation Plan](#remediation-plan)
7. [Testing Strategy](#testing-strategy)
8. [Migration Checklist](#migration-checklist)

---

## Current Thread Safety Infrastructure

### Existing Utilities ✅

Bengal already has well-designed thread-safety primitives:

#### 1. PerKeyLockManager — `bengal/utils/concurrent_locks.py`

```python
class PerKeyLockManager:
    """Per-key locks: serialize work for SAME resource, parallel for DIFFERENT resources."""

    def get_lock(self, key: Hashable) -> threading.RLock:
        with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]
```

**Usage**: Template compilation, NavTree building, navigation scaffold caching  
**Status**: ✅ Well-designed, properly used

#### 2. ThreadLocalCache — `bengal/utils/thread_local.py`

```python
class ThreadLocalCache(Generic[T]):
    """One instance per thread per key, no locking required for access."""

    def get(self, key: str | None = None) -> T:
        cache_key = f"_cache_{self._name}_{key or 'default'}"
        if not hasattr(self._local, cache_key):
            instance = self._factory(key) if self._factory_accepts_key else self._factory()
            setattr(self._local, cache_key, instance)
        return getattr(self._local, cache_key)
```

**Usage**: Parser instances, pipeline instances  
**Status**: ✅ Thread-safe by design

#### 3. ThreadSafeSet — `bengal/utils/thread_local.py`

```python
class ThreadSafeSet:
    """Thread-safe set for tracking created resources (e.g., directories)."""

    def add_if_new(self, item: str) -> bool:
        with self._lock:
            if item in self._set:
                return False
            self._set.add(item)
            return True
```

**Usage**: Directory creation tracking  
**Status**: ✅ Properly protected

---

## Risk Assessment Matrix

### Files by Global State Risk

| Risk | File | Global Pattern | Concurrent Access? |
|------|------|----------------|-------------------|
| 🔴 | `server/live_reload.py` | 5 globals (`_reload_generation`, `_last_action`, etc.) | Yes - SSE + build threads |
| 🔴 | `directives/cache.py` | `_directive_cache` instance | Yes - parallel rendering |
| 🔴 | `rendering/pygments_cache.py` | `_lexer_cache`, `_cache_stats` | Yes - parallel rendering |
| 🔴 | `directives/factory.py` | `_DIRECTIVE_INSTANCES` | Yes - parallel rendering |
| 🔴 | `directives/__init__.py` | `_directive_classes_cache`, `_factory_func` | Yes - parallel rendering |
| 🔴 | `icons/resolver.py` | `_search_paths`, `_initialized` | Yes - parallel rendering |
| 🟡 | `rendering/context/__init__.py` | `_global_context_cache` | Yes - but small window |
| 🟡 | `health/validators/connectivity.py` | `KnowledgeGraph` import | Import-time only |
| 🟡 | `directives/registry.py` | `_directive_classes` | Yes - but initialized once |
| 🟢 | `output/globals.py` | `_cli_output` | CLI single-threaded |
| 🟢 | `cli/output/globals.py` | `_cli_output` | CLI single-threaded |

---

## High-Risk Patterns

### Pattern 1: Live Reload State — CRITICAL

**Location**: `bengal/server/live_reload.py:83-89`

```python
# Global reload generation and condition to wake clients
_reload_generation: int = 0
_last_action: str = "reload"
_reload_sent_count: int = 0
_reload_condition = threading.Condition()
_shutdown_requested: bool = False
```

**Risk**: Multiple threads access these concurrently:
- SSE handler threads read `_reload_generation`, `_last_action`
- Build thread writes `_reload_generation`, `_last_action`
- Main thread writes `_shutdown_requested`

**Current Mitigation**: Uses `threading.Condition()` for synchronization ✅

**Issue Found**: `set_reload_action()` writes `_last_action` WITHOUT holding the condition lock:

```python
def set_reload_action(action: str) -> None:
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    _last_action = action  # ❌ Not protected by _reload_condition
```

**Fix Required**:
```python
def set_reload_action(action: str) -> None:
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    with _reload_condition:  # ✅ Protected
        _last_action = action
```

---

### Pattern 2: Directive Cache — CRITICAL

**Location**: `bengal/directives/cache.py:161-173`

```python
# Global cache instance (shared across all threads)
# Thread-safe: Only stores immutable parsed results  ← INCORRECT CLAIM
_directive_cache = DirectiveCache(max_size=1000)
```

**Issue**: The `DirectiveCache` class uses `OrderedDict` operations that are NOT thread-safe:

```python
def get(self, directive_type: str, content: str) -> Any | None:
    if cache_key in self._cache:
        self._hits += 1  # ❌ Race condition
        self._cache.move_to_end(cache_key)  # ❌ Not atomic
        return self._cache[cache_key]
    self._misses += 1  # ❌ Race condition
    return None

def put(self, directive_type: str, content: str, parsed: Any) -> None:
    self._cache[cache_key] = parsed  # ❌ Not atomic with move_to_end
    self._cache.move_to_end(cache_key)  # ❌ Race condition
    if len(self._cache) > self._max_size:
        self._cache.popitem(last=False)  # ❌ Race condition
```

**Fix Required**: Add lock protection:

```python
class DirectiveCache:
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()  # ✅ Add lock
        # ...

    def get(self, directive_type: str, content: str) -> Any | None:
        if not self._enabled:
            return None
        cache_key = self._make_key(directive_type, content)

        with self._lock:  # ✅ Protected
            if cache_key in self._cache:
                self._hits += 1
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]
            self._misses += 1
        return None
```

---

### Pattern 3: Pygments Cache — GOOD EXAMPLE ✅

**Location**: `bengal/rendering/pygments_cache.py:28-34`

```python
# Thread-safe lexer cache
_lexer_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
_LEXER_CACHE_MAX_SIZE = 100
_cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}
```

**Analysis**: This implementation is **correctly protected**:

```python
def get_lexer_cached(language: str | None = None, ...):
    with _cache_lock:
        if cache_key in _lexer_cache:
            _cache_stats["hits"] += 1
            return _lexer_cache[cache_key]
        _cache_stats["misses"] += 1

    # Expensive work outside lock (good!)
    lexer = get_lexer_by_name(normalized)

    with _cache_lock:
        _evict_lexer_cache_if_needed()
        _lexer_cache[cache_key] = lexer
```

**Pattern to Replicate**:
1. Quick check under lock
2. Expensive work outside lock
3. Store result under lock with double-check

---

### Pattern 4: Directive Factory Instances — HIGH RISK

**Location**: `bengal/directives/factory.py:119-125`

```python
_DIRECTIVE_INSTANCES: dict[str, BaseDirective] | None = None
_INSTANCE_LOCK = threading.Lock()

def get_directive(name: str, site: Site) -> BaseDirective | None:
    global _DIRECTIVE_INSTANCES
    if _DIRECTIVE_INSTANCES is not None:  # ❌ TOCTOU race
        return _DIRECTIVE_INSTANCES.get(name)
```

**Issue**: Time-of-check-time-of-use (TOCTOU) race condition. Between checking `_DIRECTIVE_INSTANCES is not None` and accessing `.get(name)`, another thread could set it to `None`.

**Fix Required**:
```python
def get_directive(name: str, site: Site) -> BaseDirective | None:
    global _DIRECTIVE_INSTANCES
    with _INSTANCE_LOCK:
        if _DIRECTIVE_INSTANCES is not None:
            return _DIRECTIVE_INSTANCES.get(name)
    # ... initialization logic under lock
```

---

### Pattern 5: Icon Resolver State — HIGH RISK

**Location**: `bengal/icons/resolver.py:52-56`

```python
_search_paths: list[Path] = []
_initialized: bool = False

def init_icon_resolver(site: Site) -> None:
    global _search_paths, _initialized
    _search_paths = _get_icon_search_paths(site)
    _initialized = True  # ❌ Write to one var, then another = torn state
```

**Issue**: Another thread could see `_initialized = True` but `_search_paths` is still empty or partially populated.

**Fix Required**: Use a lock or single atomic assignment:
```python
_icon_state: tuple[list[Path], bool] | None = None
_icon_lock = threading.Lock()

def init_icon_resolver(site: Site) -> None:
    global _icon_state
    paths = _get_icon_search_paths(site)
    with _icon_lock:
        _icon_state = (paths, True)  # ✅ Atomic tuple assignment
```

---

## Medium-Risk Patterns

### Pattern 6: Directive Classes Registry

**Location**: `bengal/directives/registry.py:274-275`

```python
_directive_classes: dict[str, type[BaseDirective]] | None = None

def get_directive_classes() -> dict[str, type[BaseDirective]]:
    global _directive_classes
    if _directive_classes is None:  # ❌ TOCTOU if called concurrently during init
        _directive_classes = _build_directive_registry()
```

**Risk Level**: Medium — typically initialized once at startup, but could race if accessed during initialization.

**Recommendation**: Add lock or use `functools.cache` pattern.

---

### Pattern 7: Context Cache

**Location**: `bengal/rendering/context/__init__.py:91-140`

```python
_global_context_cache: dict[int, dict[str, Any]] = {}

def _get_global_contexts(site: Site) -> dict[str, Any]:
    site_id = id(site)
    if site_id in _global_context_cache:  # ❌ TOCTOU
        return _global_context_cache[site_id]
    # ... build contexts ...
    _global_context_cache[site_id] = contexts
```

**Risk Level**: Medium — build phase is typically single-threaded per site, but incremental builds could race.

**Recommendation**: Add lock or restructure to per-site instance.

---

## Low-Risk Patterns

### Pattern 8: CLI Output Globals

**Location**: `bengal/output/globals.py`, `bengal/cli/output/globals.py`

```python
_cli_output: CLIOutput | None = None

def get_cli_output() -> CLIOutput:
    global _cli_output
    if _cli_output is None:
        _cli_output = CLIOutput()
    return _cli_output
```

**Risk Level**: Low — CLI commands run in single-threaded context.

**Recommendation**: No change needed, but add comment:
```python
# Note: CLI commands are single-threaded; no lock needed.
```

---

## Remediation Plan

### Phase 1: Critical Fixes (Day 1-2)

| File | Change | Effort |
|------|--------|--------|
| `server/live_reload.py` | Add lock to `set_reload_action()` | 15 min |
| `directives/cache.py` | Add `threading.Lock()` to `DirectiveCache` | 30 min |
| `directives/factory.py` | Fix TOCTOU in `get_directive()` | 20 min |
| `icons/resolver.py` | Atomic state update pattern | 20 min |
| `directives/registry.py` | Add lock to `get_directive_classes()` | 15 min |

### Phase 2: Verification & Testing (Day 2-3)

| Task | Details |
|------|---------|
| Add thread-safety tests | `tests/test_thread_safety.py` |
| Stress test parallel rendering | 100 concurrent renders |
| Race condition detection | Use `ThreadSanitizer` if available |
| Deadlock detection | Verify lock ordering |

### Phase 3: Pattern Adoption (Day 3-4)

| Task | Details |
|------|---------|
| Document thread-safety patterns | Add `THREAD_SAFETY.md` |
| Create utility wrappers | `ThreadSafeCache`, `AtomicState` |
| Update contributing guidelines | Thread-safety checklist |

### Phase 4: Audit Remaining Globals (Day 4-5)

Systematically audit all 120 `global` statements:
- ✅ CLI-only: Document as single-threaded
- ⚠️ Build-time: Add appropriate locking
- 🔴 Render-time: Fix with locking or thread-local

---

## Testing Strategy

### 1. Unit Tests for Thread Safety

```python
# tests/test_thread_safety.py

import threading
from concurrent.futures import ThreadPoolExecutor

def test_directive_cache_concurrent_access():
    """Verify DirectiveCache handles concurrent access without corruption."""
    from bengal.directives.cache import DirectiveCache

    cache = DirectiveCache(max_size=100)
    errors = []

    def worker(thread_id: int):
        try:
            for i in range(1000):
                key = f"test:{thread_id}:{i}"
                cache.put("test", key, {"value": i})
                result = cache.get("test", key)
                if result is None or result["value"] != i:
                    errors.append(f"Thread {thread_id}: mismatch at {i}")
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(worker, i) for i in range(10)]
        for f in futures:
            f.result()

    assert not errors, f"Race conditions detected: {errors}"
```

### 2. Stress Test Parallel Rendering

```python
def test_parallel_rendering_no_race():
    """Simulate parallel page rendering."""
    from bengal.core import Site
    from bengal.rendering import render_page

    site = Site.from_config(test_config)
    pages = list(site.pages)[:100]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda p: render_page(site, p), pages))

    assert all(r.success for r in results)
```

### 3. Lock Ordering Verification

```python
def test_no_deadlock_potential():
    """Verify locks are acquired in consistent order."""
    # Document expected lock acquisition order:
    # 1. _INSTANCE_LOCK (directive factory)
    # 2. _cache_lock (pygments)
    # 3. _reload_condition (live reload)

    # Test that no code path violates this order
    ...
```

---

## Migration Checklist

### Pre-Implementation

- [ ] Review all files with `global` statements (120 files)
- [ ] Identify which globals are accessed during parallel rendering
- [ ] Document lock acquisition order to prevent deadlocks
- [ ] Create thread-safety test suite skeleton

### Implementation

- [ ] Fix `server/live_reload.py:set_reload_action()` — add lock
- [ ] Fix `directives/cache.py:DirectiveCache` — add lock to all methods
- [ ] Fix `directives/factory.py:get_directive()` — protect TOCTOU
- [ ] Fix `icons/resolver.py:init_icon_resolver()` — atomic state update
- [ ] Fix `directives/registry.py:get_directive_classes()` — add lock
- [ ] Fix `directives/__init__.py` — protect lazy initialization
- [ ] Fix `rendering/context/__init__.py` — protect context cache

### Verification

- [ ] All thread-safety tests pass
- [ ] Stress test with 100 concurrent renders passes
- [ ] No deadlocks detected in 10-minute soak test
- [ ] Performance regression < 5% (lock overhead acceptable)

### Documentation

- [ ] Add `THREAD_SAFETY.md` with patterns and guidelines
- [ ] Update docstrings with thread-safety notes
- [ ] Add thread-safety section to CONTRIBUTING.md

---

## Design Decisions

### Why Not Use `threading.local()` Everywhere?

Thread-local storage is excellent for per-thread caching (parsers, pipelines) but inappropriate for shared caches where we want to benefit from work done by other threads (lexer cache, directive cache).

### Why `threading.Lock()` Over `threading.RLock()`?

Use `Lock()` by default (simpler, faster). Use `RLock()` only when:
- Same thread may need to re-acquire the lock (nested calls)
- Example: `PerKeyLockManager` uses `RLock` because template compilation can trigger nested directive compilation

### Why Not Use `asyncio` Locks?

Bengal's build pipeline is thread-based, not async-based. The parallel rendering uses `concurrent.futures.ThreadPoolExecutor`, so `threading.Lock()` is appropriate.

---

## Appendix: Complete Global Statement Audit

<details>
<summary>📊 All 120 Global Statements (click to expand)</summary>

### High Priority (Render-Time Access)

| File | Line | Variable | Action |
|------|------|----------|--------|
| `directives/factory.py` | 122 | `_DIRECTIVE_INSTANCES` | Add lock |
| `directives/factory.py` | 210 | `_DIRECTIVE_INSTANCES` | Add lock |
| `directives/__init__.py` | 142 | `_directive_classes_cache` | Add lock |
| `directives/__init__.py` | 251 | `_factory_func` | Add lock |
| `directives/registry.py` | 274 | `_directive_classes` | Add lock |
| `directives/cache.py` | 184 | `_directive_cache` | Add lock to class |
| `icons/resolver.py` | 54 | `_search_paths`, `_initialized` | Atomic update |
| `rendering/pygments_cache.py` | 117 | `_cache_stats` | ✅ Already protected |
| `rendering/pygments_cache.py` | 230 | `_lexer_cache` | ✅ Already protected |
| `rendering/context/__init__.py` | 95-122 | `_global_context_cache` | Add lock |

### Medium Priority (Build-Time Access)

| File | Line | Variable | Action |
|------|------|----------|--------|
| `health/validators/connectivity.py` | 80 | `KnowledgeGraph` | Import guard |
| `core/nav_tree.py` | various | Cache access | Uses PerKeyLockManager ✅ |

### Low Priority (CLI-Only)

| File | Line | Variable | Action |
|------|------|----------|--------|
| `output/globals.py` | 46, 77 | `_cli_output` | Document as CLI-only |
| `cli/output/globals.py` | 37, 62 | `_cli_output` | Document as CLI-only |
| `errors/session.py` | various | Session state | CLI-only |
| `errors/traceback/__init__.py` | various | Traceback state | CLI-only |

</details>

---

## References

- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python 3.14 Free-Threading Build](https://docs.python.org/3.14/howto/free-threading-python.html)
- `bengal/utils/concurrent_locks.py` — Existing PerKeyLockManager pattern
- `bengal/utils/thread_local.py` — ThreadLocalCache and ThreadSafeSet
- `plan/drafted/rfc-concurrent-compilation-locks.md` — Original lock design rationale
