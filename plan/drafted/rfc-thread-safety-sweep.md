# RFC: Thread Safety Sweep for Free-Threading Support

**Status**: Draft  
**Created**: 2025-01-24  
**Updated**: 2025-01-24  
**Author**: AI Assistant  
**Subsystem**: Cross-cutting (all packages)  
**Confidence**: 88% 🟢 (verified via source code inspection)  
**Priority**: P0 (Critical) — Core feature for Python 3.14 free-threading  
**Estimated Effort**: 2-4 days

---

## Executive Summary

Bengal targets Python 3.14 with free-threading (PEP 703) as a core differentiator. This RFC documents a systematic audit of thread safety across the codebase, identifying **34 global mutation sites** across **19 files**, **58 threading/lock usages**, and several patterns requiring attention for safe concurrent execution.

**Key Findings**:

| Category | Count | Risk | Action Required |
|----------|-------|------|-----------------|
| Unprotected shared caches | 4 | 🔴 High | Add thread-safe access patterns |
| Global state mutations | 34 | 🟡 Audit | Review each; protect or document |
| Existing Lock usage | 58 | 🟢 Good | Verify correctness, no deadlocks |
| Correct double-check patterns | 2 | 🟢 Good | Already thread-safe |
| Thread-local patterns | 4 | 🟢 Good | Already thread-safe by design |
| CLI-only globals | 18 | 🟢 Low | Single-threaded CLI context |

**Current State**: Bengal has **strong foundations** with `PerKeyLockManager`, `ThreadLocalCache`, and `ThreadSafeSet` utilities already in place. The `pygments_cache.py` demonstrates the correct pattern. However, several high-traffic paths have unprotected shared state that could cause data races under free-threading.

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
6. [Already Correct Patterns](#already-correct-patterns)
7. [Remediation Plan](#remediation-plan)
8. [Testing Strategy](#testing-strategy)
9. [Migration Checklist](#migration-checklist)

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
| 🔴 | `directives/cache.py` | `DirectiveCache` class methods | Yes - parallel rendering |
| 🔴 | `icons/resolver.py` | `_icon_cache`, `_not_found_cache`, `_search_paths` | Yes - parallel rendering |
| 🔴 | `server/live_reload.py` | `set_reload_action()` unprotected | Yes - SSE + build threads |
| 🟡 | `rendering/context/__init__.py` | `_global_context_cache` | Yes - but small window |
| 🟡 | `directives/registry.py` | `_directive_classes` | Yes - but initialized once |
| 🟢 | `directives/factory.py` | `_DIRECTIVE_INSTANCES` | ✅ Already uses double-check locking |
| 🟢 | `rendering/pygments_cache.py` | `_lexer_cache`, `_cache_stats` | ✅ Already protected |
| 🟢 | `output/globals.py` | `_cli_output` | CLI single-threaded |
| 🟢 | `cli/output/globals.py` | `_cli_output` | CLI single-threaded |

---

## High-Risk Patterns

### Pattern 1: Directive Cache — CRITICAL

**Location**: `bengal/directives/cache.py:16-159`

```python
# Global cache instance (shared across all threads)
# Thread-safe: Only stores immutable parsed results  ← INCORRECT CLAIM
_directive_cache = DirectiveCache(max_size=1000)
```

**Issue**: The `DirectiveCache` class uses `OrderedDict` operations that are NOT thread-safe:

```python
def get(self, directive_type: str, content: str) -> Any | None:
    if cache_key in self._cache:
        self._hits += 1  # ❌ Race condition on counter
        self._cache.move_to_end(cache_key)  # ❌ Not atomic
        return self._cache[cache_key]
    self._misses += 1  # ❌ Race condition on counter
    return None

def put(self, directive_type: str, content: str, parsed: Any) -> None:
    self._cache[cache_key] = parsed  # ❌ Not atomic with move_to_end
    self._cache.move_to_end(cache_key)  # ❌ Race condition
    if len(self._cache) > self._max_size:
        self._cache.popitem(last=False)  # ❌ Race condition
```

**Fix Required**: Add lock protection following the `pygments_cache.py` pattern:

```python
class DirectiveCache:
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()  # ✅ Add lock
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._enabled = True

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

    def put(self, directive_type: str, content: str, parsed: Any) -> None:
        if not self._enabled:
            return
        cache_key = self._make_key(directive_type, content)

        with self._lock:  # ✅ Protected
            self._cache[cache_key] = parsed
            self._cache.move_to_end(cache_key)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
```

---

### Pattern 2: Icon Resolver Caches — CRITICAL

**Location**: `bengal/icons/resolver.py:37-140`

The icon resolver has **two separate thread-safety issues**:

#### Issue 2a: Torn State in `initialize()`

```python
# Lines 37-40
_search_paths: list[Path] = []
_icon_cache: dict[str, str] = {}
_not_found_cache: set[str] = set()
_initialized: bool = False

def initialize(site: Site, preload: bool = False) -> None:
    global _search_paths, _initialized
    _search_paths = _get_icon_search_paths(site)  # Write 1
    _icon_cache.clear()
    _not_found_cache.clear()
    _initialized = True  # Write 2 — ❌ Torn state between writes
```

**Risk**: Another thread could see `_initialized = True` but `_search_paths` still empty.

#### Issue 2b: Unprotected Cache Access in `load_icon()`

```python
def load_icon(name: str) -> str | None:
    if name in _icon_cache:          # ❌ TOCTOU race
        return _icon_cache[name]

    if name in _not_found_cache:     # ❌ TOCTOU race
        return None

    # ... search for icon ...

    _icon_cache[name] = content      # ❌ Unprotected write
    # ...
    _not_found_cache.add(name)       # ❌ Unprotected write
```

**Fix Required**: Use a lock for all state access:

```python
import threading

_icon_lock = threading.Lock()
_search_paths: list[Path] = []
_icon_cache: dict[str, str] = {}
_not_found_cache: set[str] = set()
_initialized: bool = False

def initialize(site: Site, preload: bool = False) -> None:
    global _search_paths, _initialized
    paths = _get_icon_search_paths(site)  # Compute outside lock

    with _icon_lock:
        _search_paths = paths
        _icon_cache.clear()
        _not_found_cache.clear()
        _initialized = True

def load_icon(name: str) -> str | None:
    with _icon_lock:
        if name in _icon_cache:
            return _icon_cache[name]
        if name in _not_found_cache:
            return None
        search_paths = _search_paths.copy() if _initialized else [_get_fallback_path()]

    # Expensive I/O outside lock
    for icons_dir in search_paths:
        icon_path = icons_dir / f"{name}.svg"
        if icon_path.exists():
            try:
                content = icon_path.read_text(encoding="utf-8")
                with _icon_lock:
                    _icon_cache[name] = content
                return content
            except OSError:
                continue

    with _icon_lock:
        _not_found_cache.add(name)
    return None
```

---

### Pattern 3: Live Reload State — CRITICAL

**Location**: `bengal/server/live_reload.py:83-89, 621-639`

```python
# Lines 83-89: Global reload state
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

**Current Mitigation**: Uses `threading.Condition()` for most operations ✅

**Issue Found**: `set_reload_action()` (lines 621-639) writes `_last_action` WITHOUT holding the condition lock:

```python
def set_reload_action(action: str) -> None:
    """Set the next reload action type for SSE clients."""
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    _last_action = action  # ❌ Line 638: Not protected by _reload_condition
    logger.debug("reload_action_set", action=_last_action)
```

**Fix Required**:

```python
def set_reload_action(action: str) -> None:
    """Set the next reload action type for SSE clients."""
    global _last_action
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    with _reload_condition:  # ✅ Protected
        _last_action = action
    logger.debug("reload_action_set", action=action)
```

---

## Medium-Risk Patterns

### Pattern 4: Directive Classes Registry

**Location**: `bengal/directives/registry.py:263-277`

```python
_directive_classes: list[type] | None = None

def _get_directive_classes() -> list[type]:
    global _directive_classes
    if _directive_classes is None:  # ❌ TOCTOU if called concurrently during init
        _directive_classes = get_directive_classes()
    return _directive_classes
```

**Risk Level**: Medium — typically initialized once at startup, but could race if accessed during initialization.

**Recommendation**: Add lock or use `functools.cache` pattern:

```python
import threading

_directive_classes: list[type] | None = None
_registry_lock = threading.Lock()

def _get_directive_classes() -> list[type]:
    global _directive_classes
    if _directive_classes is not None:
        return _directive_classes

    with _registry_lock:
        if _directive_classes is not None:  # Double-check
            return _directive_classes
        _directive_classes = get_directive_classes()
        return _directive_classes
```

---

### Pattern 5: Context Cache

**Location**: `bengal/rendering/context/__init__.py:100-133`

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

**Recommendation**: Add lock or restructure to per-site instance:

```python
import threading

_global_context_cache: dict[int, dict[str, Any]] = {}
_context_lock = threading.Lock()

def _get_global_contexts(site: Site) -> dict[str, Any]:
    site_id = id(site)

    with _context_lock:
        if site_id in _global_context_cache:
            return _global_context_cache[site_id]

    # Build contexts outside lock (expensive)
    theme_obj = site.theme_config if hasattr(site, "theme_config") else None
    contexts = {
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj else ThemeContext._empty(),
        "menus": MenusContext(site),
    }

    with _context_lock:
        # Double-check: another thread may have built while we computed
        if site_id not in _global_context_cache:
            _global_context_cache[site_id] = contexts
        return _global_context_cache[site_id]
```

---

## Low-Risk Patterns

### Pattern 6: CLI Output Globals

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

**Recommendation**: No change needed, but add comment for clarity:

```python
# Note: CLI commands are single-threaded; no lock needed.
_cli_output: CLIOutput | None = None
```

---

## Already Correct Patterns

### Pattern 7: Directive Factory — CORRECTLY PROTECTED ✅

**Location**: `bengal/directives/factory.py:110-130`

```python
_DIRECTIVE_INSTANCES: list[Any] | None = None
_INSTANCE_LOCK = Lock()

def _get_directive_instances() -> list[Any]:
    global _DIRECTIVE_INSTANCES
    if _DIRECTIVE_INSTANCES is not None:  # Fast path (safe read)
        return _DIRECTIVE_INSTANCES

    with _INSTANCE_LOCK:
        # Double-check after acquiring lock
        if _DIRECTIVE_INSTANCES is not None:
            return _DIRECTIVE_INSTANCES

        _DIRECTIVE_INSTANCES = [...]  # Build list
        return _DIRECTIVE_INSTANCES
```

**Status**: ✅ Uses correct double-check locking pattern. No fix needed.

**Why This Is Safe**:
1. First check without lock only returns if already initialized (immutable read)
2. Never mutates without holding the lock
3. Double-check inside lock prevents race on initialization
4. Assignment to `_DIRECTIVE_INSTANCES` is atomic in Python

---

### Pattern 8: Pygments Cache — CORRECTLY PROTECTED ✅

**Location**: `bengal/rendering/pygments_cache.py:28-34, 90-225`

```python
# Thread-safe lexer cache
_lexer_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
_LEXER_CACHE_MAX_SIZE = 100
_cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}
```

**Analysis**: This implementation demonstrates the **correct pattern**:

```python
def get_lexer_cached(language: str | None = None, ...):
    # Check cache under lock
    with _cache_lock:
        if cache_key in _lexer_cache:
            _cache_stats["hits"] += 1
            return _lexer_cache[cache_key]
        _cache_stats["misses"] += 1

    # Expensive work OUTSIDE lock (good!)
    lexer = get_lexer_by_name(normalized)

    # Store under lock
    with _cache_lock:
        _evict_lexer_cache_if_needed()
        _lexer_cache[cache_key] = lexer
    return lexer
```

**Pattern to Replicate**:
1. Quick check under lock
2. Expensive work outside lock  
3. Store result under lock

---

## Remediation Plan

### Phase 1: Critical Fixes (Day 1)

| File | Change | Effort |
|------|--------|--------|
| `directives/cache.py` | Add `threading.Lock()` to `DirectiveCache` class | 30 min |
| `icons/resolver.py` | Add `_icon_lock` for all state access | 45 min |
| `server/live_reload.py` | Add lock to `set_reload_action()` (line 638) | 10 min |

### Phase 2: Medium Priority Fixes (Day 1-2)

| File | Change | Effort |
|------|--------|--------|
| `directives/registry.py` | Add lock to `_get_directive_classes()` | 15 min |
| `rendering/context/__init__.py` | Add lock to `_get_global_contexts()` | 20 min |

### Phase 3: Verification & Testing (Day 2-3)

| Task | Details |
|------|---------|
| Add thread-safety tests | `tests/test_thread_safety.py` |
| Stress test parallel rendering | 100 concurrent renders |
| Race condition detection | Use `ThreadSanitizer` if available |
| Deadlock detection | Verify lock ordering |

### Phase 4: Documentation (Day 3-4)

| Task | Details |
|------|---------|
| Document thread-safety patterns | Add `THREAD_SAFETY.md` |
| Update docstrings | Add thread-safety notes to protected modules |
| Update contributing guidelines | Thread-safety checklist |

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
                # Note: result may be None due to LRU eviction, that's OK
                if result is not None and result["value"] != i:
                    errors.append(f"Thread {thread_id}: value mismatch at {i}")
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(worker, i) for i in range(10)]
        for f in futures:
            f.result()

    assert not errors, f"Race conditions detected: {errors}"


def test_icon_resolver_concurrent_load():
    """Verify icon resolver handles concurrent access safely."""
    from bengal.icons import resolver

    errors = []
    results = {}
    results_lock = threading.Lock()

    def worker(thread_id: int):
        try:
            for icon_name in ["warning", "info", "success", "error"]:
                content = resolver.load_icon(icon_name)
                with results_lock:
                    if icon_name in results:
                        if results[icon_name] != content:
                            errors.append(f"Thread {thread_id}: {icon_name} inconsistent")
                    else:
                        results[icon_name] = content
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
    # 1. _icon_lock (icon resolver)
    # 2. DirectiveCache._lock
    # 3. _cache_lock (pygments)
    # 4. _reload_condition (live reload)
    #
    # No code path should acquire these in reverse order.
    ...
```

---

## Migration Checklist

### Pre-Implementation

- [ ] Review all files with `global` statements (19 files, 34 sites)
- [ ] Identify which globals are accessed during parallel rendering
- [ ] Document lock acquisition order to prevent deadlocks
- [ ] Create thread-safety test suite skeleton

### Implementation

- [ ] Fix `directives/cache.py:DirectiveCache` — add lock to all methods
- [ ] Fix `icons/resolver.py` — add `_icon_lock` for all state access
- [ ] Fix `server/live_reload.py:set_reload_action()` — add lock (line 638)
- [ ] Fix `directives/registry.py:_get_directive_classes()` — add lock
- [ ] Fix `rendering/context/__init__.py:_get_global_contexts()` — add lock
- [ ] Update comment in `directives/cache.py` — remove incorrect "Thread-safe" claim

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

Thread-local storage is excellent for per-thread caching (parsers, pipelines) but inappropriate for shared caches where we want to benefit from work done by other threads (lexer cache, directive cache, icon cache).

### Why `threading.Lock()` Over `threading.RLock()`?

Use `Lock()` by default (simpler, faster). Use `RLock()` only when:
- Same thread may need to re-acquire the lock (nested calls)
- Example: `PerKeyLockManager` uses `RLock` because template compilation can trigger nested directive compilation

### Why Not Use `asyncio` Locks?

Bengal's build pipeline is thread-based, not async-based. The parallel rendering uses `concurrent.futures.ThreadPoolExecutor`, so `threading.Lock()` is appropriate.

### Lock Acquisition Order (Deadlock Prevention)

When multiple locks must be held, always acquire in this order:

1. `_icon_lock` (icon resolver)
2. `DirectiveCache._lock` (directive cache)
3. `_cache_lock` (pygments cache)
4. `_context_lock` (context cache)
5. `_registry_lock` (directive registry)
6. `_reload_condition` (live reload)

No code path should acquire these in reverse order.

---

## Appendix: Complete Global Statement Audit

<details>
<summary>📊 All Global Mutation Sites (click to expand)</summary>

### Critical Priority (Parallel Rendering)

| File | Line | Variable | Status |
|------|------|----------|--------|
| `directives/cache.py` | 163 | `_directive_cache` | ❌ Add lock to class |
| `icons/resolver.py` | 37-40 | `_search_paths`, `_icon_cache`, `_not_found_cache`, `_initialized` | ❌ Add lock |
| `server/live_reload.py` | 638 | `_last_action` (in `set_reload_action`) | ❌ Add lock |

### Medium Priority (Build-Time)

| File | Line | Variable | Status |
|------|------|----------|--------|
| `directives/registry.py` | 274 | `_directive_classes` | ❌ Add lock |
| `rendering/context/__init__.py` | 100-132 | `_global_context_cache` | ❌ Add lock |

### Already Protected ✅

| File | Line | Variable | Status |
|------|------|----------|--------|
| `directives/factory.py` | 110-130 | `_DIRECTIVE_INSTANCES` | ✅ Double-check locking |
| `rendering/pygments_cache.py` | 29-34 | `_lexer_cache`, `_cache_stats` | ✅ Lock protected |
| `server/live_reload.py` | 548-551 | `_reload_generation` (in `notify_clients_reload`) | ✅ Condition protected |
| `server/live_reload.py` | 604-608 | `_last_action` (in `send_reload_payload`) | ✅ Condition protected |

### Low Priority (CLI-Only)

| File | Line | Variable | Status |
|------|------|----------|--------|
| `output/globals.py` | 46, 77 | `_cli_output` | 🟢 Document as CLI-only |
| `cli/output/globals.py` | 37, 62 | `_cli_output` | 🟢 Document as CLI-only |
| `errors/session.py` | various | Session state | 🟢 CLI-only |

</details>

---

## References

- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python 3.14 Free-Threading Build](https://docs.python.org/3.14/howto/free-threading-python.html)
- `bengal/utils/concurrent_locks.py` — Existing PerKeyLockManager pattern
- `bengal/utils/thread_local.py` — ThreadLocalCache and ThreadSafeSet
- `bengal/rendering/pygments_cache.py` — Reference implementation for cache locking
- `plan/drafted/rfc-concurrent-compilation-locks.md` — Original lock design rationale
