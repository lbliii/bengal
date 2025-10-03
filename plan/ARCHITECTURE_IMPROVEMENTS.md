# Bengal SSG - Architecture Improvements Plan

**Created:** October 2, 2025  
**Status:** Strategic Plan  
**Goal:** Address architectural gaps to make Bengal production-ready and competitive with Hugo

---

## 📋 Executive Summary

This document outlines a mature, phased approach to addressing four architectural areas that need strengthening:

1. **Parallel Processing** - Expand ThreadPoolExecutor usage beyond page rendering
2. **Incremental Builds** - Implement file change tracking and selective rebuilding
3. **Asset Pipeline** - Complete minification and optimization implementations
4. **Site Object Coupling** - Extract BuildOrchestrator to reduce responsibilities

**Priority Order:** Incremental Builds → Parallel Processing → Asset Pipeline → Refactoring
**Total Estimated Effort:** 20-30 hours across 3-4 weeks
**Impact:** 10-50x faster builds for large sites, matching Hugo's performance

---

## 🎯 Priority 1: Incremental Builds (HIGHEST IMPACT)

**Status:** Not Implemented (CLI flag exists but ignored)  
**Impact:** 🔴 Critical - This is the #1 performance gap vs Hugo  
**Effort:** 8-12 hours  
**Dependencies:** None

### Problem Statement

Currently, every build processes **all** pages and assets, even if only one file changed. For a 1,000-page site:
- Full build: ~30 seconds
- With incremental: ~0.5 seconds (60x faster)

This is Hugo's killer feature and Bengal's biggest gap.

### Solution Architecture

#### 1. Build Cache System (`bengal/cache/build_cache.py`)

```python
@dataclass
class BuildCache:
    """Tracks file hashes and dependencies between builds."""
    
    # File hash → last modified timestamp
    file_hashes: Dict[Path, str]
    
    # Page → list of dependencies (templates, partials, config)
    dependencies: Dict[Path, Set[Path]]
    
    # Output → source mapping
    output_sources: Dict[Path, Path]
    
    # Taxonomy → affected pages (for tag changes)
    taxonomy_deps: Dict[str, Set[Path]]
```

**Key Methods:**
- `is_changed(path: Path) -> bool` - Check if file hash changed
- `get_affected_pages(changed_file: Path) -> List[Page]` - Find dependent pages
- `save()` / `load()` - Persist cache between builds
- `invalidate(path: Path)` - Clear cache for specific file

#### 2. Dependency Tracker (`bengal/cache/dependency_tracker.py`)

```python
class DependencyTracker:
    """Builds dependency graph during rendering."""
    
    def track_template(self, page: Page, template: Path):
        """Record that page depends on template."""
        
    def track_partial(self, page: Page, partial: Path):
        """Record partial dependency."""
        
    def track_config(self, page: Page):
        """Record config dependency."""
        
    def track_taxonomy(self, page: Page, tags: List[str]):
        """Record taxonomy dependencies."""
```

#### 3. Integration Points

**Site.build() changes:**

```python
def build(self, parallel: bool = True, incremental: bool = False) -> None:
    if incremental:
        cache = BuildCache.load(self.output_dir / ".bengal-cache.json")
        
        # Determine what changed
        changed_files = self._find_changed_files(cache)
        
        # Find affected pages
        pages_to_rebuild = self._find_affected_pages(changed_files, cache)
        
        # Only rebuild what's needed
        if pages_to_rebuild:
            print(f"Incremental build: {len(pages_to_rebuild)} pages")
            self.pages = pages_to_rebuild
        else:
            print("No changes detected, skipping build")
            return
    
    # Rest of build process...
    
    if incremental:
        cache.update(self.pages)
        cache.save()
```

### Implementation Phases

#### Phase 1.1: Basic Cache (3-4 hours)
- [ ] Create `bengal/cache/` module
- [ ] Implement `BuildCache` class with file hashing
- [ ] Implement `save()` / `load()` with JSON persistence
- [ ] Add cache location config option
- [ ] Test: Detect changed files correctly

#### Phase 1.2: Dependency Tracking (4-5 hours)
- [ ] Implement `DependencyTracker` class
- [ ] Integrate with `TemplateEngine` to track template usage
- [ ] Track partial inclusion during rendering
- [ ] Track config changes (affect all pages)
- [ ] Test: Build dependency graph correctly

#### Phase 1.3: Selective Rebuild (3-4 hours)
- [ ] Implement `_find_changed_files()` in Site
- [ ] Implement `_find_affected_pages()` in Site
- [ ] Handle taxonomy changes (tag change affects tag pages)
- [ ] Handle section changes (affects archive pages)
- [ ] Integrate with existing build pipeline
- [ ] Test: Only rebuild affected pages

#### Phase 1.4: Edge Cases & Polish (1-2 hours)
- [ ] Handle deleted files
- [ ] Handle renamed files
- [ ] Clear cache on config change
- [ ] Add `--force-rebuild` flag to ignore cache
- [ ] Add cache statistics to build output
- [ ] Test: Edge cases work correctly

### Success Metrics

- [ ] 50x+ speedup for single-file changes (30s → 0.5s)
- [ ] Correct output (incremental === full build)
- [ ] Cache persists between builds
- [ ] Dev server uses incremental builds
- [ ] Tests cover all dependency types

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missed dependencies → stale output | Comprehensive testing, --force-rebuild flag |
| Cache corruption | Validate cache on load, fall back to full build |
| Complex dependency graphs | Keep it simple: over-invalidate if unsure |
| Cache too large | Store hashes only, not file contents |

---

## 🎯 Priority 2: Parallel Processing Expansion (HIGH IMPACT)

**Status:** Partially Implemented (pages only)  
**Impact:** 🟡 High - 2-4x speedup potential  
**Effort:** 4-6 hours  
**Dependencies:** None (can run in parallel with Priority 1)

### Problem Statement

Currently, parallel processing only applies to page rendering:
- ✅ Page rendering: Parallel (ThreadPoolExecutor)
- ❌ Asset processing: Sequential
- ❌ Discovery: Sequential
- ❌ Post-processing: Sequential

For a site with 500 images + 100 CSS/JS files, asset processing takes ~10 seconds sequentially but could take ~2 seconds in parallel.

### Solution Architecture

#### 1. Parallel Asset Processing

**Current code (Site._process_assets):**
```python
for asset in self.assets:  # Sequential!
    if minify and asset.asset_type in ('css', 'javascript'):
        asset.minify()
    if optimize and asset.asset_type == 'image':
        asset.optimize()
    asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
```

**Improved code:**
```python
def _process_assets_parallel(self) -> None:
    """Process assets in parallel."""
    max_workers = self.config.get("max_workers", 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(self._process_single_asset, asset)
            for asset in self.assets
        ]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing asset: {e}")

def _process_single_asset(self, asset: Asset) -> None:
    """Process a single asset (called in parallel)."""
    minify = self.config.get("minify_assets", True)
    optimize = self.config.get("optimize_assets", True)
    fingerprint = self.config.get("fingerprint_assets", True)
    assets_output = self.output_dir / "assets"
    
    try:
        if minify and asset.asset_type in ('css', 'javascript'):
            asset.minify()
        if optimize and asset.asset_type == 'image':
            asset.optimize()
        asset.copy_to_output(assets_output, use_fingerprint=fingerprint)
    except Exception as e:
        print(f"Warning: Failed to process {asset.source_path}: {e}")
```

#### 2. Parallel Discovery (Optional, Low Priority)

Discovery is usually fast (< 1s), so parallelizing it may not be worth complexity:
- Content discovery: Walk directory, parse frontmatter
- Asset discovery: Walk directory, categorize files

**Skip this unless profiling shows it's a bottleneck.**

#### 3. Parallel Post-Processing

Post-processing tasks are independent and can run in parallel:
- Sitemap generation
- RSS feed generation
- Link validation

```python
def _post_process_parallel(self) -> None:
    """Run post-processing tasks in parallel."""
    tasks = []
    
    if self.config.get("generate_sitemap", True):
        tasks.append(('sitemap', self._generate_sitemap))
    
    if self.config.get("generate_rss", True):
        tasks.append(('rss', self._generate_rss))
    
    if self.config.get("validate_links", True):
        tasks.append(('links', self._validate_links))
    
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(task): name for name, task in tasks}
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")
```

### Implementation Phases

#### Phase 2.1: Parallel Asset Processing (2-3 hours)
- [ ] Extract `_process_single_asset()` method
- [ ] Implement `_process_assets_parallel()`
- [ ] Add config option: `parallel_assets` (default: true)
- [ ] Test: All assets processed correctly
- [ ] Test: Error handling works
- [ ] Benchmark: Measure speedup

#### Phase 2.2: Parallel Post-Processing (1-2 hours)
- [ ] Extract post-processing tasks to separate methods
- [ ] Implement `_post_process_parallel()`
- [ ] Test: All tasks complete successfully
- [ ] Test: Errors don't crash build

#### Phase 2.3: Configuration & Tuning (1 hour)
- [ ] Add `max_workers` to config (default: CPU count)
- [ ] Add `parallel_assets` toggle
- [ ] Add `parallel_postprocess` toggle
- [ ] Document configuration options
- [ ] Test: Configuration options work

### Success Metrics

- [ ] 2-4x speedup for asset-heavy sites
- [ ] No regression in output quality
- [ ] Graceful error handling
- [ ] Configurable (can disable if issues)

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race conditions in file I/O | Use unique output paths per asset |
| Memory usage with many workers | Limit max_workers by default |
| Harder to debug | Add verbose mode, good error messages |

---

## 🎯 Priority 3: Complete Asset Pipeline (MEDIUM IMPACT)

**Status:** Partially Implemented (methods exist but incomplete)  
**Impact:** 🟢 Medium - Better UX, smaller bundles  
**Effort:** 4-6 hours  
**Dependencies:** None

### Problem Statement

Asset methods exist but don't fully work:
- `Asset.minify()` - Requires optional dependencies (csscompressor, jsmin)
- `Asset.optimize()` - Requires Pillow, basic implementation
- Error handling is minimal
- No fallback for missing dependencies

### Current Gaps

1. **CSS Minification:** Works if `csscompressor` installed, silently fails otherwise
2. **JS Minification:** Works if `jsmin` installed, silently fails otherwise
3. **Image Optimization:** Basic Pillow usage, no advanced optimization
4. **Missing:** HTML minification, SVG optimization, font subsetting

### Solution Architecture

#### 1. Robust Dependency Handling

```python
class AssetOptimizer:
    """Centralized asset optimization with graceful fallbacks."""
    
    def __init__(self):
        self.has_csscompressor = self._check_import('csscompressor')
        self.has_jsmin = self._check_import('jsmin')
        self.has_pillow = self._check_import('PIL')
        
        if not self.has_csscompressor:
            print("⚠️  Install csscompressor for CSS minification: pip install csscompressor")
        if not self.has_jsmin:
            print("⚠️  Install jsmin for JS minification: pip install jsmin")
        if not self.has_pillow:
            print("⚠️  Install Pillow for image optimization: pip install Pillow")
```

#### 2. Enhanced Image Optimization

```python
def _optimize_image_advanced(self) -> None:
    """Advanced image optimization with multiple strategies."""
    from PIL import Image
    
    img = Image.open(self.source_path)
    
    # Strategy 1: Format conversion (PNG → WebP for photos)
    if self.source_path.suffix in ('.png', '.jpg', '.jpeg'):
        # Check if should convert to WebP
        if self._should_convert_webp():
            self._save_webp_variant(img)
    
    # Strategy 2: Resize large images
    if img.width > 2000 or img.height > 2000:
        img = self._resize_preserve_aspect(img, max_size=2000)
    
    # Strategy 3: Progressive JPEG
    if self.source_path.suffix in ('.jpg', '.jpeg'):
        img.save(output, 'JPEG', quality=85, optimize=True, progressive=True)
    
    # Strategy 4: Quantize PNG
    elif self.source_path.suffix == '.png':
        if img.mode == 'RGBA':
            img = img.quantize(colors=256)
        img.save(output, 'PNG', optimize=True)
```

#### 3. Optional: Advanced Minification

**HTML Minification** (for rendered pages):
```python
def minify_html(html: str) -> str:
    """Minify HTML output."""
    try:
        import htmlmin
        return htmlmin.minify(html, remove_comments=True, remove_empty_space=True)
    except ImportError:
        return html  # Fallback: return as-is
```

**SVG Optimization:**
```python
def optimize_svg(self) -> None:
    """Optimize SVG files."""
    try:
        import scour.scour
        # Use scour to optimize SVG
    except ImportError:
        # Fallback: just copy
        pass
```

### Implementation Phases

#### Phase 3.1: Robust Error Handling (1-2 hours)
- [ ] Create `AssetOptimizer` class
- [ ] Centralize dependency checking
- [ ] Add helpful error messages with installation instructions
- [ ] Fallback gracefully when dependencies missing
- [ ] Test: Works with/without optional deps

#### Phase 3.2: Enhanced Image Optimization (2-3 hours)
- [ ] Implement progressive JPEG
- [ ] Implement PNG quantization
- [ ] Add image resizing for oversized images
- [ ] Add WebP generation (optional)
- [ ] Test: Images optimized correctly
- [ ] Benchmark: Measure size reduction

#### Phase 3.3: Configuration & Presets (1 hour)
- [ ] Add optimization levels: 'none', 'basic', 'aggressive'
- [ ] Add per-asset-type configuration
- [ ] Add max image dimensions config
- [ ] Document optimization options
- [ ] Test: Configuration works

#### Phase 3.4: Optional Advanced Features (1-2 hours)
- [ ] HTML minification for rendered pages
- [ ] SVG optimization
- [ ] Add `bengal check-deps` command to verify optional dependencies
- [ ] Generate optimization report (bytes saved)

### Success Metrics

- [ ] CSS/JS minification works reliably
- [ ] Image optimization reduces file sizes 20-50%
- [ ] Clear error messages when dependencies missing
- [ ] Configuration allows fine-tuning
- [ ] No build failures due to missing deps

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking images during optimization | Extensive testing, keep originals |
| Slow optimization | Make it optional, add config to disable |
| Optional deps create confusion | Clear documentation, helper command |

---

## 🎯 Priority 4: Reduce Site Object Coupling (LOW PRIORITY)

**Status:** Working but could be cleaner  
**Impact:** 🔵 Low - Architectural cleanliness, no user-facing impact  
**Effort:** 3-4 hours  
**Dependencies:** Should be done after other improvements

### Problem Statement

The `Site` object has many responsibilities:
1. Configuration management
2. Content discovery orchestration
3. Asset discovery orchestration
4. Taxonomy collection
5. Dynamic page generation
6. Build orchestration
7. Asset processing coordination
8. Post-processing coordination
9. Dev server launching

While not a "God object" (each method is focused), it could be more modular.

### Solution Architecture

#### Extract BuildOrchestrator

```python
class BuildOrchestrator:
    """
    Orchestrates the build process, separating concerns from Site.
    
    Site holds data (pages, assets, config).
    BuildOrchestrator manages workflow.
    """
    
    def __init__(self, site: Site):
        self.site = site
        self.pipeline = RenderingPipeline(site)
        self.cache = None  # For incremental builds
    
    def build(self, parallel: bool = True, incremental: bool = False) -> None:
        """Main build orchestration."""
        # Discovery phase
        self._discover_content()
        self._discover_assets()
        
        # Preparation phase
        self._collect_taxonomies()
        self._generate_dynamic_pages()
        
        # Build phase
        if incremental:
            self._incremental_build()
        elif parallel:
            self._parallel_build()
        else:
            self._sequential_build()
        
        # Finalization phase
        self._process_assets()
        self._post_process()
    
    def _discover_content(self):
        self.site.discover_content()
    
    def _discover_assets(self):
        self.site.discover_assets()
    
    # ... other orchestration methods
```

**Site becomes primarily a data container:**
```python
@dataclass
class Site:
    """Data model for a site."""
    root_path: Path
    config: Dict[str, Any]
    pages: List[Page] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    taxonomies: Dict[str, Dict[str, List[Page]]] = field(default_factory=dict)
    
    def build(self, **kwargs):
        """Convenience method - delegates to orchestrator."""
        orchestrator = BuildOrchestrator(self)
        orchestrator.build(**kwargs)
```

### Implementation Phases

#### Phase 4.1: Extract BuildOrchestrator (2-3 hours)
- [ ] Create `bengal/core/build_orchestrator.py`
- [ ] Move build logic from Site to BuildOrchestrator
- [ ] Keep Site.build() as convenience wrapper
- [ ] Test: All builds still work
- [ ] Update documentation

#### Phase 4.2: Extract Other Orchestrators (Optional, 1-2 hours)
- [ ] Create `DiscoveryOrchestrator` (if needed)
- [ ] Create `PostProcessOrchestrator` (if needed)
- [ ] Move related methods
- [ ] Test: Everything still works

#### Phase 4.3: Update Tests (1 hour)
- [ ] Update unit tests for Site
- [ ] Add unit tests for BuildOrchestrator
- [ ] Ensure integration tests pass

### Success Metrics

- [ ] Site object < 200 lines (currently ~465)
- [ ] BuildOrchestrator handles build workflow
- [ ] All tests pass
- [ ] No breaking changes to public API
- [ ] Easier to test build logic in isolation

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking changes | Keep Site.build() as wrapper |
| Over-engineering | Only extract if truly improves clarity |
| More files to navigate | Document architecture clearly |

---

## 📊 Comparison: Priority vs Impact

| Improvement | Priority | User Impact | Dev Impact | Effort | When |
|-------------|----------|-------------|------------|--------|------|
| Incremental Builds | 🔴 Critical | 50x faster rebuilds | Better DX | 8-12h | Week 1-2 |
| Parallel Processing | 🟡 High | 2-4x faster builds | Negligible | 4-6h | Week 2 |
| Asset Pipeline | 🟢 Medium | Smaller bundles | Optional deps | 4-6h | Week 3 |
| Refactor Site | 🔵 Low | None | Cleaner code | 3-4h | Week 4 |

---

## 🗓️ Recommended Implementation Timeline

### Week 1: Incremental Builds Foundation
**Goal:** Get basic incremental builds working

- **Day 1-2:** Cache system and file hashing
- **Day 3-4:** Dependency tracking
- **Day 5:** Integration and testing

**Deliverable:** `bengal build --incremental` works for simple cases

### Week 2: Complete Incremental + Parallel Expansion
**Goal:** Production-ready incremental builds + parallel assets

- **Day 1-2:** Edge cases and polish for incremental builds
- **Day 3-4:** Parallel asset processing
- **Day 5:** Testing and benchmarking

**Deliverable:** Incremental builds handle all cases, assets process in parallel

### Week 3: Asset Pipeline Polish
**Goal:** Robust, well-documented asset optimization

- **Day 1-2:** Enhanced image optimization
- **Day 3:** Configuration and error handling
- **Day 4-5:** Documentation and examples

**Deliverable:** Asset pipeline is production-ready with good docs

### Week 4: Cleanup and Testing
**Goal:** Code quality and comprehensive tests

- **Day 1-2:** Extract BuildOrchestrator (if desired)
- **Day 3-4:** Write comprehensive tests
- **Day 5:** Documentation updates

**Deliverable:** Clean architecture, well-tested, documented

---

## ✅ Success Criteria

### Incremental Builds
- [ ] Detect changed files correctly (100% accuracy)
- [ ] Rebuild only affected pages
- [ ] Handle all dependency types (templates, config, taxonomies)
- [ ] 50x+ speedup for single-file changes
- [ ] Cache persists correctly between builds
- [ ] Works with dev server
- [ ] Tests cover 90%+ of code paths

### Parallel Processing
- [ ] Assets process in parallel
- [ ] Configurable worker count
- [ ] 2-4x speedup for asset-heavy sites
- [ ] Graceful error handling
- [ ] No race conditions

### Asset Pipeline
- [ ] CSS/JS minification works when deps installed
- [ ] Image optimization reduces sizes 20-50%
- [ ] Graceful fallback when deps missing
- [ ] Clear documentation
- [ ] Configurable optimization levels

### Refactoring
- [ ] BuildOrchestrator handles build workflow
- [ ] Site object is primarily data
- [ ] All tests pass
- [ ] No breaking changes to public API
- [ ] Documentation updated

---

## 📈 Expected Performance Improvements

### Small Site (10 pages, 20 assets)
- **Before:** 2s build time
- **After (incremental):** 0.1s for single change (20x faster)
- **After (parallel):** 1.5s full build (1.3x faster)

### Medium Site (100 pages, 200 assets)
- **Before:** 15s build time
- **After (incremental):** 0.3s for single change (50x faster)
- **After (parallel):** 6s full build (2.5x faster)

### Large Site (1,000 pages, 1,000 assets)
- **Before:** 180s build time (3 minutes)
- **After (incremental):** 0.5s for single change (360x faster)
- **After (parallel):** 60s full build (3x faster)

### Hugo Comparison (for 1,000 pages)
- **Hugo:** 1-2s build (incremental is default)
- **Bengal (before):** 180s
- **Bengal (after):** 0.5s incremental, 60s full ← **Competitive!**

---

## 🎯 Next Steps

1. **Review this plan** with stakeholders
2. **Create feature branches** for each priority
3. **Set up benchmarking infrastructure** before starting (to measure improvements)
4. **Begin with Priority 1** (Incremental Builds)
5. **Write tests first** (TDD approach)
6. **Document as you go** (don't leave docs for the end)
7. **Get feedback early** (don't build in isolation)

---

## 📚 Additional Resources

### Research & Inspiration
- **Hugo's Incremental Builds:** Study `hugo --navigateToChanged`
- **Webpack Caching:** Research persistent cache strategies
- **Gatsby's Build System:** Look at dependency tracking
- **Next.js Incremental Static Regeneration:** Study their approach

### Tools & Libraries
- **watchdog:** Already used for file watching
- **joblib:** Alternative to ThreadPoolExecutor with better caching
- **diskcache:** Alternative to JSON for cache persistence
- **msgpack:** Faster cache serialization than JSON

### Testing
- **pytest-benchmark:** For performance testing
- **pytest-xdist:** Already have this for parallel tests
- **hypothesis:** Property-based testing for cache logic

---

## 🤔 Open Questions

1. **Cache format:** JSON (human-readable) vs msgpack (faster)?
2. **Cache location:** `.bengal-cache/` directory vs single file?
3. **Parallel assets:** Always parallel or configurable default?
4. **BuildOrchestrator:** Worth the refactoring or keep Site as-is?
5. **Asset optimization:** Make optional deps required for better UX?

---

## 🎉 Conclusion

These improvements will transform Bengal from "working prototype" to "production-ready competitor to Hugo":

- **Incremental builds** close the biggest performance gap
- **Parallel processing** adds polish and speed
- **Asset pipeline** provides professional optimization
- **Refactoring** keeps code maintainable as project grows

**After these improvements, Bengal will be:**
- ✅ Fast (competitive with Hugo)
- ✅ Feature-complete (pagination, taxonomies, themes)
- ✅ Well-architected (clean, modular, testable)
- ✅ Production-ready (for real projects)

**Estimated completion:** 3-4 weeks of focused development

---

**Ready to begin? Start with Priority 1: Incremental Builds!**

