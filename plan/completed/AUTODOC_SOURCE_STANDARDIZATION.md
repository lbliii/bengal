# Autodoc Source Metadata Standardization

**Date:** 2025-10-12  
**Status:** ✅ Complete

## Problem

Source file metadata was inconsistent and user-unfriendly across autodoc:

1. **CLI docs**: Source shown at bottom as italic text with absolute paths
   - `*Source: /Users/llane/Documents/github/python/bengal/bengal/cli/commands/build.py:162*`

2. **API docs**: Source in frontmatter but as relative path
   - `source_file: "../../bengal/analysis/graph_visualizer.py"`

3. **Display inconsistency**: API template had nice `.api-meta` box, CLI didn't use it

4. **Path format**: Neither format was user-friendly - end users don't want to see filesystem implementation details

## Solution

Standardized source metadata across all autodoc types:

1. **Project-relative paths**: All paths now shown as `bengal/core/site.py:45`
2. **Frontmatter storage**: Both CLI and API store source in frontmatter
3. **Unified display**: Both use the `.api-meta` box styling
4. **Path normalization filter**: Added `project_relative` Jinja filter to autodoc generator

## Changes Made

### 1. Added Path Normalization Filter

**File:** `bengal/autodoc/generator.py`

```python
def _make_path_project_relative(self, path: Path | str | None) -> str:
    """
    Convert absolute or relative path to project-relative format.

    Returns: Project-relative path string (e.g., 'bengal/core/site.py')
    """
    # Try relative to CWD (project root)
    # Fall back to finding common root indicators (bengal, src, lib, etc.)
```

Registered as Jinja filter: `env.filters["project_relative"]`

### 2. Updated CLI Autodoc Template

**File:** `bengal/autodoc/templates/cli/command.md.jinja2`

- **Moved source to frontmatter** (was at bottom)
- **Applied filter**: `source_file: "{{ element.source_file | project_relative }}"`
- **Added source_line**: Separate field for better display control

### 3. Updated Python Autodoc Template

**File:** `bengal/autodoc/templates/python/module.md.jinja2`

- **Applied filter**: `source_file: "{{ element.source_file | project_relative }}"`
- Now generates clean paths like `bengal/core/site.py`

### 4. Updated CLI Reference Template

**File:** `bengal/themes/default/templates/cli-reference/single.html`

- **Added `.api-meta` box** to display source (matching API template)
- Shows: `Source: bengal/cli/commands/build.py:162`

### 5. API Reference Template (no changes needed)

**File:** `bengal/themes/default/templates/api-reference/single.html`

- Already had the `.api-meta` box
- Now gets clean paths from the filter

## Results

### Before

**API docs:**
```html
<div class="api-meta">
  <div class="api-meta-item">
    <strong>Source:</strong>
    <code>../../bengal/analysis/graph_visualizer.py</code>
  </div>
</div>
```

**CLI docs:**
```markdown
---

*Source: /Users/llane/Documents/github/python/bengal/bengal/cli/commands/build.py:162*
```

### After

**Both API and CLI docs:**
```html
<div class="api-meta">
  <div class="api-meta-item">
    <strong>Source:</strong>
    <code>bengal/cli/commands/build.py:162</code>
  </div>
</div>
```

## Benefits

1. **User-friendly paths**: `bengal/core/site.py` instead of `../../` or absolute paths
2. **Consistent display**: Both API and CLI use the same styling
3. **Better metadata**: Source and line number separated for flexibility
4. **Maintainable**: Single filter handles all path normalization
5. **Extensible**: Other autodoc types (OpenAPI, etc.) can use the same filter

## Testing

✅ All tests pass (30 passed, 2 skipped)  
✅ No linter errors  
✅ Filter handles absolute, relative, and various path formats

## Future Enhancements

- Add GitHub/GitLab links to source (if repo URL configured)
- Support custom path display formats
- Add hover tooltips with full absolute path
