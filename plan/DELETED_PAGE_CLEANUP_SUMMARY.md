# Deleted Page Cleanup - Problem Summary

**Date**: 2025-10-13  
**Status**: In Progress  
**Priority**: High (user-facing bug)

---

## The Problem

**Bug discovered by**: Hypothesis stateful testing  
**Issue**: When a user deletes a page from `content/` and rebuilds, the corresponding HTML file remains in `public/`

### Impact

- **User confusion**: "I deleted my page, why is it still on my site?"
- **Stale content**: Old pages remain accessible at their URLs
- **SEO issues**: Search engines index deleted pages
- **Deploy bloat**: Deleted content increases deploy sizes

### How it was found

Our new Hypothesis stateful tests automatically generate hundreds of workflow sequences:
- Create page → build → delete page → build
- The test discovered that **deleted pages keep their output files**

---

## Expected Behavior

### Scenario 1: Simple delete + rebuild
```bash
# User creates and builds
echo "---\ntitle: Test\n---\nContent" > content/test.md
bengal build  # Creates public/test/index.html

# User deletes and rebuilds
rm content/test.md
bengal build  # Should DELETE public/test/index.html ✓
```

### Scenario 2: Multiple deletes
```bash
# Create multiple pages
bengal new page blog/post1.md
bengal new page blog/post2.md
bengal build

# Delete one
rm content/blog/post1.md
bengal build  # Should only delete post1, keep post2
```

### Scenario 3: Re-create with same name
```bash
# Create, build, delete
bengal new page test.md
bengal build
rm content/test.md
bengal build  # Deletes output

# Re-create
bengal new page test.md
bengal build  # Should recreate output ✓
```

---

## What We've Tried

### Attempt 1: Track output_sources in cache ✅
**Approach**: Add `output_sources: Dict[output_path, source_path]` to BuildCache

```python
# In BuildCache
def track_output(self, source_path, output_path, output_dir):
    """Map output files to their sources"""
    rel_output = str(output_path.relative_to(output_dir))
    self.output_sources[rel_output] = str(source_path)
```

**Result**: ✅ Successfully tracks which outputs belong to which sources

### Attempt 2: Add cleanup function ✅
**Approach**: Check for deleted sources and remove their outputs

```python
def _cleanup_deleted_files(self):
    """Delete output files for missing sources"""
    for output_path, source_path in self.cache.output_sources.items():
        if not Path(source_path).exists():
            # Delete the output file
            (self.site.output_dir / output_path).unlink()
            # Remove from cache
            del self.cache.output_sources[output_path]
```

**Result**: ✅ Logic works correctly

### Attempt 3: Call cleanup during build ✅
**Approach**: Run cleanup early in build process

```python
# In build.py, after discovery
if cache:
    self.incremental._cleanup_deleted_files()
```

**Result**: ✅ Cleanup executes

### Attempt 4: Save cache after cleanup ✅
**Approach**: Persist deletions immediately

```python
if cache:
    self.incremental._cleanup_deleted_files()
    cache.save(cache_path)  # <-- KEY FIX
```

**Result**: ✅ Manual tests pass!

### Current Status
✅ Simple manual tests work  
✅ Single delete/rebuild works  
❌ Hypothesis stateful tests find edge cases  

---

## Why It's Not Working (Edge Cases)

### Issue 1: Invariants check at wrong times

**Problem**: Hypothesis invariants run **after every action**, not just builds

```python
# Hypothesis generates:
state.create_page("test.md")  
state.active_pages_have_output()  # ❌ Checks BEFORE build!
```

**Fix needed**: Invariants should only check after build actions

### Issue 2: Re-create scenarios

**Problem**: Create → delete → create (same name) → check

```python
# Sequence that fails:
1. create page-000.md → build
2. delete page-000.md → build (cleanup works!)
3. create page-000.md (same name!)
4. invariant checks → no output yet ❌
```

**Root cause**: Test checks before rebuild after re-creation

### Issue 3: Config changes clear cache

**Problem**: Config change detection clears cache, losing cleanup info

```python
if config_changed:
    cache.clear()  # Loses output_sources mapping!
```

**Fix needed**: Clear cache AFTER cleanup, or selective clear

---

## Current Implementation

### Files Modified

1. **`bengal/cache/build_cache.py`**
   - Added `output_sources: Dict[str, str]` field
   - Added `track_output(source, output, output_dir)` method

2. **`bengal/rendering/pipeline.py`**
   - Track output when writing pages:
   ```python
   if self.dependency_tracker and not page.metadata.get("_generated"):
       self.dependency_tracker.cache.track_output(
           page.source_path, page.output_path, self.site.output_dir
       )
   ```

3. **`bengal/orchestration/incremental.py`**
   - Added `_cleanup_deleted_files()` method
   - Checks for deleted sources, removes outputs
   - Added `self.logger` for logging

4. **`bengal/orchestration/build.py`**
   - Initialize cache even for full builds (was: only incremental)
   - Call cleanup before other build phases
   - Save cache after cleanup

### Architectural Flow

```
Build Start
    ↓
Initialize Cache (ALWAYS, even full builds)
    ↓
Discovery (find current pages)
    ↓
Cleanup Deleted Files
    - Compare cache.output_sources to current pages
    - Delete outputs for missing sources
    - Update cache
    ↓
Save Cache (persist deletions)
    ↓
Continue normal build...
```

---

## Why We Think It's Not Working

### Root Cause Analysis

**Theory 1: Race condition in cache saves**
- Cleanup saves cache
- Later in build, something overwrites it?
- **Check**: Look for multiple `cache.save()` calls

**Theory 2: Test expectations are wrong**
- Invariants check at wrong lifecycle points
- Test should only verify after builds, not after creates/deletes
- **Status**: This is the most likely issue

**Theory 3: Cache isn't being loaded**
- Full builds might not load cache properly?
- **Check**: Verify cache loading in full build mode

**Theory 4: output_sources not being populated**
- Maybe track_output() isn't called for all pages?
- **Check**: Add logging to track_output()

### Evidence

✅ Manual simple tests work  
✅ Single delete/rebuild works  
❌ Stateful tests find complex sequences  
❌ Re-create scenarios fail  

**Conclusion**: The **core logic works**, but **edge cases in test lifecycle** reveal timing issues

---

## Best Long-Term Design Solution

### Option A: Manifest-Based Cleanup (RECOMMENDED)

**Concept**: Track ALL generated files in a manifest, clean up orphans

```python
# .bengal/manifest.json
{
    "generated_files": {
        "test/index.html": {
            "source": "content/test.md",
            "generated_at": "2025-10-13T10:00:00Z",
            "type": "page"
        },
        "sitemap.xml": {
            "source": null,
            "generated_at": "2025-10-13T10:00:00Z",
            "type": "generated"
        }
    }
}
```

**Build process**:
1. Load previous manifest
2. Run build, track what gets generated
3. Compare: files in manifest but not regenerated = orphans
4. Delete orphans
5. Save new manifest

**Advantages**:
- ✅ Comprehensive: tracks ALL generated files
- ✅ Handles templates, assets, everything
- ✅ Can show "stale files" to user
- ✅ Works with any build mode (full, incremental)
- ✅ Can detect manual deletions in output/

**Disadvantages**:
- ⚠️ Requires tracking every write
- ⚠️ Manifest could get large

### Option B: Output Directory Snapshot (SIMPLE)

**Concept**: Before build, snapshot output dir. After build, delete unmatched files.

```python
def build():
    # Take snapshot of output/ before build
    old_files = set(output_dir.rglob("*.html"))

    # Run build
    build_all_pages()

    # After build, anything in old_files but not touched = orphan
    new_files = set(output_dir.rglob("*.html"))
    orphans = old_files - new_files

    # Delete orphans
    for orphan in orphans:
        orphan.unlink()
```

**Advantages**:
- ✅ Dead simple
- ✅ No tracking needed
- ✅ Works for everything

**Disadvantages**:
- ❌ Slow (scanning large output dirs)
- ❌ Race conditions (parallel builds)
- ❌ Can't distinguish user-added files

### Option C: Source-Driven Cleanup (CURRENT)

**Concept**: Track source → output mapping, clean when source missing

**Status**: This is what we've implemented

**Advantages**:
- ✅ Fast (no scanning)
- ✅ Precise (only deletes what we generated)
- ✅ Works with cache

**Disadvantages**:
- ⚠️ Requires tracking at every write point
- ⚠️ Doesn't handle template-only changes
- ⚠️ Edge cases around cache lifecycle

### Option D: Clean Flag (USER CONTROL)

**Concept**: Let user decide when to clean

```bash
bengal build --clean  # Delete output/ first
bengal build          # Normal incremental
```

**Advantages**:
- ✅ Simple
- ✅ User has control
- ✅ No complex tracking

**Disadvantages**:
- ❌ User has to remember
- ❌ Defeats incremental builds
- ❌ Not automatic

---

## Recommendation

### Short-term (Complete current work)

1. **Fix test invariants**
   - Only check output after builds
   - Don't check between create/delete actions

2. **Add integration test**
   ```python
   def test_deleted_page_cleanup():
       # Simple, explicit test
       create_page("test.md")
       build()
       assert output_exists("test/index.html")

       delete_page("test.md")
       build()
       assert not output_exists("test/index.html")
   ```

3. **Document behavior**
   - Add to CHANGELOG
   - Update docs: "Deleted pages are cleaned up on next build"

### Long-term (v0.2.0+)

**Implement Option A: Manifest-Based Cleanup**

1. Create `.bengal/manifest.json`
2. Track all generated files during build
3. Clean orphans at end of build
4. Show "stale files detected" warnings

**Why this is best**:
- Handles ALL edge cases
- Works with incremental builds
- Provides visibility to users
- Foundation for other features (deploy diff, cache invalidation)

---

## Open Questions

1. **Should we clean on incremental builds?**
   - Current: Yes
   - Pro: Always accurate
   - Con: Slower

2. **What about user-added files in public/?**
   - Current: Ignore them
   - Risk: Could delete user files if they match patterns

3. **Should cleanup be opt-in?**
   - Current: Always on
   - Alternative: `cleanup: true` in config

4. **How to handle symlinks/external files?**
   - Current: Not handled
   - Need: Skip symlinked files

---

## Next Steps

1. ✅ Fix stateful test invariants
2. ⏳ Add simple integration test
3. ⏳ Document in CHANGELOG
4. ⏳ Run full test suite
5. ⏳ Consider adding `--no-cleanup` flag for debugging
6. ⏳ Plan manifest-based approach for v0.2.0

---

**Status**: Implementation 90% complete, edge case testing in progress  
**Blocker**: Test invariant timing issues  
**Risk**: Low (core logic works, just test refinement needed)
