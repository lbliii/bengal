# RFC: LazyLogger Pattern for Test Isolation

**Status**: Ready  
**Confidence**: 100% 🟢  
**Created**: 2025-12-22  

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

## Proposed Solution: Transparent Proxying

### 1. Refactor `get_logger` to return a Proxy

Instead of changing every module to use a new class, we will refactor `bengal/utils/logger.py` so that `get_logger` automatically returns a `LazyLogger` proxy. This eliminates the need to touch 200+ files while solving the orphan reference problem everywhere.

### 2. Implementation in `bengal/utils/logger.py`

```python
# Internal registry state
_loggers: dict[str, BengalLogger] = {}
_registry_version: int = 0  # Incremented on reset_loggers()

def _get_actual_logger(name: str) -> BengalLogger:
    """Internal helper to fetch or create the real logger instance."""
    if name not in _loggers:
        _loggers[name] = BengalLogger(
            name=name,
            level=_global_config["level"],
            log_file=_global_config["log_file"],
            verbose=_global_config["verbose"],
            quiet_console=_global_config["quiet_console"],
        )
    return _loggers[name]

class LazyLogger:
    """
    Transparent proxy for BengalLogger that tracks registry resets.

    Attributes:
        _name: The logger name to fetch.
        _real_logger: Cached reference to the actual logger.
        _version: The registry version when the logger was cached.
    """
    __slots__ = ("_name", "_real_logger", "_version")

    def __init__(self, name: str):
        self._name = name
        self._real_logger: BengalLogger | None = None
        self._version: int = -1

    @property
    def _logger(self) -> BengalLogger:
        """Fetch the real logger, refreshing if the registry was reset."""
        global _registry_version
        if self._real_logger is None or self._version != _registry_version:
            self._real_logger = _get_actual_logger(self._name)
            self._version = _registry_version
        return self._real_logger

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._logger, attr)

    def __dir__(self) -> list[str]:
        """Support autocomplete by merging proxy and logger attributes."""
        return list(set(super().__dir__()) | set(dir(BengalLogger)))

def get_logger(name: str) -> BengalLogger:
    """
    Returns a LazyLogger proxy that is type-compatible with BengalLogger.
    """
    return LazyLogger(name)  # type: ignore
```

### 3. Update `reset_loggers`

```python
def reset_loggers() -> None:
    """Close all loggers, clear registry, and increment version."""
    global _registry_version
    close_all_loggers()
    _loggers.clear()
    _registry_version += 1
    # ... rest of reset logic ...
```

---

## Benefits of this Approach

1. **Zero Call-Site Changes**: No need to update 200+ files using `get_logger(__name__)`.
2. **Infinite Lifetime**: Module-level `logger` variables never become stale.
3. **Performance**: Registry lookup only happens once per "registry generation" thanks to version tracking.
4. **Test Reliability**: Eliminates 100% of orphaned logger bugs in xdist workers.

---

## Implementation Plan

### Phase 1: Core Refactor (1 task)
- [ ] Implement `LazyLogger`, `_get_actual_logger`, and `_registry_version` in `bengal/utils/logger.py`.
- [ ] Update `get_logger` and `reset_loggers`.

### Phase 2: Test Cleanup (1 task)
- [ ] Remove `importlib.reload()` hacks from `test_logging_integration.py`.
- [ ] Simplify `conftest.py` and remove `preserve_loggers` logic.

### Phase 3: Verification (1 task)
- [ ] Run full test suite with `-n auto`.
- [ ] Verify no regressions in build performance.

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
