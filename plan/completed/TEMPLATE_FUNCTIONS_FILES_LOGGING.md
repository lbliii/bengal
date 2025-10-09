# Template Functions: Files Module Logging

**Date:** 2025-10-09  
**Status:** ✅ Complete  
**Implementation Time:** 10 minutes  

## Summary

Added structured logging to `bengal/rendering/template_functions/files.py`, completing the observability coverage for all template functions with file I/O operations.

## Changes Made

### Module: `files.py`
**Functions Updated:** `read_file()`, `file_size()`

**Note:** `file_exists()` was left as-is since it's a simple boolean check that doesn't need logging (returns True/False, no error states).

### 1. Infrastructure
Added logger import and initialization:
```python
from bengal.utils.logger import get_logger

logger = get_logger(__name__)
```

### 2. `read_file()` Function

**Added logging for:**
- ⚠️ **Warning:** File not found (with attempted path)
- ⚠️ **Warning:** Path exists but is not a file (e.g., directory)
- ❌ **Error:** IOError during read (permissions, disk errors)
- ❌ **Error:** UnicodeDecodeError (binary files, wrong encoding)
- 🐛 **Debug:** Successful reads (size, line count)

**Before:**
```python
def read_file(path: str, root_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        return ''  # ❌ Silent failure
    
    try:
        return f.read()
    except (IOError, UnicodeDecodeError):
        return ''  # ❌ No context
```

**After:**
```python
def read_file(path: str, root_path: Path) -> str:
    if not file_path.exists():
        logger.warning(
            "file_not_found",
            path=path,
            attempted=str(file_path),
            caller="template"
        )
        return ''
    
    if not file_path.is_file():
        logger.warning(
            "path_not_file",
            path=path,
            message="Path exists but is not a file (directory?)"
        )
        return ''
    
    try:
        content = f.read()
        logger.debug(
            "file_read",
            path=path,
            size_bytes=len(content),
            lines=content.count('\n') + 1
        )
        return content
    except UnicodeDecodeError as e:
        logger.error(
            "file_encoding_error",
            path=path,
            error=str(e),
            message="File contains invalid UTF-8 characters",
            suggestion="File may be binary or use a different encoding"
        )
        return ''
```

### 3. `file_size()` Function

**Added logging for:**
- ⚠️ **Warning:** File not found
- ⚠️ **Warning:** Path is not a file
- ❌ **Error:** Stat errors (permissions, disk errors)
- 🐛 **Debug:** Successful size computation

**Key Improvements:**
- Distinguishes between "file not found" and "path is directory"
- Logs both raw bytes and human-readable size
- Provides error context for stat failures

## Benefits

### 1. Better Template Debugging

**Before:**
```
{{ read_file('LICENSE') }}
<!-- Empty output, no idea why -->
```

**After:**
```
⚠️ file_not_found path=LICENSE attempted=/path/to/LICENSE
<!-- Now you know the file is missing! -->
```

### 2. Encoding Issues Detected

**Before:**
```python
{{ read_file('binary.pdf') }}
# Returns empty string silently
```

**After:**
```
❌ file_encoding_error path=binary.pdf 
   message="File contains invalid UTF-8 characters"
   suggestion="File may be binary or use a different encoding"
```

### 3. Permission Issues Visible

**Before:**
```python
{{ read_file('protected.txt') }}
# Empty string, no clue why
```

**After:**
```
❌ file_read_error path=protected.txt 
   error="Permission denied"
   error_type="IOError"
```

## Event Names

Consistent naming following established patterns:

- `file_not_found` - File doesn't exist
- `path_not_file` - Path exists but isn't a file (directory, symlink, etc.)
- `file_read` - Successful file read
- `file_read_error` - IOError during read
- `file_encoding_error` - UTF-8 decoding failed
- `file_size_computed` - Successful size computation
- `file_stat_error` - Error getting file stats

## Testing

✅ **Build Test:** Showcase example builds successfully  
✅ **No Linter Errors:** All files pass linting  
✅ **Backward Compatible:** No breaking changes to API  

```bash
cd examples/showcase
bengal build
# ✨ Built 198 pages in 0.9s
```

## Summary of All Template Function Logging

We've now added logging to all template functions with I/O operations:

| Module | Functions with Logging | Type | Status |
|--------|----------------------|------|--------|
| `data.py` | `get_data()` | JSON/YAML loading | ✅ Done |
| `images.py` | `image_dimensions()`, `image_data_uri()` | Image file I/O | ✅ Done |
| `crossref.py` | `doc()`, `ref()` | Cross-reference lookups | ✅ Done |
| `taxonomies.py` | `popular_tags()`, `related_posts()` | Taxonomy operations | ✅ Done |
| **`files.py`** | `read_file()`, `file_size()` | File system I/O | ✅ Done |

### Functions WITHOUT Logging (Intentional)

Pure functions with no I/O or failure modes:
- `strings.py` - String manipulation
- `collections.py` - List/dict operations  
- `math_functions.py` - Math operations
- `dates.py` - Date formatting
- `urls.py` - URL generation
- `seo.py` - Meta tag generation
- `content.py` - HTML manipulation
- `debug.py` - Debug helpers
- `pagination_helpers.py` - Pagination math
- `advanced_strings.py` - Advanced string operations
- `advanced_collections.py` - Advanced collection operations

These don't need logging because they:
1. Don't perform I/O
2. Don't have silent failure modes
3. Raise exceptions appropriately when they fail
4. Are simple, deterministic transformations

## Files Modified

1. `bengal/rendering/template_functions/files.py` - Added comprehensive logging

## Complete Observability Coverage

Template functions now have **complete observability coverage** for all I/O operations:

✅ File system operations (`files.py`, `data.py`, `images.py`)  
✅ Cross-reference lookups (`crossref.py`)  
✅ Taxonomy operations (`taxonomies.py`)  
✅ All silent failures now log warnings or errors  
✅ All successful operations log debug events  
✅ Consistent with rest of codebase logging patterns  

---

**Template function observability is now complete!** 🎉

