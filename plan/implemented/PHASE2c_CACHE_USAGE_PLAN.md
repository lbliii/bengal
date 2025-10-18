# Phase 2c: Cache Usage Implementation Plan

**Date**: October 16, 2025  
**Status**: PLANNING  
**Depends on**: Phase 2a (cache components) + Phase 2b (cache integration) ✅
**Branch**: Will be `feature/phase2c-cache-usage`

## Overview

Phase 2c builds on Phase 2b's cache persistence by actually **using** those caches to optimize the build pipeline. Instead of loading all pages, discovering all assets, and regenerating all tags, we now skip work for unchanged content.

**Expected performance gains**: ~300-400ms per incremental build for typical 1000-page sites

## The Three Usage Patterns

### Pattern 1: Lazy Page Loading 🚀
**Current**: Discover all pages (parse all markdown files)  
**Target**: Load only changed pages fresh, reuse unchanged from cache

### Pattern 2: Selective Asset Discovery 📦  
**Current**: Discover all assets (scan all directories)  
**Target**: Process only assets needed by changed pages

### Pattern 3: Incremental Tag Generation 🏷️
**Current**: Rebuild all tag pages  
**Target**: Regenerate only affected tag pages

---

## Step 1: Lazy Page Loading with PageProxy

### Architecture

```
Old Flow:
  ContentDiscovery.discover()
    ├── Scan all markdown files
    ├── Parse all frontmatter
    ├── Create Page objects for all
    └── Return [page1, page2, page3, ...]

New Flow:
  IncrementalPageDiscovery.discover()
    ├── Load PageDiscoveryCache
    ├── Scan filesystem (lightweight)
    ├── For unchanged files:
    │   └── Create PageProxy (metadata only, lazy load full page on demand)
    ├── For changed files:
    │   └── Parse fully, create normal Page objects
    └── Return mix of [Page, Page, PageProxy, PageProxy, ...]
```

### What is PageProxy?

A lightweight placeholder that holds:
- source_path
- metadata (title, date, tags, etc.) ← from cache
- _lazy_loaded = False

On first access to `.content` or other lazy properties:
- Load full markdown from disk
- Parse frontmatter
- Set _lazy_loaded = True

### Implementation Steps

#### Step 1.1: Create PageProxy Class
**File**: `bengal/core/page/proxy.py`

```python
class PageProxy:
    """Lazy-loaded page placeholder."""

    def __init__(self, source_path, metadata_from_cache):
        self.source_path = source_path
        self.title = metadata_from_cache.title
        self.date = metadata_from_cache.date
        self.tags = metadata_from_cache.tags
        self._lazy_loaded = False
        self._full_page = None

    def _ensure_loaded(self):
        """Load full page content on first access."""
        if not self._lazy_loaded:
            # Parse from disk
            self._full_page = parse_page(self.source_path)
            self._lazy_loaded = True

    @property
    def content(self):
        self._ensure_loaded()
        return self._full_page.content

    # ... other lazy properties
```

#### Step 1.2: Update ContentDiscovery
**File**: `bengal/discovery/content_discovery.py`

Add optional parameter:
```python
def discover(self, use_cache=False, cache=None):
    """
    Discover content with optional lazy loading.

    Args:
        use_cache: Whether to use PageDiscoveryCache for lazy loading
        cache: PageDiscoveryCache instance (if use_cache=True)
    """
    if use_cache and cache:
        return self._discover_with_cache(cache)
    else:
        return self._discover_full()  # Current implementation
```

#### Step 1.3: Wire into Incremental Builds
**File**: `bengal/orchestration/build.py`

In `ContentOrchestrator.discover()`:
```python
def discover(self, incremental=False):
    """Discover content with optional lazy loading."""
    discovery = ContentDiscovery(content_dir)

    if incremental:
        cache = PageDiscoveryCache(...)
        self.site.pages = discovery.discover(use_cache=True, cache=cache)
    else:
        self.site.pages = discovery.discover()
```

### Performance Impact
- Lazy loading removes: ~80ms (page parsing for unchanged files)
- Cache lookup adds: ~5ms
- **Net gain**: ~75ms per incremental build

### Testing Strategy
- Test PageProxy lazy loading on first access
- Test that lazy pages behave identically to normal pages
- Test mixed Page + PageProxy lists in rendering pipeline
- Test cache invalidation (revert to full load if cache stale)

---

## Step 2: Selective Asset Discovery

### Architecture

```
Old Flow:
  AssetDiscovery.discover()
    ├── Scan /assets directory
    ├── Scan theme /assets
    ├── Return all assets [asset1, asset2, asset3, ...]

New Flow (incremental):
  SelectiveAssetDiscovery.discover(changed_pages)
    ├── Load AssetDependencyMap from cache
    ├── Get assets needed by changed_pages
    ├── Filter to ONLY needed assets
    └── Return [asset1, asset3] (skip asset2 if unchanged)
```

### Key Insight
We don't need to discover unused assets. If an asset isn't referenced by any changed page, it's already in the output directory from a previous build.

### Implementation Steps

#### Step 2.1: Create SelectiveAssetDiscovery
**File**: `bengal/orchestration/asset.py`

Update `AssetOrchestrator.process()`:
```python
def process(self, assets, incremental=False, changed_pages=None):
    """Process assets with optional selective discovery."""

    if incremental and changed_pages:
        # Load asset dependency map
        asset_map = AssetDependencyMap(...)

        # Get assets needed by changed pages
        needed_assets = set()
        for page in changed_pages:
            page_assets = asset_map.get_page_assets(page.source_path)
            if page_assets:
                needed_assets.update(page_assets)

        # Filter assets to only what we need
        assets_to_process = [
            a for a in assets
            if matches_needed(a, needed_assets)
        ]
    else:
        assets_to_process = assets

    # Process only needed assets
    self._process_assets(assets_to_process)
```

#### Step 2.2: Wire into Build Pipeline
**File**: `bengal/orchestration/build.py`

In the asset processing phase:
```python
# Phase 7: Process Assets
self.assets.process(
    assets_to_process,
    parallel=parallel,
    incremental=incremental,
    changed_pages=pages_to_build if incremental else None,
)
```

### Performance Impact
- Skips fingerprinting unused assets: ~50ms
- Skips copying unchanged assets: ~30ms
- **Net gain**: ~80ms per incremental build

### Caveats
- CSS/JS concatenation might reference shared assets
- Background images might not show in changed pages
- Solution: Provide opt-out flag for sites with complex asset dependencies

---

## Step 3: Incremental Tag Page Generation

### Architecture

```
Old Flow:
  TaxonomyOrchestrator.collect_and_generate()
    ├── Rebuild all taxonomies from all pages
    ├── Generate ALL tag pages
    ├── Generate tag index page
    └── Output: 100+ tag pages

New Flow (incremental):
  TaxonomyOrchestrator.collect_and_generate_incremental(affected_tags)
    ├── Load TaxonomyIndex from cache
    ├── Update only affected tags
    ├── Generate ONLY changed tag pages
    └── Output: 5-10 tag pages (only what changed)
```

### Key Insight
Tag pages are deterministic. If tag members haven't changed, the tag page HTML is identical. We only regenerate affected tag pages.

### Implementation Steps

#### Step 3.1: Enhanced TaxonomyIndex Usage
**File**: `bengal/orchestration/taxonomy.py`

The incremental method already exists! We just need to wire it better:

```python
def collect_and_generate_incremental(self, changed_pages, cache):
    """
    Incrementally update taxonomies.

    Already implemented in Phase 2a!
    Just need to use TaxonomyIndex to skip unchanged tags.
    """
    affected_tags = self._determine_affected_tags(changed_pages, cache)

    # NEW: Use TaxonomyIndex to avoid full rebuild
    index = TaxonomyIndex(...)

    # Only regenerate affected tag pages
    for tag_slug in affected_tags:
        old_entry = index.get_tag(tag_slug)
        new_entry = self._compute_tag_entry(tag_slug)

        if old_entry and old_entry.page_paths == new_entry.page_paths:
            # Tag members unchanged, skip regeneration
            logger.debug(f"Skipping tag {tag_slug} - no changes")
            continue

        # Tag changed, regenerate its page
        self._generate_tag_page(tag_slug)
        index.update_tag(tag_slug, ...)

    index.save_to_disk()
```

#### Step 3.2: Add Comparison Logic
**File**: `bengal/cache/taxonomy_index.py`

Add helper method:
```python
def pages_changed(self, tag_slug, new_page_paths):
    """Check if tag page content would change."""
    entry = self.get_tag(tag_slug)
    if not entry:
        return True  # New tag
    return set(entry.page_paths) != set(new_page_paths)
```

#### Step 3.3: Hook into Build
Already done in Phase 2b! Just verify it's being used:

```python
# Phase 4: Taxonomies & Dynamic Pages
if incremental and pages_to_build:
    affected_tags = self.taxonomy.collect_and_generate_incremental(
        pages_to_build, cache
    )
```

### Performance Impact
- Skip taxonomy rebuild: ~60ms
- Skip unchanged tag page generation: ~100ms  
- **Net gain**: ~160ms per incremental build

---

## Combined Performance Impact

| Phase | Operation | Time Saved | Cumulative |
|-------|-----------|-----------|-----------|
| 2a | find_work_early() | ~30ms | ~30ms |
| 2b | Cache integration (overhead) | -230ms | -200ms |
| 2c | Lazy page loading | ~75ms | -125ms |
| 2c | Selective asset discovery | ~80ms | -45ms |
| 2c | Incremental tag generation | ~160ms | +115ms |
| **Total** | **Incremental build** | **~190ms saved** | **Phases 2a+2b+2c** |

For typical 1000-page site:
- Full build: ~10 seconds (unchanged)
- Incremental build (Phase 2a): ~8-9 seconds (1-2s saved)
- Incremental build (Phase 2b): ~8 seconds (2-3s saved due to cache persistence)
- Incremental build (Phase 2c): ~7-8 seconds (2-3s saved + lazy loading)

---

## Implementation Order

### Priority 1 (Must Do)
1. ✅ Phase 2c Step 1: Lazy Page Loading
   - Create PageProxy class
   - Update ContentDiscovery
   - Wire into incremental builds
   - Write integration tests

### Priority 2 (Should Do)
2. ✅ Phase 2c Step 3: Incremental Tag Generation  
   - Add comparison logic to TaxonomyIndex
   - Verify existing incremental method works
   - Write integration tests

### Priority 3 (Nice to Have)
3. ⚠️ Phase 2c Step 2: Selective Asset Discovery
   - Create SelectiveAssetDiscovery
   - Add matching logic
   - Provide opt-out for complex setups
   - Write integration tests

---

## Risk Assessment

### Low Risk ✅
- **Incremental tag generation**: Already implemented, just optimization
- **TaxonomyIndex usage**: Metadata-based, no state changes

### Medium Risk ⚠️
- **PageProxy lazy loading**: Needs thorough testing
  - Risk: Rendering code might not handle lazy properties
  - Mitigation: Proxy inherits from Page, implements all properties
  - Testing: Run full build with all proxy pages

- **Selective asset discovery**: Complex asset dependencies
  - Risk: Missing needed assets in complex sites
  - Mitigation: Opt-out flag, conservative asset inclusion
  - Testing: Test with real sites (showcase)

### Mitigation Strategy
- Feature flags for each optimization (disable in config if needed)
- Extensive integration tests
- Real-world testing with showcase site
- Gradual rollout (Phase 2c.1 → 2c.2 → 2c.3)

---

## Testing Plan

### Unit Tests
- PageProxy lazy loading behavior
- TaxonomyIndex comparison logic
- AssetDependencyMap filtering

### Integration Tests
- Full build with mixed Page + PageProxy
- Incremental build with lazy loading
- Tag page regeneration detection
- Asset discovery filtering

### Benchmark Tests
- Measure savings for each optimization
- Before/after timing comparison
- Profile memory usage

### Acceptance Tests
- Build showcase site with Phase 2c enabled
- Verify output is identical to Phase 2a
- No visual differences in generated HTML

---

## Configuration & Feature Flags

Add to `bengal.toml`:

```toml
[incremental]
# Enable lazy page loading (default: true)
lazy_page_loading = true

# Enable selective asset discovery (default: true)
selective_asset_discovery = true

# Enable incremental tag generation (default: true)
incremental_tags = true
```

Allow opt-out in case of issues:
```python
if config.get('incremental', {}).get('lazy_page_loading', True):
    use_lazy_loading = True
```

---

## Files That Will Change

### New Files
- `bengal/core/page/proxy.py` - PageProxy class
- Tests for each component

### Modified Files
- `bengal/discovery/content_discovery.py` - Add lazy loading support
- `bengal/orchestration/asset.py` - Add selective discovery
- `bengal/cache/taxonomy_index.py` - Add comparison logic
- `bengal/orchestration/build.py` - Wire all three together

### No Changes Needed
- Phase 2b cache components (already complete)
- Cache persistence (already integrated)
- PageDiscoveryCache (already persisting)
- AssetDependencyMap (already persisting)
- TaxonomyIndex (already persisting)

---

## Success Criteria

✅ Phase 2c is complete when:

1. **Lazy Page Loading**
   - PageProxy passes all rendering tests
   - Incremental builds use proxies for unchanged pages
   - Performance improves by ~75ms

2. **Selective Asset Discovery**
   - Assets filtered correctly from changed pages
   - No missing assets in output
   - Performance improves by ~80ms

3. **Incremental Tag Generation**
   - Tag pages regenerated only when needed
   - Output identical to full build
   - Performance improves by ~160ms

4. **Combined Tests**
   - All 11 existing tests still pass
   - 15+ new integration tests pass
   - Showcase site builds identically

5. **Documentation**
   - Configuration options documented
   - Feature flags documented
   - Performance gains documented in CHANGELOG

---

## Timeline Estimate

- **Phase 2c.1 (Lazy Loading)**: 2-3 days (most complex)
- **Phase 2c.2 (Incremental Tags)**: 1 day (mostly verification)
- **Phase 2c.3 (Selective Assets)**: 2 days (matching logic)
- **Testing & Integration**: 2 days
- **Total**: ~7 days (depending on complexity)

---

## Next Steps

1. ✅ Code review of Phase 2b
2. ✅ Merge Phase 2b to main
3. Create Phase 2c branch: `feature/phase2c-cache-usage`
4. Start with Step 1: Lazy Page Loading (PageProxy)
5. Test thoroughly before moving to Step 2
6. Integrate steps gradually into build pipeline

---

**Ready to begin Phase 2c.1: Lazy Page Loading implementation!**
