# Improved Error Messaging

## Changes Made

### 1. **Config Change Detection** - Clearer Messages

**Before**:
```
Config file changed - performing full rebuild
```

**After**:
```
# First incremental build:
Config not in cache - performing full rebuild
(This is normal for the first incremental build)

# Actual config change:
Config file modified - performing full rebuild
Changed: bengal.toml
```

**Why**: Users know if it's expected (first build) vs actual change.

---

### 2. **Incremental Build Status** - More Informative

**Before**:
```
Incremental build: 1 pages, 0 assets
```

**After**:
```
Incremental build: 1 page, 0 assets (skipped 999 cached)
Changed: 1 modified pages
```

**Why**: Shows how much work was skipped (validates incremental is working).

---

### 3. **No Changes Detected** - Celebratory

**Before**:
```
No changes detected - skipping build
```

**After**:
```
✓ No changes detected - build skipped
  Cached: 1000 pages, 50 assets
```

**Why**: Positive reinforcement that caching is working.

---

### 4. **Config First-Time Detection** - Internal Logging

**Before**:
```python
if changed:
    logger.info("config_changed", config_file=config_file.name)
```

**After**:
```python
if changed:
    if is_new:
        logger.info("config_not_cached",
                   config_file=config_file.name,
                   reason="first_build_or_cache_cleared")
    else:
        logger.info("config_changed",
                   config_file=config_file.name,
                   reason="content_modified")
```

**Why**: Logs distinguish between first-time vs actual change.

---

### 5. **Related Posts Skip** - Explanation

**Before**:
```python
logger.info("related_posts_skipped", reason="large_site_or_no_tags")
```

**After**:
```python
logger.info("related_posts_skipped",
           reason="large_site_or_no_tags",
           page_count=len(self.site.pages),
           threshold=5000)
logger.debug("related_posts_skip_detail",
            message=f"Skipped related posts for performance (site has {page_count} pages, threshold is 5000)")
```

**Why**: Users understand why feature was skipped and what the threshold is.

---

## Example User Experience

### First Build (Full)
```bash
$ bengal build
✓ Discovery     Done
✓ Assets        Done
✓ Rendering     Done
✓ Post-process  Done

Built 1000 pages in 5.69s
```

### Second Build (Incremental, No Changes)
```bash
$ bengal build --incremental
✓ No changes detected - build skipped
  Cached: 1000 pages, 50 assets
```

### Third Build (Incremental, 1 Change)
```bash
$ bengal build --incremental
  Incremental build: 1 page, 0 assets (skipped 999 cached)
  Changed: 1 modified pages

✓ Discovery     Done
✓ Assets        Done
✓ Rendering     Done
✓ Post-process  Done

Built in 0.76s (was 5.69s - 7.5x faster)
```

### Fourth Build (Config Changed)
```bash
$ bengal build --incremental
  Config file modified - performing full rebuild
  Changed: bengal.toml

✓ Discovery     Done
✓ Assets        Done
✓ Rendering     Done
✓ Post-process  Done

Built 1000 pages in 5.71s
```

### Large Site (Related Posts Skipped)
```bash
$ bengal build
  Related posts skipped (10000 pages > 5000 threshold)

✓ Discovery     Done
✓ Assets        Done
✓ Rendering     Done
✓ Post-process  Done

Built 10000 pages in 125s
```

---

## Benefits

1. **Users understand what's happening**
   - "Config not in cache" vs "Config changed"
   - "Skipped 999 cached" shows incremental working

2. **Debugging is easier**
   - Logs distinguish first-time vs actual changes
   - Structured logging with reason codes

3. **Performance transparency**
   - Shows why related posts was skipped
   - Shows exact threshold (5000 pages)

4. **Positive feedback**
   - "✓ No changes detected" feels good
   - Shows time saved ("was 5.69s - 7.5x faster")

---

## Future Improvements

### Add Build Speed Comparison
```bash
Built in 0.76s (7.5x faster than full build)
```

### Add --verbose Details
```bash
$ bengal build --incremental --verbose
  Incremental build: 1 page, 0 assets (skipped 999 cached)
  Changed files:
    • Modified pages: content/post.md
    • Template changes: 0
    • Asset changes: 0
```

### Add Cache Statistics
```bash
$ bengal build --incremental
  Cache hit rate: 99.9% (999/1000 pages)
  Incremental build: 1 page, 0 assets
```

### Add Performance Hints
```bash
$ bengal build
  ⚠ Site has 12000 pages - consider enabling memory_optimized mode
  ⚠ Related posts disabled (>5000 pages) - set features.related_posts=true to force

Built 12000 pages in 450s (26.7 pps)
```
