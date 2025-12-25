# RFC: Content Types Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Last Verified**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/content_types/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified against source code)  
**Priority**: P4 (Low) — Internal package with intentional graceful degradation design  
**Estimated Effort**: 0.5 hours (single dev)

---

## Executive Summary

The `bengal/content_types/` package has **minimal adoption** of the Bengal error system. The package is designed for **graceful degradation** (returning defaults instead of raising), which is appropriate for its internal use case. However, it lacks structured logging for debugging, input validation for public APIs, and could benefit from lightweight improvements without changing its core design philosophy.

**Current state**:
- **0 uses** of Bengal error framework
- **0 error codes** used
- **5 locations** with bare `except Exception` (all in template resolution)
- **0 `record_error()` calls**: No session tracking
- **No validation** on public API inputs

**Adoption Score**: 2/10

**Recommendation**: Add debug-level logging for unknown content types, add input validation to `register_strategy()`, and consolidate duplicate template-checking code. Do **not** add error codes or convert to raising exceptions—the graceful degradation design is correct for this internal package.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Design Philosophy](#design-philosophy)
5. [Proposed Changes](#proposed-changes)
6. [Implementation Phases](#implementation-phases)
7. [Success Criteria](#success-criteria)
8. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Package Purpose

The `content_types` package implements the **Strategy Pattern** for content type-specific behavior:
- **Sorting**: How pages are ordered (by date, weight, alphabetical)
- **Filtering**: Which pages appear in listings
- **Pagination**: Whether pagination applies
- **Template Selection**: Which templates to use for list/single views

### Why This Analysis Matters

While the package functions correctly, there are debugging and maintainability gaps:

| Issue | Impact |
|-------|--------|
| No logging for unknown content types | Hard to debug why wrong sorting/templates apply |
| No validation in `register_strategy()` | Silent overwrites of built-in strategies |
| Bare `except Exception` in 5 places | May swallow unexpected errors |
| Duplicate template-checking code | Maintenance burden across 5 strategy classes |

### Why Low Priority

The content_types package is **intentionally designed for graceful degradation**:

1. **Internal-use only**: Users don't directly configure content types in error-prone ways
2. **No external dependencies**: No network calls, no file I/O that could fail
3. **Silent fallbacks are correct**: Unknown type → PageStrategy is the right behavior
4. **Detection is heuristic**: Ambiguity is expected; there's no "wrong" answer

---

## Current State Evidence

### Files in Package

| File | Purpose | Lines | Bengal Error Usage |
|------|---------|-------|-------------------|
| `__init__.py` | Package exports | 57 | ❌ None |
| `base.py` | `ContentTypeStrategy` abstract base | 330 | ❌ None |
| `registry.py` | Registry, detection, registration | 292 | ❌ None |
| `strategies.py` | 9 concrete strategy implementations | 637 | ❌ None |

**Total**: 1,316 lines, 0 Bengal error framework usage

### Error Handling Patterns Found

#### Pattern 1: Silent Fallback for Unknown Types

**Location**: `registry.py:125-151`

```python
def get_strategy(content_type: str) -> ContentTypeStrategy:
    """Get the strategy for a content type."""
    return CONTENT_TYPE_REGISTRY.get(content_type, PageStrategy())
```

**Analysis**:
- ✅ Graceful fallback (correct design)
- ❌ No debug logging when fallback occurs
- ❌ No way to know if requested type was valid

#### Pattern 2: Bare Exception Catch in Template Checking

**Locations**: `base.py:226-237`, `strategies.py:124-132, 229-237, 331-339, 430-438`

```python
def template_exists(name: str) -> bool:
    if template_engine is None:
        return False
    try:
        template_engine.env.get_template(name)
        return True
    except Exception as e:
        logger.debug(
            "content_type_template_check_failed",
            template=name,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_false",
        )
        return False
```

**Analysis**:
- ✅ Uses structured logging
- ✅ Logs error details for debugging
- ❌ Catches `Exception` broadly (could swallow unexpected errors)
- ❌ Duplicated across 5 locations (DRY violation)

#### Pattern 3: No Validation in Registration

**Location**: `registry.py:248-291`

```python
def register_strategy(content_type: str, strategy: ContentTypeStrategy) -> None:
    """Register a custom content type strategy."""
    CONTENT_TYPE_REGISTRY[content_type] = strategy
```

**Analysis**:
- ❌ No type checking on `strategy` parameter
- ❌ No warning when overwriting built-in strategies
- ❌ No validation that `content_type` is a valid string

#### Pattern 4: Silent Detection Fallback

**Location**: `registry.py:154-245`

```python
def detect_content_type(section: Section, config: dict[str, Any] | None = None) -> str:
    # ... detection logic ...

    # 5. Final fallback
    return "list"
```

**Analysis**:
- ✅ Always returns valid type (correct design)
- ❌ No logging of detection path for debugging
- Detection decision is opaque

---

## Gap Analysis

### Summary Table

| Category | Count | Severity | Action |
|----------|-------|----------|--------|
| Bengal error imports | 0 | Low | No action needed |
| Error codes used | 0 | Low | No action needed |
| `record_error()` calls | 0 | Low | No action needed |
| Bare `except Exception` | 5 | Low | Consider narrowing |
| Missing input validation | 1 | Medium | Add validation |
| Missing debug logging | 2 | Medium | Add logging |
| Code duplication | 5 | Low | Consider extraction |

### Detailed Gaps

#### Gap 1: No Logging for Unknown Content Types

**Impact**: When a typo in `content_type` metadata causes wrong sorting/templates, there's no log entry to help debug.

**Example Scenario**:
```yaml
# In _index.md
content_type: blogg  # Typo!
```

Currently: Silently uses `PageStrategy`, pages sorted by weight instead of date.

**Recommendation**: Add debug-level logging when falling back.

#### Gap 2: No Validation in `register_strategy()`

**Impact**: Plugin developers could accidentally overwrite built-in strategies or pass invalid objects.

**Example Scenario**:
```python
register_strategy("blog", {"not": "a strategy"})  # No error raised
```

**Recommendation**: Add type checking and warning for overwrites.

#### Gap 3: Duplicate Template-Checking Code

**Impact**: Same 10-line function duplicated in 5 places (`base.py`, and 4 strategies in `strategies.py`).

**Recommendation**: Extract to shared utility in `base.py`.

---

## Design Philosophy

### Why Graceful Degradation Is Correct

The content_types package should **not** raise exceptions for most cases:

1. **Unknown content type**: Use PageStrategy (generic, always works)
2. **Template not found**: Try next in fallback chain
3. **Detection ambiguity**: Return best guess or default

This is intentional because:
- Content type is often **auto-detected**, not user-configured
- The "wrong" content type causes minor UX issues (sorting), not broken builds
- Failing loudly would create friction for edge cases that work fine with defaults

### When Exceptions ARE Appropriate

Exceptions should be raised for:
- **Invalid API usage**: `register_strategy(None, ...)` or non-strategy objects
- **Type errors**: Wrong parameter types that indicate programmer error

---

## Proposed Changes

### Phase 1: Add Debug Logging (15 min)

#### 1.1 Add Logger Import to `registry.py`

**File**: `bengal/content_types/registry.py`

**Change**: Add import at top of file

```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)
```

#### 1.2 Add Logging to `get_strategy()`

**File**: `bengal/content_types/registry.py:125-151`

**Before**:
```python
def get_strategy(content_type: str) -> ContentTypeStrategy:
    """Get the strategy for a content type."""
    return CONTENT_TYPE_REGISTRY.get(content_type, PageStrategy())
```

**After**:
```python
def get_strategy(content_type: str) -> ContentTypeStrategy:
    """Get the strategy for a content type."""
    strategy = CONTENT_TYPE_REGISTRY.get(content_type)
    if strategy is None:
        logger.debug(
            "content_type_fallback",
            requested_type=content_type,
            fallback_strategy="PageStrategy",
            registered_types=list(CONTENT_TYPE_REGISTRY.keys()),
        )
        return PageStrategy()
    return strategy
```

### Phase 2: Add Input Validation (15 min)

#### 2.1 Validate `register_strategy()` Inputs

**File**: `bengal/content_types/registry.py:248-291`

**Before**:
```python
def register_strategy(content_type: str, strategy: ContentTypeStrategy) -> None:
    """Register a custom content type strategy."""
    CONTENT_TYPE_REGISTRY[content_type] = strategy
```

**After**:
```python
def register_strategy(content_type: str, strategy: ContentTypeStrategy) -> None:
    """
    Register a custom content type strategy.

    Args:
        content_type: Type name to register. Use lowercase, hyphenated names.
        strategy: Strategy instance. Must be a ContentTypeStrategy subclass.

    Raises:
        TypeError: If strategy is not a ContentTypeStrategy instance.
        ValueError: If content_type is empty or not a string.
    """
    # Validate content_type
    if not isinstance(content_type, str) or not content_type.strip():
        raise ValueError(
            f"content_type must be a non-empty string, got {type(content_type).__name__}"
        )

    # Validate strategy type
    if not isinstance(strategy, ContentTypeStrategy):
        raise TypeError(
            f"strategy must be a ContentTypeStrategy instance, "
            f"got {type(strategy).__name__}"
        )

    # Warn if overwriting built-in
    if content_type in CONTENT_TYPE_REGISTRY:
        existing = CONTENT_TYPE_REGISTRY[content_type]
        logger.info(
            "content_type_strategy_replaced",
            content_type=content_type,
            old_strategy=type(existing).__name__,
            new_strategy=type(strategy).__name__,
        )

    CONTENT_TYPE_REGISTRY[content_type] = strategy
```

### Phase 3: Extract Shared Template Helper (Optional, 15 min)

#### 3.1 Add Helper to Base Class

**File**: `bengal/content_types/base.py`

Add as a static method or module-level function:

```python
def _check_template_exists(template_name: str, template_engine: Any) -> bool:
    """
    Check if a template exists in the template engine.

    Args:
        template_name: Template path to check (e.g., "blog/list.html")
        template_engine: Template engine instance with env.get_template()

    Returns:
        True if template exists, False otherwise
    """
    if template_engine is None:
        return False
    try:
        template_engine.env.get_template(template_name)
        return True
    except Exception as e:
        logger.debug(
            "template_existence_check_failed",
            template=template_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False
```

Then update all 5 locations to use this shared helper.

---

## Implementation Phases

| Phase | Changes | Time | Risk |
|-------|---------|------|------|
| 1 | Add debug logging for fallbacks | 15 min | None |
| 2 | Add input validation to `register_strategy()` | 15 min | Low (new exceptions) |
| 3 | Extract shared template helper (optional) | 15 min | Low (refactor) |

**Total**: 30-45 minutes

### Phase Dependencies

```
Phase 1 (logging) ─┬─> Phase 2 (validation)
                   │
                   └─> Phase 3 (refactor) [optional]
```

Phases 2 and 3 can be done independently after Phase 1.

---

## Success Criteria

### Metrics

| Criterion | Before | After |
|-----------|--------|-------|
| Debug logging for fallbacks | ❌ | ✅ |
| Input validation in `register_strategy()` | ❌ | ✅ |
| Type checking for strategy parameter | ❌ | ✅ |
| Warning for built-in overwrites | ❌ | ✅ |
| Adoption Score | 2/10 | 5/10 |

### Test Coverage

Add tests for:
- [ ] `get_strategy()` logs when falling back
- [ ] `register_strategy()` raises `TypeError` for non-strategy
- [ ] `register_strategy()` raises `ValueError` for empty string
- [ ] `register_strategy()` logs warning when overwriting

### Non-Goals

The following are explicitly **not** goals of this RFC:
- ❌ Adding error codes to `ErrorCode` enum
- ❌ Converting silent fallbacks to exceptions
- ❌ Adding `record_error()` session tracking
- ❌ Changing the graceful degradation design

---

## Risks and Mitigations

### Risk 1: New Exceptions in `register_strategy()`

**Risk**: Existing code that passes invalid arguments will now fail.

**Mitigation**:
- Review all `register_strategy()` call sites (grep shows only test files)
- Exceptions are for true programmer errors, not runtime conditions
- Add clear error messages with fix suggestions

**Call Site Search**:
```bash
grep -r "register_strategy" bengal/ tests/ --include="*.py"
```

### Risk 2: Logging Volume

**Risk**: Debug logging for every fallback could create noise.

**Mitigation**:
- Use `logger.debug()` (filtered out in production)
- Log only once per unique content_type per build (could add dedup if needed)

---

## Appendix: File References

### Files to Modify

| File | Lines | Changes |
|------|-------|---------|
| `bengal/content_types/registry.py` | 292 | Add logger, update `get_strategy()`, update `register_strategy()` |
| `bengal/content_types/base.py` | 330 | Extract template helper (Phase 3) |
| `bengal/content_types/strategies.py` | 637 | Use shared template helper (Phase 3) |

### Related Files (No Changes)

| File | Relationship |
|------|--------------|
| `bengal/errors/codes.py` | No new codes needed |
| `bengal/content_types/__init__.py` | Exports unchanged |
| `tests/unit/content_types/test_strategies.py` | Add validation tests |

### Test File Updates

**File**: `tests/unit/content_types/test_strategies.py`

Add new test class:

```python
class TestRegisterStrategyValidation:
    """Test input validation for register_strategy()."""

    def test_raises_type_error_for_non_strategy(self):
        """Should raise TypeError when strategy is not ContentTypeStrategy."""
        with pytest.raises(TypeError, match="must be a ContentTypeStrategy"):
            register_strategy("test", {"not": "a strategy"})

    def test_raises_value_error_for_empty_content_type(self):
        """Should raise ValueError for empty content type string."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_strategy("", PageStrategy())

    def test_raises_value_error_for_non_string_content_type(self):
        """Should raise ValueError when content_type is not a string."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_strategy(123, PageStrategy())

    def test_logs_warning_when_overwriting_builtin(self, caplog):
        """Should log info when overwriting an existing strategy."""
        import logging

        with caplog.at_level(logging.INFO):
            register_strategy("blog", PageStrategy())

        assert "content_type_strategy_replaced" in caplog.text

        # Restore original
        register_strategy("blog", BlogStrategy())
```

---

## Decision

**Recommendation**: Implement Phases 1 and 2 (30 minutes total). Phase 3 is optional and can be deferred.

**Rationale**: The content_types package is low-risk and functioning correctly. The proposed changes improve debuggability and catch programmer errors without changing the core design philosophy of graceful degradation.
