# Phase 2b Integration Strategy & Architecture Review

**Status**: Planning (Phase 2a complete, 2b not yet started)  
**Date**: October 16, 2025  
**Branch**: feature/phase2-lazy-discovery

## Current State

**Phase 2a Complete**: 3 production-ready cache components
- PageDiscoveryCache: Page metadata for lazy loading
- AssetDependencyMap: Asset reference tracking
- TaxonomyIndex: Tag-to-pages mapping

**Phase 2b Challenge**: How to integrate these into the build pipeline?

## The Integration Problem

### Current ContentOrchestrator.discover() Flow

```
discover()
  ├── discover_content()
  │   ├── ContentDiscovery().discover()
  │   │   └── Loads ALL pages from disk (full discovery)
  │   ├── _setup_page_references()
  │   ├── _apply_cascades()
  │   ├── _set_output_paths()
  │   ├── _check_weight_metadata()
  │   └── _build_xref_index()
  └── discover_assets()
      └── AssetDiscovery().discover()
          └── Loads ALL assets from disk
```

### Challenge: ContentDiscovery loads everything

The current implementation uses ContentDiscovery which does full discovery:
- Recursively scans all content files
- Parses frontmatter
- Creates Page objects
- Returns ALL pages

To use PageDiscoveryCache effectively, we need conditional discovery:
- Load only CHANGED pages fresh
- Restore UNCHANGED pages from cache
- Merge the two sets

## Solution Paths

### Option A: Refactor discover() (Current Thinking)

**Approach:**
```python
def discover_incremental(self, incremental=False):
    if incremental:
        # Load cache
        cache = PageDiscoveryCache()
        discovery = ConditionalContentDiscovery()  # NEW

        # Discover changed files only
        changed_pages = discovery.discover_changed()

        # Restore unchanged from cache
        cached_pages = cache.restore_valid_pages()

        # Merge
        self.site.pages = changed_pages + cached_pages
    else:
        # Current full discovery
        self.discover_content()
```

**Pros:**
- Incremental discovery at discovery time (earliest possible)
- Less memory usage (don't load unchanged pages into memory)
- Cache stays small

**Cons:**
- Requires new ConditionalContentDiscovery class
- More complex page merging logic
- Cache invalidation becomes critical
- Hard to get right (state management)

**Risks:**
- Stale cached page objects could cause subtle bugs
- Complex to maintain both discovery paths
- Performance gains might be less than expected if we're loading files anyway

---

### Option B: Full Discovery + Filter (Simpler, Less Optimal)

**Approach:**
```python
def discover(self):
    # Always do full discovery
    discovery = ContentDiscovery()
    all_pages = discovery.discover()

    # But cache the results
    self.cache.cache_all_pages(all_pages)

    # In incremental build, filter what we process
    if incremental:
        pages_to_build = self.incremental.find_work_early()
        # Only these get rendered, but all are in memory
    else:
        pages_to_build = all_pages
```

**Pros:**
- No refactoring needed in discovery layer
- Simpler, more reliable
- Cache is passive (write-only during discovery)
- PageDiscoveryCache used only by downstream phases

**Cons:**
- Doesn't save memory during discovery phase
- Doesn't save page parsing time
- Cache primarily helps with "repeated unchanged pages" scenario

**Benefits:**
- Memory savings come from rendering phase (already optimized)
- Cleaner separation of concerns
- Easier to understand and maintain

---

### Option C: Hybrid - Smart Discovery with Validation

**Approach:**
```python
def discover(self):
    cache = PageDiscoveryCache()
    discovery = ContentDiscovery()

    # Full discovery (current behavior)
    all_pages = discovery.discover()

    # Validate discovered pages against cache
    for page in all_pages:
        cached = cache.get_metadata(page.source_path)
        if cached and page.matches_metadata(cached):
            # Mark as trusted/cached
            page._from_cache = True

    # Cache the discovery result
    cache.save_discovery_result(all_pages)

    self.site.pages = all_pages
```

**Pros:**
- Validates that cache metadata matches reality
- Detects stale cache early
- Simple to implement
- Doesn't require discovery refactoring

**Cons:**
- Still loads all pages into memory
- Still parses all files
- Cache validation adds overhead

---

## Recommendation: Option B (Full Discovery + Filter)

**Why NOT Option A (refactor discover)?**

1. **Discovery layer complexity**: ContentDiscovery does file I/O, parsing, frontmatter extraction. Splitting this into "changed only" + "from cache" is error-prone.

2. **Cache consistency**: Cached Page objects might become stale. We can't guarantee they're valid after on-disk changes.

3. **Discovery is not the bottleneck**: Analysis shows page discovery (~80ms) is smaller than other phases. But rendering (40ms) is already optimized. The real gains come from **not processing unchanged pages in later phases**, not from skipping discovery.

4. **Separation of concerns**: PageDiscoveryCache should be used for **later phase optimization**, not early discovery. It's metadata for filtering, not a page store.

5. **Easier to maintain**: Discovery stays simple. Caches are used post-discovery by orchestrators that know what to do with them.

**Why Option B (Full Discovery + Filter)?**

1. **Simpler**: No discovery refactoring needed
2. **Safer**: Cache is metadata-only, doesn't replace real discovery
3. **More maintainable**: Discovery and caching are separate concerns
4. **Still gets gains**: Downstream phases still benefit from cache filtering
5. **Incremental already works**: We have `incremental.find_work_early()` that filters pages before expensive operations

---

## Better Long-Term Architecture

Instead of "discovery-time" optimization, use caches as **"phase filters"**:

```
Full Discovery (always)
  ├─→ Parse all metadata
  ├─→ Build all Page objects
  ├─→ Save to PageDiscoveryCache
  │
  ├─→ Find work early (incremental)
  │   └─→ Filter to pages_to_build
  │
  ├─→ Render pages_to_build (uses cache for context)
  ├─→ Process assets_to_process (uses AssetDependencyMap)
  └─→ Update taxonomy (uses TaxonomyIndex)
```

This approach:
- ✅ Keeps discovery simple
- ✅ Uses caches for filtering, not replacement
- ✅ Leverages existing `find_work_early()` optimization
- ✅ Works with all three caches naturally
- ✅ Easier to debug and maintain

---

## Phase 2b Implementation (Recommended)

### Step 1: Cache Save Integration (Easy)
After discovery, save metadata to PageDiscoveryCache:
```python
# In build.py after ContentOrchestrator.discover()
page_cache = PageDiscoveryCache()
for page in site.pages:
    metadata = PageMetadata(
        source_path=str(page.source_path),
        title=page.title,
        date=page.date.isoformat() if page.date else None,
        tags=page.tags,
        section=str(page.section.path) if page.section else None,
        slug=page.slug,
    )
    page_cache.add_metadata(metadata)
page_cache.save_to_disk()
```

### Step 2: Asset Tracking (Easy)
During rendering, track which assets are used:
```python
# In RenderOrchestrator or template rendering
asset_map = AssetDependencyMap()
for page in pages_rendered:
    assets = extract_assets_from_rendered_html(page.rendered_html)
    asset_map.track_page_assets(page.source_path, assets)
asset_map.save_to_disk()
```

### Step 3: Taxonomy Index Usage (Medium)
Instead of full rebuild, use TaxonomyIndex:
```python
# In TaxonomyOrchestrator
index = TaxonomyIndex()
for page in changed_pages:
    if page.tags:
        for tag in page.tags:
            tag_slug = normalize_tag(tag)
            pages = index.get_pages_for_tag(tag_slug) or []
            pages.append(str(page.source_path))
            index.update_tag(tag_slug, tag, pages)
index.save_to_disk()
```

---

## Why This Is Better Long-Term

1. **Simpler to reason about**: Caches are data, not alternate discovery paths
2. **Fewer edge cases**: No cache validation needed during discovery
3. **Better composability**: Each orchestrator can use relevant cache independently
4. **Easier testing**: Cache save/load is testable separately from discovery
5. **Future scalability**: If we later want true lazy discovery, cache foundation is there

---

## What About Performance?

**Discovery optimization (Option A) would save**: ~80ms per discovery  
**Phase filtering (Option B) saves**: ~190ms across all phases

Option B's gains are already baked in from Phase 1 and will improve further as we optimize each phase.

---

## Recommendation Summary

**Don't refactor discover().** Keep it simple.

**Instead:**
1. Use PageDiscoveryCache as a **metadata store** post-discovery
2. Use AssetDependencyMap to **track asset usage** during rendering
3. Use TaxonomyIndex to **avoid full taxonomy rebuilds**
4. These naturally integrate with existing `find_work_early()` optimization
5. Discovery stays a "get all fresh data" operation
6. Filtering happens downstream where each phase knows what it needs

This is architecturally cleaner and achieves the performance goals with less risk.
