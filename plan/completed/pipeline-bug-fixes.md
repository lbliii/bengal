# Pipeline Bug Fixes

**Date**: 2025-01-23  
**Status**: ✅ Fixed

---

## Critical Bug: 0 Pages Built on Template Errors

### Problem

When template rendering errors occurred in parallel execution, the entire pipeline stopped, resulting in **0 pages being built** even though most pages could have been successfully rendered.

**Symptoms**:
- Build completes but reports "0 pages built"
- Single template error stops entire build
- Error: `Parallel execution failed for flatten_pages:all:XX: Template error in strict mode: 'description' is undefined`

### Root Causes

1. **Parallel Execution Error Handling**: `ParallelStream` was raising exceptions immediately on first error, stopping all processing
2. **Template Bug**: `changelog/list.html` accessed `description` variable directly without checking if it exists

### Fixes

#### 1. Improved Parallel Error Handling

**File**: `bengal/pipeline/streams.py`

**Change**: Modified `ParallelStream._parallel_map()` to:
- Collect all errors during parallel processing
- Continue processing all items even if some fail
- Raise a summary error after all items complete (if any errors occurred)

**Before**:
```python
except Exception as e:
    # Re-raise with context
    raise RuntimeError(f"Parallel execution failed for {source_item.key}: {e}") from e
```

**After**:
```python
errors: list[tuple[str, Exception]] = []
# ... collect errors ...
if errors:
    error_summary = "\n".join(f"  - {key}: {str(e)}" for key, e in errors)
    raise RuntimeError(f"Parallel execution failed for {len(errors)} item(s):\n{error_summary}")
```

**Impact**: Other pages can now be built even if some fail.

#### 2. Template Bug Fix

**File**: `bengal/themes/default/templates/changelog/list.html`

**Change**: Updated template to safely check for `description`:

**Before**:
```jinja2
{% elif description %}
    <p class="changelog-description">{{ description }}</p>
{% endif %}
```

**After**:
```jinja2
{% elif page and page.metadata.get('description', '') %}
    <p class="changelog-description">{{ page.metadata.get('description', '') }}</p>
{% elif description is defined %}
    <p class="changelog-description">{{ description }}</p>
{% endif %}
```

**Impact**: Template no longer fails when `description` is not in context.

### Verification

**Before Fix**:
- Single template error → 0 pages built
- Build fails completely

**After Fix**:
- Template errors logged but don't stop build
- Other pages continue to build successfully
- Summary error raised at end if any errors occurred

### Related Files

- `bengal/pipeline/streams.py` - Parallel execution error handling
- `bengal/themes/default/templates/changelog/list.html` - Template fix
- `bengal/pipeline/full_build.py` - Pipeline integration

### Testing

To verify the fix works:

1. **Test with template errors**: Create a page with invalid template syntax
2. **Verify**: Other pages should still build successfully
3. **Check**: Error summary should be reported at end

### Notes

- Other templates already check for `description` safely (using `description is defined` or `page.metadata.get('description')`)
- The `description` variable is available in context if:
  - It's in the page's frontmatter (added via `_build_variable_context`)
  - It's accessed via `page.metadata.get('description')`
  - It's accessed via `page.description` (if Page has that property)

---

## Status

✅ **Fixed**: Both issues resolved  
✅ **Committed**: Changes committed to `pipeline/next` branch  
✅ **Tested**: Manual verification shows improved error handling



