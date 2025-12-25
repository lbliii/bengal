# RFC: Assets Package Error Handling Adoption

**Status**: Implemented  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/assets/`  
**Confidence**: 95% 🟢 (verified via code inspection of 3 source files and errors package)  
**Priority**: P2 (Medium) — Error consistency improves debugging and user experience  
**Estimated Effort**: 2-3 hours (single dev)

---

## Executive Summary

The `bengal/assets/` package has **partial error handling adoption**. It imports from `bengal.errors` but uses the base `BengalError` instead of the domain-specific `BengalAssetError`, and does not use the asset-specific error codes (`X001`-`X006`) that are already defined.

**Current state**:
- **3 source files**: `__init__.py` (49 LOC), `manifest.py` (316 LOC), `pipeline.py` (514 LOC)
- **Imports `BengalError`**: Yes, but uses base class not `BengalAssetError`
- **Uses `ErrorCode`**: No — asset codes `X001`-`X006` exist but are unused
- **Silent failures**: Multiple `logger.error()` calls that don't raise exceptions

**True gaps**:
- `pipeline.py:475` uses `BengalError` instead of `BengalAssetError`
- No `ErrorCode` usage (should use `X003` for processing failures)
- 5 error logging sites that could benefit from structured errors or raising
- `manifest.py` silently returns `None` on load failures
- `BengalAssetError` missing from test file mapping in `exceptions.py`

**Recommendation**: Adopt `BengalAssetError` with proper error codes, add structured error handling to manifest loading, and update the test file mapping.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Proposed Changes](#proposed-changes)
5. [Implementation Plan](#implementation-plan)
6. [Success Criteria](#success-criteria)
7. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

The assets package handles critical build infrastructure:
- **Asset manifest**: Tracks fingerprinted URLs for cache-busting
- **Node pipeline**: Compiles SCSS, PostCSS, and JavaScript/TypeScript

Without proper error handling:
- **Silent failures hide problems**: SCSS compilation failures just log and continue
- **Investigation is harder**: No error codes for searchability or documentation
- **Inconsistent user experience**: Assets errors don't match the rest of Bengal's error UX
- **AI troubleshooting impaired**: No structured debug payloads or investigation commands

### Error Codes Available But Unused

The `bengal/errors/codes.py` already defines asset-specific error codes:

| Code | Value | Intended Use |
|------|-------|--------------|
| `X001` | `asset_not_found` | Missing asset file |
| `X002` | `asset_invalid_path` | Invalid asset path |
| `X003` | `asset_processing_failed` | Pipeline compilation failure |
| `X004` | `asset_copy_error` | File copy failure |
| `X005` | `asset_fingerprint_error` | Hashing failure |
| `X006` | `asset_minify_error` | Minification failure |

**None of these are currently used.**

---

## Current State Evidence

### Source Files

| File | Lines | Imports Errors? | Uses Structured Errors? |
|------|-------|-----------------|-------------------------|
| `__init__.py` | 49 | ❌ No | N/A (docstring only) |
| `manifest.py` | 316 | ❌ No | ❌ Generic exception handling |
| `pipeline.py` | 514 | ✅ Yes | ⚠️ Partial (uses `BengalError`) |

### Error Handling in `pipeline.py`

**One exception raised** (`pipeline.py:472-478`):

```python
from bengal.errors import BengalError

error_msg = proc.stderr.strip() or proc.stdout.strip()
raise BengalError(
    f"Asset pipeline command failed: {error_msg}",
    suggestion="Check command output and ensure required tools are installed",
)
```

**Issues**:
1. Uses `BengalError` base class instead of `BengalAssetError`
2. No `ErrorCode` (should be `X003`)
3. No `file_path` context
4. No `build_phase` (would be set automatically by `BengalAssetError`)

**Five silent error sites** (log but don't raise):

| Location | Event | Should Use |
|----------|-------|------------|
| `pipeline.py:202` | `pipeline_missing_cli` (sass) | `X003` or raise |
| `pipeline.py:226` | `scss_compile_failed` | `X003` or raise |
| `pipeline.py:240` | `postcss_not_found` | `X003` (warning) |
| `pipeline.py:249` | `postcss_failed` | `X003` or raise |
| `pipeline.py:262` | `pipeline_missing_cli` (esbuild) | `X003` or raise |
| `pipeline.py:292` | `esbuild_failed` | `X003` or raise |

### Error Handling in `manifest.py`

**Generic exception handling** (`manifest.py:296-300`):

```python
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:  # pragma: no cover - defensive logging path
    logger.warning("asset_manifest_load_failed", path=str(path), error=str(exc))
    return None
```

**Issues**:
1. Catches all exceptions generically
2. Returns `None` silently — caller may not realize manifest failed to load
3. No structured error for investigation

### Test File Mapping Gap

`bengal/errors/exceptions.py:269-290` defines test file mappings for all error types **except** `BengalAssetError`:

```python
test_mapping: dict[type, list[str]] = {
    BengalConfigError: ["tests/unit/config/", ...],
    BengalContentError: ["tests/unit/core/test_page.py", ...],
    BengalRenderingError: ["tests/unit/rendering/", ...],
    BengalDiscoveryError: ["tests/unit/discovery/", ...],
    BengalCacheError: ["tests/unit/cache/", ...],
    # BengalAssetError is MISSING
}
```

---

## Gap Analysis

### Tier 1: Critical (Wrong Error Class)

#### `pipeline.py:472-478` — Uses `BengalError` Instead of `BengalAssetError`

**Current**:
```python
from bengal.errors import BengalError

raise BengalError(
    f"Asset pipeline command failed: {error_msg}",
    suggestion="Check command output and ensure required tools are installed",
)
```

**Should Be**:
```python
from bengal.errors import BengalAssetError, ErrorCode

raise BengalAssetError(
    f"Asset pipeline command failed: {error_msg}",
    code=ErrorCode.X003,
    file_path=src,  # or relevant path
    suggestion="Check command output and ensure required tools are installed",
)
```

**Benefits**:
- Auto-sets `build_phase=BuildPhase.ASSET_PROCESSING`
- Error code enables searchability and docs linking
- `file_path` enables "view problematic file" investigation commands

### Tier 2: Missing Error Codes in Logging

These sites log errors but don't use `ErrorCode` for structured tracking:

| Location | Current | Recommended Change |
|----------|---------|-------------------|
| `pipeline.py:202` | `logger.error("pipeline_missing_cli", ...)` | Add `code=ErrorCode.X003.value` to log |
| `pipeline.py:226` | `logger.error("scss_compile_failed", ...)` | Add `code=ErrorCode.X003.value` to log |
| `pipeline.py:262` | `logger.error("pipeline_missing_cli", ...)` | Add `code=ErrorCode.X003.value` to log |
| `pipeline.py:292` | `logger.error("esbuild_failed", ...)` | Add `code=ErrorCode.X003.value` to log |

**Note**: These are intentionally non-fatal (pipeline continues without that tool). Adding error codes to logs enables filtering and searching without changing behavior.

### Tier 3: Silent Manifest Load Failure

`manifest.py:296-300` returns `None` on failure without any structured error context.

**Options**:
1. **Keep current behavior** but add error code to log for searchability
2. **Raise `BengalAssetError`** to make failure explicit (breaking change)
3. **Return sentinel** that indicates failure reason

**Recommendation**: Option 1 (minimal change) — add error code to warning log:

```python
logger.warning(
    "asset_manifest_load_failed",
    path=str(path),
    error=str(exc),
    error_code=ErrorCode.X004.value,  # asset_copy_error or new code
)
```

### Tier 4: Missing Test File Mapping

`exceptions.py:269-290` should include:

```python
BengalAssetError: [
    "tests/unit/assets/",
    "tests/integration/test_assets.py",
],
```

---

## Proposed Changes

### Change 1: Update `pipeline.py` Exception

**File**: `bengal/assets/pipeline.py:472-478`

**Before**:
```python
from bengal.errors import BengalError

error_msg = proc.stderr.strip() or proc.stdout.strip()
raise BengalError(
    f"Asset pipeline command failed: {error_msg}",
    suggestion="Check command output and ensure required tools are installed",
)
```

**After**:
```python
from bengal.errors import BengalAssetError, ErrorCode

error_msg = proc.stderr.strip() or proc.stdout.strip()
raise BengalAssetError(
    f"Asset pipeline command failed: {error_msg}",
    code=ErrorCode.X003,
    suggestion="Check command output and ensure required tools are installed",
)
```

### Change 2: Add Error Codes to Logger Calls

**Files**: `bengal/assets/pipeline.py` (5 locations), `bengal/assets/manifest.py` (1 location)

Add `error_code` field to structured logs:

```python
# pipeline.py:202
logger.error(
    "pipeline_missing_cli",
    tool="sass",
    hint="npm i -D sass",
    error_code=ErrorCode.X003.value,
)

# pipeline.py:226
logger.error(
    "scss_compile_failed",
    source=str(src),
    error=str(e),
    error_code=ErrorCode.X003.value,
)

# manifest.py:299
logger.warning(
    "asset_manifest_load_failed",
    path=str(path),
    error=str(exc),
    error_code=ErrorCode.X001.value,  # asset_not_found equivalent
)
```

### Change 3: Add Test File Mapping

**File**: `bengal/errors/exceptions.py:269-290`

**Add entry**:
```python
BengalAssetError: [
    "tests/unit/assets/",
    "tests/integration/test_assets.py",
],
```

### Change 4: Add Import to `manifest.py`

**File**: `bengal/assets/manifest.py`

**Add import**:
```python
from bengal.errors import ErrorCode
```

---

## Implementation Plan

### Phase 1: Core Exception Fix (30 min)

1. Update `pipeline.py:472-478`:
   - Change `BengalError` → `BengalAssetError`
   - Add `code=ErrorCode.X003`
   - Update import statement

2. Add test file mapping to `exceptions.py`

### Phase 2: Structured Logging (30 min)

1. Add `ErrorCode` import to `pipeline.py` and `manifest.py`
2. Add `error_code` field to all 6 logger calls
3. Verify logs still work correctly

### Phase 3: Verification (30 min)

1. Run existing asset tests
2. Manually trigger a pipeline error to verify new format
3. Check that `get_investigation_commands()` works on asset errors

---

## Success Criteria

### Phase 1 Complete When:

- [x] `pipeline.py` uses `BengalAssetError` instead of `BengalError`
- [x] `ErrorCode.X003` is passed to exception
- [x] `BengalAssetError` added to test file mapping in `exceptions.py`
- [x] All existing tests pass

### Phase 2 Complete When:

- [x] All 6 logger error/warning calls include `error_code` field
- [x] Logs are searchable by error code

### Final Metrics:

| Metric | Before | After |
|--------|--------|-------|
| Uses `BengalAssetError` | 0 | 1 |
| Uses `ErrorCode.X*` | 0 | 7 |
| Test file mapping entries | 5 | 6 |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Exception message format changes | Low | Low | Update any tests that match on message |
| Log format changes break parsing | Low | Low | `error_code` is additive, not breaking |
| Import cycles | Very Low | Medium | `ErrorCode` is in `codes.py`, no cycle risk |

---

## Dependencies

### On Other Packages

- `bengal/errors/` — Provides `BengalAssetError`, `ErrorCode`

### On Other RFCs

- None — This is a self-contained improvement

---

## References

- `bengal/assets/pipeline.py:472-478` — Current exception site
- `bengal/assets/manifest.py:296-300` — Silent failure site
- `bengal/errors/codes.py:199-206` — Asset error codes (X001-X006)
- `bengal/errors/exceptions.py:560-589` — `BengalAssetError` class
- `bengal/errors/exceptions.py:269-290` — Test file mapping (missing asset entry)

---

## Appendix: Full Error Code Reference

| Code | Value | When to Use |
|------|-------|-------------|
| `X001` | `asset_not_found` | Asset file does not exist |
| `X002` | `asset_invalid_path` | Path is malformed or outside allowed directories |
| `X003` | `asset_processing_failed` | SCSS/PostCSS/esbuild compilation error |
| `X004` | `asset_copy_error` | Failed to copy asset to output |
| `X005` | `asset_fingerprint_error` | Content hashing failed |
| `X006` | `asset_minify_error` | Minification failed |
