# Monkey Patch Refactoring - Completed

## Overview

Refactored the Pygments lexer caching monkey patch from an inline implementation to a clean, testable, context-manager-based approach.

## What Was Changed

### Before
- Inline monkey patching in `PythonMarkdownParser.__init__()`
- Patch logic mixed with parser initialization
- No way to restore original functions
- Hard to test in isolation
- Module-level side effects not clearly documented

### After
- Extracted to dedicated `PygmentsPatch` class
- Context manager support for temporary patching
- Clean apply/restore API
- Fully tested with 22 unit tests
- Clear documentation about scope and side effects

## Files Changed

### New Files
1. **`bengal/rendering/parsers/pygments_patch.py`**
   - Standalone `PygmentsPatch` class
   - Context manager support
   - Class methods: `apply()`, `restore()`, `is_patched()`
   - Comprehensive docstrings with performance metrics
   - Clear warnings about process-wide scope

2. **`tests/unit/rendering/test_pygments_patch.py`**
   - 22 comprehensive unit tests
   - Tests for apply, restore, context manager, state management
   - Integration tests with `PythonMarkdownParser`
   - Error handling tests
   - All tests passing ✅

### Modified Files
1. **`bengal/rendering/parsers/python_markdown.py`**
   - Simplified initialization
   - Now just calls `PygmentsPatch.apply()`
   - Cleaner and more maintainable

## Key Features

### 1. Context Manager Support
```python
# Temporary patching (e.g., in tests)
with PygmentsPatch():
    parser.parse(content)
# Patch automatically removed
```

### 2. Explicit Control
```python
# One-time application (typical usage)
PygmentsPatch.apply()

# Optional: restore later
PygmentsPatch.restore()

# Check state
if PygmentsPatch.is_patched():
    print("Patch is active")
```

### 3. Idempotent & Safe
- Calling `apply()` multiple times is safe
- Automatically checks if already patched
- Fails gracefully if dependencies missing
- Nested context managers work correctly

## Performance Impact

**No change** - the performance optimization remains intact:
- Before: 86s (73% in plugin discovery)
- After: ~29s (3× faster)

The refactoring only improves **code quality**, not performance.

## Testing

All 22 tests pass:
```bash
pytest tests/unit/rendering/test_pygments_patch.py -v
# ============================== 22 passed in 9.12s ==============================
```

Test coverage includes:
- ✅ Basic apply/restore operations
- ✅ Idempotent behavior
- ✅ Context manager usage
- ✅ State management
- ✅ Error handling
- ✅ Integration with PythonMarkdownParser
- ✅ Module-level effects
- ✅ Documentation completeness

## Documentation Improvements

### Clear Scope Declaration
The module docstring now explicitly states:
- **Scope**: Process-wide (affects global module state)
- **Use case**: Safe for CLI tools and single-process applications
- **Caution**: May not be suitable for multi-tenant web applications

### Performance Metrics
Documented in code:
- Specific test case (826-page site)
- Before/after timings
- Percentage improvement (3× faster)

### Code Examples
- How to use as context manager
- How to apply one-time
- How to check state

## Why This Approach?

### Considered Alternatives
1. **Custom CodeHilite extension** - More complex, upstream maintenance burden
2. **Extension wrapper** - Adds another layer of abstraction
3. **Upstream contribution** - Long-term solution, but not immediate
4. **Complete removal** - Loses significant performance benefit

### Why We Kept the Patch (Improved)
1. **3× performance gain** is substantial
2. **Stable API** - Pygments lexer functions are stable
3. **CLI context** - Bengal controls the entire process
4. **Now testable** - Can verify behavior in isolation
5. **Explicit** - Clear about what's happening and where
6. **Reversible** - Can remove if needed

## Migration Notes

No migration needed! The change is **100% backward compatible**:
- Same behavior for existing code
- No API changes for users
- Performance characteristics identical

## Future Considerations

If Bengal becomes a **library** (not just CLI):
- Consider replacing with custom CodeHilite extension
- Or make patch optional via configuration
- Or contribute caching support upstream to python-markdown

For now, as a **CLI tool**, this approach is optimal.

## Test Coverage Metrics

```
bengal/rendering/parsers/pygments_patch.py    88% coverage
- Missing: error paths and edge cases that are hard to trigger
- Core functionality: 100% covered
```

## Lessons Learned

1. **Monkey patches can be cleaned up** without removing them entirely
2. **Context managers** make testing much easier
3. **Class-level state** is acceptable when scope is clear
4. **Good documentation** makes "unusual" patterns acceptable
5. **Tests first** ensures refactoring doesn't break behavior

## Related Files

- `bengal/rendering/parsers/python_markdown.py` - Uses the patch
- `bengal/rendering/pygments_cache.py` - The cache implementation used
- `tests/performance/investigate_*_parsers.py` - Performance investigation tools (still use monkey patches, but that's fine for debug tools)

## Status

✅ **Completed**
- Refactored implementation
- Added comprehensive tests
- Updated documentation
- All tests passing
- No breaking changes
