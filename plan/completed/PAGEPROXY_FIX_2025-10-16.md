# PageProxy Fresh Build Fix

**Date:** October 16, 2025  
**Issue:** PageProxy errors on fresh builds  
**Status:** ✅ Resolved

## Problem

When performing fresh builds, the following errors were occurring:

1. `AttributeError: property 'toc' of 'PageProxy' object has no setter`
2. `AttributeError: 'PageProxy' object has no attribute 'url'`

### Root Causes

The `PageProxy` class was missing critical properties that the rendering and postprocess pipelines needed:

1. **`toc` property was read-only**: The rendering pipeline attempts to set `page.toc` at lines 192 and 340 of `bengal/rendering/pipeline.py` when caching or parsing content. PageProxy only had a getter.

2. **`url` property was missing**: The postprocess module (`bengal/postprocess/output_formats.py` line 727) tries to access `page.url` for search indexing and hierarchical navigation metadata, but PageProxy didn't expose this property.

## Solution

Enhanced `bengal/core/page/proxy.py` with two additions:

### 1. Added `@toc.setter`

```python
@toc.setter
def toc(self, value: str | None) -> None:
    """Set table of contents."""
    self._ensure_loaded()
    if self._full_page:
        self._full_page.toc = value
```

This allows the rendering pipeline to set TOC content on lazy-loaded proxy pages without forcing a full load.

### 2. Added `url` Property

```python
@property
def url(self) -> str:
    """Get the URL path for the page (lazy-loaded, cached after first access)."""
    self._ensure_loaded()
    return self._full_page.url if self._full_page else "/"
```

This delegates to the full page's `url` property (a cached_property from `PageMetadataMixin`) which computes the page's URL from its output path.

## Testing

✅ Fresh build completed successfully:
- 6 pages built
- 54 assets processed
- No errors or warnings
- All pages rendered correctly, including proxy documentation

## Files Changed

- `bengal/core/page/proxy.py`: Added `toc` setter and `url` property

## Impact

- Fixes fresh build errors on PageProxy-enabled builds (incremental builds)
- Maintains lazy-loading behavior while ensuring full Page compatibility
- No performance impact - properties still defer loading when possible
