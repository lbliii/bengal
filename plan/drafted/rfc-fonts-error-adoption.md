# RFC: Fonts Package Error System Adoption

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/fonts/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P3 (Low) — Fonts are optional; failures visible as missing styling  
**Estimated Effort**: 1-2 hours (single dev)

---

## Executive Summary

The `bengal/fonts/` package has **minimal error system integration**. It uses the generic `BengalError` base class instead of the domain-appropriate `BengalAssetError`, has no error codes, no error session recording, and relies heavily on silent failures (returning `[]` or `None` on errors).

**Current state**:
- **2 exception raises**: Both use generic `BengalError` (not `BengalAssetError`)
- **0 error codes**: No `ErrorCode` usage anywhere
- **0 `record_error()` calls**: No error session tracking
- **7 silent failure points**: 4 in `downloader.py` + 3 in `__init__.py`
- **5 exception handlers**: All catch-and-swallow or catch-and-continue patterns

**Adoption Score**: 3/10

**Recommendation**: Replace `BengalError` with `BengalAssetError`, add font-specific error codes (X007-X010), integrate `record_error()` for session tracking, and improve error visibility for download failures.

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

The fonts package currently:
- Uses generic `BengalError` instead of `BengalAssetError`
- Has no error codes for any operation
- Doesn't record errors to the session for aggregation
- Silently swallows download failures, returning empty results
- Provides no investigation helpers or build phase context

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No error codes | Can't search for error docs | No quick code lookup |
| No session recording | No error aggregation in build summary | Missing error patterns |
| Silent failures | Fonts silently not downloaded | Hard-to-debug missing fonts |
| Generic exception class | Wrong build phase assigned | Misleading investigation hints |
| No investigation commands | No grep patterns provided | Manual debugging required |

### Example Failure Scenario

1. User configures `fonts.primary = "NonexistentFont:400"` in `bengal.toml`
2. `GoogleFontsDownloader.download_font()` fails silently, returns `[]`
3. `FontHelper.process()` generates empty CSS or returns `None`
4. Build completes successfully with no font errors shown
5. User's site loads with broken/missing font styling
6. User has no error messages to investigate

---

## Current State Evidence

### Package Structure

```
bengal/fonts/
├── __init__.py      # FontHelper, rewrite_font_urls_with_fingerprints
├── downloader.py    # GoogleFontsDownloader, FontVariant
└── generator.py     # FontCSSGenerator
```

### Exception Class Usage

**File**: `bengal/fonts/downloader.py:176-182`

```python
from bengal.errors import BengalError

if output_dir is None:
    raise BengalError(
        "output_dir is required for download_font",
        suggestion="Provide an absolute output directory path",
    )
```

**Issue**: Uses generic `BengalError` instead of `BengalAssetError`. Fonts are assets processed during the build phase and should use the asset-specific exception class.

**Same pattern at**: `downloader.py:266-272` (download_ttf_font)

### Error Code Usage

**Total**: 0 uses of `ErrorCode` in entire fonts package.

| File | `ErrorCode` Import | Usage |
|------|--------------------|-------|
| `__init__.py` | ❌ None | 0 |
| `downloader.py` | ❌ None | 0 |
| `generator.py` | ❌ None | 0 |

### Silent Failure Points

**7 locations** return empty results on errors without raising:

| File | Line | Trigger | Return | Consequence |
|------|------|---------|--------|-------------|
| `downloader.py` | 195 | No fonts found in API response | `[]` | Font silently skipped |
| `downloader.py` | 232 | Any download exception | `[]` | All fonts silently skipped |
| `downloader.py` | 285 | No TTF fonts found | `[]` | TTF font silently skipped |
| `downloader.py` | 322 | Any TTF download exception | `[]` | All TTF fonts silently skipped |
| `__init__.py` | 206 | Empty config | `None` | Expected behavior ✅ |
| `__init__.py` | 212 | No fonts parsed from config | `None` | Config error hidden |
| `__init__.py` | 239 | No CSS content generated | `None` | Generation failure hidden |

**Example** (`downloader.py:228-232`):

```python
except Exception as e:
    logger.error(
        "font_download_failed", family=family, error=str(e), error_type=type(e).__name__
    )
    return []  # Silently continues without fonts
```

### Exception Handlers

**5 exception catch blocks** in `downloader.py`:

| Location | Catches | Action | Outcome |
|----------|---------|--------|---------|
| Line 228-232 | `Exception` | Log error, return `[]` | Silent failure ❌ |
| Line 318-322 | `Exception` | Log error, return `[]` | Silent failure ❌ |
| Line 385-392 | `ssl.SSLError`, `URLError` | SSL fallback or re-raise | Correct ✅ |
| Line 450-457 | `ssl.SSLError`, `URLError` | SSL fallback or re-raise | Correct ✅ |
| Line 464-473 | `Exception` | Log debug, cleanup, re-raise | Correct ✅ |

### Logger Usage

**4 logging calls** for errors/warnings in `downloader.py`:

| Location | Level | Event Key | Notes |
|----------|-------|-----------|-------|
| Line 194 | `warning` | `no_fonts_found_for_family` | No error code |
| Line 229 | `error` | `font_download_failed` | No error code |
| Line 284 | `warning` | `no_ttf_fonts_found_for_family` | No error code |
| Line 319 | `error` | `ttf_font_download_failed` | No error code |

### Missing Font Error Codes

**File**: `bengal/errors/codes.py:220-225`

Current X-series codes are for general asset errors:

```python
# Asset errors (X001-X099)
X001 = "asset_not_found"
X002 = "asset_invalid_path"
X003 = "asset_processing_failed"
X004 = "asset_copy_error"
X005 = "asset_fingerprint_error"
X006 = "asset_minify_error"
# No font-specific codes
```

---

## Gap Analysis

### 1. Wrong Exception Class

**Current**: `BengalError` (generic base class)  
**Expected**: `BengalAssetError` (fonts are assets processed during build)

The base `BengalError` class doesn't set a default build phase, while `BengalAssetError` correctly defaults to `BuildPhase.ASSET_PROCESSING`.

**Impact**: Investigation helpers and test mappings won't point to the correct subsystem.

### 2. Missing Font Error Codes

**Current**: No font-specific error codes  
**Expected**: X007-X010 for font operations

| Proposed Code | Value | Use Case |
|---------------|-------|----------|
| X007 | `font_download_config_error` | Missing output_dir or invalid config |
| X008 | `font_download_failed` | Network/API failure downloading font |
| X009 | `font_not_found` | Font family not available from Google Fonts |
| X010 | `font_css_generation_failed` | CSS generation failure |

### 3. No Error Session Recording

**Current**: 0 calls to `record_error()` in fonts package  
**Expected**: All significant errors recorded for session aggregation

**Impact**: Build summaries don't include font download failures. Users running `bengal build` see no indication that fonts failed to download.

### 4. Silent Failures Hide Problems

**Current**: Download failures return `[]`, callers get no indication of failure  
**Expected**:
- Errors recorded to session (always)
- Option to raise in strict mode (for CI/CD builds)

**Decision Point**: Should font download failures:
- A) Warn and continue (current behavior) — lenient, but hides problems
- B) Raise in strict mode — fail fast for CI/CD
- C) Always record to session — visible in summary even if build continues

**Recommendation**: Option C as baseline + Option B for strict mode.

### 5. No Build Phase Context

**Current**: Uses `BengalError` which has no default build phase  
**Expected**: `BengalAssetError` with `BuildPhase.ASSET_PROCESSING`

---

## Proposed Changes

### Phase 1: Add Error Codes (10 min)

**File**: `bengal/errors/codes.py`

Add after X006:

```python
# ============================================================
# Asset errors (X001-X099) - continued: Fonts
# ============================================================
X007 = "font_download_config_error"  # Missing output_dir or invalid config
X008 = "font_download_failed"        # Network/API failure downloading font
X009 = "font_not_found"              # Font family not available from Google Fonts
X010 = "font_css_generation_failed"  # CSS generation failure
```

### Phase 2: Update Exception Class Usage (30 min)

#### 2.1 `download_font` — Use BengalAssetError

**File**: `bengal/fonts/downloader.py:176-182`

```python
# Current
from bengal.errors import BengalError

if output_dir is None:
    raise BengalError(
        "output_dir is required for download_font",
        suggestion="Provide an absolute output directory path",
    )

# After
from bengal.errors import BengalAssetError, ErrorCode

if output_dir is None:
    raise BengalAssetError(
        "output_dir is required for download_font",
        code=ErrorCode.X007,
        suggestion="Provide an absolute output directory path",
    )
```

#### 2.2 `download_ttf_font` — Use BengalAssetError

**File**: `bengal/fonts/downloader.py:266-272`

```python
# Current
from bengal.errors import BengalError

if output_dir is None:
    raise BengalError(
        "output_dir is required for download_ttf_font",
        suggestion="Provide an absolute output directory path",
    )

# After
from bengal.errors import BengalAssetError, ErrorCode

if output_dir is None:
    raise BengalAssetError(
        "output_dir is required for download_ttf_font",
        code=ErrorCode.X007,
        suggestion="Provide an absolute output directory path",
    )
```

### Phase 3: Add Error Recording (30 min)

#### 3.1 `download_font` exception handler

**File**: `bengal/fonts/downloader.py:228-232`

```python
# Current
except Exception as e:
    logger.error(
        "font_download_failed", family=family, error=str(e), error_type=type(e).__name__
    )
    return []

# After
except Exception as e:
    from bengal.errors import BengalAssetError, ErrorCode, record_error

    error = BengalAssetError(
        f"Failed to download font '{family}'",
        code=ErrorCode.X008,
        suggestion=f"Check network connectivity and that '{family}' is a valid Google Font",
        original_error=e,
    )
    record_error(error, file_path=None)

    logger.error(
        "font_download_failed",
        family=family,
        error=str(e),
        error_type=type(e).__name__,
        code="X008",
    )
    return []
```

#### 3.2 `download_ttf_font` exception handler

**File**: `bengal/fonts/downloader.py:318-322`

```python
# Current
except Exception as e:
    logger.error(
        "ttf_font_download_failed", family=family, error=str(e), error_type=type(e).__name__
    )
    return []

# After
except Exception as e:
    from bengal.errors import BengalAssetError, ErrorCode, record_error

    error = BengalAssetError(
        f"Failed to download TTF font '{family}'",
        code=ErrorCode.X008,
        suggestion=f"Check network connectivity and that '{family}' is a valid Google Font",
        original_error=e,
    )
    record_error(error, file_path=None)

    logger.error(
        "ttf_font_download_failed",
        family=family,
        error=str(e),
        error_type=type(e).__name__,
        code="X008",
    )
    return []
```

#### 3.3 No fonts found warnings

**File**: `bengal/fonts/downloader.py:193-195`

```python
# Current
if not font_urls:
    logger.warning("no_fonts_found_for_family", family=family)
    return []

# After
if not font_urls:
    from bengal.errors import BengalAssetError, ErrorCode, record_error

    error = BengalAssetError(
        f"Font '{family}' not found in Google Fonts",
        code=ErrorCode.X009,
        suggestion=f"Verify '{family}' is a valid Google Font name at fonts.google.com",
    )
    record_error(error, file_path=None)

    logger.warning("no_fonts_found_for_family", family=family, code="X009")
    return []
```

### Phase 4: Update Test Mapping (5 min)

**File**: `bengal/errors/exceptions.py` (in `get_related_test_files`)

```python
test_mapping: dict[type, list[str]] = {
    # ... existing mappings ...
    BengalAssetError: [
        "tests/unit/assets/",
        "tests/unit/health/validators/test_fonts.py",  # ADD
        "tests/integration/test_assets.py",
    ],
}
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add X007-X010 error codes | 10 min | P1 |
| 2 | Update exception class to `BengalAssetError` | 30 min | P1 |
| 3 | Add `record_error()` calls | 30 min | P1 |
| 4 | Update test mapping | 5 min | P2 |

**Total**: 1.25 hours

---

## Success Criteria

### Must Have

- [ ] X007-X010 error codes defined in `codes.py`
- [ ] All raises use `BengalAssetError` instead of `BengalError`
- [ ] All raises include appropriate error code
- [ ] `record_error()` called for download failures
- [ ] `record_error()` called for font-not-found warnings
- [ ] Error logging includes code reference

### Should Have

- [ ] Test mapping updated for fonts
- [ ] All existing tests pass after changes

### Nice to Have

- [ ] Strict mode option for font downloads that raises on failure
- [ ] Distinct handling for `font_not_found` vs `font_download_failed`
- [ ] CSS generation failure recording in `FontCSSGenerator`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking callers expecting `[]` | Low | Low | Return type unchanged; error recording is additive |
| Import order issues | Low | Medium | Use deferred imports inside exception handlers |
| Test failures | Low | Low | Only 1 test file (`test_fonts.py`), validator-focused not error-focused |
| Circular imports | Low | Medium | Import `record_error` inside handlers, not at module level |

---

## Files Changed

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `bengal/errors/codes.py` | Add error codes | +5 |
| `bengal/fonts/downloader.py` | Use BengalAssetError + codes + record_error | +30 |
| `bengal/errors/exceptions.py` | Add test mapping | +1 |
| **Total** | — | ~36 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Exception class design | 3/10 | 9/10 | Uses `BengalAssetError` |
| Error code usage | 0/10 | 9/10 | Codes X007-X010 integrated |
| Error session recording | 0/10 | 9/10 | `record_error()` added |
| Build phase tracking | 3/10 | 9/10 | Inherited from `BengalAssetError` |
| Investigation helpers | 2/10 | 7/10 | Test mapping added |
| Silent failure handling | 4/10 | 7/10 | Errors recorded, still returns `[]` |
| **Overall** | **3/10** | **8/10** | — |

---

## References

- `bengal/fonts/downloader.py:176-182,228-232,318-322` — Exception raises and handlers
- `bengal/fonts/__init__.py:206,212,239` — Silent return None points
- `bengal/errors/codes.py:220-225` — Current X-series codes (X001-X006)
- `bengal/errors/exceptions.py:570-599` — `BengalAssetError` class definition
- `bengal/errors/recovery.py` — Recovery pattern examples
- `tests/unit/health/validators/test_fonts.py` — Font validator tests (6 tests)
