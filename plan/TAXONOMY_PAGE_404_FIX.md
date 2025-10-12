# Taxonomy Page 404 Fix

**Date**: 2025-10-12
**Status**: ✅ Fixed

## Problem

Taxonomy tag pages (e.g., `/tags/functions/`) were showing 404 errors in the dev server, even though tag counts were displaying correctly in widgets.

## Root Cause

The dev server's incremental rebuild had a critical flaw:

1. **Server clears all pages**: On each rebuild, `site.pages = []` is cleared (including generated taxonomy pages)
2. **Early exit logic**: If no content changed, build would exit early or skip taxonomy generation
3. **Missing pages**: Taxonomy pages were never regenerated, leading to 404s

### Code Flow Issue

```python
# BuildHandler._clear_ephemeral_state()
self.site.pages = []  # Clears ALL pages including generated ones

# BuildOrchestrator.build()
if not pages_to_build and not assets_to_process:
    return  # Exit early - taxonomy pages never regenerated!

# OR later in taxonomy phase:
if incremental and pages_to_build:
    # Only runs if pages changed
    self.taxonomy.collect_and_generate_incremental(...)
# else: No pages changed, skip taxonomy updates
```

The issue: **No content changed → Early exit → Taxonomy pages cleared but not regenerated → 404**

## Solution

The fix required 5 changes across 2 files to ensure taxonomy pages are:
1. Generated even when no content changes (dev server case)
2. Added to the rendering queue so they're actually written to disk

### 1. Prevent Early Exit When Taxonomies Exist

**File**: `bengal/orchestration/build.py` (lines 274-284)

```python
# Check if we need to regenerate taxonomy pages
# (This happens in dev server when site.pages is cleared but content hasn't changed)
# If cache has tags, we need to regenerate taxonomy pages even if no content changed
needs_taxonomy_regen = bool(cache.get_all_tags())

if not pages_to_build and not assets_to_process and not needs_taxonomy_regen:
    # Only exit early if we truly have nothing to do
    return
```

### 2. Handle Empty Changed Pages List

**File**: `bengal/orchestration/build.py` (lines 349-356)

Added branch to handle incremental builds with no content changes:

```python
elif incremental and not pages_to_build:
    # Incremental but no pages changed: Still need to regenerate taxonomy pages
    # because site.pages was cleared (dev server case)
    affected_tags = self.taxonomy.collect_and_generate_incremental([], cache)
    self.site._affected_tags = affected_tags
```

### 3. Set affected_tags for Full Builds

**File**: `bengal/orchestration/build.py` (lines 362-364)

Ensure `affected_tags` is set for full builds so Phase 6 knows to add taxonomy pages:

```python
# Mark all tags as affected (for Phase 6 - adding to pages_to_build)
if hasattr(self.site, "taxonomies") and "tags" in self.site.taxonomies:
    affected_tags = set(self.site.taxonomies["tags"].keys())
```

### 4. Add Generated Pages to Render Queue

**File**: `bengal/orchestration/build.py` (lines 420-445)

**THE CRITICAL FIX**: After generating taxonomy pages, add them to `pages_to_build` so they actually get rendered:

```python
# Phase 6: Update filtered pages list (add generated pages)
if affected_tags:
    pages_to_build_set = set(pages_to_build) if pages_to_build else set()

    # Add newly generated tag pages to rebuild set
    for page in self.site.pages:
        if page.metadata.get("_generated") and page.metadata.get("type") in ("tag", "tag-index"):
            tag_slug = page.metadata.get("_tag_slug")
            should_include = (
                not incremental or  # Full build: include all
                page.metadata.get("type") == "tag-index" or  # Always include tag index
                tag_slug in affected_tags  # Include affected tag pages
            )

            if should_include:
                pages_to_build_set.add(page)

    pages_to_build = list(pages_to_build_set)
```

### 5. Generate All Tag Pages When No Content Changed

**File**: `bengal/orchestration/taxonomy.py` (lines 97-116)

Modified `collect_and_generate_incremental()` to handle empty `changed_pages`:

```python
# STEP 3: Generate tag pages
# Special case: If no pages changed but we have tags, regenerate ALL tag pages
if not changed_pages and self.site.taxonomies.get("tags"):
    all_tags = set(self.site.taxonomies["tags"].keys())
    self.generate_dynamic_pages_for_tags(all_tags)
    affected_tags = all_tags
elif affected_tags:
    # Normal case: Only regenerate affected tag pages
    self.generate_dynamic_pages_for_tags(affected_tags)
```

## Root Cause (Updated)

There were actually **THREE bugs**:

1. **Generation Bug**: Taxonomy pages weren't being generated when no content changed (fixed in first attempt)
2. **Rendering Bug**: Generated taxonomy pages weren't being added to `pages_to_build`, so they were never passed to the renderer!
3. **i18n Bug** (THE ROOT CAUSE): The incremental taxonomy generation method didn't support i18n, so it wasn't generating locale-specific tag pages!

The build process works like this:
```
Phase 2: Determine pages_to_build (filtering)
Phase 3: Generate section archives → added to site.pages
Phase 4: Generate taxonomy pages → added to site.pages
Phase 6: Add generated pages to pages_to_build ← THIS WAS BROKEN
Phase 8: Render pages in pages_to_build
```

The Phase 6 code existed but had bugs:
- Only ran when `incremental and affected_tags`
- Didn't set `affected_tags` for full builds
- Didn't work when `pages_to_build` was empty

**The i18n Bug**: The showcase site has i18n enabled (`strategy = "prefix"` with English and French). The full build method `generate_dynamic_pages()` has i18n support and generates tag pages like `/en/tags/advanced/` and `/fr/tags/advanced/`. However, the incremental method `generate_dynamic_pages_for_tags()` did NOT have i18n support - it only used the simple non-i18n page creation methods. So incremental builds (dev server) were generating `/tags/advanced/` instead of `/en/tags/advanced/`, causing 404s!

## Changes Made

### `bengal/orchestration/build.py`

1. **Lines 274-284**: Added check for `needs_taxonomy_regen` to prevent early exit when taxonomy pages need regeneration
2. **Lines 349-356**: Added branch to handle incremental builds with no changed pages
3. **Lines 362-364**: Set `affected_tags` for full builds so Phase 6 runs
4. **Lines 420-445**: Fixed Phase 6 logic to properly add all generated taxonomy pages to `pages_to_build`

### `bengal/orchestration/taxonomy.py`

1. **Lines 97-116**: Modified to regenerate all taxonomy pages when no content changed but taxonomies exist in cache
2. **Lines 237-322**: Added i18n support to `generate_dynamic_pages_for_tags()` to match `generate_dynamic_pages()` - now generates per-locale tag pages correctly in incremental builds

## Testing

To verify the fix:

1. **Restart dev server** (changes require restart):
   ```bash
   # Stop server (Ctrl+C)
   cd examples/showcase
   bengal serve
   ```

2. Navigate to tag pages (with i18n prefix):
   - `http://localhost:5173/en/tags/advanced/` ← Should work now!
   - `http://localhost:5173/en/tags/functions/` ← Should work now!
   - `http://localhost:5173/en/tags/` ← Tag index should work
   - `http://localhost:5173/fr/tags/` ← French tag index

3. Tag counts in widgets should continue to work
4. Modify a content file and verify incremental rebuild still works
5. Check that tag HTML files exist in `public/en/tags/` and `public/fr/tags/`

## Impact

- **Dev Server**: Taxonomy pages now regenerate correctly on every rebuild
- **Performance**: Minimal impact - only regenerates taxonomy pages when needed
- **Incremental Builds**: Still optimized - only regenerates affected tags when content changes
- **Full Builds**: No change - continues to work as before

## Future Considerations

The root issue is that `site.pages` is cleared on every dev server rebuild. A more architectural solution would be to:

1. Preserve generated pages across rebuilds
2. Only regenerate them when their source data (tags, sections) changes
3. This would make incremental builds even faster

However, the current fix is simple, effective, and maintains the existing architecture.
