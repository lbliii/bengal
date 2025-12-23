# Plan: LazyLogger Pattern for Test Isolation

**RFC**: `rfc-lazy-logger-pattern.md`  
**Status**: Ready  
**Estimated Time**: 45-60 minutes  
**Created**: 2025-12-22

---

## Executive Summary

Implement transparent LazyLogger proxy in `bengal/utils/logger.py` to eliminate orphaned logger references in pytest-xdist. Zero call-site changes required.

**Impact**:
- 1 file modified (core refactor)
- 2 files simplified (test cleanup)
- Eliminates 4 accumulated test fixture hacks

---

## Phase 1: Core Refactor

### Task 1.1: Add Registry Version Counter

**File**: `bengal/utils/logger.py`  
**Location**: After line 408 (`_loggers: dict[str, BengalLogger] = {}`)

**Add**:
```python
_registry_version: int = 0  # Incremented on reset_loggers()
```

**Commit**: `utils(logger): add _registry_version counter for lazy logger invalidation`

---

### Task 1.2: Add Internal Logger Factory

**File**: `bengal/utils/logger.py`  
**Location**: After `_global_config` definition (after line 423)

**Add**:
```python
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
```

**Commit**: `utils(logger): add _get_actual_logger internal factory`

---

### Task 1.3: Implement LazyLogger Proxy Class

**File**: `bengal/utils/logger.py`  
**Location**: After `_get_actual_logger()` definition

**Add**:
```python
class LazyLogger:
    """
    Transparent proxy for BengalLogger that tracks registry resets.

    Module-level `logger = get_logger(__name__)` references hold this proxy.
    When `reset_loggers()` is called, the registry version increments and
    the proxy will fetch a fresh logger on next access.

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
```

**Commit**: `utils(logger): implement LazyLogger transparent proxy with version tracking`

---

### Task 1.4: Update get_logger to Return LazyLogger

**File**: `bengal/utils/logger.py`  
**Location**: Replace existing `get_logger()` function (lines 483-502)

**Replace with**:
```python
def get_logger(name: str) -> BengalLogger:
    """
    Get a logger proxy for the given name.

    Returns a LazyLogger proxy that automatically refreshes when
    reset_loggers() is called. This ensures module-level logger
    references never become stale.

    Args:
        name: Logger name (typically __name__)

    Returns:
        LazyLogger proxy (type-compatible with BengalLogger)
    """
    return LazyLogger(name)  # type: ignore[return-value]
```

**Commit**: `utils(logger): refactor get_logger to return LazyLogger proxy`

---

### Task 1.5: Update reset_loggers to Increment Version

**File**: `bengal/utils/logger.py`  
**Location**: Update existing `reset_loggers()` function (lines 528-535)

**Replace with**:
```python
def reset_loggers() -> None:
    """Close all loggers, clear registry, and increment version counter."""
    global _registry_version
    close_all_loggers()
    _loggers.clear()
    _registry_version += 1
    _global_config["level"] = LogLevel.INFO
    _global_config["log_file"] = None
    _global_config["verbose"] = False
    _global_config["quiet_console"] = False
```

**Commit**: `utils(logger): update reset_loggers to increment _registry_version`

---

## Phase 2: Test Cleanup

### Task 2.1: Simplify fresh_logger_state Fixture

**File**: `tests/integration/test_logging_integration.py`  
**Location**: Replace `fresh_logger_state` fixture (lines 65-148)

**Replace with**:
```python
@pytest.fixture(autouse=True)
def fresh_logger_state():
    """
    Reset logger state before each test.

    With LazyLogger, we can simply call reset_loggers() and all module-level
    logger references will automatically refresh on next access. No need for
    importlib.reload() hacks.
    """
    from bengal.utils.logger import (
        _global_config,
        close_all_loggers,
        reset_loggers,
        set_console_quiet,
    )

    # Clean reset before test
    reset_loggers()
    set_console_quiet(False)

    yield

    # Clean reset after test
    reset_loggers()
    set_console_quiet(False)
```

**Also remove**:
- The `pytestmark = pytest.mark.preserve_loggers` line (line 152)
- The import of `importlib` (no longer needed)
- References to `_loggers` registry (no longer directly accessed)

**Commit**: `tests(logging): simplify fresh_logger_state fixture using LazyLogger; remove reload hacks`

---

### Task 2.2: Remove preserve_loggers Logic from conftest.py

**File**: `tests/conftest.py`  
**Location**: Update `reset_bengal_state` fixture (around lines 324-331)

**Remove** the preserve_loggers check and always call reset_loggers():

**Change from**:
```python
    # 2. Reset logger state (close file handles, clear registry)
    # Skip for tests that manage their own logger state (marked with preserve_loggers)
    if not request.node.get_closest_marker("preserve_loggers"):
        try:
            from bengal.utils.logger import reset_loggers

            reset_loggers()
        except ImportError:
            logger.debug("Logger reset skipped: reset_loggers not available")
```

**Change to**:
```python
    # 2. Reset logger state (close file handles, clear registry)
    # LazyLogger pattern ensures module-level references auto-refresh
    try:
        from bengal.utils.logger import reset_loggers

        reset_loggers()
    except ImportError:
        logger.debug("Logger reset skipped: reset_loggers not available")
```

**Also update** the docstring to remove the preserve_loggers reference (around line 281-282).

**Commit**: `tests(conftest): remove preserve_loggers marker logic; LazyLogger handles isolation`

---

## Phase 3: Verification

### Task 3.1: Run Full Test Suite with xdist

**Command**:
```bash
cd /Users/llane/Documents/github/python/bengal
pytest tests/ -n auto --tb=short
```

**Success Criteria**:
- All logging integration tests pass
- No orphaned logger errors
- No test isolation failures

---

### Task 3.2: Run Targeted Logging Tests

**Command**:
```bash
pytest tests/integration/test_logging_integration.py -v -n 2
```

**Success Criteria**:
- All tests pass under parallel execution
- Events captured correctly

---

### Task 3.3: Verify No Performance Regression

**Command**:
```bash
pytest tests/integration/test_build_workflow.py -v --durations=10
```

**Success Criteria**:
- Build times remain stable
- No significant regression (< 5% increase)

---

## Files Modified

| File | Type | Changes |
|------|------|---------|
| `bengal/utils/logger.py` | Core | Add LazyLogger, _registry_version, update get_logger/reset_loggers |
| `tests/integration/test_logging_integration.py` | Test | Remove reload hacks, simplify fixture, remove preserve_loggers |
| `tests/conftest.py` | Test | Remove preserve_loggers conditional logic |

---

## Rollback Plan

If issues arise:
1. Revert all commits in this plan
2. Logger system returns to direct `BengalLogger` instantiation
3. Test hacks (`importlib.reload`, `preserve_loggers`) remain in place

---

## Success Criteria Checklist

- [ ] All logging integration tests pass with `-n auto`
- [ ] No `importlib.reload()` in test code
- [ ] No `preserve_loggers` marker needed
- [ ] No performance regression in build times
- [ ] LazyLogger pattern documented in `bengal/utils/logger.py`

---

## Post-Implementation

After successful verification:
1. Delete RFC: `rm plan/ready/rfc-lazy-logger-pattern.md`
2. Delete Plan: `rm plan/ready/plan-lazy-logger-pattern.md`
3. Update changelog with summary
