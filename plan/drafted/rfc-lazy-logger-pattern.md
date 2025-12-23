# RFC: LazyLogger Pattern for Test Isolation

**Status**: Draft  
**Created**: 2025-12-22  
**Author**: AI Assistant  
**Confidence**: 95% 🟢

---

## Executive Summary

Replace module-level `logger = get_logger(__name__)` with `logger = LazyLogger(__name__)` to eliminate orphaned logger references that cause test failures in pytest-xdist workers.

**Impact**: ~15 module changes, eliminates 4 accumulated test fixture hacks, prevents recurring bug class.

---

## Problem Statement

### The Bug Pattern

We've had **4 consecutive fix attempts** for the same underlying issue:

```
157be17f tests(logging): fix orphaned logger references... (reload modules)
8ef9bfe9 tests(logging): fix test isolation for logger state...
b365a6fb tests(logging): fix orphaned logger instances...
6d20beed tests(logging): fix orphaned logger instances...
```

### Root Cause

Every orchestration module uses this pattern:

```python
# bengal/orchestration/build/__init__.py (and 15+ others)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)  # Reference captured at import time

class BuildOrchestrator:
    def build(self):
        logger.info("build_start", ...)  # Uses the captured reference
```

**The problem**: When tests call `reset_loggers()` (which clears `_loggers` registry), the module-level `logger` variable still references the OLD logger object. Events go to the orphaned logger, while tests retrieve NEW loggers from the registry.

```
┌─────────────────────────────────────────────────────────────────┐
│  Test A (no preserve_loggers marker)                            │
│  └─ teardown: reset_loggers() → _loggers.clear()               │
├─────────────────────────────────────────────────────────────────┤
│  Test B (logging test with preserve_loggers)                    │
│  └─ configure_logging() → updates empty _loggers               │
│  └─ Site.build() → uses orphaned module-level logger           │
│  └─ get_logger() → returns NEW logger (empty events)           │
│  └─ ASSERTION FAILS: expected events, got []                   │
└─────────────────────────────────────────────────────────────────┘
```

### Why Previous Fixes Failed

| Fix | Approach | Why Incomplete |
|-----|----------|----------------|
| `preserve_loggers` marker | Skip reset for this test | Previous test's reset already ran |
| Clear events, keep registry | Preserve logger objects | Doesn't help if registry already cleared |
| Reload modules | Force fresh logger refs | Hack, fragile, slow |

---

## Proposed Solution

### LazyLogger Proxy

Add a proxy class that always fetches from the current registry:

```python
# bengal/utils/logger.py

class LazyLogger:
    """
    Logger proxy that always fetches from the current registry.

    Prevents orphaned logger references when _loggers registry is cleared
    between tests, since we fetch fresh on every attribute access.

    Usage:
        logger = LazyLogger(__name__)
        logger.info("message")  # Always uses current registry
    """
    __slots__ = ('_name',)

    def __init__(self, name: str):
        self._name = name

    def __getattr__(self, attr: str) -> Any:
        """Delegate to the current logger in registry."""
        return getattr(get_logger(self._name), attr)

    def __repr__(self) -> str:
        return f"LazyLogger({self._name!r})"
```

### Module Updates

Change all modules from:

```python
from bengal.utils.logger import get_logger
logger = get_logger(__name__)
```

To:

```python
from bengal.utils.logger import LazyLogger
logger = LazyLogger(__name__)
```

### Affected Modules

```
bengal/orchestration/build/__init__.py
bengal/orchestration/content.py
bengal/orchestration/asset.py
bengal/orchestration/menu.py
bengal/orchestration/postprocess.py
bengal/orchestration/render.py
bengal/orchestration/section.py
bengal/orchestration/static.py
bengal/orchestration/streaming.py
bengal/orchestration/taxonomy.py
bengal/orchestration/related_posts.py
bengal/orchestration/incremental/orchestrator.py
bengal/orchestration/incremental/cache_manager.py
bengal/orchestration/incremental/change_detector.py
bengal/orchestration/incremental/cleanup.py
bengal/orchestration/incremental/cascade_tracker.py
bengal/orchestration/incremental/rebuild_filter.py
```

---

## Test Fixture Cleanup

After this change, we can **remove** accumulated test fixture complexity:

### Remove from `test_logging_integration.py`:

1. The `importlib.reload()` hack (lines 42-50 in reset_loggers fixture)
2. Complex fixture comments explaining orphan behavior
3. Possibly the `preserve_loggers` marker entirely

### Simplify `conftest.py`:

1. `reset_loggers()` can safely clear the registry without orphaning references
2. No need for `preserve_loggers` marker check

---

## Performance Considerations

**Overhead**: One extra attribute lookup per log call.

```python
# Before: Direct attribute access
logger.info(...)  # 1 lookup

# After: Proxy delegation  
logger.info(...)  # 2 lookups (LazyLogger.__getattr__ → get_logger → BengalLogger.info)
```

**Benchmarks needed**: Verify overhead is negligible for hot paths.

**Mitigation if needed**: Cache the logger reference per-call using `__getattr__` that returns bound methods:

```python
def __getattr__(self, attr: str) -> Any:
    # Could cache for the lifetime of one log call
    return getattr(get_logger(self._name), attr)
```

---

## Implementation Plan

### Phase 1: Add LazyLogger (1 task)
- [ ] Add `LazyLogger` class to `bengal/utils/logger.py`
- [ ] Add `__all__` export

### Phase 2: Migrate Modules (1 task, mechanical)
- [ ] Update all 17 modules to use `LazyLogger(__name__)`
- [ ] Run full test suite to verify

### Phase 3: Cleanup Test Fixtures (1 task)
- [ ] Remove `importlib.reload()` hack from `test_logging_integration.py`
- [ ] Simplify or remove `preserve_loggers` marker
- [ ] Update fixture comments

### Phase 4: Verify (1 task)
- [ ] Run full test suite with `-n 2` (xdist)
- [ ] Run full test suite with `-n auto`
- [ ] Verify CI passes

---

## Alternatives Considered

### 1. Dependency Injection

```python
class BuildOrchestrator:
    def __init__(self, site: Site, logger: BengalLogger | None = None):
        self.logger = logger or get_logger(__name__)
```

**Rejected**: Requires changing every constructor signature, propagating logger through call chains.

### 2. Thread-Local Loggers

```python
_thread_loggers = threading.local()

def get_logger(name: str) -> BengalLogger:
    if not hasattr(_thread_loggers, 'loggers'):
        _thread_loggers.loggers = {}
    ...
```

**Rejected**: pytest-xdist uses processes, not threads. Would need process-local instead.

### 3. Never Clear Registry in Tests

**Rejected**: Risks cross-test contamination, defeats purpose of isolation.

### 4. Keep Current Reload Hack

**Rejected**: Fragile, slow, requires maintaining list of modules to reload.

---

## Success Criteria

- [ ] All logging integration tests pass with xdist (`-n 2`, `-n auto`)
- [ ] No `importlib.reload()` in test code
- [ ] No `preserve_loggers` marker needed
- [ ] No performance regression in build times
- [ ] Pattern documented in `bengal/utils/logger.py`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead | Low | Low | Benchmark, cache if needed |
| Missed module migration | Low | Medium | grep for `get_logger(__name__)` |
| New test failures | Low | Low | Full test suite run |

---

## References

- Commits attempting to fix: `157be17f`, `8ef9bfe9`, `b365a6fb`, `6d20beed`
- Python logging best practices: [docs.python.org/3/howto/logging.html](https://docs.python.org/3/howto/logging.html)
- pytest-xdist isolation: [pytest-xdist docs](https://pytest-xdist.readthedocs.io/)
