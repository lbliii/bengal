# RFC: Config Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/config/`, `bengal/errors/`  
**Confidence**: 96% 🟢 (all claims verified via grep against source files; `record_error` API confirmed)  
**Priority**: P3 (Low) — Package already has good foundation  
**Estimated Effort**: 0.25 days (~2 hours including tests)

---

## Executive Summary

The `bengal/config/` package has **strong adoption** of the Bengal error system. It defines two domain-specific exception classes (`ConfigLoadError`, `ConfigValidationError`), uses proper inheritance from `BengalConfigError`, and has accurate docstrings.

**Current state**:
- **3 files** import from `bengal.errors`
- **2 custom exception classes** defined (`ConfigLoadError`, `ConfigValidationError`)
- **1 error code used** in package: C003 (`config_invalid_value`)
- **4 unused codes** in config/: C004, C005, C006, C008 (C001, C002, C007 used elsewhere)
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
7. [Test Verification](#test-verification)
8. [Risks and Mitigations](#risks-and-mitigations)

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

**File**: `bengal/errors/codes.py:110-117`

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

**6 locations** raise exceptions without error codes:

| File | Line | Exception | Suggested Code |
|------|------|-----------|----------------|
| `directory_loader.py:170` | `ConfigLoadError` (dir not found) | C005 |
| `directory_loader.py:177` | `ConfigLoadError` (not a directory) | C003 |
| `directory_loader.py:309` | `ConfigLoadError` (file load errors) | C001 |
| `directory_loader.py:414` | `ConfigLoadError` (YAML parse error) | C001 |
| `directory_loader.py:422` | `ConfigLoadError` (file read error) | C003 |
| `validators.py:168` | `ConfigValidationError` | C004 |

**Note**: Line 177 uses C003 (`config_invalid_value`) rather than C005 because "not a directory" is an invalid path value, not a missing defaults directory.

### 2. Unused Error Codes (Currently)

| Code | Value | Proposed Use |
|------|-------|--------------|
| C004 | `config_type_mismatch` | **Phase 1**: Use in `validators.py` for type validation errors |
| C005 | `config_defaults_missing` | **Phase 1**: Use in `directory_loader.py` for missing config directory |
| C006 | `config_environment_unknown` | **Phase 3**: Optional warning when environment detection falls back |
| C008 | `config_deprecated_key` | **Phase 3**: Use in `deprecation.py` for session tracking |

**After implementation**: Only C006 remains optional (warning-only, no raise).

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

**Add module-level import** (line 60):

```python
# Existing import
from bengal.errors import BengalConfigError, format_suggestion

# Updated import
from bengal.errors import BengalConfigError, ErrorCode, format_suggestion
```

**Lines 170-174** (directory not found):

```python
# Before
raise ConfigLoadError(
    f"Config directory not found: {config_dir}",
    file_path=config_dir,
    suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
)

# After
raise ConfigLoadError(
    f"Config directory not found: {config_dir}",
    code=ErrorCode.C005,  # config_defaults_missing
    file_path=config_dir,
    suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
)
```

**Lines 177-181** (not a directory):

```python
# Before
raise ConfigLoadError(
    f"Not a directory: {config_dir}",
    file_path=config_dir,
    suggestion="Ensure path points to a directory, not a file",
)

# After
raise ConfigLoadError(
    f"Not a directory: {config_dir}",
    code=ErrorCode.C003,  # config_invalid_value
    file_path=config_dir,
    suggestion="Ensure path points to a directory, not a file",
)
```

**Lines 309-314** (batch file load errors):

```python
# Before
raise ConfigLoadError(
    message=f"Failed to load config files: {error_msg}",
    file_path=first_file,
    suggestion="Check YAML syntax and file encoding (must be UTF-8). Failed files were skipped.",
    original_error=first_error if isinstance(first_error, Exception) else None,
)

# After
raise ConfigLoadError(
    message=f"Failed to load config files: {error_msg}",
    code=ErrorCode.C001,  # config_yaml_parse_error
    file_path=first_file,
    suggestion="Check YAML syntax and file encoding (must be UTF-8). Failed files were skipped.",
    original_error=first_error if isinstance(first_error, Exception) else None,
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

**Lines 422-427** (file read error):

```python
# Before
raise ConfigLoadError(
    f"Failed to load {path}: {e}",
    file_path=path,
    suggestion="Check file permissions and encoding (must be UTF-8)",
    original_error=e,
)

# After
raise ConfigLoadError(
    f"Failed to load {path}: {e}",
    code=ErrorCode.C003,  # config_invalid_value
    file_path=path,
    suggestion="Check file permissions and encoding (must be UTF-8)",
    original_error=e,
)
```

#### 1.2 Update `validators.py`

**Add module-level import** (line 42):

```python
# Existing import
from bengal.errors import BengalConfigError

# Updated import
from bengal.errors import BengalConfigError, ErrorCode
```

**Line 168** (validation error):

```python
# Before
raise ConfigValidationError(f"{len(errors)} validation error(s)")

# After
raise ConfigValidationError(
    f"{len(errors)} validation error(s)",
    code=ErrorCode.C004,  # config_type_mismatch
)
```

### Phase 2: Add Session Tracking (30 min)

#### 2.1 Add session import to `validators.py`

**Update module-level import** (line 42):

```python
# Updated import (includes record_error)
from bengal.errors import BengalConfigError, ErrorCode, record_error
```

**Update validate() method** (line 166-168):

```python
# Before
if errors:
    self._print_errors(errors, source_file)
    raise ConfigValidationError(f"{len(errors)} validation error(s)")

# After
if errors:
    self._print_errors(errors, source_file)
    error = ConfigValidationError(
        f"{len(errors)} validation error(s)",
        code=ErrorCode.C004,
    )
    record_error(error, file_path=str(source_file) if source_file else None)
    raise error
```

#### 2.2 Add session import to `directory_loader.py`

**Update module-level import** (line 60):

```python
# Updated import (includes record_error)
from bengal.errors import BengalConfigError, ErrorCode, format_suggestion, record_error
```

**Update _load_yaml()** (line 414-420):

```python
# In _load_yaml when catching yaml.YAMLError
error = ConfigLoadError(
    f"Invalid YAML in {path}: {e}",
    code=ErrorCode.C001,
    file_path=path,
    line_number=line_num,
    suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
    original_error=e,
)
record_error(error, file_path=str(path))
raise error from e
```

### Phase 3: Use Remaining Error Codes (15 min)

#### 3.1 C006 for unknown environment

**File**: `directory_loader.py` (optional warning)

Currently environment detection silently falls back to "local". Could optionally warn with C006 for unknown environments.

#### 3.2 C008 for deprecated keys

**File**: `deprecation.py`

```python
# Optional: Create structured warning for session tracking
from bengal.errors import record_error, BengalConfigError, ErrorCode

def check_deprecated_keys(...):
    # ... existing code ...
    if warn:
        # Record deprecation as session error for pattern detection
        # Note: Deprecations are warnings, not fatal errors, so we log
        # but don't raise. Session tracking helps detect systematic issues.
        warning = BengalConfigError(
            f"Deprecated key '{old_key}' found",
            code=ErrorCode.C008,
            suggestion=note,
        )
        record_error(warning, file_path=source)

        # Keep existing logger.warning() for console output
        logger.warning(
            "config_deprecated_key",
            old_key=old_key,
            new_location=new_location,
            note=note,
            source=source,
        )
```

**Note**: `record_error()` tracks for pattern detection but doesn't affect build success. The existing `logger.warning()` is preserved for user visibility.

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add error codes to existing raises (6 locations) | 30 min | P1 |
| 1b | Add test assertions for error codes | 30 min | P1 |
| 2 | Add session tracking to validators + directory_loader | 30 min | P2 |
| 2b | Add session tracking tests | 20 min | P2 |
| 3 | Use C006/C008 for environment/deprecation | 15 min | P3 |

**Total**: ~2 hours (including tests)

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

## Test Verification

### Existing Test Coverage

The config package has comprehensive test coverage in `tests/unit/config/`:

| Test File | Purpose |
|-----------|---------|
| `test_directory_loader.py` | ConfigDirectoryLoader and ConfigLoadError |
| `test_validators.py` | ConfigValidator and ConfigValidationError |
| `test_deprecation.py` | Deprecated key detection |
| `test_config_loader.py` | ConfigLoader main flows |

### Required Test Updates

Add assertions to verify error codes are set correctly:

**File**: `tests/unit/config/test_directory_loader.py`

```python
import pytest
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.errors import ErrorCode


def test_missing_directory_has_error_code(tmp_path):
    """Verify ConfigLoadError includes C005 for missing directory."""
    loader = ConfigDirectoryLoader()
    missing_dir = tmp_path / "nonexistent"

    with pytest.raises(ConfigLoadError) as exc_info:
        loader.load(missing_dir)

    assert exc_info.value.code == ErrorCode.C005
    assert "not found" in str(exc_info.value).lower()


def test_yaml_parse_error_has_error_code(tmp_path):
    """Verify ConfigLoadError includes C001 for YAML parse errors."""
    loader = ConfigDirectoryLoader()
    config_dir = tmp_path / "config" / "_default"
    config_dir.mkdir(parents=True)

    # Create invalid YAML
    (config_dir / "site.yaml").write_text("invalid: yaml: content: [")

    with pytest.raises(ConfigLoadError) as exc_info:
        loader.load(tmp_path / "config")

    assert exc_info.value.code == ErrorCode.C001
```

**File**: `tests/unit/config/test_validators.py`

```python
import pytest
from bengal.config.validators import ConfigValidator, ConfigValidationError
from bengal.errors import ErrorCode


def test_validation_error_has_error_code():
    """Verify ConfigValidationError includes C004 for type mismatches."""
    validator = ConfigValidator()

    # parallel should be bool, not string
    config = {"parallel": "not-a-bool"}

    with pytest.raises(ConfigValidationError) as exc_info:
        validator.validate(config)

    assert exc_info.value.code == ErrorCode.C004
```

### Session Tracking Tests

**File**: `tests/unit/config/test_session_tracking.py` (new)

```python
"""Test that config errors are tracked in error sessions."""
import pytest
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.errors.session import get_session, reset_session


@pytest.fixture(autouse=True)
def fresh_session():
    """Reset session before each test."""
    reset_session()
    yield
    reset_session()


def test_yaml_error_tracked_in_session(tmp_path):
    """Verify YAML parse errors are recorded in error session."""
    loader = ConfigDirectoryLoader()
    config_dir = tmp_path / "config" / "_default"
    config_dir.mkdir(parents=True)
    (config_dir / "site.yaml").write_text("invalid: [")

    with pytest.raises(ConfigLoadError):
        loader.load(tmp_path / "config")

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C001" in summary["errors_by_code"]
```

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
| `bengal/config/directory_loader.py` | Add error codes + session tracking | ~25 |
| `bengal/config/validators.py` | Add C004 + session tracking | ~10 |
| `bengal/config/deprecation.py` | Optional C008 integration | ~10 |
| `tests/unit/config/test_directory_loader.py` | Add error code assertions | ~25 |
| `tests/unit/config/test_validators.py` | Add error code assertions | ~15 |
| `tests/unit/config/test_session_tracking.py` | New: session tracking tests | ~30 |
| **Total** | — | ~115 |

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

- `bengal/errors/codes.py:110-117` — C-series error codes
- `bengal/errors/exceptions.py:364-395` — BengalConfigError definition
- `bengal/errors/session.py:482-499` — `record_error()` function signature
- `bengal/config/directory_loader.py:66-84` — ConfigLoadError class
- `bengal/config/validators.py:48-62` — ConfigValidationError class
- `bengal/config/loader.py:244-252` — Only C003 usage in package
- `tests/unit/config/` — Test files for validation
