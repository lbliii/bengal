# RFC: Autodoc Package Error Handling Adoption

**Status**: Ready for Review  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/autodoc/`  
**Confidence**: 92% 🟢 (verified via grep across autodoc and errors packages)  
**Priority**: P2 (Medium) — Error consistency improves debugging and user experience  
**Estimated Effort**: 3-4 hours (single dev)

---

## Executive Summary

The `bengal/autodoc/` package has **partial adoption** of Bengal's structured error handling framework. Core error paths correctly use `BengalError` subclasses with `ErrorCode`, but significant gaps exist in extractors and models.

**Current state**:
- **12 imports** of Bengal error classes across autodoc
- **18 uses** of `ErrorCode` (but only 3 distinct codes: `D001`, `D002`, `C003`)
- **20 logging calls** that should be structured errors
- **3 locations** raising `BengalError` without codes

**True gaps**:
- `models/common.py` — uses base `BengalError` without error codes
- `extractors/openapi.py` — logs errors instead of raising structured exceptions
- `extractors/python/extractor.py` — catches exceptions broadly, logs instead of structured errors
- All orchestrator failures use same `D001` code (semantic mismatch: `D001` means "content_dir_not_found", not extraction failure)

**Recommendation**: Add autodoc-specific error codes (`O001-O006`), convert critical logging to structured errors, and apply `enrich_error()` pattern from discovery package.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Proposed Error Codes](#proposed-error-codes)
5. [Implementation Plan](#implementation-plan)
6. [Migration Guide](#migration-guide)
7. [Success Criteria](#success-criteria)
8. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

Bengal's error handling framework provides:
- **Unique error codes** for quick identification and documentation linking
- **Actionable suggestions** guiding users to fixes
- **Context enrichment** with file paths, build phases, and debug payloads
- **Session tracking** for detecting recurring patterns
- **Recovery patterns** for graceful degradation

Without consistent adoption in autodoc:
- **Debugging is harder** — generic exceptions lack context
- **User experience suffers** — no actionable suggestions for extraction failures
- **Error tracking is incomplete** — session tracking can't aggregate autodoc errors
- **Documentation gaps** — no error code documentation for autodoc failures
- **Semantic mismatch** — autodoc uses `D001` ("content_dir_not_found") for extraction failures, violating code semantics

### Current Adoption Score

| Aspect | Score | Notes |
|--------|-------|-------|
| Exception Classes | 🟢 80% | Uses `BengalDiscoveryError`, `BengalConfigError` |
| Error Codes | 🟡 60% | Codes used but limited variety; some missing |
| Suggestions | 🟢 85% | Actionable suggestions included when errors raised |
| Context Enrichment | 🟠 40% | `file_path` used sometimes; no `BuildPhase`, no `enrich_error()` |
| Graceful Degradation | 🟡 65% | Some paths return `[]` vs raise; not using `error_recovery_context()` |

**Overall: 66% 🟡 Moderate Adoption**

---

## Current State Evidence

### Correct Usage (What's Working)

**`extractor.py:212-219`** — Proper structured error:

```python
from bengal.errors import BengalDiscoveryError, ErrorCode

raise BengalDiscoveryError(
    f"Source must be a file or directory: {source}",
    file_path=source if isinstance(source, Path) else None,
    suggestion="Provide a valid file or directory path for autodoc extraction",
    code=ErrorCode.D002,
)
```

**`cli.py:102-108`** — Config validation:

```python
from bengal.errors import BengalConfigError, ErrorCode

raise BengalConfigError(
    f"Unsupported framework: {framework}. Use 'click', 'argparse', or 'typer'",
    suggestion="Set framework to 'click', 'argparse', or 'typer'",
    code=ErrorCode.C003,
)
```

**`orchestrator.py:498-505`** — Strict mode enforcement:

```python
from bengal.errors import BengalDiscoveryError, ErrorCode

raise BengalDiscoveryError(
    f"Python extraction failed in strict mode: {e}",
    suggestion="Fix Python source code issues or disable strict mode",
    file_path=source_dir,
    code=ErrorCode.D001,
) from e
```

### Error Code Usage Summary

| File | ErrorCode | Count | Context | Semantic Match? |
|------|-----------|-------|---------|-----------------|
| `extractor.py:212` | `D002` | 1 | Invalid source path | ✅ Correct |
| `orchestrator.py` | `D001` | 5 | All extraction failures | ❌ Mismatch |
| `cli.py:102,134` | `C003` | 2 | Framework validation | ✅ Correct |
| `cli.py:612` | `D001` | 1 | Typer extraction failure | ❌ Mismatch |

**Critical Issue**: `D001` is defined as `"content_dir_not_found"` but used for extraction failures. This is a semantic mismatch — the error code's meaning doesn't match its usage.

---

## Gap Analysis

### Gap 1: Missing Error Codes in `models/common.py`

**Location**: `bengal/autodoc/models/common.py:36-48, 89-105`

```python
# Current (no error code)
from bengal.errors import BengalError

if self.line < 1:
    raise BengalError(
        f"Line must be >= 1, got {self.line}",
        suggestion="Line numbers must be 1-based (first line is 1)",
    )
```

**Problem**: Uses base `BengalError` without:
- Specific error code
- Appropriate subclass (`BengalContentError` or `BengalConfigError`)
- File context

**Fix**: Use `BengalContentError` with a parsing/validation code.

---

### Gap 2: OpenAPI Extractor Uses Logging Instead of Structured Errors

**Location**: `bengal/autodoc/extractors/openapi.py:92-104`

```python
# Current (logs and returns empty list)
if not source.exists():
    logger.warning(f"OpenAPI spec not found: {source}")
    return []

try:
    content = source.read_text(encoding="utf-8")
    # ... parse ...
except Exception as e:
    logger.error(f"Failed to parse OpenAPI spec {source}: {e}")
    return []
```

**Problem**:
- File not found → should raise `BengalDiscoveryError` with `D002`
- Parse failure → should raise `BengalContentError` with `P001` or `P002`
- No actionable suggestions provided

**Logging locations that should be errors**:
| Line | Message | Should Be |
|------|---------|-----------|
| 67 | "External $ref not supported" | Warning OK (graceful degradation) |
| 77 | "Could not resolve $ref" | Warning OK (graceful degradation) |
| 93 | "OpenAPI spec not found" | `BengalDiscoveryError(code=D002)` |
| 103 | "Failed to parse OpenAPI spec" | `BengalContentError(code=P001/P002)` |

---

### Gap 3: Python Extractor Catches Exceptions Broadly

**Location**: `bengal/autodoc/extractors/python/extractor.py:280-304, 333-358`

```python
# Current (logs and continues)
except SyntaxError as e:
    logger.warning(f"Syntax error in {py_file}: line {e.lineno}, {e.msg}")
except Exception as e:
    import traceback
    logger.warning(
        f"Failed to extract {py_file}\n"
        f"  Error: {type(e).__name__}: {e}\n"
    )
```

**Problem**:
- No structured error context
- No error codes for tracking
- Cannot aggregate extraction failures in error session
- Compare to `discovery/content_parser.py` which uses `enrich_error()`

---

### Gap 4: Semantic Mismatch and Repetitive Error Codes

**Location**: `bengal/autodoc/orchestration/orchestrator.py`

**Critical Issue**: All autodoc failures use `D001`, but `D001` is defined as `"content_dir_not_found"` in `bengal/errors/codes.py:146`. This violates the error code's semantic meaning — autodoc extraction failures are not "content directory not found" errors.

```python
# From bengal/errors/codes.py:146
D001 = "content_dir_not_found"  # ← Semantic: discovery can't find content directory
```

| Line | Failure Type | Current Code | Semantic Issue | Should Be |
|------|--------------|--------------|----------------|-----------|
| 504 | Python extraction failed | `D001` | ❌ Not a missing directory | `O001` |
| 548 | CLI extraction failed | `D001` | ❌ Not a missing directory | `O002` |
| 595 | OpenAPI extraction failed | `D001` | ❌ Not a missing directory | `O003` |
| 607 | No elements produced | `D001` | ❌ Not a missing directory | `O004` |
| 628 | Final failure summary | `D001` | ❌ Not a missing directory | `O005` |

**Also in**: `bengal/autodoc/extractors/cli.py:612` — uses `D001` for Typer extraction failure.

**Problems**:
1. Violates error code semantics — `D001` has a specific meaning
2. Cannot distinguish failure types in error tracking
3. Documentation links to wrong error description
4. Logs misleading error codes

---

### Gap 5: Missing Context Enrichment

**Best practice from `discovery/content_parser.py:122-131`**:

```python
from bengal.errors import BengalDiscoveryError, ErrorContext, enrich_error

context = ErrorContext(
    file_path=self.file_path,
    phase=BuildPhase.DISCOVERY,
    component="content_parser",
)
enrich_error(error, context, BengalDiscoveryError)
```

**Current autodoc**: Does not use `enrich_error()`, `ErrorContext`, or `BuildPhase`.

---

## Proposed Error Codes

Add new autodoc-specific codes to `bengal/errors/codes.py`. Start with 6 critical codes (can expand later if needed):

```python
# ============================================================
# Autodoc errors (O001-O099)
# ============================================================
O001 = "autodoc_extraction_failed"        # General extraction failure (strict mode)
O002 = "autodoc_syntax_error"             # Python syntax error in source
O003 = "autodoc_openapi_parse_failed"     # OpenAPI YAML/JSON parse failure
O004 = "autodoc_cli_load_failed"          # CLI app import/load failure
O005 = "autodoc_invalid_source"           # Invalid source path/location
O006 = "autodoc_no_elements_produced"     # Extraction produced no elements
```

**Rationale for 6 codes vs 11**:
- Avoids over-engineering — start minimal, expand if needed
- Each code represents a distinct failure category
- Sufficient granularity for debugging and documentation

**Update `ErrorCode.category` property** (`bengal/errors/codes.py:238-251`):

```python
categories = {
    # ... existing ...
    "O": "autodoc",
}
```

**Update `ErrorCode.subsystem` property** (`bengal/errors/codes.py:264-277`):

```python
subsystem_map = {
    # ... existing ...
    "O": "autodoc",
}
```

**Update module docstring** (`bengal/errors/codes.py:8-23`):

```rst
====  ================  =================================
Code  Category          Description
====  ================  =================================
...
O     Autodoc           Autodoc extraction and generation
====  ================  =================================
```

---

## Implementation Plan

### Phase 1: Add Error Codes (20 min)

**File**: `bengal/errors/codes.py`

1. Add `O001-O006` error codes after the Graph errors section (~line 215)
2. Update `category` property mapping (line 248)
3. Update `subsystem` property mapping (line 275)
4. Update module docstring table (lines 8-23)

### Phase 2: Fix `models/common.py` (15 min)

**File**: `bengal/autodoc/models/common.py`

**Lines to update**: 35-48, 89-106

```python
# Before (lines 37-43)
from bengal.errors import BengalError
if self.line < 1:
    raise BengalError(
        f"Line must be >= 1, got {self.line}",
        suggestion="Line numbers must be 1-based (first line is 1)",
    )

# After
from bengal.errors import BengalContentError, ErrorCode
if self.line < 1:
    raise BengalContentError(
        f"Line must be >= 1, got {self.line}",
        suggestion="Line numbers must be 1-based (first line is 1)",
        code=ErrorCode.O005,  # autodoc_invalid_source
    )
```

**Also update**: `QualifiedName.__post_init__` (lines 89-106) — same pattern.

### Phase 3: Fix OpenAPI Extractor (30 min)

**Changes to `extractors/openapi.py`**:

```python
# Before
if not source.exists():
    logger.warning(f"OpenAPI spec not found: {source}")
    return []

# After
if not source.exists():
    from bengal.errors import BengalDiscoveryError, ErrorCode
    raise BengalDiscoveryError(
        f"OpenAPI spec not found: {source}",
        file_path=source,
        suggestion="Ensure the OpenAPI spec file exists at the configured path",
        code=ErrorCode.D002,
    )
```

```python
# Before
except Exception as e:
    logger.error(f"Failed to parse OpenAPI spec {source}: {e}")
    return []

# After
except yaml.YAMLError as e:
    from bengal.errors import BengalContentError, ErrorCode
    raise BengalContentError(
        f"Failed to parse OpenAPI YAML spec: {e}",
        file_path=source,
        suggestion="Check YAML syntax in your OpenAPI specification",
        code=ErrorCode.P001,
    ) from e
except json.JSONDecodeError as e:
    from bengal.errors import BengalContentError, ErrorCode
    raise BengalContentError(
        f"Failed to parse OpenAPI JSON spec: {e}",
        file_path=source,
        suggestion="Check JSON syntax in your OpenAPI specification",
        code=ErrorCode.P002,
    ) from e
```

### Phase 4: Update Orchestrator Error Codes (20 min)

**File**: `bengal/autodoc/orchestration/orchestrator.py`

Replace all `ErrorCode.D001` with specific codes:

| Line | Context | Current | New | Rationale |
|------|---------|---------|-----|-----------|
| 504 | Python extraction failed | `D001` | `O001` | General extraction failure |
| 548 | CLI extraction failed | `D001` | `O004` | CLI load failure |
| 595 | OpenAPI extraction failed | `D001` | `O003` | OpenAPI parse failure |
| 607 | No elements produced | `D001` | `O006` | No elements produced |
| 628 | Final strict mode failure | `D001` | `O001` | General extraction failure |

**File**: `bengal/autodoc/extractors/cli.py`

| Line | Context | Current | New |
|------|---------|---------|-----|
| 612 | Typer extraction failed | `D001` | `O004` |

### Phase 5: Add Context Enrichment (Optional, 45 min)

**File**: `bengal/autodoc/extractors/python/extractor.py`

**Add `enrich_error()` usage to Python extractor** (lines 282-305, 331-360):

```python
from bengal.errors import (
    BengalContentError,
    ErrorContext,
    ErrorCode,
    enrich_error,
)

context = ErrorContext(
    file_path=py_file,
    operation="extracting Python documentation",
    suggestion="Fix source code issues or exclude file",
)

try:
    file_elements = self._extract_file(py_file)
    elements.extend(file_elements)
except SyntaxError as e:
    error = BengalContentError(
        f"Syntax error in {py_file}: line {e.lineno}, {e.msg}",
        file_path=py_file,
        suggestion="Fix Python syntax error before extraction",
        code=ErrorCode.O002,  # autodoc_syntax_error
    )
    enrich_error(error, context, BengalContentError)
    # In non-strict mode, log and continue; in strict mode, raise
    if self.config.get("strict", False):
        raise error from e
    logger.warning(str(error))
```

**Note**: This phase is optional because the current logging behavior provides graceful degradation. Only implement if strict error tracking is required.

---

## Migration Guide

### For Autodoc Users

**No breaking changes** — existing code continues to work.

**New capabilities**:
- Error codes in exceptions enable filtering and documentation lookup
- Actionable suggestions guide resolution
- Strict mode failures now have distinct codes

**Error code reference**:

| Code | Meaning | Common Cause |
|------|---------|--------------|
| `O001` | Extraction failed | General extraction failure in strict mode |
| `O002` | Syntax error | Python file has syntax errors |
| `O003` | OpenAPI parse failed | Invalid YAML/JSON in OpenAPI spec |
| `O004` | CLI load failed | Can't import/load CLI application |
| `O005` | Invalid source | Bad file path or source location |
| `O006` | No elements | Extraction produced no documentation |

### For Autodoc Developers

**Pattern to follow**:

```python
# ✅ Good: Structured error with code and suggestion
from bengal.errors import BengalDiscoveryError, ErrorCode

raise BengalDiscoveryError(
    "Descriptive message",
    file_path=source_path,
    suggestion="Actionable fix description",
    code=ErrorCode.O001,
)

# ❌ Bad: Logging and returning empty
logger.error(f"Something failed: {e}")
return []

# ❌ Bad: Base BengalError without code
raise BengalError("Something failed")

# ❌ Bad: Using wrong semantic code (D001 = content_dir_not_found)
code=ErrorCode.D001  # Don't use for extraction failures!
```

---

## Success Criteria

### Quantitative

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Files using error codes | 3 | 6 | 6 |
| Distinct error codes used | 3 (D001, D002, C003) | 8+ (O001-O006 + existing) | 8+ |
| Semantic mismatches (D001 misuse) | 6 | 0 | 0 |
| Logging calls for real errors | 2 (OpenAPI) | 0 | 0 |
| `BengalError` without code | 3 | 0 | 0 |

### Qualitative

- [ ] All autodoc errors have unique, searchable codes
- [ ] All raised errors include actionable suggestions
- [ ] OpenAPI extractor raises structured errors (not logging)
- [ ] Orchestrator failures distinguishable by error code
- [ ] `models/common.py` uses appropriate exception class and code
- [ ] No semantic mismatch — autodoc uses `O*` codes, not `D001`

---

## Risks and Mitigations

### Risk 1: Breaking Existing Error Handling

**Mitigation**: New error codes are additive. Existing `D001` usage can be kept for backward compatibility if callers catch by code.

### Risk 2: Test Failures

**Mitigation**:
- Update tests that expect specific error types/messages
- Add new tests for new error codes
- Search for `D001` assertions in autodoc tests

**Test files requiring updates**:

```bash
# Find tests that may assert on D001 or error messages
grep -r "D001\|ErrorCode\|BengalDiscoveryError" tests/autodoc/
```

| Test File | Likely Changes |
|-----------|----------------|
| `tests/autodoc/test_orchestrator.py` | Update `D001` → `O001/O003/O004/O006` |
| `tests/autodoc/extractors/test_python_extractor.py` | Add `O002` syntax error tests |
| `tests/autodoc/extractors/test_openapi.py` | Add `O003` parse error tests |
| `tests/autodoc/extractors/test_cli.py` | Update `D001` → `O004` |
| `tests/autodoc/models/test_common.py` | Update `BengalError` → `BengalContentError` + `O005` |

### Risk 3: Over-Engineering

**Mitigation**:
- Phase 5 (context enrichment) is optional
- Focus on high-impact changes first (Phases 1-4)
- Keep `$ref` resolution warnings as logging (graceful degradation is appropriate there)

---

## Appendix: Files to Modify

### Production Code

| File | Changes | Priority |
|------|---------|----------|
| `bengal/errors/codes.py` | Add `O001-O006` codes, update category/subsystem maps | P1 |
| `bengal/autodoc/models/common.py` | Use `BengalContentError` + `ErrorCode.O005` | P1 |
| `bengal/autodoc/extractors/openapi.py` | Convert `logger.warning/error` to structured errors | P1 |
| `bengal/autodoc/orchestration/orchestrator.py` | Replace `D001` with `O001/O003/O004/O006` | P1 |
| `bengal/autodoc/extractors/cli.py` | Replace `D001` with `O004` | P1 |
| `bengal/autodoc/extractors/python/extractor.py` | Optional: add `enrich_error()` | P2 |

### Test Code

| File | Changes |
|------|---------|
| `tests/autodoc/test_orchestrator.py` | Update error code assertions |
| `tests/autodoc/extractors/test_openapi.py` | Add parse error tests |
| `tests/autodoc/extractors/test_cli.py` | Update error code assertions |
| `tests/autodoc/models/test_common.py` | Update exception type assertions |

---

## References

- `bengal/errors/__init__.py` — Error handling framework documentation
- `bengal/errors/codes.py` — Existing error code definitions
- `bengal/discovery/content_parser.py:119-167` — Best practice for `enrich_error()`
- `bengal/errors/context.py` — `ErrorContext` definition

---

## Verification Commands

Run after implementation to verify success:

```bash
# 1. Verify no D001 misuse in autodoc (should return 0 matches)
grep -rn "ErrorCode.D001" bengal/autodoc/
# Expected: No output

# 2. Verify O* codes are used
grep -rn "ErrorCode.O00" bengal/autodoc/
# Expected: Multiple matches in orchestrator.py, cli.py, models/common.py, openapi.py

# 3. Verify no base BengalError without code
grep -rn "raise BengalError(" bengal/autodoc/
# Expected: No output

# 4. Verify OpenAPI uses structured errors
grep -rn "logger.error\|logger.warning.*OpenAPI" bengal/autodoc/extractors/openapi.py
# Expected: Only $ref warnings (graceful degradation), no file-not-found or parse errors

# 5. Run autodoc tests
pytest tests/autodoc/ -v
# Expected: All tests pass
```
