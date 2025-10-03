# _index.md Page Rendering Fix

**Date**: October 3, 2025  
**Status**: ✅ Complete

## Problem Summary

Pages like `api/v2/` and `api/` in the example site were experiencing three critical issues:

1. **Missing CSS**: Pages were using a fallback template instead of the proper template
2. **Wrong Output Path**: `_index.md` files were being rendered to `_index/index.html` instead of `index.html`
3. **Incorrect Canonical URLs**: URLs showed `/v2/` instead of `/api/v2/`

## Root Causes

### Issue 1: Output Path Generation
**Location**: `bengal/rendering/pipeline.py:124`

The `_determine_output_path()` method checked if `stem != "index"` to apply pretty URLs, but `_index.md` has stem `_index`, not `index`. This caused:
- `api/v2/_index.md` → `public/api/v2/_index/index.html` ❌
- Should be: `api/v2/_index.md` → `public/api/v2/index.html` ✅

### Issue 2: Template Selection
**Location**: `bengal/rendering/renderer.py:192`

The `_get_template_name()` method didn't recognize `_index.md` files as section index pages, so they defaulted to `page.html` instead of `index.html`. Without explicit `type: index` in frontmatter, the fallback template was used.

### Issue 3: URL Calculation Timing
**Location**: `bengal/rendering/pipeline.py:42`

The `output_path` was set AFTER template rendering in `_write_output()`. When templates tried to generate canonical URLs via `page.url`, the `output_path` was None, causing fallback to slug-based URLs which were incorrect for nested `_index.md` files.

## Solutions Implemented

### Fix 1: Output Path Handling for _index.md
**File**: `bengal/rendering/pipeline.py`

```python
# Handle index pages specially (index.md and _index.md → index.html)
# Others can optionally use pretty URLs (about.md → about/index.html)
if self.site.config.get("pretty_urls", True) and output_rel_path.stem not in ("index", "_index"):
    output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
elif output_rel_path.stem == "_index":
    # _index.md should become index.html in the same directory
    output_rel_path = output_rel_path.parent / "index.html"
```

### Fix 2: Template Selection for _index.md
**File**: `bengal/rendering/renderer.py`

```python
def _get_template_name(self, page: Page) -> str:
    # Check page metadata for custom template
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # Check if this is an _index.md file (section index)
    if page.source_path.stem == '_index':
        # Use index template for section index pages
        return 'index.html'
    
    # ... rest of template selection logic
```

### Fix 3: Set Output Path Before Rendering
**File**: `bengal/rendering/pipeline.py`

```python
def process_page(self, page: Page) -> None:
    # Stage 0: Determine output path early so page.url works correctly
    if not page.output_path:
        page.output_path = self._determine_output_path(page)
    
    # ... then proceed with content preprocessing and template rendering
```

### Fix 4: Improved Slug Property
**File**: `bengal/core/page.py`

```python
@property
def slug(self) -> str:
    # Check metadata first
    if "slug" in self.metadata:
        return self.metadata["slug"]
    
    # Special handling for _index.md files
    if self.source_path.stem == "_index":
        # Use the parent directory name as the slug
        return self.source_path.parent.name
    
    return self.source_path.stem
```

### Bonus: Created Missing Index Page
**File**: `examples/quickstart/content/api/_index.md`

Created a missing `_index.md` for the `/api/` section so it has a proper landing page.

## Results

### Before
- ❌ `api/v2/_index/index.html` - Wrong path
- ❌ No CSS (fallback template)
- ❌ Canonical URL: `https://example.com/v2/`
- ❌ No `/api/` landing page

### After
- ✅ `api/v2/index.html` - Correct path
- ✅ Full CSS and proper template (`index.html`)
- ✅ Canonical URL: `https://example.com/api/v2/`
- ✅ Proper `/api/` landing page
- ✅ Full navigation, header, footer
- ✅ Theme toggle and mobile navigation

## Testing

```bash
# Clean build
cd examples/quickstart
rm -rf public
python -m bengal.cli build .

# Verify structure
ls -la public/api/          # Should show index.html
ls -la public/api/v2/       # Should show index.html

# Verify canonical URLs
grep canonical public/api/index.html      # Should be /api/
grep canonical public/api/v2/index.html   # Should be /api/v2/

# Verify CSS
grep stylesheet public/api/v2/index.html  # Should include style.css
```

## Impact

- **All `_index.md` files** now render correctly as section index pages
- **Nested sections** (e.g., `api/v2/`, `docs/guides/`) work properly
- **SEO improved** with correct canonical URLs
- **Consistent styling** across all page types
- **No breaking changes** - existing sites continue to work

## Files Modified

1. `bengal/rendering/pipeline.py` - Output path and processing order
2. `bengal/rendering/renderer.py` - Template selection logic
3. `bengal/core/page.py` - Slug property improvement
4. `examples/quickstart/content/api/_index.md` - New example file

## Related Issues

This fix addresses the core pattern for section index pages, similar to Hugo's `_index.md` convention. It ensures that:
- Section landing pages render properly
- Multi-level navigation works correctly
- URLs are clean and SEO-friendly

