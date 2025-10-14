# Bug Bash Progress - October 14, 2025

## Summary
Started with **50+ failing tests**, currently at **~48 failures** (down from 53 after fixing side effects).

## Bugs Fixed ✅

### 1. **truncate_chars Bug** (CRITICAL)
- **Issue**: Function produced output longer than requested (e.g., 13 chars instead of 10)
- **Root Cause**: Added suffix AFTER taking `length` characters instead of accounting for it
- **Fix**: Changed to truncate at `(length - len(suffix))` so total never exceeds `length`
- **Files Modified**:
  - `bengal/utils/text.py` - Fixed implementation
  - `tests/unit/utils/test_text_properties.py` - Already had correct expectations
  - `tests/unit/template_functions/test_strings.py` - Updated test expectations
  - `tests/unit/utils/test_text.py` - Updated test expectations
- **Tests Fixed**: 4 tests

### 2. **jinja_utils Bugs** (8 tests)
- **Issue**: `safe_get()` not returning defaults, `has_value()` treating 0/[] as truthy
- **Root Causes**:
  1. `has_value()` only checked for empty string, not all falsy values
  2. `safe_get()` returned methods for primitives instead of default
  3. `safe_get()` didn't handle `__getattr__` returning None for missing attrs
  4. `ensure_defined()` wasn't replacing None with default
- **Fixes**:
  - `has_value()`: Changed to use `bool(value)` to check all falsy values
  - `safe_get()`: Added primitive type check, handle None from `__getattr__`, catch all exceptions
  - `ensure_defined()`: Now replaces both Undefined AND None with default
- **Files Modified**:
  - `bengal/rendering/jinja_utils.py`
  - `tests/unit/rendering/test_jinja_utils.py`
- **Tests Fixed**: 8 tests (all jinja_utils tests now pass!)

## Remaining Failures (~48)

### By Category:
1. **Config/Logging** (2): verbose mode, log format
2. **Assets** (2): minification hints, theme asset dedup
3. **Parallel Processing** (3): sequential/parallel switching, error handling
4. **Section Orchestrator** (2): finalize without index, archive metadata
5. **Rendering/Parser** (12+):
   - Data table directive (2)
   - Cards directive (1)
   - MyST syntax/tabs (3)
   - Mistune parser (3)
   - Syntax highlighting (2)
   - Template engine (2)
6. **Orchestration** (4): incremental (2), taxonomy (2)
7. **Server** (3): live reload, component preview, request handler
8. **Utils** (5): file_io, logger, page_initializer, rich_console
9. **Integration** (12+): stateful workflows, incremental sequence, output quality
10. **Misc** (3): theme swizzle, section sorting, discovery

## Next Steps
1. Focus on high-impact bugs: incremental builds, parser issues
2. Fix systematic issues (e.g., all mistune parser tests)
3. Address integration test failures last (often side effects)

## Notes
- Property-based testing (Hypothesis) caught the truncate_chars bug!
- jinja_utils changes required updating `ensure_defined` behavior
- Some test expectations were outdated/contradictory
