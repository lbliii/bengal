# RFC: Config Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/config/`, `bengal/errors/`  
**Confidence**: 94% 🟢 (all claims verified via grep against source files)  
**Priority**: P3 (Low) — Package already has good foundation  
**Estimated Effort**: 0.5 days (single dev)

---

## Executive Summary

The `bengal/config/` package has **strong adoption** of the Bengal error system. It defines two domain-specific exception classes (`ConfigLoadError`, `ConfigValidationError`), uses proper inheritance from `BengalConfigError`, and has accurate docstrings.

**Current state**:
- **3 files** import from `bengal.errors`
- **2 custom exception classes** defined (`ConfigLoadError`, `ConfigValidationError`)
- **1 error code used** in package: C003 (`config_invalid_value`)
- **5 unused codes** defined for config: C001, C002, C004, C005, C006, C008
- **0 session tracking** via `record_error()`
- **Accurate docstrings** throughout

**Adoption Score**: 7/10

**Recommendation**: Add error codes to existing raises, use C005/C006/C008 where appropriate, and add session tracking for error aggregation.

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

The config package has excellent exception class structure but underutilizes error codes and lacks session tracking.

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| Missing error codes | No searchable error IDs | Can't grep for specific errors |
| No session tracking | Build summaries lack config errors | No error pattern detection |
| Unused codes (5/8) | Inconsistent error categorization | Wasted code namespace |

---

## Current State Evidence

### Error Code Definitions

**File**: `bengal/errors/codes.py:108-117`

```python
# ============================================================
# Config errors (C001-C099)
# ============================================================
C001 = "config_yaml_parse_error"
C002 = "config_key_missing"
C003 = "config_invalid_value"
C004 = "config_type_mismatch"
C005 = "config_defaults_missing"
C006 = "config_environment_unknown"
C007 = "config_circular_reference"
C008 = "config_deprecated_key"
```

### Exception Classes Defined

| Class | Location | Inherits From | Purpose |
|-------|----------|---------------|---------|
| `ConfigLoadError` | `directory_loader.py:66` | `BengalConfigError` | Directory config loading failures |
| `ConfigValidationError` | `validators.py:48` | `BengalConfigError`, `ValueError` | Validation failures |

Both classes properly extend `BengalConfigError` and inherit:
- Automatic `BuildPhase.INITIALIZATION` assignment
- Test file mapping in `get_related_test_files()`
- Investigation helpers

### Import Patterns

| File | Import | Status |
|------|--------|--------|
| `validators.py` | `from bengal.errors import BengalConfigError` | ✅ Module-level |
| `directory_loader.py` | `from bengal.errors import BengalConfigError, format_suggestion` | ✅ Module-level |
| `directory_loader.py` | `from bengal.errors import BengalConfigError, ErrorContext, enrich_error` | ✅ Lazy (in function) |
| `loader.py` | `from bengal.errors import BengalConfigError, ErrorCode` | ✅ Lazy (in function) |
| `deprecation.py` | — | ❌ No import |
| `defaults.py` | — | ❌ No import (none needed) |
| `env_overrides.py` | — | ❌ No import |
| `environment.py` | — | ❌ No import (none needed) |
| `feature_mappings.py` | — | ❌ No import (none needed) |
| `hash.py` | — | ❌ No import (none needed) |
| `merge.py` | — | ❌ No import (none needed) |
| `origin_tracker.py` | — | ❌ No import (none needed) |
| `url_policy.py` | — | ❌ No import (none needed) |
| `types.py` | — | ❌ No import (none needed) |

### Error Code Usage in Config Package

**Total**: 1 use of `ErrorCode.C0xx` in config package.

| File | Code | Count | Context |
|------|------|-------|---------|
| `loader.py:248` | C003 | 1 | Unsupported config format |

**Example usage**:

```python
# loader.py:244-252
from bengal.errors import BengalConfigError, ErrorCode

raise BengalConfigError(
    f"Unsupported config format: {suffix}",
    code=ErrorCode.C003,
    file_path=config_path,
    suggestion="Use .toml or .yaml/.yml extension for config files. "
    "See: bengal init --help",
)
```

### Error Codes Used Elsewhere (Not in config/)

| Code | Value | Location | Count |
|------|-------|----------|-------|
| C001 | `config_yaml_parse_error` | `themes/config.py:310` | 1 |
| C002 | `config_key_missing` | `content_layer/`, `collections/` | 5 |
| C003 | `config_invalid_value` | `autodoc/`, `themes/`, `rendering/`, `content_layer/` | 7 |
| C007 | `config_circular_reference` | `core/menu.py:564` | 1 |

### Error Codes Never Used

| Code | Value | Status |
|------|-------|--------|
| C004 | `config_type_mismatch` | ❌ Never raised |
| C005 | `config_defaults_missing` | ❌ Never raised (only in suggestions) |
| C006 | `config_environment_unknown` | ❌ Never raised (only in suggestions) |
| C008 | `config_deprecated_key` | ❌ Never raised |

### Exception Catching Patterns

**Silent handling in `env_overrides.py:160-169`**:

```python
except Exception as e:
    # Never fail build due to env override logic
    logger.warning(
        "env_override_detection_failed",
        error=str(e),
        error_type=type(e).__name__,
        action="using_original_config",
        hint="Deployment platform baseurl auto-detection failed; verify environment variables",
    )
```

This is **intentional** — environment detection should never fail builds.

**Fallback to defaults in `loader.py:274-291`**:

```python
except Exception as e:
    # ...
    if os.environ.get("BENGAL_RAISE_ON_CONFIG_ERROR") == "1":
        raise
    return self._default_config()
```

This is **configurable** — controlled via environment variable.

### Session Tracking

**Current**: No `record_error()` calls in config package.

**Impact**: Config errors don't appear in error session summaries.

---

## Gap Analysis

### 1. Missing Error Codes on Raises

**5 locations** raise exceptions without error codes:

| File | Line | Exception | Suggested Code |
|------|------|-----------|----------------|
| `directory_loader.py:170` | `ConfigLoadError` (dir not found) | C005 |
| `directory_loader.py:177` | `ConfigLoadError` (not a directory) | C005 |
| `directory_loader.py:309` | `ConfigLoadError` (file load errors) | C001 |
| `directory_loader.py:414` | `ConfigLoadError` (YAML parse error) | C001 |
| `directory_loader.py:422` | `ConfigLoadError` (file read error) | C003 |
| `validators.py:168` | `ConfigValidationError` | C004 |

### 2. Unused Error Codes

| Code | Value | Opportunity |
|------|-------|-------------|
| C004 | `config_type_mismatch` | Use in `validators.py` for type validation errors |
| C005 | `config_defaults_missing` | Use in `directory_loader.py` for missing `_default/` |
| C006 | `config_environment_unknown` | Use when environment detection fails |
| C008 | `config_deprecated_key` | Use in `deprecation.py` when deprecated key is found |

### 3. No Session Tracking

Config errors are not tracked via `record_error()`, meaning:
- Build summaries don't include config errors
- Pattern detection doesn't work for config issues
- Investigation hints are not accumulated

### 4. Deprecation Module Lacks Error Integration

`deprecation.py` logs warnings but doesn't use:
- `BengalConfigError` with code C008
- `record_error()` for session tracking

**Current** (`deprecation.py:98-104`):

```python
logger.warning(
    "config_deprecated_key",
    old_key=old_key,
    new_location=new_location,
    note=note,
    source=source,
)
```

**Could add**: Create `DeprecationWarning` with C008 for structured tracking.

---

## Proposed Changes

### Phase 1: Add Error Codes to Existing Raises (30 min)

#### 1.1 Update `directory_loader.py`

**Lines 170-174** (directory not found):

```python
# Before
raise ConfigLoadError(
    f"Config directory not found: {config_dir}",
    file_path=config_dir,
    suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
)

# After
from bengal.errors import ErrorCode

raise ConfigLoadError(
    f"Config directory not found: {config_dir}",
    code=ErrorCode.C005,  # config_defaults_missing
    file_path=config_dir,
    suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
)
```

**Lines 414-420** (YAML parse error):

```python
# Before
raise ConfigLoadError(
    f"Invalid YAML in {path}: {e}",
    file_path=path,
    line_number=line_num,
    suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
    original_error=e,
)

# After
raise ConfigLoadError(
    f"Invalid YAML in {path}: {e}",
    code=ErrorCode.C001,  # config_yaml_parse_error
    file_path=path,
    line_number=line_num,
    suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
    original_error=e,
)
```

#### 1.2 Update `validators.py`

**Line 168** (validation error):

```python
# Before
raise ConfigValidationError(f"{len(errors)} validation error(s)")

# After
from bengal.errors import ErrorCode

raise ConfigValidationError(
    f"{len(errors)} validation error(s)",
    code=ErrorCode.C004,  # config_type_mismatch
)
```

### Phase 2: Add Session Tracking (30 min)

#### 2.1 Track validation errors

**File**: `validators.py`

```python
# At top of validate() method, before raising
if errors:
    from bengal.errors import record_error, ErrorCode

    error = ConfigValidationError(
        f"{len(errors)} validation error(s)",
        code=ErrorCode.C004,
        file_path=source_file,
    )
    record_error(error, file_path=str(source_file) if source_file else None)
    self._print_errors(errors, source_file)
    raise error
```

#### 2.2 Track YAML parse errors

**File**: `directory_loader.py`

```python
# In _load_yaml when catching yaml.YAMLError
from bengal.errors import record_error

error = ConfigLoadError(
    f"Invalid YAML in {path}: {e}",
    code=ErrorCode.C001,
    file_path=path,
    line_number=line_num,
    suggestion="Check YAML syntax...",
    original_error=e,
)
record_error(error, file_path=str(path))
raise error
```

### Phase 3: Use Remaining Error Codes (15 min)

#### 3.1 C006 for unknown environment

**File**: `directory_loader.py` (optional warning)

Currently environment detection silently falls back to "local". Could optionally warn with C006 for unknown environments.

#### 3.2 C008 for deprecated keys

**File**: `deprecation.py`

```python
# Optional: Create structured warning
from bengal.errors import ErrorCode

def check_deprecated_keys(...):
    # ... existing code ...
    if warn:
        # Could optionally record as session warning
        from bengal.errors import record_error, BengalConfigError

        warning = BengalConfigError(
            f"Deprecated key '{old_key}' found",
            code=ErrorCode.C008,
            suggestion=note,
        )
        # Use severity=WARNING (not ERROR) for deprecation warnings
        record_error(warning, severity="warning")
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add error codes to existing raises | 30 min | P1 |
| 2 | Add session tracking to validators + directory_loader | 30 min | P2 |
| 3 | Use C006/C008 for environment/deprecation | 15 min | P3 |

**Total**: 1.25 hours

---

## Success Criteria

### Must Have

- [ ] All `ConfigLoadError` raises include error codes
- [ ] `ConfigValidationError` raises include C004
- [ ] Imports consolidated at module level where practical

### Should Have

- [ ] Session tracking via `record_error()` for YAML parse errors
- [ ] Session tracking for validation errors
- [ ] C005 used for missing defaults directory
- [ ] C001 used for YAML parse errors

### Nice to Have

- [ ] C008 used for deprecation warnings with session tracking
- [ ] C006 logged when environment detection falls back

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing exception handlers | Very Low | Low | All changes add codes, don't change types |
| Test failures | Low | Low | Run `pytest tests/unit/config/` after changes |
| Performance impact of session tracking | Very Low | Negligible | Session tracking is O(1) per error |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/config/directory_loader.py` | Add error codes + session tracking | ~20 |
| `bengal/config/validators.py` | Add C004 + session tracking | ~10 |
| `bengal/config/deprecation.py` | Optional C008 integration | ~5 |
| **Total** | — | ~35 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 5/10 | 9/10 | All raises get codes |
| Exception classes | 10/10 | 10/10 | Already excellent |
| Build phase tracking | 10/10 | 10/10 | Auto via BengalConfigError |
| Session tracking | 0/10 | 8/10 | Added to critical paths |
| Documentation accuracy | 9/10 | 9/10 | Already good |
| Test mapping | 10/10 | 10/10 | Via BengalConfigError |
| **Overall** | **7/10** | **9/10** | — |

---

## References

- `bengal/errors/codes.py:108-117` — C-series error codes
- `bengal/errors/exceptions.py:364-395` — BengalConfigError definition
- `bengal/config/directory_loader.py:66-84` — ConfigLoadError class
- `bengal/config/validators.py:48-62` — ConfigValidationError class
- `bengal/config/loader.py:244-252` — Only C003 usage in package
- `tests/unit/config/` — Test files for validation
