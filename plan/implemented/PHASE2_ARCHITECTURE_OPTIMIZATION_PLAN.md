# Phase 2: Architectural Optimization Plan

**Status**: Planning (Ready for implementation after Phase 1)  
**Target**: 10-15x speedup for incremental builds  
**Estimated Timeline**: 10-14 weeks  
**Expected Result**: ~205ms (3.36x speedup) vs current 518ms baseline

## Overview

Phase 1 optimized specific bottlenecks, reducing single-page incremental builds from 518ms to 435ms (83ms saved). However, the pipeline still spends significant time discovering and processing ALL pages upfront, even when only 1 page changes.

Phase 2 implements architectural changes to lazy-load pages, stream taxonomies, and discover assets on-demand.

## Current State Analysis

**Time Breakdown (435ms)**:
- Page discovery & parsing: ~80ms (19%)
- Metadata extraction: ~60ms (14%)
- Asset discovery: ~50ms (11%)
- Menu building: ~40ms (9%)
- Taxonomy operations: ~80ms (18%)
- Rendering: ~40ms (9%)
- Other phases: ~85ms (20%)

**Rendering is fully optimized (10x), but page discovery is not.**

## Phase 2 Components

### 1. Lazy Page Discovery (~80ms gain, 3-4x speedup)

**Problem**: ContentOrchestrator discovers all pages upfront, loading full metadata even for unchanged pages.

**Solution**: Implement PageDiscoveryCache to store page metadata and lazy-load page content on demand.

**Implementation**:
- Create `bengal/cache/page_discovery_cache.py`
- Store: source_path → PageMetadata (title, date, tags, section, slug)
- Save to `.bengal/page_cache.json` after each build
- Lazy-load full page content when accessed

**Key Changes**:
- `ContentOrchestrator.discover()` - Load only changed pages, restore unchanged from cache
- `Page` class - Add PageProxy for lazy content loading
- Build pipeline - Load full content on first render

**Expected Benefits**:
- Skip discovery for 99 unchanged pages (~80ms)
- Only process changed pages in incremental builds
- No behavior change (lazy loading ensures correctness)

**Risks**: Cache invalidation, metadata accuracy

---

### 2. Streaming Taxonomies (~60ms gain, 2-3x speedup)

**Problem**: TaxonomyOrchestrator rebuilds entire taxonomy structure even when only 1 tag changed.

**Solution**: Maintain incremental TaxonomyIndex and only update affected entries.

**Implementation**:
- Create `bengal/cache/taxonomy_index.py`
- Format: `tag_slug → [page_paths]`
- Store in `.bengal/taxonomy_index.json`
- Update only changed tags, reuse unchanged

**Key Changes**:
- `TaxonomyOrchestrator.collect_and_generate_incremental()` - Load existing index, update only affected tags
- Avoid full taxonomy rebuild when possible
- Stream tag page generation (generate as we go)

**Expected Benefits**:
- Skip taxonomy rebuild when only content changes (~60ms)
- Avoid batch tag page collection/generation
- Incremental taxonomy updates

**Risks**: Index out of sync with page data

---

### 3. On-Demand Asset Discovery (~50ms gain, 1.5-2x speedup)

**Problem**: AssetOrchestrator discovers ALL assets upfront, then filters to needed ones later.

**Solution**: Track asset dependencies per page and discover assets on-demand.

**Implementation**:
- Create `bengal/cache/asset_dependency_map.py`
- Format: `source_path → [asset_urls]`
- Build during page parsing
- Store in `.bengal/asset_deps.json`

**Key Changes**:
- `AssetOrchestrator.discover()` - Load dependency map, discover only needed assets
- Page parser - Extract and track asset references
- Build fingerprint cache for incremental asset processing

**Expected Benefits**:
- Skip asset discovery for unchanged pages (~50ms)
- Focus on only needed assets
- Incremental asset fingerprinting

**Risks**: Missing asset dependencies, cache staleness

---

### 4. Incremental Menus (~40ms gain, 1.3-1.5x speedup)

**Problem**: Menu building already has incremental mode, but doesn't cache menu HTML output.

**Solution**: Further optimize with menu HTML caching and selective updates.

**Implementation**:
- Enhance `MenuOrchestrator` with menu HTML cache
- Cache: `section_path → menu_html`
- Update only affected subsections
- Pre-compute navigation links

**Key Changes**:
- `MenuOrchestrator.build()` - Accept cache_menu_html parameter
- Store menu HTML per section in cache
- Invalidate only affected sections
- Cache next/prev page relationships

**Expected Benefits**:
- Skip menu rebuild for unrelated changes (~40ms)
- Reuse cached HTML for unchanged menus
- Faster navigation link computation

**Risks**: Cache invalidation complexity

## Implementation Phases

### Phase 2a: Foundation (3-4 weeks)

1. Implement PageDiscoveryCache
   - Create persistent metadata storage
   - Implement lazy page loading with PageProxy
   - Add cache validation and consistency checks

2. Create AssetDependencyMap
   - Track asset references during parsing
   - Build dependency graph
   - Implement on-demand discovery

3. Build TaxonomyIndex
   - Create persistent storage format
   - Implement incremental update logic
   - Add index validation

### Phase 2b: Integration (3-4 weeks)

1. Update ContentOrchestrator
   - Integrate PageDiscoveryCache
   - Implement conditional discovery
   - Add lazy loading paths

2. Modify TaxonomyOrchestrator
   - Integrate TaxonomyIndex
   - Implement incremental updates
   - Avoid full rebuilds

3. Update AssetOrchestrator
   - Integrate dependency mapping
   - Implement on-demand discovery
   - Add selective asset processing

4. Enhance MenuOrchestrator
   - Add menu HTML caching
   - Implement selective updates
   - Cache navigation links

### Phase 2c: Optimization (2-3 weeks)

1. Performance tuning
   - Optimize cache serialization
   - Fine-tune lazy loading thresholds
   - Benchmark improvements

2. Cache management
   - Add cache invalidation strategy
   - Implement cache warming
   - Add cache statistics

3. Integration testing
   - Full pipeline tests
   - Large site scenarios (5K+ pages)
   - Cache corruption handling

### Phase 2d: Testing & Documentation (2-3 weeks)

1. Comprehensive testing
   - Unit tests for each component
   - Integration tests
   - Benchmark validation

2. Documentation
   - Architecture design docs
   - Cache format specs
   - Performance guide
   - Troubleshooting guide

## Performance Projections

**Phase 1 + Phase 2 Combined**:
```
Single-page incremental improvement:
- Before Phase 1:     518ms (1.33x)
- After Phase 1:      435ms (1.59x)
- After Phase 2:      ~205ms (3.36x)

Full improvement:     313ms saved (-60%)
Speedup factor:       2.53x vs original
```

**Still below 10-15x target** due to:
- Minimum work needed (rendering: 40ms)
- Architecture constraints
- System I/O overhead

**Could reach 10-15x with Phase 3**:
- Parallel page discovery
- Multi-threaded taxonomy building
- Distributed rendering (if applicable)

## Risk Assessment

**Low Risk**:
- Lazy page loading (well-encapsulated)
- Asset dependency tracking (additive)
- Menu caching (already partially implemented)

**Medium Risk**:
- Page metadata cache (correctness critical)
- Taxonomy index persistence (sync issues)
- Cache invalidation logic

**Mitigation**:
- Comprehensive unit tests
- Cache validation on startup
- Graceful fallback to full build
- CI cache consistency checks
- Versioned cache format for migrations

## Testing Strategy

**Unit Tests**:
- PageDiscoveryCache load/save/validate
- AssetDependencyMap tracking/lookup
- TaxonomyIndex incremental updates
- MenuCache HTML output caching

**Integration Tests**:
- Full incremental build with all caches
- Cache corruption and recovery
- Large site scenarios (1K, 5K, 10K pages)
- Config changes (cache invalidation)
- Clean builds vs incremental

**Benchmarks**:
- Compare Phase 1 vs Phase 2 performance
- Measure cache overhead
- Validate speedup targets
- Test various site sizes and configurations

## Deliverables

**Code**:
- PageDiscoveryCache implementation
- AssetDependencyMap implementation
- TaxonomyIndex enhancement
- MenuCache optimization
- Build pipeline integration

**Documentation**:
- Architecture design document
- Cache format specifications
- Performance improvement guide
- Troubleshooting and cache management
- Migration guide from Phase 1

**Testing**:
- Comprehensive test suite
- Benchmark results and comparisons
- Performance validation report
- Known limitations and workarounds

## Maintenance & Operations

**Cache Management**:
- Version cache format for migrations
- Document cache invalidation strategy
- Provide cache inspection tools
- Add cache health checks

**Monitoring**:
- Cache hit/miss rates
- Cache size metrics
- Performance improvements realized
- Any cache-related errors or warnings

**Support**:
- Troubleshooting guide for cache issues
- How to clear/rebuild caches
- Performance tuning guide
- Upgrade path documentation

## Future Enhancements (Phase 3+)

- Parallel page discovery
- Multi-threaded taxonomy building
- Incremental rendering across multiple processes
- Distributed build support for very large sites
- Adaptive caching based on site characteristics
- Machine learning for prediction of affected components

## Conclusion

Phase 2 implements architectural improvements to achieve 3.36x speedup (combined with Phase 1), reducing single-page incremental builds to ~205ms. While this doesn't reach the 10-15x target, it represents significant progress toward truly incremental builds.

Further improvements would require more substantial architectural changes (Phase 3) and may have diminishing returns vs implementation complexity.

The Phase 2 plan is well-scoped, achievable, and sets the foundation for future optimizations.
