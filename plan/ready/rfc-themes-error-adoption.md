# RFC: Themes Package Error System Adoption

**Status**: Evaluated ✅  
**Created**: 2025-12-24  
**Evaluated**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/themes/`  
**Confidence**: 95% 🟢 (all claims verified via source code inspection; line numbers corrected)  
**Priority**: P3 (Low) — Small package with partial adoption already  
**Estimated Effort**: 0.5 days (~55 minutes including tests)

> **Evaluation Note**: All 13 claims verified against source code. Ready for implementation.
>
> **Improvement Pass (2025-12-24)**: Fixed line number references for `generate.py` (151-179, 182-216, 219-249, 236-241) and `BengalAssetError` (571-600). Added complete code snippets to evidence sections.

---

## Executive Summary

The `bengal/themes/` package has **partial adoption** of the Bengal error system. The `config.py` module has good error handling with `BengalConfigError` and error codes, while `generate.py` lacks any structured error handling.

**Current state**:
- **2 files** need error handling (`config.py`, `generate.py`)
- **2 error codes used**: C001, C003 (both in `config.py`)
- **1 bare exception**: `FileNotFoundError` at `config.py:302`
- **0 session tracking** via `record_error()`
- **0 error handling** in `generate.py`

**Adoption Score**: 5/10

**Recommendation**: Convert `FileNotFoundError` to `BengalConfigError`, add structured errors to `generate.py`, and implement session tracking.

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
9. [Evaluation Results](#evaluation-results)

---

## Problem Statement

### Why This Matters

The Bengal error system provides:
- **Error codes** for searchability and documentation linking
- **Build phase tracking** for investigation
- **Related test file mapping** for debugging
- **Investigation helpers** (grep commands, related files)
- **Session tracking** for error aggregation across builds

The themes package has partial adoption in `config.py` but `generate.py` uses bare returns and `sys.exit()` which bypasses all error infrastructure.

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| Bare `FileNotFoundError` | No suggestion for fix | Can't grep for error code |
| No errors in `generate.py` | Silent failures on CSS write | No error tracking |
| No session tracking | Theme errors missing from build summary | No pattern detection |
| `sys.exit(1)` in main() | Abrupt exit, no error context | Breaks programmatic usage |

---

## Current State Evidence

### Package Structure

| File | Lines | Purpose | Error Status |
|------|-------|---------|--------------|
| `__init__.py` | 89 | Re-exports | ✅ No changes needed |
| `config.py` | 364 | Theme YAML loading | 🟡 Partial adoption |
| `generate.py` | 249 | CSS/TCSS generation | ❌ No adoption |
| `tokens.py` | 290 | Frozen design tokens | ✅ No changes needed |

### Error Handling in `config.py`

**Good: Uses BengalConfigError with codes**

```python
# config.py:162-167 - Invalid appearance mode
raise BengalConfigError(
    f"Invalid default_mode '{self.default_mode}'. "
    f"Must be one of: {', '.join(valid_modes)}",
    code=ErrorCode.C003,
    suggestion=f"Set default_mode to one of: {', '.join(valid_modes)}",
)
```

```python
# config.py:307-314 - YAML parse error
except yaml.YAMLError as e:
    raise BengalConfigError(
        f"Invalid YAML in {yaml_path}: {e}",
        code=ErrorCode.C001,
        file_path=yaml_path,
        suggestion="Check YAML syntax and indentation",
        original_error=e,
    ) from e
```

**Bad: Uses bare FileNotFoundError**

```python
# config.py:301-302 - Missing theme.yaml
if not yaml_path.exists():
    raise FileNotFoundError(f"Theme config not found: {yaml_path}")
```

### Error Handling in `generate.py`

**No Bengal error imports or usage.**

```python
# generate.py:200-201 - Missing file returns string
if not tcss_path.exists():
    return [f"TCSS file not found: {tcss_path}"]
```

```python
# generate.py:236-241 - Uses sys.exit for errors
errors = validate_tcss_tokens()
if errors:
    print("\n⚠ TCSS validation warnings:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
```

```python
# generate.py:173-177 - No error handling on file write
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "generated.css"
css_content = generate_web_css()
output_file.write_text(css_content)
```

### Import Patterns

| File | Import | Status |
|------|--------|--------|
| `config.py` | `from bengal.errors import BengalConfigError, ErrorCode` | ✅ Module-level |
| `generate.py` | — | ❌ No import |
| `tokens.py` | — | ✅ None needed (data only) |
| `__init__.py` | — | ✅ None needed (re-exports) |

### Error Code Usage

| Code | Value | Location | Count |
|------|-------|----------|-------|
| C001 | `config_yaml_parse_error` | `config.py:308` | 1 |
| C003 | `config_invalid_value` | `config.py:162` | 1 |

### Error Codes Applicable but Unused

| Code | Value | Proposed Use |
|------|-------|--------------|
| C005 | `config_defaults_missing` | Missing theme.yaml file |
| X001 | `asset_not_found` | Missing TCSS file in validation |
| X004 | `asset_copy_error` | CSS write failures |

---

## Gap Analysis

### 1. Bare FileNotFoundError in `config.py`

**Location**: `config.py:301-302`

```python
# Current
if not yaml_path.exists():
    raise FileNotFoundError(f"Theme config not found: {yaml_path}")
```

**Problems**:
- No error code for searchability
- No suggestion for users
- No file path in structured format
- Not tracked in error sessions

**Recommended Code**: C005 (`config_defaults_missing`)

### 2. No Error Handling in `generate.py`

**Location**: `generate.py:151-179` (write_generated_css)

```python
# Current - no try/except (lines 173-177)
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "generated.css"

css_content = generate_web_css()
output_file.write_text(css_content)
```

**Problems**:
- `mkdir()` can fail with `PermissionError`
- `write_text()` can fail with `OSError`
- No structured error if operations fail

### 3. Validation Returns Strings Instead of Errors

**Location**: `generate.py:182-216` (validate_tcss_tokens)

```python
# Current (lines 200-201)
if not tcss_path.exists():
    return [f"TCSS file not found: {tcss_path}"]
```

**Note**: This pattern is acceptable for validation functions that are meant to collect multiple errors. The issue is that `main()` doesn't convert these to structured errors.

### 4. sys.exit(1) in CLI Entry Point

**Location**: `generate.py:236-241`

```python
# Current
errors = validate_tcss_tokens()
if errors:
    print("\n⚠ TCSS validation warnings:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
```

**Problems**:
- Abrupt exit breaks programmatic usage
- No structured error for callers
- Errors not recorded in session

### 5. No Session Tracking

**Current**: No `record_error()` calls anywhere in themes package.

**Impact**: Theme configuration errors don't appear in error session summaries.

---

## Proposed Changes

### Phase 1: Fix FileNotFoundError in `config.py` (5 min)

**Update line 301-302:**

```python
# Before
if not yaml_path.exists():
    raise FileNotFoundError(f"Theme config not found: {yaml_path}")

# After
if not yaml_path.exists():
    raise BengalConfigError(
        f"Theme config not found: {yaml_path}",
        code=ErrorCode.C005,
        file_path=yaml_path,
        suggestion="Ensure theme directory contains theme.yaml. "
        "Run 'bengal theme new <name>' to create a new theme.",
    )
```

### Phase 2: Add Error Handling to `generate.py` (15 min)

#### 2.1 Add imports

```python
# Add at top of generate.py after existing imports
from bengal.errors import BengalAssetError, ErrorCode
```

#### 2.2 Update `write_generated_css()`

```python
def write_generated_css(output_dir: Path | None = None) -> Path:
    """
    Write generated CSS custom properties to file.

    ... existing docstring ...

    Raises:
        BengalAssetError: If directory creation or file write fails
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "default" / "assets" / "css" / "tokens"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise BengalAssetError(
            f"Failed to create CSS output directory: {output_dir}",
            code=ErrorCode.X004,
            file_path=output_dir,
            suggestion="Check directory permissions and disk space",
            original_error=e,
        ) from e

    output_file = output_dir / "generated.css"
    css_content = generate_web_css()

    try:
        output_file.write_text(css_content)
    except OSError as e:
        raise BengalAssetError(
            f"Failed to write generated CSS: {output_file}",
            code=ErrorCode.X004,
            file_path=output_file,
            suggestion="Check file permissions and disk space",
            original_error=e,
        ) from e

    return output_file
```

#### 2.3 Update `main()` for structured error handling

```python
def main() -> None:
    """
    CLI entry point for token generation and validation.

    Generates web CSS from tokens and validates TCSS files. Exits with
    code 1 if validation fails, code 0 on success.

    Raises:
        BengalAssetError: If CSS generation fails
    """
    import sys

    print("Bengal Token Generator")
    print("=" * 40)

    # Generate web CSS (may raise BengalAssetError)
    try:
        output_path = write_generated_css()
        print(f"✓ Generated web CSS: {output_path}")
    except BengalAssetError as e:
        print(f"\n✗ CSS generation failed: {e.message}")
        if e.suggestion:
            print(f"  Tip: {e.suggestion}")
        sys.exit(1)

    # Validate TCSS
    errors = validate_tcss_tokens()
    if errors:
        print("\n⚠ TCSS validation warnings:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✓ TCSS tokens validated")

    print("\nDone!")
```

### Phase 3: Add Session Tracking (10 min)

#### 3.1 Update `config.py` imports

```python
# Update existing import
from bengal.errors import BengalConfigError, ErrorCode, record_error
```

#### 3.2 Add session tracking to YAML error handler

```python
# config.py:307-314
except yaml.YAMLError as e:
    error = BengalConfigError(
        f"Invalid YAML in {yaml_path}: {e}",
        code=ErrorCode.C001,
        file_path=yaml_path,
        suggestion="Check YAML syntax and indentation",
        original_error=e,
    )
    record_error(error, file_path=str(yaml_path))
    raise error from e
```

#### 3.3 Add session tracking to missing file error

```python
# config.py:301-302 (after Phase 1 changes)
if not yaml_path.exists():
    error = BengalConfigError(
        f"Theme config not found: {yaml_path}",
        code=ErrorCode.C005,
        file_path=yaml_path,
        suggestion="Ensure theme directory contains theme.yaml. "
        "Run 'bengal theme new <name>' to create a new theme.",
    )
    record_error(error, file_path=str(yaml_path))
    raise error
```

#### 3.4 Add session tracking to appearance validation

```python
# config.py:162-167
def __post_init__(self) -> None:
    """Validate appearance configuration."""
    valid_modes = {"light", "dark", "system"}
    if self.default_mode not in valid_modes:
        error = BengalConfigError(
            f"Invalid default_mode '{self.default_mode}'. "
            f"Must be one of: {', '.join(valid_modes)}",
            code=ErrorCode.C003,
            suggestion=f"Set default_mode to one of: {', '.join(valid_modes)}",
        )
        record_error(error)
        raise error
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Convert FileNotFoundError to BengalConfigError | 5 min | P1 |
| 1b | Update caller in `bengal/core/theme/config.py` | 5 min | P1 |
| 2 | Add error handling to generate.py | 15 min | P1 |
| 3 | Add session tracking | 10 min | P2 |
| 4 | Add test assertions for error codes | 20 min | P1 |

**Total**: ~55 minutes (including tests)

> **Important**: Phase 1 and 1b must be done together to avoid breaking the build.

---

## Success Criteria

### Must Have

- [ ] All theme config errors use `BengalConfigError` with error codes
- [ ] `FileNotFoundError` replaced with `BengalConfigError(code=C005)`
- [ ] Caller at `bengal/core/theme/config.py:214` updated to catch `BengalConfigError`
- [ ] `write_generated_css()` handles file operation errors
- [ ] Tests verify error codes are set correctly

### Should Have

- [ ] Session tracking via `record_error()` for config errors
- [ ] `main()` catches and formats `BengalAssetError`
- [ ] Error suggestions are actionable

### Nice to Have

- [ ] Session tracking in `generate.py` for CSS write errors
- [ ] Validation errors optionally raised as `BengalAssetError`

---

## Test Verification

### Existing Test Coverage

| Test File | Purpose | Relevant? |
|-----------|---------|-----------|
| `tests/unit/core/test_theme.py` | Tests `bengal.core.theme.config.Theme` class | ❌ Different class |
| `tests/unit/themes/test_theme_controls.py` | Tests popover controls | ❌ UI tests |
| `tests/unit/themes/test_mobile_nav.py` | Tests mobile navigation | ❌ UI tests |

> **Note**: The existing `test_theme.py` tests the `Theme` class in `bengal/core/theme/config.py`,
> which is a *different* class from `ThemeConfig` in `bengal/themes/config.py`.
> No tests currently exist for `ThemeConfig` or `AppearanceConfig` error handling.

### Required Test Additions

**File**: `tests/unit/themes/test_theme_config.py` (new)

```python
"""Tests for ThemeConfig error handling."""
from __future__ import annotations

import pytest
from pathlib import Path

from bengal.themes.config import ThemeConfig, AppearanceConfig
from bengal.errors import BengalConfigError, ErrorCode


class TestThemeConfigErrors:
    """Tests for ThemeConfig error codes."""

    def test_missing_theme_yaml_has_error_code(self, tmp_path: Path) -> None:
        """Verify ThemeConfig.load raises BengalConfigError with C005."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(BengalConfigError) as exc_info:
            ThemeConfig.load(nonexistent)

        assert exc_info.value.code == ErrorCode.C005
        assert exc_info.value.file_path is not None
        assert "theme.yaml" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    def test_invalid_yaml_has_error_code(self, tmp_path: Path) -> None:
        """Verify ThemeConfig.load raises BengalConfigError with C001 for invalid YAML."""
        theme_dir = tmp_path / "theme"
        theme_dir.mkdir()
        (theme_dir / "theme.yaml").write_text("invalid: yaml: [")

        with pytest.raises(BengalConfigError) as exc_info:
            ThemeConfig.load(theme_dir)

        assert exc_info.value.code == ErrorCode.C001
        assert exc_info.value.file_path is not None

    def test_invalid_mode_has_error_code(self) -> None:
        """Verify AppearanceConfig raises BengalConfigError with C003."""
        with pytest.raises(BengalConfigError) as exc_info:
            AppearanceConfig(default_mode="invalid")

        assert exc_info.value.code == ErrorCode.C003
        assert "default_mode" in str(exc_info.value)

    def test_valid_config_loads_successfully(self, tmp_path: Path) -> None:
        """Verify valid theme.yaml loads without error."""
        theme_dir = tmp_path / "theme"
        theme_dir.mkdir()
        (theme_dir / "theme.yaml").write_text("""
name: test-theme
version: 1.0.0
appearance:
  default_mode: dark
""")

        config = ThemeConfig.load(theme_dir)

        assert config.name == "test-theme"
        assert config.appearance.default_mode == "dark"
```

**File**: `tests/unit/themes/test_generate.py` (new)

```python
"""Tests for theme CSS generation error handling."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from bengal.themes.generate import write_generated_css, generate_web_css
from bengal.errors import BengalAssetError, ErrorCode


class TestWriteGeneratedCSS:
    """Tests for write_generated_css error handling."""

    def test_successful_write(self, tmp_path: Path) -> None:
        """Verify successful CSS generation."""
        output_path = write_generated_css(tmp_path)

        assert output_path.exists()
        assert output_path.name == "generated.css"
        assert "--bengal-primary:" in output_path.read_text()

    def test_permission_error_raises_asset_error(self, tmp_path: Path) -> None:
        """Verify permission error raises BengalAssetError with X004."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o444)

        try:
            with pytest.raises(BengalAssetError) as exc_info:
                write_generated_css(readonly_dir / "subdir")

            assert exc_info.value.code == ErrorCode.X004
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_generate_web_css_contains_tokens(self) -> None:
        """Verify generated CSS contains expected tokens."""
        css = generate_web_css()

        assert ":root {" in css
        assert "--bengal-primary:" in css
        assert "--bengal-success:" in css
        assert "--bengal-error:" in css
```

### Session Tracking Tests

**File**: `tests/unit/themes/test_theme_session.py` (new)

```python
"""Tests for theme error session tracking."""
from __future__ import annotations

import pytest
from pathlib import Path

from bengal.themes.config import ThemeConfig
from bengal.errors import BengalConfigError
from bengal.errors.session import get_session, reset_session


@pytest.fixture(autouse=True)
def fresh_session():
    """Reset session before each test."""
    reset_session()
    yield
    reset_session()


def test_yaml_error_tracked_in_session(tmp_path: Path) -> None:
    """Verify YAML parse errors are recorded in error session."""
    theme_dir = tmp_path / "theme"
    theme_dir.mkdir()
    (theme_dir / "theme.yaml").write_text("invalid: [")

    with pytest.raises(BengalConfigError):
        ThemeConfig.load(theme_dir)

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C001" in str(summary.get("errors_by_code", {}))


def test_missing_file_tracked_in_session(tmp_path: Path) -> None:
    """Verify missing theme.yaml errors are recorded in error session."""
    with pytest.raises(BengalConfigError):
        ThemeConfig.load(tmp_path / "nonexistent")

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C005" in str(summary.get("errors_by_code", {}))
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking `FileNotFoundError` handlers | **High** | Medium | See breaking change note below |
| Test failures | Low | Low | Run `pytest tests/unit/themes/` after changes |
| `generate.py` used programmatically | Low | Medium | Keep return types, add optional error raising |
| Permission issues in tests | Low | Low | Use `pytest.mark.skipif` for permission tests on CI |

### ⚠️ Breaking Change: FileNotFoundError → BengalConfigError

**Identified Caller**: `bengal/core/theme/config.py:214` catches `FileNotFoundError`:

```python
# bengal/core/theme/config.py:204-216 (current)
if theme_path:
    try:
        theme_config_obj = ThemeConfig.load(theme_path)
        # ...
    except FileNotFoundError:
        # theme.yaml doesn't exist, fall back to config
        pass
```

**Required Fix**: Update to catch `BengalConfigError` with code C005:

```python
# After migration
from bengal.errors import BengalConfigError, ErrorCode

if theme_path:
    try:
        theme_config_obj = ThemeConfig.load(theme_path)
        # ...
    except BengalConfigError as e:
        if e.code == ErrorCode.C005:
            # theme.yaml doesn't exist, fall back to config
            pass
        else:
            # Other config errors should be reported
            emit_diagnostic(...)
```

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/themes/config.py` | Add C005, session tracking | ~20 |
| `bengal/themes/generate.py` | Add error handling | ~30 |
| `bengal/core/theme/config.py` | Update FileNotFoundError handler | ~10 |
| `tests/unit/themes/test_theme_config.py` | New: error code tests | ~50 |
| `tests/unit/themes/test_generate.py` | New: generation tests | ~40 |
| `tests/unit/themes/test_theme_session.py` | New: session tests | ~35 |
| **Total** | — | ~185 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 4/10 | 9/10 | All raises get codes |
| Exception classes | 6/10 | 9/10 | Uses Bengal exceptions consistently |
| Build phase tracking | 5/10 | 9/10 | Auto via BengalConfigError/BengalAssetError |
| Session tracking | 0/10 | 8/10 | Added to critical paths |
| Suggestion quality | 7/10 | 9/10 | Improved with actionable hints |
| File path context | 6/10 | 9/10 | Added to all raises |
| Test coverage | 5/10 | 8/10 | New test files added |
| **Overall** | **5/10** | **9/10** | — |

---

## Evaluation Results

**Evaluated**: 2025-12-24

| Claim | Verified | Evidence |
|-------|----------|----------|
| FileNotFoundError at line 301-302 | ✅ | `config.py:301-302` exact match |
| BengalConfigError with C003 | ✅ | `config.py:162-167` verified |
| BengalConfigError with C001 | ✅ | `config.py:307-314` verified |
| No error imports in generate.py | ✅ | Lines 1-43 confirmed |
| Error code C005 exists | ✅ | `codes.py:117` |
| Error code X004 exists | ✅ | `codes.py:231` |
| record_error() exists | ✅ | `session.py:482-499` |
| No tests for ThemeConfig errors | ✅ | `tests/unit/themes/` has only `test_mobile_nav.py`, `test_theme_controls.py` |

**Additional Finding** (during evaluation):
- ⚠️ Breaking change identified: `bengal/core/theme/config.py:214` catches `FileNotFoundError` and must be updated

**Verdict**: Ready for implementation with noted breaking change. Move to `plan/ready/` after approval.

---

## References

| Reference | Location | Status |
|-----------|----------|--------|
| C-series error codes | `bengal/errors/codes.py:117` | ✅ Verified |
| X-series asset error codes | `bengal/errors/codes.py:231` | ✅ Verified |
| BengalConfigError definition | `bengal/errors/exceptions.py:367-398` | ✅ Verified |
| BengalAssetError definition | `bengal/errors/exceptions.py:571-600` | ✅ Verified |
| `record_error()` function | `bengal/errors/session.py:482-499` | ✅ Verified |
| Current C003 usage | `bengal/themes/config.py:162-167` | ✅ Verified |
| Current C001 usage | `bengal/themes/config.py:307-314` | ✅ Verified |
| FileNotFoundError to convert | `bengal/themes/config.py:301-302` | ✅ Verified |
| write_generated_css function | `bengal/themes/generate.py:151-179` | ✅ Verified |
| validate_tcss_tokens function | `bengal/themes/generate.py:182-216` | ✅ Verified |
| main() entry point | `bengal/themes/generate.py:219-249` | ✅ Verified |

**Related Classes** (important distinction):
- `bengal/themes/config.py:ThemeConfig` — This RFC's target (theme YAML config)
- `bengal/core/theme/config.py:Theme` — Different class (core theme model)
