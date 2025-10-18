# Site Creation Patterns & Design Clarity

**Date**: October 16, 2025  
**Context**: Phase 2b integration revealed that Site creation patterns could be more intuitive.  
**Status**: Design improvement implemented

## Problem Statement

When I was implementing Phase 2b cache integration tests, I instinctively tried:

```python
# ❌ What I tried (didn't work)
config = {'site': {'title': 'Test'}, 'build': {...}}
site = Site.from_config(config)  # ERROR: expects root_path not dict
```

The issue: `Site.from_config()` is named as if it takes config, but actually requires a `root_path` first, then optional `config_path`.

## Root Cause

The method signature wasn't intuitive:
- **Method name**: `from_config` (suggests config is the main input)
- **First param**: `root_path` (actually the main input)
- **Second param**: `config_path` (optional, auto-detected)

This violated the **principle of least surprise** - the method name doesn't match the primary parameter.

## Solution Implemented

### 1. **Clarified `from_config()` Docstring**

Added explicit type hints and examples:

```python
@classmethod
def from_config(cls, root_path: Path, config_path: Path | None = None) -> Site:
    """
    Args:
        root_path: Root directory of the site (Path object)
                  The folder containing bengal.toml/bengal.yaml
        config_path: Optional explicit path to config file (Path object)
                    If not provided, searches in root_path for:
                    bengal.toml → bengal.yaml → bengal.yml
    """
```

**Key improvements:**
- Explicit type hints: `Path` not just "root directory"
- Clear what the search order is
- Example showing both auto-detection and explicit paths

### 2. **Added `Site.for_testing()` Factory**

Created a dedicated testing factory that's **unmistakably** for testing:

```python
@classmethod
def for_testing(cls, root_path: Path | None = None, config: dict | None = None) -> Site:
    """Create a Site instance for testing without requiring a config file."""
    if root_path is None:
        root_path = Path('.')
    if config is None:
        config = {'site': {'title': 'Test Site'}, 'build': {...}}
    return cls(root_path=root_path, config=config)
```

**Usage in tests:**

```python
# ✅ Crystal clear it's for testing
site = Site.for_testing()

# ✅ With custom path
site = Site.for_testing(Path('/tmp/test_site'))

# ✅ With custom config
site = Site.for_testing(config={'site': {'title': 'My Test'}})
```

### 3. **Three Clear Patterns**

Now there are three well-documented patterns:

| Pattern | Use Case | Example |
|---------|----------|---------|
| `Site.from_config(root_path)` | Production builds | `Site.from_config(Path('./mysite'))` |
| `Site.for_testing(...)` | Unit/integration tests | `Site.for_testing(config={...})` |
| `Site(root_path, config)` | Advanced/custom usage | `Site(root_path=p, config=c)` |

## Why This Matters

1. **Clarity** - Method names now accurately reflect what they do
2. **Discoverability** - IDE autocomplete shows `for_testing()` for test writers
3. **Safety** - Tests use the dedicated factory, reducing mistakes
4. **Documentation** - Docstrings explain both the "why" and "how"

## Lessons for Future API Design

When naming factory methods:

1. ✅ **Name should match primary input**:
   - `from_config(config)` - if config is main input
   - `from_path(path)` - if path is main input
   - `from_file(file_path)` - if file is main input

2. ✅ **Provide context-specific factories**:
   - `for_testing()` - obvious this is for tests
   - `for_migration()` - obvious this is for migrations
   - `from_legacy()` - obvious this handles legacy data

3. ✅ **Document expected types clearly**:
   - Use type hints: `Path` not `path`
   - Show examples of correct usage
   - Show common mistakes and how to avoid them

4. ✅ **Consider the IDE experience**:
   - Does autocomplete make it clear what this does?
   - Can developers quickly find the right factory method?
   - Are examples in the docstring realistic?

## Files Changed

- `bengal/core/site.py`:
  - Improved `from_config()` docstring
  - Added `Site.for_testing()` factory method
  - Clarified type hints and examples

- `tests/integration/test_phase2b_cache_integration.py`:
  - Updated to use `Site.for_testing()` (clearer intent)
  - Removed need for config files in tests
