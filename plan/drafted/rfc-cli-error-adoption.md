# RFC: CLI Package Error Handling Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/cli/`  
**Confidence**: 92% 🟢 (verified via code inspection of 102 Python files)  
**Priority**: P3 (Low) — CLI already has robust error handling infrastructure  
**Estimated Effort**: 3-4 hours (single dev)

---

## Executive Summary

The `bengal/cli/` package has **mature error handling adoption** with well-designed infrastructure. It already provides:

- `@handle_cli_errors` decorator for consistent command-level error handling
- `display_bengal_error()` for beautiful `BengalError` display with codes and suggestions
- `beautify_common_exception()` for user-friendly messages from common exceptions
- Proper Click exception handling (`click.Abort`, `click.UsageError`, `click.ClickException`)

**Current state**:
- **102 Python files** across commands, helpers, dashboard, templates, and skeleton modules
- **59 commands** use `@handle_cli_errors` decorator
- **79 uses** of Click exceptions (`Abort`, `UsageError`, `ClickException`)
- **17 structured log sites** across 7 files
- **4 imports** from `bengal.errors` (in error handling infrastructure)

**True gaps** (minor):
1. **No `BengalCLIError` class exists** — CLI uses Click exceptions instead (acceptable design choice)
2. **No CLI-specific error codes** (`L001`-`L099`) defined — could improve error searchability
3. **Missing test file mapping** — `exceptions.py` doesn't map any CLI-related tests
4. **Some commands catch generic `Exception`** instead of specific types
5. **Inconsistent error display** — some commands use `cli.error()`, others use `show_error()`

**Assessment**: The CLI package follows an appropriate pattern for CLI applications — using Click's exception system rather than Bengal's internal error hierarchy. This is the correct design. Only minor improvements are recommended.

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

The CLI is the user-facing entry point to Bengal. Error handling here directly impacts user experience:
- **Build failures** — Users need clear, actionable error messages
- **Configuration errors** — Help users fix their `bengal.toml` quickly
- **Command typos** — Fuzzy matching already helps (via `BengalGroup`)
- **Debugging** — `BengalError` instances show codes, suggestions, and docs links

### Design Philosophy

The CLI package correctly separates concerns:
1. **CLI errors** (user input, flags, missing files) → Click exceptions
2. **Bengal errors** (config, content, rendering) → `BengalError` hierarchy

This is the right design. The CLI should catch `BengalError` instances from the core and display them beautifully, not create its own `BengalCLIError` class.

---

## Current State Evidence

### File Statistics

| Category | Files | Lines (approx) |
|----------|-------|----------------|
| Commands | 35 | ~4,500 |
| Helpers | 13 | ~1,200 |
| Dashboard | 15 | ~2,000 |
| Templates | 12 | ~1,500 |
| Skeleton | 4 | ~400 |
| Other | 23 | ~1,800 |
| **Total** | **102** | **~11,400** |

### Error Handling Infrastructure

**`bengal/cli/helpers/error_handling.py`** provides:

```python
@handle_cli_errors(show_art=True)
def my_command():
    """Decorator catches exceptions and displays them beautifully."""
    pass
```

Features:
- Catches `BengalError` → calls `display_bengal_error()`
- Catches common exceptions → calls `beautify_common_exception()`
- Respects `TracebackConfig` for traceback display
- Re-raises as `click.Abort` for proper exit codes

**`bengal/cli/helpers/error_display.py`** provides:

```python
def display_bengal_error(error: BengalError, cli: CLIOutput) -> None:
    """Beautiful display with code, category, file, suggestion, docs link."""

def beautify_common_exception(e: Exception) -> tuple[str, str | None] | None:
    """User-friendly messages for YAML, TOML, Jinja2, JSON, File errors."""
```

### Decorator Usage (59 commands)

Every significant command uses `@handle_cli_errors`:

| Command File | Decorator Count |
|--------------|-----------------|
| `commands/theme.py` | 9 |
| `commands/debug.py` | 6 |
| `commands/version.py` | 4 |
| `commands/project.py` | 4 |
| `commands/config.py` | 4 |
| `commands/new/scaffolds.py` | 4 |
| `commands/collections.py` | 3 |
| Other commands | 25 |

### Click Exception Usage (79 sites)

| Exception Type | Usage | Purpose |
|----------------|-------|---------|
| `click.Abort` | ~60 | User cancellation, fatal errors |
| `click.UsageError` | ~12 | Invalid flag combinations |
| `click.ClickException` | ~7 | Structured error exit |

### Logging Sites (17 sites across 7 files)

| File | Log Calls | Purpose |
|------|-----------|---------|
| `helpers/site_loader.py` | 4 | Debug/warning for directory detection |
| `commands/theme.py` | 6 | Theme operation logging |
| `output/core.py` | 2 | Output logging |
| `skeleton/hydrator.py` | 2 | Skeleton operation logging |
| `templates/registry.py` | 1 | Template loading |
| `progress.py` | 1 | Progress tracking |
| `helpers/traceback.py` | 1 | Traceback config |

---

## Gap Analysis

### Tier 1: Not Applicable (Correct Design)

#### No `BengalCLIError` Class — By Design

The CLI correctly uses Click's exception system for CLI-layer errors:
- `click.Abort` for user cancellation or explicit abort
- `click.UsageError` for invalid options/arguments
- `click.ClickException` for structured error exit

**This is the right design.** CLI errors are fundamentally different from Bengal core errors.

### Tier 2: Minor Improvements

#### 2.1: Inconsistent Error Display Methods

**Issue**: Some commands use `cli.error()` + `click.Abort`, others use `show_error()`.

**Current patterns**:
```python
# Pattern A (most commands)
cli.error(f"Source directory does not exist: {root_path}")
raise click.Abort()

# Pattern B (some commands)
show_error(f"Failed to initialize: {e}", show_art=False)
raise click.Abort() from e
```

**Recommendation**: Standardize on `cli.error()` pattern (no ASCII art on errors).

#### 2.2: Generic Exception Catching

**Issue**: Some commands catch broad `Exception` instead of specific types.

**Locations**:
- `health.py:201` — `except Exception as e:`
- `health.py:253` — `except Exception as e:`
- `init.py:169` — `except Exception as e:`
- `sources.py:257` — `except Exception as e:`
- `site_loader.py:247` — `except Exception as e:`

**Current**:
```python
except Exception as e:
    cli.error(f"Link check failed: {e}")
    raise click.Abort() from e
```

**Recommendation**: Keep as-is. The `@handle_cli_errors` decorator already handles specific `BengalError` types. Catching `Exception` at command boundaries is appropriate for CLIs.

#### 2.3: No CLI-Specific Error Codes

**Issue**: While Bengal has error codes (C001, R001, etc.), there are no CLI-specific codes.

**Potential codes (NOT recommended for implementation)**:
| Code | Value | When to Use |
|------|-------|-------------|
| `L001` | `cli_invalid_flags` | Conflicting flag combinations |
| `L002` | `cli_missing_site` | Site directory not found |
| `L003` | `cli_config_not_found` | Config file not found |

**Assessment**: NOT RECOMMENDED. CLI errors are transient user input errors, not structured errors that need codes and documentation. Click's built-in error messages are sufficient.

#### 2.4: Missing Test File Mapping

**Issue**: `exceptions.py` doesn't include CLI test mappings.

**Current test mapping** (from `exceptions.py:267-298`):
```python
test_mapping: dict[type, list[str]] = {
    BengalConfigError: ["tests/unit/config/", ...],
    BengalContentError: ["tests/unit/core/test_page.py", ...],
    BengalRenderingError: ["tests/unit/rendering/", ...],
    # ... no CLI mapping
}
```

**Recommendation**: Add CLI test paths to error investigation commands, even though CLI doesn't use `BengalError` directly. When a `BengalError` originates from CLI-invoked operations, include CLI test paths.

---

## Proposed Changes

### Change 1: Standardize Error Display (Optional - Low Priority)

**Goal**: Consistent error display across all commands.

**Files to update**: `init.py`, possibly others using `show_error()`.

**Before**:
```python
except Exception as e:
    show_error(f"Failed to initialize: {e}", show_art=False)
    raise click.Abort() from e
```

**After**:
```python
except Exception as e:
    cli.error(f"Failed to initialize: {e}")
    raise click.Abort() from e
```

**Impact**: Minor. Improves consistency but `show_error()` already works well.

### Change 2: Add Error Code to Logger Calls (Optional)

**Goal**: Structured logs for CLI operations.

**Example in `site_loader.py`**:
```python
logger.warning(
    "parent_bengal_project_detected",
    current=root_path.name,
    parent=parent.name,
    hint="You may be running from wrong directory",
    # Add: error_code="CLI_WARN_01" (optional structured identifier)
)
```

**Impact**: Enables log filtering and searching. Low priority.

### Change 3: Document CLI Error Patterns (Recommended)

**Goal**: Document the CLI error handling architecture.

**Add to docstring in `error_handling.py`**:
```python
"""
CLI Error Handling Architecture
================================

Bengal CLI uses a layered error handling approach:

1. **Click Exceptions** (CLI-layer errors):
   - `click.Abort` — User cancellation or fatal CLI error
   - `click.UsageError` — Invalid flag combinations, missing arguments
   - `click.ClickException` — Structured error with exit code

2. **BengalError** (Core-layer errors):
   - Caught by `@handle_cli_errors` decorator
   - Displayed via `display_bengal_error()` with code, suggestion, docs link
   - Converted to `click.Abort` for proper exit

3. **Common Exceptions** (Python stdlib errors):
   - Caught by `@handle_cli_errors` decorator
   - Beautified via `beautify_common_exception()` (YAML, JSON, Jinja2, etc.)
   - Converted to `click.Abort` for proper exit

Usage:
    @click.command()
    @handle_cli_errors(show_art=True)
    def my_command():
        # Raise Click exceptions for CLI errors
        raise click.UsageError("--foo and --bar cannot be used together")

        # Let BengalError propagate - decorator handles it
        site.build()  # May raise BengalRenderingError
"""
```

---

## Implementation Plan

### Phase 1: Documentation (30 min) — Recommended

1. Update `error_handling.py` docstring with architecture overview
2. Add examples for each error handling pattern
3. Document the design decision (Click vs BengalError)

### Phase 2: Minor Cleanup (Optional, 1 hour)

1. Replace `show_error()` with `cli.error()` in `init.py`
2. Audit other commands for consistency
3. No code changes required to error flow

### Phase 3: Verification (30 min)

1. Run existing CLI tests
2. Manually trigger error conditions to verify display
3. Confirm `BengalError` display still works beautifully

---

## Success Criteria

### Already Met:

- [x] All commands use `@handle_cli_errors` decorator
- [x] `BengalError` instances display with codes and suggestions
- [x] Common exceptions are beautified
- [x] Click exceptions used appropriately for CLI errors
- [x] Traceback configuration respected

### Recommended Improvements:

- [ ] Documentation added to `error_handling.py`
- [ ] Consistent use of `cli.error()` across all commands
- [ ] Architecture decision documented

### Final Metrics:

| Metric | Current | After (if changes made) |
|--------|---------|-------------------------|
| Commands with `@handle_cli_errors` | 59 | 59 (unchanged) |
| Click exception sites | 79 | 79 (unchanged) |
| `BengalError` display support | ✅ | ✅ |
| Documentation | ❌ | ✅ |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Changing error display breaks UX | Very Low | Low | Only cosmetic changes proposed |
| Adding codes adds complexity | N/A | N/A | NOT implementing CLI codes |
| Documentation becomes stale | Low | Low | Keep in module docstring |

---

## Comparison with Other Packages

| Package | Error Class | Uses ErrorCode | Decorator | Status |
|---------|-------------|----------------|-----------|--------|
| `bengal/config/` | `BengalConfigError` | ✅ C001-C008 | N/A | ✅ Mature |
| `bengal/rendering/` | `BengalRenderingError` | ✅ R001-R010 | N/A | ✅ Mature |
| `bengal/assets/` | `BengalAssetError` | ⚠️ Partial | N/A | 🔄 RFC exists |
| **`bengal/cli/`** | **Click exceptions** | **N/A (by design)** | **✅ 59 uses** | **✅ Mature** |

**Key insight**: CLI is different from other packages. It's the boundary between user input and Bengal internals. Using Click's exception system is the correct pattern.

---

## Conclusion

The CLI package has **excellent error handling adoption**. The infrastructure is well-designed, consistently applied, and follows best practices for CLI applications.

**Recommendation**: Mark as **no action required** for error handling migration. The only improvements are documentation updates and minor cosmetic consistency, which can be done opportunistically.

---

## References

- `bengal/cli/helpers/error_handling.py:38-136` — `@handle_cli_errors` decorator
- `bengal/cli/helpers/error_display.py:39-150` — `display_bengal_error()` function
- `bengal/cli/helpers/error_display.py:153-272` — `beautify_common_exception()` function
- `bengal/cli/base.py:375-435` — Fuzzy command matching with suggestions
- `bengal/errors/exceptions.py:267-298` — Test file mapping (no CLI entry)

---

## Appendix: Commands Using `@handle_cli_errors`

<details>
<summary>Full list of 59 decorated commands (click to expand)</summary>

| File | Commands |
|------|----------|
| `commands/validate.py` | `validate` |
| `commands/skeleton.py` | `skeleton` |
| `commands/graph/report.py` | `report` |
| `commands/init.py` | `init` |
| `commands/version.py` | `show`, `archive`, `compare`, `list` |
| `commands/new/scaffolds.py` | `page`, `layout`, `partial`, `theme` |
| `commands/clean.py` | `clean` |
| `commands/explain.py` | `explain` |
| `commands/engine.py` | `globals`, `dump` |
| `commands/graph/orphans.py` | `orphans` |
| `commands/collections.py` | `list`, `show`, `stats` |
| `commands/fix.py` | `fix` |
| `commands/debug.py` | 6 debug commands |
| `commands/new/site.py` | `site` |
| `commands/perf.py` | `perf` |
| `commands/graph/__main__.py` | `analyze` |
| `commands/build.py` | `build` |
| `commands/serve.py` | `serve` |
| `commands/health.py` | `linkcheck` |
| `commands/theme.py` | 9 theme commands |
| `commands/site.py` | `site` |
| `commands/project.py` | 4 project commands |
| `commands/graph/suggest.py` | `suggest` |
| `commands/graph/communities.py` | `communities` |
| `commands/config.py` | `show`, `doctor`, `diff`, `init` |
| `commands/assets.py` | `build`, `watch` |
| `commands/graph/pagerank.py` | `pagerank` |
| `commands/graph/bridges.py` | `bridges` |

</details>
