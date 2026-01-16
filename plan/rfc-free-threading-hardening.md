# RFC: Free Threading Hardening

**Status**: Evaluated ✅  
**Created**: 2026-01-16  
**Evaluated**: 2026-01-16  
**Author**: Claude Opus 4.5  
**Confidence**: 95% 🟢  
**Category**: Concurrency / Thread Safety / PEP 703

> **Evaluation Summary**: All evidence claims verified against codebase. 5 `@lru_cache` usages confirmed, singleton races verified at exact locations, existing thread-safe primitives (`LRUCache`, `ThreadSafeSet`, `PerKeyLockManager`) ready for use. Ready for `::plan`.

---

## Executive Summary

Bengal targets Python 3.14+ which includes free threading (PEP 703 - no GIL). A comprehensive audit reveals **6 thread-safety issues** that would cause data corruption or race conditions when running with `PYTHON_GIL=0`:

| Severity | Count | Impact |
|----------|-------|--------|
| 🔴 CRITICAL | 4 | Data corruption, cache inconsistency |
| 🟠 MODERATE | 1 | Partial reconfiguration during use |
| 🟡 LOW | 1 | Stale reads (cosmetic) |

**Good news**: Bengal already has excellent free-threading patterns in place:
- Custom thread-safe `LRUCache` with RLock
- `ContextVar` usage for thread-local state
- `PerKeyLockManager` for per-resource locking
- Context propagation to ThreadPoolExecutor workers

**Target**: Zero thread-safety issues for free-threaded Python deployment.

---

## Goals & Non-Goals

### Goals

1. **Fix all identified thread-safety issues** — Replace unsafe patterns with Bengal's existing thread-safe primitives
2. **Maintain API compatibility** — No changes to public interfaces or behavior
3. **Minimal code churn** — Targeted fixes only, no speculative refactoring
4. **Add validation** — CI job with `PYTHON_GIL=0` and stress tests

### Non-Goals

- **Full immutable architecture** — Would require major refactor with diminishing returns
- **Runtime thread-safety detection** — Debug overhead not justified for known issues
- **Async migration** — Free threading is orthogonal to async/await patterns
- **Performance optimization** — Focus is correctness; benchmark after to verify no regression

---

## Problem Statement

### What is Free Threading?

Python 3.13+ (experimental) and 3.14+ (stable) support running without the Global Interpreter Lock (GIL). This enables true parallelism in `ThreadPoolExecutor` but exposes race conditions that were previously masked by the GIL.

### Bengal's Parallel Architecture

Bengal uses `ThreadPoolExecutor` extensively for parallel rendering:

```
BuildOrchestrator
    └── RenderOrchestrator._render_pages_parallel()
            └── ThreadPoolExecutor(max_workers=N)
                    ├── Worker 1: render(page_1)
                    ├── Worker 2: render(page_2)
                    └── Worker N: render(page_N)
```

Under the GIL, these workers serialize on Python bytecode execution. Without the GIL, they execute **truly in parallel**, exposing:

1. **TOCTOU races**: Check-then-act patterns on shared state
2. **Dict corruption**: Concurrent dict modifications
3. **Lost updates**: Non-atomic increment/assignment operations
4. **Cache inconsistency**: `@lru_cache` internal dict corruption

---

## Evidence

### Audit Methodology

```bash
# 1. Grep for global mutable state
grep -r "^_[a-z_]+\s*=" bengal/

# 2. Find lock usage patterns
grep -r "threading\.(Lock|RLock)" bengal/

# 3. Identify @lru_cache usage (known thread-unsafe under free-threading)
grep -rn "@lru_cache" bengal/ --include="*.py"

# 4. Find singleton patterns
grep -r "global _" bengal/

# 5. Find module-level mutable collections
grep -rn "^_[a-z_]*:\s*\(dict\|set\|list\)\[" bengal/ --include="*.py"
```

**Verified counts** (2026-01-16):
- `@lru_cache` usages: **5** (all in rendering/autodoc paths)
- Singleton patterns: **3** (registry, logger, directive cache)
- Protected by locks: **12** modules already use RLock/Lock

### Issue 1: `@lru_cache` Is Not Thread-Safe 🔴

**Severity**: CRITICAL  
**Impact**: Cache corruption, wrong return values, crashes

Python's `functools.lru_cache` uses an internal dict without locking. Under free threading, concurrent access corrupts the cache structure.

**Evidence** (5 occurrences):

| File | Function | Line | Max Size |
|------|----------|------|----------|
| `bengal/autodoc/base.py` | `_cached_param_info` | 42 | 1024 |
| `bengal/rendering/template_functions/icons.py` | `_render_icon_cached` | 59 | 512 |
| `bengal/assets/css/__init__.py` | `get_directive_base_css` | 32 | 1 |
| `bengal/core/theme/registry.py` | `get_installed_themes` | 248 | 1 |
| `bengal/directives/_icons.py` | `render_svg_icon` | 89 | 512 |

**Code sample** (`bengal/autodoc/base.py:42`):

```python
@lru_cache(maxsize=1024)  # NOT thread-safe!
def _cached_param_info(
    name: str,
    type_hint: str | None,
    default: str | None,
    description: str | None,
) -> ParamInfo:
    ...
```

**Why this matters**: Autodoc rendering happens in parallel. Multiple workers calling `_cached_param_info` simultaneously will corrupt the cache.

---

### Issue 2: Singleton Race in `scaffolds/registry.py` 🔴

**Severity**: CRITICAL  
**Impact**: Duplicate registries, lost template registrations

**Evidence** (`bengal/scaffolds/registry.py:258-272`):

```python
_registry: TemplateRegistry | None = None

def _get_registry() -> TemplateRegistry:
    global _registry
    if _registry is None:      # Thread A: checks, sees None
        _registry = TemplateRegistry()  # Thread B: also creates!
    return _registry           # Thread A: returns Thread B's instance
```

Classic TOCTOU (Time-Of-Check-Time-Of-Use) race. Two threads can both see `None` and create separate registry instances.

---

### Issue 3: Logger Registry Unprotected 🔴

**Severity**: CRITICAL  
**Impact**: Dict corruption, lost loggers, crashes

**Evidence** (`bengal/utils/observability/logger.py`):

```python
# Line 685-687: get_logger modifies dict without lock
def get_logger(name: str) -> BengalLogger:
    if name not in _lazy_loggers:  # Check
        _lazy_loggers[name] = LazyLogger(name)  # Act - RACE!
    return _lazy_loggers[name]

# Line 714-724: reset_loggers modifies multiple globals
def reset_loggers() -> None:
    global _registry_version
    close_all_loggers()
    _loggers.clear()           # No lock!
    _lazy_loggers.clear()      # No lock!
    _registry_version += 1     # Non-atomic increment!
```

Additional unprotected operations:
- `configure_logging()` iterates `_loggers` while modifying `_global_config`
- `set_console_quiet()` iterates `_loggers` without lock

---

### Issue 4: Unprotected Set in `rendering/assets.py` 🔴

**Severity**: HIGH  
**Impact**: Set corruption, duplicate warnings

**Evidence** (`bengal/rendering/assets.py:51`):

```python
_fallback_warned: set[str] = set()  # Module-level mutable set
```

Modified without lock in `resolve_asset_url()`:

```python
if logical_path not in _fallback_warned:
    _fallback_warned.add(logical_path)  # RACE: two threads add same item
    logger.debug(...)
```

Bengal already has `ThreadSafeSet` in `utils/concurrency/thread_local.py` that could be used here.

---

### Issue 5: Directive Cache Configuration Race 🟠

**Severity**: MODERATE  
**Impact**: Partial reconfiguration during active use

**Evidence** (`bengal/directives/cache.py:149-156`):

```python
def configure_cache(max_size: int | None = None, ...) -> None:
    global _directive_cache
    if max_size is not None:
        was_enabled = _directive_cache._cache.enabled  # Read old
        _directive_cache = DirectiveCache(max_size=max_size)  # Replace
        # Another thread may still reference old instance!
```

Less critical because `configure_cache()` is typically called at startup, not during builds.

---

### Issue 6: Live Reload Action Read 🟡

**Severity**: LOW  
**Impact**: Stale action string (cosmetic only)

**Evidence** (`bengal/server/live_reload.py:335`):

```python
# Inside SSE handler, outside lock:
self.wfile.write(f"data: {_last_action}\n\n".encode())
```

Low severity because SSE is eventually consistent and the action will be correct on next event.

---

## Good Patterns Already Present ✅

Bengal has excellent free-threading awareness in key areas:

### Thread-Safe LRUCache

```python
# bengal/utils/primitives/lru_cache.py
class LRUCache[K, V]:
    def __init__(self, ...):
        self._lock = threading.RLock()  # All operations protected

    def get(self, key: K) -> V | None:
        with self._lock:
            ...
```

### ContextVar for Thread-Local State

```python
# bengal/rendering/assets.py
_asset_manifest: ContextVar[AssetManifestContext | None] = ContextVar(
    "asset_manifest",
    default=None,
)
```

ContextVars are designed for free threading - each thread/context has independent storage.

### Context Propagation to Workers

```python
# bengal/orchestration/render/orchestrator.py:601-604
# CRITICAL: Copy parent context for each task to propagate ContextVars
future_to_page = {
    executor.submit(contextvars.copy_context().run, render_page, page): page
    for page in sorted_pages
}
```

### PerKeyLockManager

```python
# bengal/utils/concurrency/concurrent_locks.py
class PerKeyLockManager:
    """Allows parallel work on different keys, serializes same key."""
    def get_lock(self, key: Hashable) -> threading.RLock:
        with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]
```

---

## Options

### Option A: Minimal Fixes (Recommended) ⭐

Fix only the identified issues with targeted changes.

| Change | Effort | Risk |
|--------|--------|------|
| Replace `@lru_cache` with `LRUCache` | Medium | Low |
| Add lock to scaffold registry | Low | None |
| Add lock to logger registry | Medium | Low |
| Use `ThreadSafeSet` for warnings | Low | None |
| Add lock to directive cache config | Low | None |

**Pros**: 
- Minimal code churn
- Uses existing Bengal primitives
- Easy to review

**Cons**:
- Manual audit may have missed issues (mitigated by stress tests)

**Confidence**: 95% 🟢 (verified against codebase)

---

### Option B: Defensive Global State Audit

Add runtime detection for unprotected global mutations.

```python
# bengal/utils/concurrency/guards.py
class ThreadSafeDict(dict):
    """Dict that warns on unprotected concurrent access (debug mode)."""
    def __setitem__(self, key, value):
        if _DEBUG_THREADING and not _in_lock():
            warnings.warn(f"Unprotected dict write: {key}")
        super().__setitem__(key, value)
```

**Pros**:
- Catches issues we missed
- Useful for future development

**Cons**:
- Runtime overhead
- False positives in single-threaded code

**Confidence**: 78% 🟡

---

### Option C: Immutable-First Architecture

Refactor to use immutable data structures where possible.

**Pros**:
- Eliminates entire class of bugs
- Better for reasoning about code

**Cons**:
- Major refactor
- Performance implications
- Not necessary given Option A fixes

**Confidence**: 65% 🟠 (high effort, diminishing returns)

---

## Recommendation

**Option A: Minimal Fixes** with highest confidence (95%).

Bengal already has the right primitives (`LRUCache`, `ThreadSafeSet`, `PerKeyLockManager`). The issues are isolated and can be fixed with targeted changes.

**Why 95% confidence**:
- All 5 `@lru_cache` locations verified in codebase ✅
- Thread-safe `LRUCache` primitive exists with RLock ✅
- `ThreadSafeSet.add_if_new()` method matches proposed usage exactly ✅
- Singleton race pattern confirmed at `scaffolds/registry.py:270` ✅
- Context propagation already implemented in `RenderOrchestrator` ✅

---

## Implementation Plan

### Phase 1: Critical Fixes (P0)

**1.1 Replace `@lru_cache` with `LRUCache`**

```python
# Before (bengal/rendering/template_functions/icons.py)
@lru_cache(maxsize=512)
def _render_icon_cached(name: str, size: int, css_class: str, aria_label: str) -> str:
    ...

# After
from bengal.utils.primitives import LRUCache

_icon_cache: LRUCache[tuple[str, int, str, str], str] = LRUCache(
    maxsize=512, name="icon_render"
)

def _render_icon_cached(name: str, size: int, css_class: str, aria_label: str) -> str:
    key = (name, size, css_class, aria_label)
    return _icon_cache.get_or_set(key, lambda: _render_icon_impl(name, size, css_class, aria_label))
```

Files to update:
- [ ] `bengal/autodoc/base.py`
- [ ] `bengal/rendering/template_functions/icons.py`
- [ ] `bengal/assets/css/__init__.py`
- [ ] `bengal/core/theme/registry.py`
- [ ] `bengal/directives/_icons.py`

**1.2 Fix scaffold registry singleton**

```python
# bengal/scaffolds/registry.py
import threading

_registry: TemplateRegistry | None = None
_registry_lock = threading.Lock()

def _get_registry() -> TemplateRegistry:
    global _registry
    if _registry is not None:  # Fast path (no lock)
        return _registry
    with _registry_lock:
        if _registry is None:  # Double-check under lock
            _registry = TemplateRegistry()
        return _registry
```

**1.3 Add locks to logger registry**

```python
# bengal/utils/observability/logger.py
_logger_lock = threading.Lock()

def get_logger(name: str) -> BengalLogger:
    # Fast path: already exists
    if name in _lazy_loggers:
        return _lazy_loggers[name]
    with _logger_lock:
        if name not in _lazy_loggers:
            _lazy_loggers[name] = LazyLogger(name)
        return _lazy_loggers[name]

def reset_loggers() -> None:
    global _registry_version
    with _logger_lock:
        close_all_loggers()
        _loggers.clear()
        _lazy_loggers.clear()
        _registry_version += 1
        # Reset config
        _global_config["level"] = LogLevel.INFO
        _global_config["log_file"] = None
        _global_config["verbose"] = False
        _global_config["quiet_console"] = False
```

### Phase 2: High Priority Fixes (P1)

**2.1 Use ThreadSafeSet for fallback warnings**

```python
# bengal/rendering/assets.py
from bengal.utils.concurrency.thread_local import ThreadSafeSet

_fallback_warned = ThreadSafeSet()

# In resolve_asset_url():
# Note: ThreadSafeSet.add_if_new() returns True if item was added (not present before)
# This matches the existing check-then-log pattern perfectly
if _fallback_warned.add_if_new(logical_path):
    logger.debug("asset_manifest_disk_fallback", ...)
```

**Existing primitive** (`bengal/utils/concurrency/thread_local.py:145-150`):
```python
def add_if_new(self, item: str) -> bool:
    """Add item if not present, return True if added.
    Thread-safe check-and-add operation."""
    with self._lock:
        if item in self._set:
            return False
        self._set.add(item)
        return True
```

### Phase 3: Moderate Priority (P2)

**3.1 Add lock to directive cache configuration**

```python
# bengal/directives/cache.py
_config_lock = threading.Lock()

def configure_cache(max_size: int | None = None, enabled: bool | None = None) -> None:
    global _directive_cache
    with _config_lock:
        if max_size is not None:
            was_enabled = _directive_cache._cache.enabled
            _directive_cache = DirectiveCache(max_size=max_size)
            if not was_enabled:
                _directive_cache.disable()
        if enabled is not None:
            if enabled:
                _directive_cache.enable()
            else:
                _directive_cache.disable()
```

### Phase 4: Validation

**4.1 Add free-threading CI job**

```yaml
# .github/workflows/test.yml
free-threading:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: "3.14t"  # Free-threaded build
    - name: Run tests with GIL disabled
      env:
        PYTHON_GIL: "0"
      run: |
        pytest tests/ -x -v --tb=short
```

**4.2 Add thread-safety stress tests**

```python
# tests/test_thread_safety.py
import concurrent.futures
import threading

def test_lru_cache_replacement_thread_safety():
    """Verify @lru_cache replacements are thread-safe."""
    from bengal.rendering.template_functions.icons import _render_icon_cached
    
    errors = []
    
    def worker():
        for i in range(100):
            try:
                _render_icon_cached(f"icon_{i % 10}", 20, "", "")
            except Exception as e:
                errors.append(e)
    
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert not errors, f"Thread safety errors: {errors}"


def test_scaffold_registry_singleton_thread_safety():
    """Verify scaffold registry singleton is thread-safe."""
    from bengal.scaffolds import registry
    
    # Reset to test initialization race
    registry._registry = None
    
    instances = []
    errors = []
    lock = threading.Lock()
    
    def worker():
        try:
            instance = registry._get_registry()
            with lock:
                instances.append(id(instance))
        except Exception as e:
            with lock:
                errors.append(e)
    
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert not errors, f"Thread safety errors: {errors}"
    # All threads should get the same singleton instance
    assert len(set(instances)) == 1, f"Multiple instances created: {set(instances)}"


def test_logger_registry_thread_safety():
    """Verify logger registry handles concurrent get_logger calls."""
    from bengal.utils.observability.logger import get_logger, reset_loggers
    
    reset_loggers()
    errors = []
    
    def worker(thread_id: int):
        try:
            for i in range(50):
                # Each thread creates loggers with overlapping names
                logger = get_logger(f"test.module.{i % 10}")
                logger.debug("test", thread_id=thread_id)
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert not errors, f"Thread safety errors: {errors}"
```

---

## Commits

```bash
# Phase 1.1
git add -A && git commit -m "rendering: replace @lru_cache with thread-safe LRUCache"

# Phase 1.2  
git add -A && git commit -m "scaffolds: add lock to singleton registry pattern"

# Phase 1.3
git add -A && git commit -m "observability: add thread safety to logger registry"

# Phase 2.1
git add -A && git commit -m "rendering: use ThreadSafeSet for fallback warnings"

# Phase 3.1
git add -A && git commit -m "directives: add lock to cache configuration"

# Phase 4
git add -A && git commit -m "tests: add free-threading CI and stress tests"
```

---

## Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Each fixed module |
| Stress | Concurrent access patterns |
| Integration | Full build with `PYTHON_GIL=0` |
| CI | Python 3.14t matrix job |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression from added locks | Low | Medium | Benchmark before/after; use fast-path patterns |
| Missed issues in audit | Medium | High | Add stress tests; enable TSAN in CI |
| Breaking existing tests | Low | Low | Run full test suite after each change |

---

## Success Criteria

### Code Changes
- [ ] All 5 `@lru_cache` usages replaced with `LRUCache`
- [ ] Scaffold registry uses double-checked locking
- [ ] Logger registry protected by lock
- [ ] `_fallback_warned` uses `ThreadSafeSet`
- [ ] Directive cache config protected by lock

### Validation
- [ ] `test_lru_cache_replacement_thread_safety` passes
- [ ] `test_scaffold_registry_singleton_thread_safety` passes
- [ ] `test_logger_registry_thread_safety` passes
- [ ] Full test suite passes with `PYTHON_GIL=0`
- [ ] CI includes Python 3.14t matrix job

### Verification Commands
```bash
# Run thread-safety stress tests
pytest tests/test_thread_safety.py -v -x

# Run full suite with GIL disabled (requires Python 3.14t)
PYTHON_GIL=0 pytest tests/ -x --tb=short

# Verify no new @lru_cache usages introduced
grep -rn "@lru_cache" bengal/ --include="*.py" | wc -l  # Should be 0
```

---

## Related RFCs

- `rfc-contextvar-config-implementation.md` - ContextVar patterns for thread-local config
- `rfc-build-performance-optimizations.md` - Parallel rendering architecture
- `rfc-cache-invalidation-architecture.md` - Cache lifecycle management

---

## Appendix: Thread-Safe Patterns Reference

### Pattern 1: Double-Checked Locking (Singleton)

```python
_instance: T | None = None
_lock = threading.Lock()

def get_instance() -> T:
    if _instance is not None:  # Fast path (no lock)
        return _instance
    with _lock:
        if _instance is None:  # Double-check under lock
            _instance = create_instance()
        return _instance
```

### Pattern 2: LRUCache get_or_set

```python
cache: LRUCache[K, V] = LRUCache(maxsize=100)

def get_value(key: K) -> V:
    return cache.get_or_set(key, lambda: compute_value(key))
```

### Pattern 3: ThreadSafeSet for Deduplication

```python
from bengal.utils.concurrency.thread_local import ThreadSafeSet

_seen = ThreadSafeSet()

def process_once(item: str) -> None:
    if _seen.add_if_new(item):
        do_work(item)
```

### Pattern 4: ContextVar for Thread-Local State

```python
from contextvars import ContextVar

_current_page: ContextVar[Page | None] = ContextVar("current_page", default=None)

def set_page(page: Page) -> Token:
    return _current_page.set(page)

def get_page() -> Page | None:
    return _current_page.get()
```
