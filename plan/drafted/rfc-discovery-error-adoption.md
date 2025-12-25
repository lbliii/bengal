# RFC: Discovery Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/discovery/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Discovery errors are user-facing; consistency improves debugging  
**Estimated Effort**: 1.25 hours (single dev)

---

## Executive Summary

The `bengal/discovery/` package has **mixed error handling adoption**. Two modules (`content_parser.py`, `page_factory.py`) demonstrate strong integration with error codes, `enrich_error()`, and session recording. Five modules have **minimal to no error system usage**, relying on bare logger calls and silent failures.

**Current state**:
- **5 error code usages**: Across 3 files (`content_parser.py`, `git_version_adapter.py`, `page_factory.py`)
- **1 `record_error()` call**: Only in `content_parser.py:272`
- **8 logger.warning calls**: Without error codes or session recording
- **3 silent failure points**: Return empty values without tracking errors
- **4 files with no error imports**: `directory_walker.py`, `asset_discovery.py`, `section_builder.py`, `version_resolver.py`

**Adoption Score**: 5.5/10

**Recommendation**: Add discovery-specific error codes (D012-D014), integrate `record_error()` at warning sites, eliminate silent failures, and standardize logger calls with error codes.

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

The discovery package has inconsistent adoption:
- Some modules (`content_parser.py`, `page_factory.py`) are well-integrated
- Others (`directory_walker.py`, `asset_discovery.py`) use bare logger calls
- Silent failures hide errors from build summaries
- Missing error codes prevent documentation linking

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No error codes in warnings | Can't search for error docs | No quick code lookup |
| No session recording | Errors missing from build summary | Missing error patterns |
| Silent failures | Build appears successful despite issues | Hard-to-debug missing content |
| Inconsistent patterns | Confusing error experience | Maintenance burden |

---

## Current State Evidence

### Error Code Usage

**Total**: 5 usages of `ErrorCode` across 3 files.

| File | Location | Code | Usage |
|------|----------|------|-------|
| `content_parser.py` | Line 268 | `N011` | Collection validation failure |
| `git_version_adapter.py` | Line 284 | `D007` | Git worktree creation failure |
| `page_factory.py` | Line 106 | `N004` | Missing output_path |
| `page_factory.py` | Line 118 | `D002` | Relative output_path |
| `page_factory.py` | Line 148 | `N010` | Invalid slug URL |

### `record_error()` Usage

**Total**: 1 call in entire discovery package.

| File | Location | Context |
|------|----------|---------|
| `content_parser.py` | Line 272 | Records `ContentValidationError` to session |

### Error System Imports by File

| File | Imports | Score |
|------|---------|-------|
| `content_parser.py` | `BengalDiscoveryError`, `ErrorContext`, `enrich_error`, `ErrorCode`, `record_error` | ✅ Strong |
| `page_factory.py` | `BengalContentError`, `ErrorCode`, `ErrorContext`, `enrich_error` | ✅ Strong |
| `git_version_adapter.py` | `BengalDiscoveryError`, `ErrorCode` | 🟡 Partial |
| `content_discovery.py` | `with_error_recovery` | 🟡 Partial |
| `directory_walker.py` | None | 🔴 None |
| `asset_discovery.py` | None | 🔴 None |
| `section_builder.py` | None | 🔴 None |
| `version_resolver.py` | None | 🔴 None |

### Logger Warnings Without Error Codes

**8 locations** use `logger.warning()` without error codes or session recording:

| File | Location | Event | Problem |
|------|----------|-------|---------|
| `directory_walker.py` | Line 131-135 | `symlink_loop_detected` | No error code, no recording |
| `directory_walker.py` | Line 141-148 | `directory_stat_failed` | No error code, no recording |
| `directory_walker.py` | Line 163-169 | `directory_permission_denied` | No error code, silent failure |
| `asset_discovery.py` | Line 131 | `asset_missing_path` | No error code, no recording |
| `content_discovery.py` | Line 190-193 | `content_dir_missing` | No error code, no recording |
| `git_version_adapter.py` | Line 369 | `git_branches_failed` | No error code, no recording |
| `git_version_adapter.py` | Line 396 | `git_tags_failed` | No error code, no recording |
| `content_discovery.py` | Line 428-434 | `page_creation_failed` | No error code, no recording |

**Example** (`directory_walker.py:141-148`):

```python
except (OSError, PermissionError) as e:
    logger.warning(
        "directory_stat_failed",
        path=str(directory),
        error=str(e),
        error_type=type(e).__name__,
        action="skipping",
    )
    return True  # Silently continues
```

### Silent Failures

**3 locations** return empty values on errors without any tracking:

| File | Location | Trigger | Return Value | Problem |
|------|----------|---------|--------------|---------|
| `directory_walker.py` | Line 169 | `PermissionError` | `[]` | Permission errors invisible |
| `git_version_adapter.py` | Line 412-413 | Git command fails | `""` | Missing commit SHA |
| `git_version_adapter.py` | Line 368-369, 395-396 | Git ref list fails | Continues with partial data | Missing versions |

### Well-Integrated Patterns (Reference)

**`content_parser.py`** demonstrates the target pattern:

```python
# Line 123-131: Error enrichment
context = ErrorContext(
    file_path=file_path,
    operation="parsing frontmatter",
    suggestion="Fix frontmatter YAML syntax",
    original_error=error,
)
enrich_error(error, context, BengalDiscoveryError)

# Line 258-272: Error recording with code
from bengal.errors import ErrorCode, record_error

error = ContentValidationError(
    message=f"Validation failed for {file_path}",
    path=file_path,
    errors=result.errors,
    collection_name=collection_name,
    code=ErrorCode.N011,
)

# Record for session aggregation
record_error(error, file_path=str(file_path))
```

---

## Gap Analysis

### 1. Missing Discovery Error Codes

**Current**: D-series codes end at D011
**Expected**: Additional codes for discovery-specific errors

| Proposed Code | Value | Use Case |
|---------------|-------|----------|
| D012 | `symlink_loop_detected` | Circular symlink in content directory |
| D013 | `asset_stat_failed` | Asset file stat failed |
| D014 | `git_ref_fetch_failed` | Git branch/tag list failed |

### 2. Logger Warnings Lack Error Codes

**Current**: 8 `logger.warning()` calls without `code=` parameter
**Expected**: All warnings include error code for searchability

**Example fix**:

```python
# Before
logger.warning(
    "symlink_loop_detected",
    path=str(directory),
    action="skipping_to_prevent_infinite_recursion",
)

# After
logger.warning(
    "symlink_loop_detected",
    path=str(directory),
    action="skipping_to_prevent_infinite_recursion",
    code="D012",
)
```

### 3. No Error Session Recording in 7/8 Modules

**Current**: Only `content_parser.py` calls `record_error()`
**Expected**: All warning-level errors recorded for session aggregation

**Impact**: Build summaries don't include discovery errors except collection validation.

### 4. Silent Failures Hide Errors

**Current**: 3 locations return empty values without logging or recording
**Expected**: Errors recorded before returning fallback values

**Example** (`directory_walker.py:163-169`):

```python
# Before
except PermissionError as e:
    logger.warning(
        "directory_permission_denied",
        path=str(directory),
        error=str(e),
        action="skipping",
    )
    return []

# After
except PermissionError as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Permission denied reading directory: {directory}",
        code=ErrorCode.D007,
        file_path=directory,
        suggestion="Check directory permissions or exclude from discovery",
        original_error=e,
    )
    record_error(error, file_path=str(directory))
    logger.warning(
        "directory_permission_denied",
        path=str(directory),
        error=str(e),
        action="skipping",
        code="D007",
    )
    return []
```

### 5. Files With No Error System Integration

**4 files** have no error system imports:
- `directory_walker.py` — Critical for symlink and permission errors
- `asset_discovery.py` — Asset stat failures
- `section_builder.py` — Minimal error cases (acceptable)
- `version_resolver.py` — Minimal error cases (acceptable)

---

## Proposed Changes

### Phase 1: Add Error Codes (15 min)

**File**: `bengal/errors/codes.py`

Add after D011:

```python
# ============================================================
# Discovery errors (D001-D020) - continued
# ============================================================
D012 = "symlink_loop_detected"      # Circular symlink in content
D013 = "asset_stat_failed"          # Asset file stat failed
D014 = "git_ref_fetch_failed"       # Git branch/tag list failed
```

### Phase 2: Update `directory_walker.py` (20 min)

**File**: `bengal/discovery/directory_walker.py`

#### 2.1 `check_symlink_loop()` — Add error recording

```python
# Line 130-148: Replace warning with error recording

if inode_key in self.visited_inodes:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Symlink loop detected at {directory}",
        code=ErrorCode.D012,
        file_path=directory,
        suggestion="Remove circular symlink or exclude directory from discovery",
    )
    record_error(error, file_path=str(directory))
    logger.warning(
        "symlink_loop_detected",
        path=str(directory),
        action="skipping_to_prevent_infinite_recursion",
        code="D012",
    )
    return True
```

#### 2.2 `list_directory()` — Add error recording

```python
# Line 162-169: Replace warning with error recording

except PermissionError as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Permission denied reading directory: {directory}",
        code=ErrorCode.D007,
        file_path=directory,
        suggestion="Check directory permissions or exclude from discovery",
        original_error=e,
    )
    record_error(error, file_path=str(directory))
    logger.warning(
        "directory_permission_denied",
        path=str(directory),
        error=str(e),
        action="skipping",
        code="D007",
    )
    return []
```

### Phase 3: Update `content_discovery.py` (15 min)

**File**: `bengal/discovery/content_discovery.py`

#### 3.1 `_discover_full()` — Record content_dir_missing

```python
# Line 189-193: Add error recording

if not self.content_dir.exists():
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Content directory not found: {self.content_dir}",
        code=ErrorCode.D001,
        file_path=self.content_dir,
        suggestion="Create content directory or check bengal.yaml config",
    )
    record_error(error, file_path=str(self.content_dir))
    logger.warning(
        "content_dir_missing",
        content_dir=str(self.content_dir),
        action="returning_empty",
        code="D001",
    )
    return self.sections, self.pages
```

#### 3.2 `_create_page()` — Record page_creation_failed

```python
# Line 427-434: Add error recording

except Exception as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Failed to create page from {file_path}",
        code=ErrorCode.D002,
        file_path=file_path,
        original_error=e,
        suggestion="Check file encoding and frontmatter syntax",
    )
    record_error(error, file_path=str(file_path))
    logger.error(
        "page_creation_failed",
        file_path=str(file_path),
        error=str(e),
        error_type=type(e).__name__,
        code="D002",
    )
    raise
```

### Phase 4: Update `git_version_adapter.py` (15 min)

**File**: `bengal/discovery/git_version_adapter.py`

#### 4.1 `_get_refs()` — Record git fetch failures

```python
# Line 368-369: Add error recording for branches

except subprocess.CalledProcessError as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Failed to list git branches: {e.stderr}",
        code=ErrorCode.D014,
        file_path=self.repo_path,
        suggestion="Check git repository state and permissions",
        original_error=e,
    )
    record_error(error, file_path=str(self.repo_path))
    logger.warning("git_branches_failed", error=e.stderr, code="D014")

# Line 395-396: Same for tags
except subprocess.CalledProcessError as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Failed to list git tags: {e.stderr}",
        code=ErrorCode.D014,
        file_path=self.repo_path,
        suggestion="Check git repository state and permissions",
        original_error=e,
    )
    record_error(error, file_path=str(self.repo_path))
    logger.warning("git_tags_failed", error=e.stderr, code="D014")
```

### Phase 5: Update `asset_discovery.py` (10 min)

**File**: `bengal/discovery/asset_discovery.py`

```python
# Line 129-131: Add error recording

except (AttributeError, FileNotFoundError) as e:
    from bengal.errors import record_error, BengalDiscoveryError, ErrorCode

    error = BengalDiscoveryError(
        f"Asset path missing or invalid: {asset}",
        code=ErrorCode.D013,
        suggestion="Check asset source path configuration",
        original_error=e if isinstance(e, Exception) else None,
    )
    record_error(error)
    logger.warning("asset_missing_path", asset=str(asset), code="D013")
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add D012-D014 error codes | 15 min | P1 |
| 2 | Update `directory_walker.py` (2 locations) | 20 min | P1 |
| 3 | Update `content_discovery.py` (2 locations) | 15 min | P1 |
| 4 | Update `git_version_adapter.py` (2 locations) | 15 min | P2 |
| 5 | Update `asset_discovery.py` (1 location) | 10 min | P2 |

**Total**: 1.25 hours

---

## Success Criteria

### Must Have

- [ ] D012-D014 error codes defined in `codes.py`
- [ ] `record_error()` called in `directory_walker.py` (2 locations)
- [ ] `record_error()` called in `content_discovery.py` (2 locations)
- [ ] All `logger.warning()` calls include `code=` parameter

### Should Have

- [ ] `git_version_adapter.py` records git failures
- [ ] `asset_discovery.py` records asset errors
- [ ] All existing tests pass after changes

### Nice to Have

- [ ] Investigation helpers for discovery errors
- [ ] Test mapping updated in `exceptions.py`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing error handlers | Low | Low | All changes are additive |
| Test failures | Low | Low | Run `pytest tests/unit/discovery/` after changes |
| Circular imports | Low | Medium | Use `from bengal.errors import ...` inside functions |
| Performance overhead | Very Low | Low | `record_error()` is lightweight dict append |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/errors/codes.py` | Add error codes | +3 |
| `bengal/discovery/directory_walker.py` | Add error recording | +25 |
| `bengal/discovery/content_discovery.py` | Add error recording | +20 |
| `bengal/discovery/git_version_adapter.py` | Add error recording | +20 |
| `bengal/discovery/asset_discovery.py` | Add error recording | +10 |
| **Total** | — | ~78 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 5/10 | 9/10 | Codes in all warning sites |
| `record_error()` usage | 2/10 | 9/10 | All warnings recorded |
| `enrich_error()` usage | 6/10 | 6/10 | Already adequate |
| Silent failure handling | 4/10 | 8/10 | Errors recorded before fallback |
| Logger consistency | 3/10 | 9/10 | All warnings include `code=` |
| **Overall** | **5.5/10** | **8.5/10** | — |

---

## References

- `bengal/discovery/directory_walker.py:131-169` — 3 warning sites without codes
- `bengal/discovery/content_discovery.py:190-193, 428-434` — 2 warning sites
- `bengal/discovery/git_version_adapter.py:368-369, 395-396` — 2 warning sites
- `bengal/discovery/asset_discovery.py:129-131` — 1 warning site
- `bengal/discovery/content_parser.py:258-272` — Reference implementation
- `bengal/errors/codes.py:160-172` — Current D-series codes (D001-D011)
- `bengal/errors/session.py` — `record_error()` implementation
- `tests/unit/discovery/` — Test files for validation

---

## Verification Notes

**Verified**: 2025-12-24

All claims in this RFC have been verified against the source code:

- ✅ 5 `ErrorCode` usages confirmed via `grep "ErrorCode\."` in discovery/
- ✅ 1 `record_error()` call confirmed at `content_parser.py:272`
- ✅ 8 `logger.warning()` calls without codes confirmed
- ✅ 3 silent failure points verified
- ✅ 4 files with no error imports confirmed

**Ready for implementation.**
