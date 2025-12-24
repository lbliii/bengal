# RFC: Collections Package Error System Adoption

**Status**: Evaluated  
**Created**: 2025-12-24  
**Evaluated**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/collections/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Content validation is user-facing; errors need consistency  
**Estimated Effort**: 0.5 days (single dev)

---

## Executive Summary

The `bengal/collections/` package has **strong exception class design** but **incomplete error code integration**. Exception classes properly extend `BengalContentError`, but error codes are underutilized and error tracking/session recording is absent.

**Current state**:
- **3 exception classes**: `ContentValidationError`, `CollectionNotFoundError`, `SchemaError` — all extend `BengalContentError` ✅
- **1 error code usage**: Only `ErrorCode.C002` in `__init__.py:170`
- **0 collection-specific codes**: No N0xx codes used for validation errors
- **0 `record_error()` calls**: No error session tracking
- **4 silent failure points**: `loader.py` catches exceptions and returns empty dict

**Adoption Score**: 6/10

**Recommendation**: Add collection-specific error codes (N011-N015), integrate codes into exception raises, add `record_error()` for session tracking, and improve error propagation in `loader.py`.

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
- **Error session recording** for build summaries
- **Investigation helpers** (grep commands, related files)
- **Consistent formatting** across the codebase

The collections package has well-designed exception classes but:
- Exception raises don't include error codes (except one `C002` use)
- Errors aren't recorded to the session for aggregation
- `loader.py` silently swallows errors, returning empty dicts
- No collection-specific error codes exist

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No error codes | Can't search for error docs | No quick code lookup |
| No session recording | No error aggregation in build summary | Missing error patterns |
| Silent failures in loader | Collections silently not loaded | Hard-to-debug missing schemas |
| Generic codes only | Vague error categorization | No collection-specific documentation |

---

## Current State Evidence

### Exception Class Hierarchy

**File**: `bengal/collections/errors.py`

```
BengalContentError (base, from bengal.errors)
├── ContentValidationError  - Content fails schema validation
├── CollectionNotFoundError - Referenced collection doesn't exist
└── SchemaError             - Schema definition is invalid
```

All three extend `BengalContentError` ✅ — verified in `test_errors.py:192,228,252`.

### Error Code Usage

**Total**: 1 usage of `ErrorCode` in entire collections package.

| File | Location | Code | Usage |
|------|----------|------|-------|
| `__init__.py` | Line 170 | `C002` | `CollectionConfig.__post_init__` raises when missing directory/loader |

**Example** (`__init__.py:163-171`):

```python
from bengal.errors import BengalConfigError, ErrorCode

if self.directory is None and self.loader is None:
    raise BengalConfigError(
        "CollectionConfig requires either 'directory' (for local content) "
        "or 'loader' (for remote content)",
        suggestion="Set either 'directory' for local content or 'loader' for remote content",
        code=ErrorCode.C002,
    )
```

### Exception Raises Without Codes

**`ContentValidationError`** — Raised in 1 location, no error code:

```python
# discovery/content_parser.py:262-267
raise ContentValidationError(
    message=f"Validation failed for {file_path}",
    path=file_path,
    errors=result.errors,
    collection_name=collection_name,
)  # No code=ErrorCode.Nxxx
```

**`CollectionNotFoundError`** — No raises found in codebase (only tests).

**`SchemaError`** — No raises found in codebase (only tests).

### Silent Failures in `loader.py`

**4 locations** catch exceptions and return empty dict without raising:

| Location | Trigger | Action | Problem |
|----------|---------|--------|---------|
| Line 229-235 | Module spec creation fails | `return {}` + warning log | Silent failure |
| Line 243-249 | `collections` not defined | `return {}` + warning log | Silent failure |
| Line 251-257 | `collections` not a dict | `return {}` + warning log | Silent failure |
| Line 269-276 | Any import error | `return {}` + error log | Silent failure |

**Example** (`loader.py:269-276`):

```python
except Exception as e:
    logger.error(
        "collections_load_error",
        path=str(collections_path),
        error=str(e),
        error_type=type(e).__name__,
    )
    return {}  # Silently continues without collections
```

### Missing Content Error Codes

**File**: `bengal/errors/codes.py:120-131`

Current N-series codes are for general content errors:

```python
# Content errors (N001-N099)
N001 = "frontmatter_invalid"
N002 = "frontmatter_date_invalid"
N003 = "content_file_encoding"
N004 = "content_file_not_found"
N005 = "content_markdown_error"
N006 = "content_shortcode_error"
N007 = "content_toc_extraction_error"
N008 = "content_taxonomy_invalid"
N009 = "content_weight_invalid"
N010 = "content_slug_invalid"
# No collection-specific codes
```

---

## Gap Analysis

### 1. Missing Collection Error Codes

**Current**: No collection-specific error codes  
**Expected**: N011-N015 for collection operations

| Proposed Code | Value | Use Case |
|---------------|-------|----------|
| N011 | `collection_validation_failed` | Schema validation failure |
| N012 | `collection_not_found` | Unknown collection referenced |
| N013 | `collection_schema_invalid` | Schema class definition error |
| N014 | `collection_load_failed` | collections.py import error |
| N015 | `collection_directory_missing` | Collection directory doesn't exist |

### 2. Exception Classes Don't Use Codes

**Current**: `ContentValidationError`, `CollectionNotFoundError`, `SchemaError` don't accept/use error codes  
**Expected**: All raises include appropriate error code

**Example fix** — `ContentValidationError`:

```python
# Current
raise ContentValidationError(
    message=f"Validation failed for {file_path}",
    path=file_path,
    errors=result.errors,
    collection_name=collection_name,
)

# After
raise ContentValidationError(
    message=f"Validation failed for {file_path}",
    path=file_path,
    errors=result.errors,
    collection_name=collection_name,
    code=ErrorCode.N011,  # collection_validation_failed
)
```

### 3. No Error Session Recording

**Current**: 0 calls to `record_error()` in collections package  
**Expected**: All raised errors recorded for session aggregation

**Impact**: Build summaries don't include collection validation errors.

> **Note**: `record_error()` adoption is low across Bengal (only 3 calls in `analysis/graph_builder.py`). This RFC aligns collections with the intended pattern.

### 4. Silent Failure in `loader.py`

**Current**: Returns `{}` on errors, builds proceed without collections  
**Expected**: Option to raise on collection loading failures; always record errors

**Decision needed**: Should collection load failures:
- A) Warn and continue (current behavior) — lenient, but hides config issues
- B) Raise in strict mode — fail fast for invalid collections.py
- C) Always record to session — visible in summary even if build continues

**Recommendation**: Option C + add strict mode option for Option B.

### 5. Missing `BuildPhase.DISCOVERY` for Collection Errors

Collections are loaded during discovery phase, but `ContentValidationError` inherits `BuildPhase.PARSING` from `BengalContentError`.

**Current**: Build phase is `PARSING` (inherited)  
**Expected**: `DISCOVERY` for collection loading, `PARSING` for validation

---

## Proposed Changes

### Phase 1: Add Error Codes (15 min)

**File**: `bengal/errors/codes.py`

Add after N010:

```python
# ============================================================
# Content errors (N001-N099) - continued: Collections
# ============================================================
N011 = "collection_validation_failed"   # Schema validation failure
N012 = "collection_not_found"           # Unknown collection referenced
N013 = "collection_schema_invalid"      # Schema class definition error
N014 = "collection_load_failed"         # collections.py import error
N015 = "collection_directory_missing"   # Collection directory doesn't exist
```

### Phase 2: Update Exception Classes (30 min)

#### 2.1 `ContentValidationError` — Accept code parameter

**File**: `bengal/collections/errors.py:118-146`

```python
def __init__(
    self,
    message: str,
    path: Path,
    errors: list[ValidationError] | None = None,
    collection_name: str | None = None,
    *,
    code: ErrorCode | None = None,  # ADD
    suggestion: str | None = None,
    original_error: Exception | None = None,
) -> None:
    # Default to N011 if not provided
    if code is None:
        from bengal.errors import ErrorCode
        code = ErrorCode.N011

    super().__init__(
        message=message,
        file_path=path,
        suggestion=suggestion,
        original_error=original_error,
        code=code,  # PASS to parent
    )
```

#### 2.2 `CollectionNotFoundError` — Add code

**File**: `bengal/collections/errors.py:235-265`

```python
def __init__(
    self,
    collection_name: str,
    available: list[str] | None = None,
    *,
    suggestion: str | None = None,
) -> None:
    # ...existing logic...

    from bengal.errors import ErrorCode

    super().__init__(
        message=message,
        suggestion=suggestion,
        code=ErrorCode.N012,  # collection_not_found
    )
```

#### 2.3 `SchemaError` — Add code

**File**: `bengal/collections/errors.py:286-312`

```python
def __init__(
    self,
    schema_name: str,
    message: str,
    *,
    file_path: Path | None = None,
    suggestion: str | None = None,
    original_error: Exception | None = None,
) -> None:
    # ...existing logic...

    from bengal.errors import ErrorCode

    super().__init__(
        message=error_message,
        file_path=file_path,
        suggestion=suggestion,
        original_error=original_error,
        code=ErrorCode.N013,  # collection_schema_invalid
    )
```

### Phase 3: Add Error Recording (30 min)

#### 3.1 `ContentParser.validate_against_collection`

**File**: `bengal/discovery/content_parser.py:257-267`

```python
if not result.valid:
    from bengal.errors import record_error, ErrorCode

    error = ContentValidationError(
        message=f"Validation failed for {file_path}",
        path=file_path,
        errors=result.errors,
        collection_name=collection_name,
        code=ErrorCode.N011,
    )

    # Record for session aggregation
    record_error(error, file_path=str(file_path))

    if self._strict_validation:
        raise error
    else:
        logger.warning(...)
        return metadata
```

#### 3.2 `loader.py` — Add error recording

**File**: `bengal/collections/loader.py:269-276`

```python
except Exception as e:
    from bengal.errors import record_error, BengalContentError, ErrorCode

    error = BengalContentError(
        f"Failed to load collections from {collections_path}",
        code=ErrorCode.N014,
        file_path=collections_path,
        original_error=e,
        suggestion="Check collections.py for syntax errors",
    )
    record_error(error, file_path=str(collections_path))

    logger.error(
        "collections_load_error",
        path=str(collections_path),
        error=str(e),
        error_type=type(e).__name__,
        code="N014",
    )
    return {}
```

### Phase 4: Add Test Mapping (15 min)

**File**: `bengal/errors/exceptions.py` (in `get_related_test_files`)

```python
test_mapping: dict[type, list[str]] = {
    # ... existing mappings ...
    BengalContentError: [
        "tests/unit/collections/",  # ADD
        "tests/unit/content/",
    ],
}
```

> **Note**: 6 test files exist in `tests/unit/collections/`: `test_collection_config.py`, `test_discovery_integration.py`, `test_errors.py`, `test_loader.py`, `test_schema_validator.py`, `test_schemas.py`.

### Phase 5: Update Validate Collections Config (15 min)

**File**: `bengal/collections/loader.py:353-394`

Currently returns warning strings. Should use error codes:

```python
def validate_collections_config(
    collections: dict[str, CollectionConfig[Any]],
    content_root: Path,
) -> list[tuple[str, ErrorCode]]:  # Return code with message
    """..."""
    from bengal.errors import ErrorCode

    warnings: list[tuple[str, ErrorCode]] = []

    for name, config in collections.items():
        if config.directory is None:
            continue
        collection_dir = content_root / config.directory

        if not collection_dir.exists():
            warnings.append((
                f"Collection '{name}' directory does not exist: {collection_dir}",
                ErrorCode.N015,
            ))
        elif not collection_dir.is_dir():
            warnings.append((
                f"Collection '{name}' path is not a directory: {collection_dir}",
                ErrorCode.N015,
            ))

    return warnings
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add N011-N015 error codes | 15 min | P1 |
| 2 | Update exception classes to use codes | 30 min | P1 |
| 3 | Add `record_error()` calls | 30 min | P1 |
| 4 | Update test mapping | 15 min | P2 |
| 5 | Update `validate_collections_config` | 15 min | P2 |

**Total**: 1.75-2 hours

---

## Success Criteria

### Must Have

- [ ] N011-N015 error codes defined in `codes.py`
- [ ] `ContentValidationError` includes `code` parameter
- [ ] `CollectionNotFoundError` uses `ErrorCode.N012`
- [ ] `SchemaError` uses `ErrorCode.N013`
- [ ] `record_error()` called when validation fails
- [ ] Error recording in `loader.py` exception handler

### Should Have

- [ ] `validate_collections_config` returns error codes
- [ ] Test mapping updated for collections
- [ ] All existing tests pass after changes

### Nice to Have

- [ ] Strict mode option for `load_collections` that raises on errors
- [ ] Investigation helpers for collection errors

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing exception handlers | Low | Low | All changes are additive; `code` defaults to appropriate value |
| Test failures | Low | Low | Run `pytest tests/unit/collections/` after changes |
| Circular imports | Low | Medium | Use `from bengal.errors import ...` inside methods, not at module level |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/errors/codes.py` | Add error codes | +6 |
| `bengal/collections/errors.py` | Add code params to 3 classes | +15 |
| `bengal/discovery/content_parser.py` | Add record_error + code | +8 |
| `bengal/collections/loader.py` | Add error recording | +12 |
| `bengal/errors/exceptions.py` | Add test mapping | +1 |
| **Total** | — | ~42 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Exception class design | 9/10 | 9/10 | Already excellent |
| Error code usage | 2/10 | 9/10 | Codes integrated |
| Error session recording | 0/10 | 9/10 | `record_error()` added |
| Build phase tracking | 7/10 | 8/10 | Inherited from parent |
| Test mapping | 0/10 | 10/10 | Added to exceptions.py |
| Silent failure handling | 4/10 | 8/10 | Errors recorded |
| **Overall** | **6/10** | **9/10** | — |

---

## References

- `bengal/collections/errors.py` — Exception class definitions
- `bengal/collections/__init__.py:163-171` — Only current error code usage
- `bengal/collections/loader.py:229-276` — Silent failure locations (4 points)
- `bengal/discovery/content_parser.py:262-267` — ContentValidationError raise
- `bengal/errors/codes.py:120-131` — Content error codes (N001-N010)
- `bengal/errors/session.py` — `record_error()` implementation
- `tests/unit/collections/` — 6 test files for validation

---

## Evaluation Notes

**Verified**: 2025-12-24

All claims in this RFC have been verified against the source code:

- ✅ Exception hierarchy confirmed via `errors.py:80,215,268` and tests
- ✅ Single `ErrorCode` usage confirmed at `__init__.py:170`
- ✅ Zero `record_error()` calls confirmed via grep
- ✅ 4 silent failure points verified in `loader.py`
- ✅ `ContentValidationError` raise at `content_parser.py:262` lacks error code

**Ready for implementation.**
