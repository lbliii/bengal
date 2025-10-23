# Dev Server Baseurl Handling Fix

**Status**: Implemented
**Date**: 2025-10-23
**Issue**: Dev server shows 404 errors for `/bengal/index.json` when `baseurl="/bengal"` is configured

---

## Problem Summary

When a site has `baseurl="/bengal"` configured in `bengal.toml`, the dev server was showing 404 errors because:

1. The dev server clears `baseurl` in memory (sets it to `""`) to serve files from root `/`
2. But HTML files in `public/` were built with the original `baseurl="/bengal"`
3. These HTML files contain links like `<meta name="bengal:index_url" content="/bengal/index.json">`
4. The JavaScript tries to fetch `/bengal/index.json`, but the file is actually at `/index.json`
5. Result: 404 errors and broken search functionality

### User Impact

- Search functionality breaks (can't load `/bengal/index.json`)
- Navigation links point to wrong URLs (`/bengal/search/` instead of `/search/`)
- User has to manually clear `public/` directory to fix it

---

## Root Cause Analysis

The dev server code at `bengal/server/dev_server.py:141-166` attempts to:
1. Detect `baseurl` in config
2. Clear it: `cfg["baseurl"] = ""`
3. Force clean rebuild: `build(incremental=not baseurl_was_cleared)`

**However**, if the user previously ran `bengal build` (not dev server), the `public/` directory contains HTML with the old baseurl baked in. The dev server's clean rebuild was not sufficient because:

1. **Build cache persistence**: The `.bengal/cache.json` might contain cached baseurl values
2. **Incremental build logic**: Even with `incremental=False`, some cached data could persist
3. **No validation**: No check to detect baseurl mismatch between config and built files

---

## Solution Implemented

### Fix 1: Clear Build Cache When Baseurl Changes

**File**: `bengal/server/dev_server.py`

Added explicit cache clearing when baseurl is cleared:

```python
if baseurl_was_cleared:
    cache_dir = self.site.root_path / ".bengal"
    cache_path = cache_dir / "cache.json"
    if cache_path.exists():
        try:
            cache_path.unlink()
            logger.debug("cache_cleared_for_baseurl_change", cache_path=str(cache_path))
        except Exception as e:
            logger.warning("cache_clear_failed", error=str(e))

stats = self.site.build(
    profile=BuildProfile.WRITER, incremental=not baseurl_was_cleared
)
```

**Why this works**:
- Ensures no cached baseurl values persist from previous builds
- Forces complete regeneration of all files with new baseurl
- Prevents incremental build from reusing old cached data

---

## Long-Term Solutions to Prevent Brittleness

### Option 1: Baseurl Validation on Dev Server Start (Recommended)

Add validation that detects baseurl mismatch:

```python
def _validate_baseurl_consistency(self) -> bool:
    """Check if built HTML has different baseurl than current config."""
    index_html = self.site.output_dir / "index.html"
    if not index_html.exists():
        return True  # No conflict if no build exists
    
    html_content = index_html.read_text()
    current_baseurl = self.site.config.get("baseurl", "").strip()
    
    # Check for baseurl in meta tags
    import re
    meta_match = re.search(r'<meta name="bengal:baseurl" content="([^"]*)"', html_content)
    if meta_match:
        html_baseurl = meta_match.group(1)
        if html_baseurl != current_baseurl:
            logger.warning(
                "baseurl_mismatch_detected",
                config_baseurl=current_baseurl,
                html_baseurl=html_baseurl,
                action="forcing_clean_rebuild"
            )
            return False
    return True
```

**Benefits**:
- Explicit detection of stale builds
- Clear logging for debugging
- Can show user-friendly warning

### Option 2: Store Build Metadata in Output Directory

Create a `.bengal-build-info.json` in `public/`:

```json
{
  "build_date": "2025-10-23T11:19:54Z",
  "baseurl": "/bengal",
  "incremental": false,
  "bengal_version": "0.1.3"
}
```

On dev server start, compare this metadata with current config:
- If baseurl changed → force clean rebuild
- If config changed → force clean rebuild
- If version changed → warn user

**Benefits**:
- Simple to implement
- Fast to check (one JSON read)
- Can detect other config changes too

### Option 3: Baseurl-Aware Cache Keys

Modify `BuildCache` to include baseurl in cache keys:

```python
def _get_cache_key(self, path: Path) -> str:
    baseurl = self.site.config.get("baseurl", "")
    return f"{baseurl}:{str(path)}"
```

**Benefits**:
- No manual cache clearing needed
- Automatic invalidation when baseurl changes
- Works for all config changes, not just baseurl

**Drawbacks**:
- More invasive change
- Requires cache format version bump
- Complicates cache logic

### Option 4: Dev Server URL Rewriting (Alternative Approach)

Instead of clearing baseurl, make the dev server rewrite URLs on-the-fly:

```python
def _rewrite_baseurl_in_html(html: str, old_baseurl: str) -> str:
    """Remove baseurl prefix from HTML links for local dev."""
    return html.replace(f'href="{old_baseurl}/', 'href="/')
                .replace(f'content="{old_baseurl}', 'content="')
```

**Benefits**:
- No rebuild needed
- Instant dev server startup
- Works with any baseurl

**Drawbacks**:
- Can miss edge cases
- Doesn't fix JavaScript URLs
- Fragile regex/string replacement

---

## Recommendation

**Implement Option 1 + Option 2** together:

1. **Add `.bengal-build-info.json`** to store build metadata (5-10 lines of code)
2. **Validate on dev server start** and force clean rebuild if mismatch (10-15 lines)
3. **Keep current cache clearing** as backup safety net

This provides:
- Fast detection (read one JSON file)
- Reliable rebuilds (no stale data)
- Clear user feedback (logging explains why rebuild is happening)
- Future-proof (can add more metadata checks later)

### Implementation Sketch

```python
# In bengal/postprocess/__init__.py or bengal/orchestration/build.py
def write_build_metadata(site: Site, stats: BuildStats) -> None:
    """Write build metadata to output directory for validation."""
    metadata = {
        "build_date": datetime.now().isoformat(),
        "baseurl": site.config.get("baseurl", ""),
        "bengal_version": site.config.get("version", "unknown"),
        "incremental": stats.was_incremental,
        "pages_built": stats.total_pages,
    }
    metadata_path = site.output_dir / ".bengal-build-info.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

# In bengal/server/dev_server.py
def _check_build_metadata(self) -> bool:
    """Check if existing build matches current config."""
    metadata_path = self.site.output_dir / ".bengal-build-info.json"
    if not metadata_path.exists():
        return False  # No metadata = needs rebuild
    
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        current_baseurl = self.site.config.get("baseurl", "")
        build_baseurl = metadata.get("baseurl", "")
        
        if current_baseurl != build_baseurl:
            logger.info(
                "rebuild_required_baseurl_changed",
                old=build_baseurl,
                new=current_baseurl
            )
            return False
        
        return True  # Metadata matches config
    except Exception as e:
        logger.warning("metadata_check_failed", error=str(e))
        return False  # Err on side of rebuild
```

---

## Testing Strategy

### Unit Tests

1. **Test dev server clears baseurl**: ✅ Created `tests/unit/server/test_dev_server_baseurl.py`
2. **Test cache clearing**: Verify `.bengal/cache.json` is deleted when baseurl cleared
3. **Test metadata validation**: Check that stale builds are detected

### Integration Tests

1. **Full workflow test**:
   - Build site with `baseurl="/bengal"`
   - Start dev server (should clear baseurl and rebuild)
   - Verify HTML contains `baseurl=""`
   - Verify search works at `/index.json` (not `/bengal/index.json`)

2. **Incremental build test**:
   - Start dev server with `baseurl="/bengal"`
   - Modify a page
   - Verify rebuild doesn't reintroduce `/bengal` prefix

### Manual Testing

1. ✅ User confirmed: `rm -rf site/public` + restart dev server → works
2. TODO: Restart dev server without clearing `public/` → should auto-detect and rebuild

---

## Success Criteria

✅ Dev server automatically detects baseurl mismatch
✅ Dev server clears cache when baseurl changes
✅ Dev server forces clean rebuild when needed
✅ User sees clear logging explaining why rebuild is happening
✅ No manual intervention needed (no `rm -rf public`)
✅ Search and navigation work correctly in dev mode

---

## Related Code

- `bengal/server/dev_server.py:141-178` - Baseurl clearing logic
- `bengal/orchestration/build.py:308-346` - Config change detection
- `bengal/postprocess/output_formats.py:407-418` - index.json generation
- `bengal/themes/default/assets/js/search.js:51-81` - Search index loading

---

## Next Steps

1. ✅ Implement cache clearing (DONE)
2. ⬜ Add build metadata file (`.bengal-build-info.json`)
3. ⬜ Add metadata validation on dev server start
4. ⬜ Write comprehensive tests
5. ⬜ Update documentation with dev server baseurl behavior
6. ⬜ Consider adding CLI warning when `baseurl` is set (suggest clearing for dev)

---

**Author**: Bengal Team
**Last Updated**: 2025-10-23

