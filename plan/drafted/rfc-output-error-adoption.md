# RFC: Output Package Error System Adoption

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/output/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P4 (Very Low) — Output is a display utility; failures are cosmetic, not functional  
**Estimated Effort**: 30 minutes (single dev)

---

## Executive Summary

The `bengal/output/` package is a **CLI output utility** for terminal messaging—it is a *consumer* of error information (displays errors to users), not a *producer* of domain errors. Its current error handling approach is **appropriate for its role**.

**Current state**:
- **0 exception raises**: No errors raised (correct for a display utility)
- **0 error codes**: No `ErrorCode` usage (not needed)
- **0 `record_error()` calls**: No error session tracking (not needed)
- **4 exception handlers**: All are defensive fallbacks with graceful degradation
- **0 logger.error/warning calls**: Silent fallbacks to defaults

**Adoption Score**: 5/10 (but largely N/A for this utility package)

**Recommendation**: Minimal changes recommended. The output package correctly uses defensive programming with fallbacks. The only enhancement would be adding debug logging for environment parsing failures and potentially standardizing the error handling pattern. **No error codes or domain exceptions needed.**

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

### Why This Package Is Different

The Bengal error system is designed for:
- **Domain errors**: Config, Content, Rendering, Discovery, Cache, Server, Template, Asset
- **Build-time failures**: Issues that affect site generation
- **User-facing problems**: Issues users need to investigate and fix

The `bengal/output/` package:
- **Is a display utility**: Formats and presents messages in terminals
- **Has no domain logic**: Doesn't process content, validate config, or generate output
- **Should never block builds**: Display failures should degrade gracefully
- **Is consumed by error handling**: The `bengal/errors/reporter.py` uses this package

### Current Role in Error Flow

```
[Domain Error Occurs]
        ↓
[bengal/errors/] creates BengalError with context
        ↓
[bengal/errors/reporter.py] formats error for display
        ↓
[bengal/output/] renders formatted error to terminal ← THIS PACKAGE
```

The output package sits at the **end** of the error pipeline, not in the middle.

### Impact Assessment

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| Environment parsing failure | Fallback to defaults (cosmetic) | Debug log available |
| Time retrieval failure | Phase dedup disabled (cosmetic) | Debug log available |
| Status code parsing failure | No color styling (cosmetic) | No user impact |

**Verdict**: All failure modes are cosmetic and appropriately handled with fallbacks.

---

## Current State Evidence

### Package Structure

```
bengal/output/
├── __init__.py      # Public API exports
├── core.py          # CLIOutput main class (843 lines)
├── dev_server.py    # DevServerOutputMixin (227 lines)
├── enums.py         # MessageLevel, OutputStyle enums
├── globals.py       # Singleton pattern (82 lines)
├── icons.py         # IconSet definitions (117 lines)
├── colors.py        # HTTP status/method colors (149 lines)
└── README.md        # Usage conventions
```

### Error System Integration

| File | Error Imports | ErrorCode Usage | record_error() | Raises |
|------|---------------|-----------------|----------------|--------|
| `__init__.py` | ❌ None | 0 | 0 | 0 |
| `core.py` | ❌ None | 0 | 0 | 0 |
| `dev_server.py` | ❌ None | 0 | 0 | 0 |
| `enums.py` | ❌ None | 0 | 0 | 0 |
| `globals.py` | ❌ None | 0 | 0 | 0 |
| `icons.py` | ❌ None | 0 | 0 | 0 |
| `colors.py` | ❌ None | 0 | 0 | 0 |

### Exception Handlers

**4 total exception handlers** in the package:

#### 1. Environment Variable Parsing (`core.py:117-131`)

```python
# Location: CLIOutput.__init__()
try:
    import os as _os

    self.dev_server = (_os.environ.get("BENGAL_DEV_SERVER") or "") == "1"
    self._phase_dedup_ms = int(_os.environ.get("BENGAL_CLI_PHASE_DEDUP_MS", "1500"))
except Exception as e:
    logger.debug(
        "cli_output_env_init_failed",
        error=str(e),
        error_type=type(e).__name__,
        action="using_defaults",
    )
    self.dev_server = False
    self._phase_dedup_ms = 1500
```

**Assessment**: ✅ Correct pattern
- Logs to debug (not user-facing)
- Falls back to sensible defaults
- Never blocks initialization

#### 2. Time Retrieval (`core.py:785-798`)

```python
# Location: CLIOutput._now_ms()
def _now_ms(self) -> int:
    """Get current monotonic time in milliseconds for phase deduplication."""
    try:
        import time as _time

        return int(_time.monotonic() * 1000)
    except Exception as e:
        logger.debug(
            "cli_output_now_ms_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="returning_zero",
        )
        return 0
```

**Assessment**: ✅ Correct pattern
- Time retrieval failure is extremely rare
- Returning 0 disables phase deduplication (acceptable degradation)
- Debug log for investigation

#### 3. Status Code Parsing (`colors.py:48-61`)

```python
# Location: get_status_color_code()
def get_status_color_code(status: str) -> str:
    try:
        code = int(status)
        if 200 <= code < 300:
            return "\033[32m"  # Green
        # ... color mapping ...
    except (ValueError, TypeError):
        return ""  # No color on parse failure
```

**Assessment**: ✅ Correct pattern
- Invalid status code results in no colorization
- Pure display concern, no user impact
- No logging needed (caller can pass anything)

#### 4. Status Style Parsing (`colors.py:108-121`)

```python
# Location: get_status_style()
def get_status_style(status: str) -> str:
    try:
        code = int(status)
        if 200 <= code < 300:
            return "green"
        # ... style mapping ...
    except (ValueError, TypeError):
        return "default"  # Default style on parse failure
```

**Assessment**: ✅ Correct pattern
- Same as above, returns sensible default
- No logging needed

### Logger Usage

**2 logging calls** in the package:

| Location | Level | Event Key | Purpose |
|----------|-------|-----------|---------|
| `core.py:124` | `debug` | `cli_output_env_init_failed` | Environment parsing fallback |
| `core.py:792` | `debug` | `cli_output_now_ms_failed` | Time retrieval fallback |

**Assessment**: ✅ Appropriate level (debug, not error/warning)

---

## Gap Analysis

### Gaps That DON'T Apply

| Typical Gap | Why N/A for Output Package |
|-------------|---------------------------|
| Wrong exception class | Package doesn't raise exceptions |
| Missing error codes | Display utilities don't need error codes |
| No error session recording | No domain errors to record |
| Silent failures hide problems | Failures are cosmetic only |
| No build phase tracking | Not part of build pipeline |

### Minor Gaps That Could Be Addressed

#### 1. Inconsistent Error Logging

**Current**: Only 2 of 4 exception handlers log their failures.

**Impact**: Low. The colors.py handlers don't need logging because:
- They're pure functions with no side effects
- Callers expect graceful degradation
- Invalid input is not necessarily an error

#### 2. No Structured Fallback Pattern

**Current**: Each handler implements fallback logic inline.

**Potential**: A utility wrapper could standardize:

```python
# Hypothetical pattern (not recommended for this small package)
def with_fallback(func, fallback, log_event=None):
    try:
        return func()
    except Exception as e:
        if log_event:
            logger.debug(log_event, error=str(e))
        return fallback
```

**Assessment**: Overkill for 4 handlers. Current inline approach is fine.

---

## Proposed Changes

### Recommendation: Minimal Changes

Given that:
1. The output package is a display utility, not a domain processor
2. All failure modes are cosmetic
3. Current fallback patterns are appropriate
4. No domain errors should originate from this package

**Proposed changes are optional enhancements, not requirements.**

### Optional Enhancement 1: Standardize Debug Logging (5 min)

Add debug logging to colors.py handlers for consistency:

**File**: `bengal/output/colors.py:48-61`

```python
# Current
except (ValueError, TypeError):
    return ""

# After (optional)
except (ValueError, TypeError) as e:
    # Note: Intentionally not logging - invalid status is expected input
    # from external sources (e.g., malformed HTTP responses)
    return ""
```

**Verdict**: No change needed. Current behavior is correct.

### Optional Enhancement 2: Type Annotations (10 min)

**Current**: Some exception handlers catch broad `Exception`.

**After**: Could narrow to specific types if desired:

```python
# core.py:117-131 could become:
except (ValueError, KeyError, AttributeError) as e:
    # More specific exception handling
```

**Verdict**: Low value. Current broad catch is defensive and appropriate.

### No-Op: Do Not Add Error Codes

The output package should NOT have its own error codes because:
1. It doesn't produce domain errors
2. Display failures should never stop builds
3. Error codes are for user-actionable issues

### No-Op: Do Not Add record_error()

The output package should NOT record errors because:
1. Display issues are not build failures
2. Error session is for build-affecting issues
3. Would add noise to error summaries

---

## Implementation Phases

| Phase | Task | Time | Priority | Recommendation |
|-------|------|------|----------|----------------|
| 1 | Review and confirm no changes needed | 5 min | P1 | ✅ Do this |
| 2 | Add code comments explaining design choice | 10 min | P3 | Optional |
| 3 | Consider standardizing exception types | 10 min | P4 | Skip |

**Total if any changes**: 15-25 minutes

**Recommendation**: Phase 1 only (confirm current design is intentional).

---

## Success Criteria

### Must Have

- [x] Package does not raise domain exceptions (verified ✅)
- [x] All failures degrade gracefully (verified ✅)
- [x] No blocking on display issues (verified ✅)
- [x] Debug logging available for investigation (verified ✅)

### Should Have (Current State)

- [x] Consistent fallback patterns (verified ✅)
- [x] No user-facing error messages for display issues (verified ✅)

### Nice to Have (Not Recommended)

- [ ] Standardized exception wrapper — Overkill for 4 handlers
- [ ] Specific exception types — Low value

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| None identified | — | — | Package design is appropriate |

---

## Files Changed

**Recommended**: No changes.

If documentation is desired:

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `bengal/output/core.py` | Add design comment | +3 |
| `bengal/output/colors.py` | Add design comment | +2 |
| **Total** | — | ~5 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Score | Notes |
|-----------|-------|-------|
| Exception class design | N/A | Doesn't raise exceptions (correct) |
| Error code usage | N/A | Display utility (no codes needed) |
| Error session recording | N/A | No domain errors to record |
| Build phase tracking | N/A | Not part of build pipeline |
| Graceful degradation | 10/10 | All failures handled with fallbacks |
| Debug logging | 8/10 | 2/4 handlers log (colors.py intentionally silent) |
| **Overall Design** | **9/10** | Appropriate for utility package |

---

## Comparison with Other Packages

| Package | Type | Error Codes Needed? | record_error() Needed? |
|---------|------|--------------------|-----------------------|
| `bengal/fonts/` | Asset processor | ✅ Yes (X007-X010) | ✅ Yes |
| `bengal/discovery/` | Content scanner | ✅ Yes (D001-D014) | ✅ Yes |
| `bengal/rendering/` | Template renderer | ✅ Yes (R001-R010) | ✅ Yes |
| **`bengal/output/`** | **Display utility** | **❌ No** | **❌ No** |

The output package is correctly categorized as infrastructure, not domain logic.

---

## References

- `bengal/output/core.py:117-131,785-798` — Exception handlers with debug logging
- `bengal/output/colors.py:48-61,108-121` — Exception handlers with silent fallback
- `bengal/errors/reporter.py` — Consumer of output package for error display
- `bengal/output/README.md` — Usage conventions and design rationale
- `tests/unit/cli/test_output.py` — Test coverage (193 lines)

---

## Conclusion

**The `bengal/output/` package has appropriate error handling for its role as a display utility.** No domain error codes, exception classes, or session recording are needed. The current defensive programming pattern with fallbacks is correct.

**Action**: Close as "Working as Designed" or add minimal documentation comments.
