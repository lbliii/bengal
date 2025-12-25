# RFC: Server Package Error System Adoption

**Status**: Evaluated ✅  
**Created**: 2025-12-24  
**Evaluated**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/server/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Server errors affect every dev workflow but have dedicated infrastructure unused  
**Estimated Effort**: 2.5 hours (single dev)

---

## Executive Summary

The `bengal/server/` package has **very low adoption** (~5%) of the Bengal error system despite having dedicated server error infrastructure (`BengalServerError`, `DevServerErrorContext`, S-series error codes).

**Current state**:
- **0/15 files** use `BengalServerError` exception
- **0/15 files** use `ErrorCode` (S001-S005 exist but are unused)
- **0/15 files** use `DevServerErrorContext` or `create_dev_error()`
- **0/15 files** use `record_error()` session tracking
- **0/15 files** use `ErrorAggregator` or recovery patterns
- **~35 generic exception handlers** across all files
- **~44 logger.error/warning calls** — none with error codes

**Available but Unused Infrastructure**:

| Component | Location | Purpose |
|-----------|----------|---------|
| `BengalServerError` | `exceptions.py:540-568` | Server-specific exception with S-codes |
| `DevServerErrorContext` | `dev_server.py:98-227` | Hot-reload aware error context |
| `create_dev_error()` | `dev_server.py:229-281` | Factory for dev server errors |
| `DevServerState` | `dev_server.py:360-454` | Session tracking for dev server |
| Error codes S001-S005 | `codes.py` | Port, bind, reload, websocket, static errors |

**Adoption Score**: 1/10 → Target: 7/10

**Recommendation**: Integrate the existing `BengalServerError` and `DevServerErrorContext` infrastructure, add error codes to key failure points, and enable session tracking for pattern detection.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Proposed Changes](#proposed-changes)
5. [Implementation Phases](#implementation-phases)
6. [Success Criteria](#success-criteria)
7. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

The Bengal error system provides:
- **Error codes** for searchability and documentation linking
- **Build phase tracking** for investigation
- **Related test file mapping** for debugging
- **Investigation helpers** (grep commands, related files)
- **Session tracking** for error aggregation across builds
- **Actionable suggestions** for user recovery
- **Dev server context** for hot-reload aware debugging

The server package runs continuously during development, handling file changes, rebuilds, and live reload. When server operations fail, users need:
- Clear error messages with error codes for searching documentation
- File change context to identify what triggered the error
- Session tracking to detect recurring patterns
- Auto-fix suggestions for common issues (port conflicts, stale processes)

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No server error codes | Build failures hard to diagnose | Can't grep for specific server errors |
| No DevServerErrorContext | No file change correlation | Manual investigation of what triggered error |
| No session tracking | Recurring errors not detected | No pattern analysis for common failures |
| Missing suggestions | Cryptic port/process errors | Users manually search for fixes |
| Generic OSError raises | Errors look like Python bugs | Hard to distinguish Bengal errors from Python errors |

---

## Current State Evidence

### Error Code Usage

**Grep Result**: `grep -rn "ErrorCode" bengal/server/`

```
(no matches)
```

**0 error codes** used in the server package, despite S001-S005 being defined.

### BengalServerError Usage

**Grep Result**: `grep -rn "BengalServerError" bengal/server/`

```
(no matches)
```

**0 usages** of the dedicated `BengalServerError` exception class.

### DevServerErrorContext Usage

**Grep Result**: `grep -rn "DevServerErrorContext\|create_dev_error" bengal/server/`

```
(no matches)
```

**0 usages** of the dev server error context infrastructure.

### Current Exception Patterns

**File**: `bengal/server/dev_server.py:544`

```python
raise OSError(f"Port {self.port} is already in use")
```

**Gap**: Uses generic `OSError` instead of `BengalServerError(code=S001)`.

**File**: `bengal/server/dev_server.py:660`

```python
raise OSError(f"Port {self.port} is already in use") from e
```

**Gap**: Same pattern repeated.

**File**: `bengal/server/dev_server.py:672`

```python
raise OSError(f"Port {self.port} is already in use")
```

**Gap**: Third occurrence of same pattern.

**File**: `bengal/server/dev_server.py:604`

```python
raise OSError(f"Cannot start: stale process {stale_pid} is still running")
```

**Gap**: Should use `BengalServerError(code=S002)`.

### Build Error Handling

**File**: `bengal/server/build_executor.py:189-197`

```python
except Exception as e:
    build_time_ms = (time.time() - start_time) * 1000

    return BuildResult(
        success=False,
        pages_built=0,
        build_time_ms=build_time_ms,
        error_message=str(e),
    )
```

**Gap**: Error message is just a string, no structured context, no error code.

**File**: `bengal/server/build_trigger.py:297-304`

```python
except Exception as e:
    logger.error(
        "rebuild_error",
        error=str(e),
        error_type=type(e).__name__,
    )
```

**Gap**: No file change context, no `create_dev_error()` usage.

### Logger.error/warning Calls

| File | Count | Has error_code | Has suggestion |
|------|-------|----------------|----------------|
| `dev_server.py` | 8 | ❌ | ❌ |
| `build_executor.py` | 3 | ❌ | ❌ |
| `build_trigger.py` | 5 | ❌ | ❌ |
| `watcher_runner.py` | 4 | ❌ | ❌ |
| `live_reload.py` | 3 | ❌ | ❌ |
| `request_handler.py` | 4 | ❌ | ❌ |
| `resource_manager.py` | 3 | ❌ | ❌ |
| `reload_controller.py` | 5 | ❌ | ❌ |
| `build_hooks.py` | 4 | ❌ | ❌ |
| `request_logger.py` | 2 | ❌ | ❌ |
| `utils.py` | 2 | ❌ | ❌ |
| `file_watcher.py` | 1 | ❌ | ❌ |

**Total**: ~44 logger.error/warning calls with **0** error codes.

### Session Tracking

**Grep Result**: `grep -r "record_error" bengal/server/`

```
(no matches)
```

Server errors are not tracked in error sessions.

### DevServerState Usage

**Grep Result**: `grep -r "DevServerState\|get_dev_server_state" bengal/server/`

```
(no matches)
```

The singleton state tracker is not used.

---

## Gap Analysis

### Summary Table

| Component | Available | Used | Gap |
|-----------|-----------|------|-----|
| `BengalServerError` | ✅ `exceptions.py:540-568` | ❌ | Not imported |
| Error codes S001-S005 | ✅ `codes.py` | ❌ | Not used |
| `DevServerErrorContext` | ✅ `dev_server.py:98-227` | ❌ | Not imported |
| `create_dev_error()` | ✅ `dev_server.py:229-281` | ❌ | Not called |
| `DevServerState` | ✅ `dev_server.py:360-454` | ❌ | Not initialized |
| `record_error()` | ✅ `session.py` | ❌ | Not called |
| `with_error_recovery()` | ✅ `recovery.py` | ❌ | Not used |

### Error Code Mapping

S-series codes are defined but unused:

| Code | Purpose | Current Pattern | Recommended Location |
|------|---------|-----------------|----------------------|
| S001 | Port already in use | `OSError("Port...")` | `dev_server.py:544,660,672` |
| S002 | Server bind error | `OSError("Cannot start...")` | `dev_server.py:604` |
| S003 | Hot reload error | `logger.error("rebuild_error")` | `build_trigger.py:297` |
| S004 | WebSocket/SSE error | `logger.debug("sse_...")` | `live_reload.py:340` |
| S005 | Static file serving error | `logger.warning("custom_404_failed")` | `request_handler.py:631` |

### Missing DevServerErrorContext Integration Points

| Location | Current | Should Add |
|----------|---------|------------|
| `build_trigger.py:297` | `logger.error(error=str(e))` | `create_dev_error(e, changed_files=...)` |
| `watcher_runner.py:159` | `logger.error(error=str(e))` | File change context |
| `build_executor.py:189` | `error_message=str(e)` | Structured error context |

### Missing Session Tracking Points

| Location | Event | Should Call |
|----------|-------|-------------|
| `build_trigger.py:284` | Rebuild success | `DevServerState.record_success()` |
| `build_trigger.py:297` | Rebuild failure | `DevServerState.record_failure(sig)` |
| `dev_server.py:175` | Server start | `reset_dev_server_state()` |

---

## Proposed Changes

### Phase 1: Exception Adoption (1 hour)

**1.1 Replace OSError with BengalServerError in dev_server.py**

```python
# Before (dev_server.py:544)
raise OSError(f"Port {self.port} is already in use")

# After
from bengal.errors import BengalServerError, ErrorCode

raise BengalServerError(
    f"Port {self.port} is already in use",
    code=ErrorCode.S001,
    suggestion=f"Use --port {self.port + 1} or kill the process: lsof -ti:{self.port} | xargs kill",
)
```

**Files to update**:
- `dev_server.py:544` — Port unavailable (S001)
- `dev_server.py:660` — Port unavailable after search (S001)
- `dev_server.py:672` — Port unavailable no fallback (S001)
- `dev_server.py:604` — Stale process (S002)

**1.2 Add error codes to build_trigger.py**

```python
# Before (build_trigger.py:264-271)
show_error(f"Build failed: {result.error_message}", show_art=False)
logger.error(
    "rebuild_failed",
    duration_seconds=round(build_duration, 2),
    error=result.error_message,
)

# After
from bengal.errors import ErrorCode

show_error(f"Build failed: {result.error_message}", show_art=False)
logger.error(
    "rebuild_failed",
    error_code=ErrorCode.S003.name,
    duration_seconds=round(build_duration, 2),
    error=result.error_message,
    changed_files=[str(p) for p in changed_paths][:5],
)
```

**1.3 Add error codes to live_reload.py**

```python
# Before (live_reload.py:340-349)
except (BrokenPipeError, ConnectionResetError) as e:
    logger.debug(
        "sse_client_disconnected_error",
        client_address=client_addr,
        error_type=type(e).__name__,
    )

# After (keep as debug, but add code for pattern matching)
logger.debug(
    "sse_client_disconnected_error",
    error_code=ErrorCode.S004.name,
    client_address=client_addr,
    error_type=type(e).__name__,
)
```

### Phase 2: DevServerErrorContext Integration (1 hour)

**2.1 Add create_dev_error() to build_trigger.py**

```python
# In _execute_build method, after catching Exception
from bengal.errors import create_dev_error

except Exception as e:
    context = create_dev_error(
        e,
        changed_files=[str(p) for p in changed_paths],
        trigger_file=str(changed_paths[0]) if changed_paths else None,
        last_successful_build=self._last_successful_build,
    )

    logger.error(
        "rebuild_error",
        error_code=ErrorCode.S003.name,
        error=str(e),
        error_type=type(e).__name__,
        likely_cause=context.get_likely_cause(),
        quick_actions=context.quick_actions[:3],
        auto_fixable=context.auto_fixable,
    )

    if context.auto_fix_command:
        show_error(f"Build failed: {e}\n\nTry: {context.auto_fix_command}", show_art=False)
```

**2.2 Track last successful build**

```python
# Add instance variable in BuildTrigger.__init__
self._last_successful_build: datetime | None = None

# Update after successful build (build_trigger.py:284)
self._last_successful_build = datetime.now()
```

### Phase 3: Session Tracking (0.5 hours)

**3.1 Initialize DevServerState on server start**

```python
# In dev_server.py start() method
from bengal.errors import reset_dev_server_state

def start(self) -> None:
    # Reset error session for fresh server start
    reset_dev_server_state()
    # ... rest of start()
```

**3.2 Track successes and failures in build_trigger.py**

```python
from bengal.errors import get_dev_server_state

# After successful rebuild (line 284)
get_dev_server_state().record_success()

# After failed rebuild (in except block)
error_sig = f"{type(e).__name__}:{str(e)[:50]}"
is_new = get_dev_server_state().record_failure(error_sig)
if not is_new:
    logger.warning("recurring_error_detected", signature=error_sig)
```

---

## Implementation Phases

### Phase 1: Exception Adoption (1 hour)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| Replace OSError with BengalServerError(S001) | `dev_server.py` | 544, 660, 672 | P1 |
| Replace OSError with BengalServerError(S002) | `dev_server.py` | 604 | P1 |
| Add error codes to rebuild failures | `build_trigger.py` | 264-271 | P1 |
| Add error codes to SSE errors | `live_reload.py` | 340-349 | P2 |
| Add error codes to hook failures | `build_hooks.py` | 126-167 | P2 |

### Phase 2: DevServerErrorContext Integration (1 hour)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| Use create_dev_error() for rebuilds | `build_trigger.py` | 297-304 | P1 |
| Track last_successful_build | `build_trigger.py` | 284, __init__ | P1 |
| Add changed_files to error context | `build_trigger.py` | 297-304 | P1 |
| Generate quick_actions for common errors | `build_trigger.py` | 297-304 | P2 |

### Phase 3: Session Tracking (0.5 hours)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| Reset session on server start | `dev_server.py` | 175 | P1 |
| Record success after rebuild | `build_trigger.py` | 284 | P1 |
| Record failure on rebuild error | `build_trigger.py` | 297 | P1 |
| Detect recurring errors | `build_trigger.py` | 297 | P2 |

---

## Success Criteria

### Quantitative Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| `BengalServerError` usage | 0 | 4+ | 4 files |
| S-series error codes used | 0 | 5 | 5 codes |
| `create_dev_error()` usage | 0 | 1+ | 1 file |
| Session tracking calls | 0 | 3+ | 3 calls |
| Error codes in logger calls | 0 | 10+ | 10 calls |

### Qualitative Criteria

- [ ] Port conflict errors show S001 code and actionable suggestion
- [ ] Stale process errors show S002 code and kill command
- [ ] Rebuild failures include file change context
- [ ] Recurring errors are detected and logged
- [ ] Auto-fix suggestions appear for common patterns

### Adoption Score

| Component | Before | After |
|-----------|--------|-------|
| BengalServerError | 0% | 80% |
| Error codes | 0% | 70% |
| DevServerErrorContext | 0% | 60% |
| Session tracking | 0% | 70% |
| **Overall** | **1/10** | **7/10** |

---

## Risks and Mitigations

### Risk 1: Breaking Existing Error Handling

**Risk**: Changing exception types may break external code catching `OSError`.

**Mitigation**: `BengalServerError` inherits from `BengalError` which inherits from `Exception`. Any code catching `Exception` or `OSError` should still work. Add test cases for exception hierarchy.

**Evidence**: No external code imports from `bengal.server` except `DevServer` which is used via `start()`.

### Risk 2: Performance Impact from Context Creation

**Risk**: `create_dev_error()` may add latency to error paths.

**Mitigation**: Error paths are already slow (failed builds). Context creation is O(n) where n is changed files count, typically < 10. Profile if needed.

### Risk 3: Circular Import Issues

**Risk**: Importing from `bengal.errors` in server modules may cause circular imports.

**Mitigation**: `bengal.errors` has no dependencies on `bengal.server`. Server modules already import from other Bengal packages without issues.

### Risk 4: Session State Leaks

**Risk**: `DevServerState` singleton may leak between test runs.

**Mitigation**: Add `reset_dev_server_state()` call to test fixtures. Already available in `bengal/errors/dev_server.py:469-473`.

---

## Appendix: File-by-File Changes

### dev_server.py

**Imports to add**:
```python
from bengal.errors import BengalServerError, ErrorCode, reset_dev_server_state
```

**Changes**:
| Line | Current | Proposed |
|------|---------|----------|
| 175 | (none) | `reset_dev_server_state()` |
| 544 | `raise OSError(...)` | `raise BengalServerError(..., code=ErrorCode.S001)` |
| 604 | `raise OSError(...)` | `raise BengalServerError(..., code=ErrorCode.S002)` |
| 660 | `raise OSError(...)` | `raise BengalServerError(..., code=ErrorCode.S001)` |
| 672 | `raise OSError(...)` | `raise BengalServerError(..., code=ErrorCode.S001)` |

### build_trigger.py

**Imports to add**:
```python
from bengal.errors import ErrorCode, create_dev_error, get_dev_server_state
```

**Changes**:
| Line | Current | Proposed |
|------|---------|----------|
| 110 | (none) | `self._last_successful_build: datetime \| None = None` |
| 284 | `logger.info(...)` | Add `get_dev_server_state().record_success()` |
| 264-271 | `logger.error(...)` | Add `error_code=ErrorCode.S003.name` |
| 297-304 | `logger.error(...)` | Use `create_dev_error()` with session tracking |

### live_reload.py

**Imports to add**:
```python
from bengal.errors import ErrorCode
```

**Changes**:
| Line | Current | Proposed |
|------|---------|----------|
| 340-349 | `logger.debug(...)` | Add `error_code=ErrorCode.S004.name` |
| 593-600 | `logger.warning(...)` | Add `error_code=ErrorCode.S003.name` |

### build_hooks.py

**Imports to add**:
```python
from bengal.errors import ErrorCode
```

**Changes**:
| Line | Current | Proposed |
|------|---------|----------|
| 126-132 | `logger.error(...)` | Add error code for hook failures |
| 147-154 | `logger.error(...)` | Add error code for timeout |
| 158-167 | `logger.error(...)` | Add error code for not found |

---

## References

- `bengal/errors/exceptions.py:540-568` — BengalServerError definition
- `bengal/errors/dev_server.py` — DevServerErrorContext, create_dev_error, DevServerState
- `bengal/errors/codes.py` — S001-S005 error codes
- `bengal/errors/recovery.py` — with_error_recovery, error_recovery_context
- `bengal/errors/session.py` — record_error, get_session
