# RFC: Cache Package Error Handling Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/cache/`, `bengal/errors/`  
**Confidence**: 94% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Cache errors impact incremental build reliability  
**Estimated Effort**: 0.5 days (single dev)

---

## Executive Summary

The `bengal/cache/` package has **minimal error system adoption**. While `BengalCacheError` and error codes (`A001-A006`) are fully defined in the error system, they are barely used in the cache package itself.

**Current state**:
- **28 source files** in `bengal/cache/`
- **2 files** use `BengalCacheError` (via `enrich_error()`)
- **0 files** use `ErrorCode.A*` — all 6 cache error codes are unused
- **14+ silent error sites** that log but don't use structured errors
- **Test mapping exists** (`tests/unit/cache/` with 17 test files)

**Adoption Score**: 3/10

**Recommendation**: Add `ErrorCode` usage to existing `BengalCacheError` raises, and convert high-impact silent logger sites to structured error handling.

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
- **Consistent formatting** across the codebase

The cache package handles critical build infrastructure:
- **Build cache**: File fingerprints, dependency tracking, incremental builds
- **Query indexes**: O(1) template lookups for sections, authors, dates
- **Taxonomy index**: Tag-to-page mappings
- **Compression**: 92-93% cache size reduction

Without proper error handling:
- **Cache corruption is silent**: Users may not realize their cache is corrupt
- **Investigation is harder**: No error codes for searchability
- **Inconsistent UX**: Cache errors don't match other Bengal error messages
- **AI troubleshooting impaired**: No structured debug payloads

### Error Codes Available But Unused

`bengal/errors/codes.py:155-163` defines 6 cache-specific error codes:

| Code | Value | Intended Use |
|------|-------|--------------|
| `A001` | `cache_corruption` | Corrupted cache file detected |
| `A002` | `cache_version_mismatch` | Cache version incompatible |
| `A003` | `cache_read_error` | Failed to read cache file |
| `A004` | `cache_write_error` | Failed to write cache file |
| `A005` | `cache_invalidation_error` | Failed to invalidate cache entry |
| `A006` | `cache_lock_timeout` | Cache file lock timeout |

**None of these are currently used anywhere in the cache package.**

---

## Current State Evidence

### BengalCacheError Usage (Only 2 Locations)

**Location 1** — `build_cache/core.py:394-412`:

```python
except Exception as e:
    from bengal.errors import BengalCacheError, ErrorContext, enrich_error

    # Enrich error with context
    context = ErrorContext(
        file_path=cache_path,
        operation="saving build cache",
        suggestion="Check disk space and permissions. Cache will be rebuilt on next build.",
        original_error=e,
    )
    enriched = enrich_error(e, context, BengalCacheError)
    logger.error(
        "cache_save_failed",
        cache_path=str(cache_path),
        error=str(enriched),
        ...
    )
```

**Issue**: Uses `BengalCacheError` but missing `ErrorCode.A004` (cache_write_error).

**Location 2** — `page_discovery_cache.py:152-168`:

```python
except Exception as e:
    from bengal.errors import BengalCacheError, ErrorContext, enrich_error

    # Enrich error with context
    context = ErrorContext(
        file_path=self.cache_path,
        operation="loading page discovery cache",
        suggestion="Cache file may be corrupted. It will be rebuilt automatically.",
        original_error=e,
    )
    enriched = enrich_error(e, context, BengalCacheError)
    logger.warning(...)
```

**Issue**: Uses `BengalCacheError` but missing `ErrorCode.A003` (cache_read_error).

### Silent Error Sites (Logger Only, No Structured Errors)

| File | Location | Event | Should Use |
|------|----------|-------|------------|
| `taxonomy_index.py` | 144 | `taxonomy_index_version_mismatch` | `A002` |
| `taxonomy_index.py` | 169 | `taxonomy_index_load_failed` | `A003` |
| `taxonomy_index.py` | 199 | `taxonomy_index_save_failed` | `A004` |
| `query_index.py` | 342 | `index_save_failed` | `A004` |
| `query_index.py` | 361 | `index_version_mismatch` | `A002` |
| `query_index.py` | 388 | `index_load_failed` | `A003` |
| `compression.py` | 145 | `CacheVersionError` raised | `A002` |
| `compression.py` | 281 | `cache_migration_failed` | `A004` |
| `cache_store.py` | 269 | `Malformed cache file` | `A001` |
| `cache_store.py` | 275 | `Cache version mismatch` | `A002` |
| `cache_store.py` | 284 | `entries is not a list` | `A001` |
| `cache_store.py` | 293 | `Failed to deserialize entry` | `A003` |
| `build_cache/core.py` | 210 | `cache_load_failed` | `A003` |
| `build_cache/core.py` | 242 | `cache_version_mismatch` | `A002` |
| `build_cache/core.py` | 315 | `cache_load_parse_failed` | `A001` |
| `build_cache/core.py` | 347 | `cache_compressed_load_failed` | `A003` |
| `build_cache/file_tracking.py` | 68 | `file_hash_failed` | — (graceful) |
| `build_cache/file_tracking.py` | 197 | `file_update_failed` | — (graceful) |
| `utils.py` | 77 | `cache_clear_failed` | `A005` |
| `utils.py` | 88 | `cache_clear_failed` | `A005` |
| `utils.py` | 127 | `template_cache_clear_failed` | `A005` |
| `utils.py` | 161 | `output_clear_failed` | `A005` |
| `paths.py` | 289 | Silent exception catch | — |
| `paths.py` | 308 | Silent exception catch | — |
| `page_discovery_cache.py` | 190 | `page_discovery_cache_save_failed` | `A004` |

### Comparison with Other Domains

| Domain | Exception Class | Uses ErrorCode | Uses ErrorContext | Auto Build Phase |
|--------|-----------------|----------------|-------------------|------------------|
| Config | `BengalConfigError` | ✅ C001-C008 | ✅ | ✅ INITIALIZATION |
| Content | `BengalContentError` | ✅ N001-N010 | ✅ | ✅ PARSING |
| Rendering | `BengalRenderingError` | ✅ R001-R010 | ✅ | ✅ RENDERING |
| Assets | `BengalAssetError` | ✅ X003 (partial) | ✅ | ✅ ASSET_PROCESSING |
| Analysis | `BengalGraphError` | ✅ G001-G002 | ⚠️ Partial | ✅ ANALYSIS |
| **Cache** | `BengalCacheError` | ❌ None used | ✅ (2 sites) | ✅ CACHE |

---

## Gap Analysis

### 1. No ErrorCode Usage

**Current**: All 6 cache error codes (A001-A006) defined but never used  
**Expected**: Error codes passed to `BengalCacheError` raises

**Evidence**: `grep -rn 'ErrorCode\.A0' bengal/cache/` returns zero matches.

### 2. Existing BengalCacheError Raises Missing Codes

**Location 1** — `build_cache/core.py:394`:
- **Has**: `BengalCacheError` + `ErrorContext`
- **Missing**: `code=ErrorCode.A004` (cache_write_error)

**Location 2** — `page_discovery_cache.py:152`:
- **Has**: `BengalCacheError` + `ErrorContext`
- **Missing**: `code=ErrorCode.A003` (cache_read_error)

### 3. High-Impact Silent Error Sites

These sites log errors but don't use structured errors. Priority order:

| Priority | File | Event | Why Important |
|----------|------|-------|---------------|
| P1 | `cache_store.py:269,284` | Cache corruption | Data loss risk |
| P1 | `compression.py:145` | Version mismatch | Already raises, just wrong type |
| P2 | `taxonomy_index.py:199` | Save failed | Loss of incremental build data |
| P2 | `query_index.py:342` | Index save failed | Loss of query index data |
| P3 | `utils.py:77,88,127,161` | Clear failed | Less critical, manual operation |

### 4. CacheVersionError Not Integrated

`bengal/cache/version.py` defines `CacheVersionError` but it's not integrated with the error system:

```python
# compression.py:145
raise CacheVersionError(f"Incompatible cache version or magic header: {path}")
```

Should use `BengalCacheError` with `ErrorCode.A002`.

---

## Proposed Changes

### Phase 1: Add ErrorCode to Existing BengalCacheError Sites (15 min)

#### 1.1 Update `build_cache/core.py:394`

**Before**:
```python
from bengal.errors import BengalCacheError, ErrorContext, enrich_error

context = ErrorContext(
    file_path=cache_path,
    operation="saving build cache",
    suggestion="Check disk space and permissions...",
    original_error=e,
)
enriched = enrich_error(e, context, BengalCacheError)
```

**After**:
```python
from bengal.errors import BengalCacheError, ErrorCode, ErrorContext, enrich_error

context = ErrorContext(
    file_path=cache_path,
    operation="saving build cache",
    suggestion="Check disk space and permissions...",
    original_error=e,
    error_code=ErrorCode.A004,  # ADD: cache_write_error
)
enriched = enrich_error(e, context, BengalCacheError)
```

#### 1.2 Update `page_discovery_cache.py:152`

**Before**:
```python
context = ErrorContext(
    file_path=self.cache_path,
    operation="loading page discovery cache",
    suggestion="Cache file may be corrupted...",
    original_error=e,
)
```

**After**:
```python
context = ErrorContext(
    file_path=self.cache_path,
    operation="loading page discovery cache",
    suggestion="Cache file may be corrupted...",
    original_error=e,
    error_code=ErrorCode.A003,  # ADD: cache_read_error
)
```

### Phase 2: Add Structured Errors to High-Impact Sites (45 min)

#### 2.1 Update `cache_store.py` (Cache Corruption)

**File**: `bengal/cache/cache_store.py:267-285`

**Before**:
```python
if not isinstance(data, dict):
    logger.error(f"Malformed cache file {self.cache_path}: expected dict...")
    return []
```

**After**:
```python
from bengal.errors import ErrorCode

if not isinstance(data, dict):
    logger.error(
        "cache_malformed",
        cache_path=str(self.cache_path),
        expected="dict",
        got=type(data).__name__,
        error_code=ErrorCode.A001.value,
    )
    return []
```

#### 2.2 Update `compression.py:145` (Version Mismatch)

**Before**:
```python
raise CacheVersionError(f"Incompatible cache version or magic header: {path}")
```

**After**:
```python
from bengal.errors import BengalCacheError, ErrorCode

raise BengalCacheError(
    f"Incompatible cache version or magic header: {path}",
    code=ErrorCode.A002,
    file_path=path,
    suggestion="Delete .bengal/ directory to rebuild cache with current version.",
)
```

#### 2.3 Update `taxonomy_index.py:199` (Save Failed)

**Before**:
```python
except Exception as e:
    logger.error(
        "taxonomy_index_save_failed",
        error=str(e),
        path=str(self.cache_path),
    )
```

**After**:
```python
from bengal.errors import ErrorCode

except Exception as e:
    logger.error(
        "taxonomy_index_save_failed",
        error=str(e),
        path=str(self.cache_path),
        error_code=ErrorCode.A004.value,
    )
```

### Phase 3: Add Error Codes to Logger Calls (30 min)

Add `error_code` field to structured logs for searchability:

| File | Line | Add |
|------|------|-----|
| `taxonomy_index.py` | 144 | `error_code=ErrorCode.A002.value` |
| `taxonomy_index.py` | 169 | `error_code=ErrorCode.A003.value` |
| `query_index.py` | 342 | `error_code=ErrorCode.A004.value` |
| `query_index.py` | 361 | `error_code=ErrorCode.A002.value` |
| `query_index.py` | 388 | `error_code=ErrorCode.A003.value` |
| `build_cache/core.py` | 210 | `error_code=ErrorCode.A003.value` |
| `build_cache/core.py` | 242 | `error_code=ErrorCode.A002.value` |
| `build_cache/core.py` | 315 | `error_code=ErrorCode.A001.value` |
| `build_cache/core.py` | 347 | `error_code=ErrorCode.A003.value` |
| `utils.py` | 77,88,127,161 | `error_code=ErrorCode.A005.value` |

### Phase 4: Optional — Replace CacheVersionError (15 min)

`CacheVersionError` in `version.py` could be replaced with `BengalCacheError` for consistency, or kept as a specialized subclass. Recommendation: Keep for now, but wrap in `BengalCacheError` at catch sites.

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add `ErrorCode` to existing `BengalCacheError` sites (2 files) | 15 min | P1 |
| 2 | Add structured errors to high-impact sites (3 files) | 45 min | P1 |
| 3 | Add `error_code` to logger calls (5 files) | 30 min | P2 |
| 4 | Wrap `CacheVersionError` in catch sites | 15 min | P3 |

**Total**: 1.5-2 hours

---

## Success Criteria

### Must Have

- [ ] `ErrorCode.A004` used in `build_cache/core.py:394`
- [ ] `ErrorCode.A003` used in `page_discovery_cache.py:152`
- [ ] `compression.py:145` uses `BengalCacheError` with `A002`
- [ ] All 6 cache error codes (A001-A006) are used somewhere

### Should Have

- [ ] All logger.error/warning calls in cache package include `error_code`
- [ ] `cache_store.py` corruption detection uses `A001`
- [ ] Version mismatch sites use `A002`

### Nice to Have

- [ ] Integration test for cache error handling
- [ ] `CacheVersionError` integrated as subclass of `BengalCacheError`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking exception handlers | Low | Low | `BengalCacheError` extends `BengalError` — no breaking change |
| Test failures | Low | Low | Run `pytest tests/unit/cache/` after changes |
| Import cycles | Very Low | Medium | `ErrorCode` is in `codes.py`, no cycle risk |
| Logging format changes | Low | Low | `error_code` is additive, not breaking |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/cache/build_cache/core.py` | Add ErrorCode import + usage | +5 |
| `bengal/cache/page_discovery_cache.py` | Add ErrorCode to context | +3 |
| `bengal/cache/compression.py` | Replace CacheVersionError raise | +8 |
| `bengal/cache/cache_store.py` | Add error_code to logger calls | +6 |
| `bengal/cache/taxonomy_index.py` | Add error_code to logger calls | +4 |
| `bengal/cache/query_index.py` | Add error_code to logger calls | +4 |
| `bengal/cache/utils.py` | Add error_code to logger calls | +5 |
| **Total** | — | ~35 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 0/10 | 9/10 | All A001-A006 codes used |
| Exception class usage | 4/10 | 8/10 | More sites use BengalCacheError |
| Build phase tracking | 10/10 | 10/10 | Already auto-set via class |
| Documentation accuracy | 8/10 | 9/10 | Docstrings match actual |
| Error propagation | 3/10 | 7/10 | Key sites have structured errors |
| Test mapping | 10/10 | 10/10 | Already maps to 17 test files |
| **Overall** | **3/10** | **8.5/10** | — |

---

## References

- `bengal/errors/codes.py:155-163` — A-series cache error codes
- `bengal/errors/exceptions.py:505-534` — `BengalCacheError` class
- `bengal/errors/context.py:95-129` — `BuildPhase.CACHE` enum
- `bengal/cache/build_cache/core.py:394` — Current BengalCacheError usage
- `bengal/cache/page_discovery_cache.py:152` — Current BengalCacheError usage
- `bengal/cache/compression.py:145` — CacheVersionError raise
- `tests/unit/cache/` — 17 test files for validation
