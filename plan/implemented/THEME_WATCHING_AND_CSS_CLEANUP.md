# Theme Watching and CSS Cleanup

**Date**: 2025-10-08  
**Status**: ✅ Complete

## Changes Made

### 1. Dev Server Now Watches Theme Changes

**Problem**: The dev server wasn't watching theme directories for changes, requiring manual rebuilds when editing templates, CSS, or JS files in themes.

**Solution**: Updated `bengal/server/dev_server.py` to watch both:
- **Project-level themes**: `{site_root}/themes/{theme_name}/`
- **Bundled themes**: `bengal/themes/default/` (for Bengal development)

**Impact**: Now when developing themes (either custom or the default theme), changes trigger automatic rebuilds with hot reload.

### 2. Extracted Inline CSS from docs-nav Partial

**Problem**: The `docs-nav.html` partial had 120+ lines of inline CSS in a `<style>` block, which:
- Can't be cached by browsers
- Duplicates on every page load
- Violates separation of concerns
- Makes templates harder to maintain

**Solution**: 
1. Created new file: `bengal/themes/default/assets/css/components/docs-nav.css`
2. Moved all docs navigation styles to the new CSS file
3. Added import to `style.css`: `@import url('components/docs-nav.css');`
4. Removed inline `<style>` block from `docs-nav.html`

**Impact**: 
- Better browser caching
- Cleaner template code
- Follows established CSS architecture
- Reduced page weight

## Files Modified

- `bengal/server/dev_server.py` - Added theme directory watching
- `bengal/themes/default/templates/partials/docs-nav.html` - Removed inline styles
- `bengal/themes/default/assets/css/style.css` - Added docs-nav.css import

## Files Created

- `bengal/themes/default/assets/css/components/docs-nav.css` - New component stylesheet

## Testing

Both changes work seamlessly with the existing dev server and CSS bundling pipeline. No breaking changes.

