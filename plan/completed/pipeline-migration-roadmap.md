# Pipeline Migration Roadmap: Full Reactive Dataflow Architecture

**Status**: Phase 1 Complete ✅ | Phase 2 In Progress 🚧  
**Created**: 2025-01-23  
**Goal**: Replace all imperative orchestrators with declarative stream-based transformations

---

## Executive Summary

The reactive dataflow pipeline is **1.9-3x faster** than standard builds and provides a cleaner architecture. This roadmap outlines the remaining work to fully embrace the pipeline architecture and remove legacy orchestrators.

**Current State**:
- ✅ Pipeline for discovery → rendering (Phase 1)
- ✅ 1.9-3x performance improvement
- ⚠️ Still uses orchestrators for sections/taxonomies/menus/assets/postprocessing

**Target State**:
- ✅ Pure stream-based architecture for all phases
- ✅ Fine-grained reactivity (only affected nodes recompute)
- ✅ Better incremental builds (15-50x speedup for single-page changes)
- ✅ Streaming output during builds
- ✅ Automatic dependency tracking

---

## Phase 1: Core Pipeline (✅ Complete)

**Status**: ✅ Complete  
**Performance**: 1.9-3x faster than standard builds

### Completed Tasks

1. ✅ **Content Discovery Stream** (`ContentDiscoveryStream`)
   - Discovers markdown files
   - Parses frontmatter and content
   - Creates `Page` objects
   - Uses `DiskCachedStream` for caching

2. ✅ **Rendering Stream** (`create_render_stream`)
   - Renders pages through templates
   - Uses `RenderingPipeline` with proper dependency tracking
   - Parallel processing support
   - Output writing

3. ✅ **Full Build Pipeline Factory** (`create_full_build_pipeline`)
   - Orchestrates discovery → rendering
   - Integrates with `BuildCache` and `DependencyTracker`
   - Proper timing and stats collection

4. ✅ **Site Integration** (`Site._build_with_pipeline`)
   - Replaces hybrid orchestrator+pipeline approach
   - Populates `site.pages` from pipeline
   - Handles static files and fonts separately

### Key Achievements

- **Performance**: Pipeline is 1.9-3x faster than standard builds
- **Architecture**: Clean separation of concerns
- **Caching**: Proper dependency tracking (no re-parsing bug)

---

## Phase 2: Replace Remaining Orchestrators (🚧 In Progress)

**Status**: 🚧 In Progress  
**Goal**: Replace all orchestrators with pure stream implementations

### Task 2.1: Taxonomy Stream ⏳

**Current**: `TaxonomyOrchestrator` builds tag/category pages  
**Target**: Stream that collects tags from pages and generates taxonomy pages

**Implementation**:
```python
def create_taxonomy_stream(
    pages_stream: Stream[Page],
    site: Site,
) -> Stream[Page]:
    """
    Collect tags from pages and generate taxonomy index pages.

    Flow:
        pages → collect_tags → group_by_tag → create_taxonomy_pages
    """
    # Collect all tags from pages
    tags_stream = pages_stream.map(lambda page: page.tags).flatten().unique()

    # Group pages by tag
    pages_by_tag = pages_stream.group_by(lambda page: page.tags)

    # Generate taxonomy pages
    taxonomy_pages = tags_stream.map(lambda tag: create_taxonomy_page(tag, pages_by_tag[tag]))

    return taxonomy_pages
```

**Files to Create**:
- `bengal/pipeline/taxonomy.py` - Taxonomy stream implementation

**Files to Modify**:
- `bengal/pipeline/full_build.py` - Integrate taxonomy stream
- `bengal/core/site.py` - Remove TaxonomyOrchestrator call

**Estimated Effort**: 2-3 hours

---

### Task 2.2: Menu/Navigation Stream ⏳

**Current**: `MenuOrchestrator` builds navigation structure  
**Target**: Stream that builds menu from pages and sections

**Implementation**:
```python
def create_menu_stream(
    pages_stream: Stream[Page],
    sections_stream: Stream[Section],
    site: Site,
) -> Stream[MenuStructure]:
    """
    Build navigation menu from pages and sections.

    Flow:
        pages + sections → build_menu_tree → menu_structure
    """
    # Combine pages and sections
    nav_items = pages_stream.map(lambda page: NavItem.from_page(page))
    section_items = sections_stream.map(lambda section: NavItem.from_section(section))

    # Build menu tree
    menu_stream = nav_items.merge(section_items).reduce(build_menu_tree)

    return menu_stream
```

**Files to Create**:
- `bengal/pipeline/menu.py` - Menu stream implementation

**Files to Modify**:
- `bengal/pipeline/full_build.py` - Integrate menu stream
- `bengal/core/site.py` - Remove MenuOrchestrator call

**Estimated Effort**: 2-3 hours

---

### Task 2.3: Sections Stream ⏳

**Current**: `SectionOrchestrator` finalizes sections and creates indexes  
**Target**: Stream that processes sections and creates index pages

**Implementation**:
```python
def create_sections_stream(
    pages_stream: Stream[Page],
    site: Site,
) -> Stream[Section]:
    """
    Process sections and create index pages.

    Flow:
        pages → group_by_section → finalize_sections → create_index_pages
    """
    # Group pages by section
    pages_by_section = pages_stream.group_by(lambda page: page.section)

    # Finalize sections
    sections_stream = pages_by_section.map(lambda section_name, pages: finalize_section(section_name, pages))

    # Create index pages
    index_pages = sections_stream.map(lambda section: create_index_page(section))

    return sections_stream, index_pages
```

**Files to Create**:
- `bengal/pipeline/sections.py` - Sections stream implementation

**Files to Modify**:
- `bengal/pipeline/full_build.py` - Integrate sections stream
- `bengal/core/site.py` - Remove SectionOrchestrator call

**Estimated Effort**: 3-4 hours

---

### Task 2.4: Assets Stream ⏳

**Current**: `AssetOrchestrator` processes and fingerprints assets  
**Target**: Stream that processes assets and generates fingerprints

**Implementation**:
```python
def create_assets_stream(
    assets: list[Asset],
    site: Site,
    parallel: bool = True,
) -> Stream[ProcessedAsset]:
    """
    Process assets (fingerprinting, optimization, etc.).

    Flow:
        assets → fingerprint → optimize → copy_to_output
    """
    assets_stream = Stream.from_iterable(assets)

    if parallel:
        assets_stream = assets_stream.parallel(workers=4)

    # Fingerprint assets
    fingerprinted = assets_stream.map(lambda asset: fingerprint_asset(asset))

    # Optimize assets (if configured)
    optimized = fingerprinted.map(lambda asset: optimize_asset(asset) if should_optimize(asset) else asset)

    # Copy to output
    copied = optimized.for_each(lambda asset: copy_asset_to_output(asset, site.output_dir))

    return copied
```

**Files to Create**:
- `bengal/pipeline/assets.py` - Assets stream implementation

**Files to Modify**:
- `bengal/pipeline/full_build.py` - Integrate assets stream
- `bengal/core/site.py` - Remove AssetOrchestrator call

**Estimated Effort**: 2-3 hours

---

### Task 2.5: Postprocessing Streams ⏳

**Current**: `PostprocessOrchestrator` generates sitemap, RSS, search index  
**Target**: Streams for each postprocessing task

**Implementation**:
```python
def create_postprocess_streams(
    pages_stream: Stream[RenderedPage],
    site: Site,
) -> dict[str, Stream]:
    """
    Create streams for postprocessing tasks.

    Returns:
        {
            "sitemap": Stream[SitemapEntry],
            "rss": Stream[RSSEntry],
            "search": Stream[SearchIndexEntry],
            "json": Stream[JSONEntry],
        }
    """
    # Sitemap stream
    sitemap_stream = pages_stream.map(lambda page: create_sitemap_entry(page))

    # RSS stream
    rss_stream = pages_stream.filter(lambda page: page.rss_enabled).map(lambda page: create_rss_entry(page))

    # Search index stream
    search_stream = pages_stream.map(lambda page: create_search_index_entry(page))

    # JSON feed stream
    json_stream = pages_stream.map(lambda page: create_json_entry(page))

    return {
        "sitemap": sitemap_stream,
        "rss": rss_stream,
        "search": search_stream,
        "json": json_stream,
    }
```

**Files to Create**:
- `bengal/pipeline/postprocess.py` - Postprocessing streams

**Files to Modify**:
- `bengal/pipeline/full_build.py` - Integrate postprocessing streams
- `bengal/core/site.py` - Remove PostprocessOrchestrator call

**Estimated Effort**: 3-4 hours

---

## Phase 3: Stream-Based Caching (⏳ Pending)

**Status**: ⏳ Pending  
**Goal**: Replace `DependencyTracker` with stream-based caching

### Task 3.1: Stream Cache Integration

**Current**: `DependencyTracker` tracks dependencies manually  
**Target**: Stream nodes automatically track dependencies

**Implementation**:
- Use `StreamCache` for node-level caching
- Stream nodes track their dependencies automatically
- Cache invalidation happens at the node level (not page level)

**Files to Modify**:
- `bengal/pipeline/cache.py` - Enhance StreamCache
- `bengal/pipeline/full_build.py` - Use stream-based caching
- `bengal/core/site.py` - Remove DependencyTracker usage

**Estimated Effort**: 4-5 hours

---

## Phase 4: Incremental Builds (⏳ Pending)

**Status**: ⏳ Pending  
**Goal**: Fine-grained reactivity for incremental builds

### Task 4.1: Change Detection Stream

**Implementation**:
```python
def create_change_detection_stream(
    site: Site,
    cache: StreamCache,
) -> Stream[Change]:
    """
    Detect changes and create change events.

    Flow:
        file_changes → detect_type → create_change_events
    """
    # Watch for file changes
    changes = watch_files(site.root_path)

    # Detect change type (content, config, template, asset)
    typed_changes = changes.map(lambda change: detect_change_type(change))

    # Create change events
    events = typed_changes.map(lambda change: create_change_event(change, cache))

    return events
```

**Estimated Effort**: 3-4 hours

### Task 4.2: Reactive Rebuild

**Implementation**:
- Only affected stream nodes recompute
- Template change → only pages using that template rebuild
- Content change → only that page + dependent pages rebuild
- Config change → full rebuild

**Estimated Effort**: 5-6 hours

---

## Phase 5: Streaming Output (⏳ Pending)

**Status**: ⏳ Pending  
**Goal**: Show pages as they complete during build

### Task 5.1: Progress Stream

**Implementation**:
```python
def create_progress_stream(
    pages_stream: Stream[RenderedPage],
    reporter: ProgressReporter,
) -> Stream[RenderedPage]:
    """
    Report progress as pages complete.

    Flow:
        rendered_pages → report_progress → continue
    """
    return pages_stream.for_each(lambda page: reporter.report_page_complete(page))
```

**Estimated Effort**: 1-2 hours

---

## Phase 6: Cleanup & Deprecation (⏳ Pending)

**Status**: ⏳ Pending  
**Goal**: Remove legacy orchestrators and consolidate build flags

### Task 6.1: Remove Orchestrators

**Files to Remove** (after migration):
- `bengal/orchestration/taxonomy.py` - Replaced by taxonomy stream
- `bengal/orchestration/menu.py` - Replaced by menu stream
- `bengal/orchestration/section.py` - Replaced by sections stream
- `bengal/orchestration/asset.py` - Replaced by assets stream
- `bengal/orchestration/postprocess.py` - Replaced by postprocess streams
- `bengal/orchestration/build/__init__.py` - Keep for static files only

**Estimated Effort**: 1 hour

### Task 6.2: Consolidate Build Flags

**See**: Build Flags Analysis section below

**Estimated Effort**: 2-3 hours

---

## Build Flags Analysis

### Current Build Flags

| Flag | Purpose | Status | Action |
|------|---------|--------|--------|
| `--pipeline` | Use reactive pipeline | ✅ Keep | Make default, remove flag |
| `--memory-optimized` | Streaming for large sites | ⚠️ Consolidate | Pipeline handles this automatically |
| `--fast` | Quiet + guaranteed parallel | ✅ Keep | Still useful for CI |
| `--parallel/--no-parallel` | Enable parallel processing | ✅ Keep | Still useful |
| `--incremental/--no-incremental` | Incremental builds | ✅ Keep | Enhanced by pipeline |
| `--quiet` | Minimal output | ✅ Keep | Still useful |
| `--verbose` | Detailed output | ✅ Keep | Still useful |
| `--profile` | Build profile (writer/dev/theme-dev) | ✅ Keep | Still useful |
| `--strict` | Fail on errors | ✅ Keep | Still useful |
| `--validate` | Validate before build | ✅ Keep | Still useful |
| `--clean-output` | Delete output before build | ✅ Keep | Still useful |
| `--perf-profile` | Performance profiling | ✅ Keep | Still useful |
| `--profile-templates` | Template profiling | ✅ Keep | Still useful |
| `--assets-pipeline` | Node-based assets | ✅ Keep | Still useful |
| `--autodoc` | Regenerate autodoc | ✅ Keep | Still useful |
| `--full-output` | Traditional output format | ✅ Keep | Still useful |
| `--log-file` | Write logs to file | ✅ Keep | Still useful |
| `--config` | Config file path | ✅ Keep | Still useful |
| `--environment` | Environment name | ✅ Keep | Still useful |
| `--debug` | Debug output | ✅ Keep | Still useful |
| `--traceback` | Traceback verbosity | ✅ Keep | Still useful |

### Recommended Changes

#### 1. Make Pipeline Default (Remove `--pipeline` Flag)

**Rationale**:
- Pipeline is 1.9-3x faster
- It's the future architecture
- No reason to keep legacy orchestrator path

**Action**:
- Make pipeline the default build path
- Remove `--pipeline` flag
- Keep `--no-pipeline` flag temporarily for debugging (deprecate)

**Timeline**: After Phase 2 completion

---

#### 2. Consolidate `--memory-optimized` into Pipeline

**Rationale**:
- Pipeline is already stream-based (memory efficient)
- `--memory-optimized` was a workaround for orchestrator memory issues
- Pipeline can handle large sites without special flag

**Action**:
- Remove `--memory-optimized` flag
- Pipeline automatically uses streaming for large sites
- Add automatic detection: if site > 5K pages, use batching

**Timeline**: After Phase 2 completion

**Implementation**:
```python
def create_full_build_pipeline(
    site: Site,
    *,
    parallel: bool = True,
    workers: int | None = None,
    use_cache: bool = True,
) -> Pipeline:
    # Auto-detect if we need batching for memory efficiency
    num_pages = len(site.pages) if hasattr(site, 'pages') else 0
    use_batching = num_pages > 5000  # Auto-enable for large sites

    if use_batching:
        # Use batched processing
        pages_stream = pages_stream.batch(size=100)
```

---

#### 3. Keep All Other Flags

**Rationale**:
- All other flags serve distinct purposes
- No conflicts with pipeline architecture
- User-facing features (profiles, output format, etc.)

---

## Migration Strategy

### Step 1: Complete Phase 2 (Current Focus)

**Priority**: High  
**Timeline**: 1-2 weeks

1. Implement taxonomy stream
2. Implement menu stream
3. Implement sections stream
4. Implement assets stream
5. Implement postprocessing streams
6. Test each stream independently
7. Integrate into full pipeline

### Step 2: Make Pipeline Default

**Priority**: High  
**Timeline**: After Phase 2

1. Make pipeline default in `Site.build()`
2. Remove `--pipeline` flag
3. Add `--no-pipeline` flag (deprecated)
4. Update documentation

### Step 3: Consolidate Memory Optimization

**Priority**: Medium  
**Timeline**: After Step 2

1. Remove `--memory-optimized` flag
2. Add automatic batching detection
3. Update documentation
4. Remove `StreamingRenderOrchestrator`

### Step 4: Stream-Based Caching

**Priority**: Medium  
**Timeline**: After Step 2

1. Implement stream-based caching
2. Replace `DependencyTracker` usage
3. Test incremental builds

### Step 5: Incremental Builds

**Priority**: Medium  
**Timeline**: After Step 4

1. Implement change detection stream
2. Implement reactive rebuild
3. Test incremental performance

### Step 6: Cleanup

**Priority**: Low  
**Timeline**: After Step 5

1. Remove legacy orchestrators
2. Update all documentation
3. Remove deprecated flags

---

## Success Criteria

### Phase 2 Complete ✅

- [ ] All orchestrators replaced with streams
- [ ] Full pipeline builds successfully
- [ ] Performance matches or exceeds current pipeline (1.9-3x faster)
- [ ] All tests pass
- [ ] Benchmarks show improvement

### Pipeline Default ✅

- [ ] Pipeline is default build path
- [ ] `--pipeline` flag removed
- [ ] `--no-pipeline` flag deprecated
- [ ] Documentation updated

### Memory Optimization Consolidated ✅

- [ ] `--memory-optimized` flag removed
- [ ] Automatic batching for large sites
- [ ] Memory usage constant for 10K+ page sites
- [ ] Documentation updated

### Stream-Based Caching ✅

- [ ] `DependencyTracker` replaced with stream cache
- [ ] Node-level dependency tracking
- [ ] Incremental builds work correctly
- [ ] Performance improved

### Incremental Builds ✅

- [ ] Fine-grained reactivity working
- [ ] Single-page changes rebuild only affected pages
- [ ] Template changes rebuild only affected pages
- [ ] 15-50x speedup for incremental builds

---

## Risks & Mitigations

### Risk 1: Breaking Changes

**Mitigation**:
- Keep `--no-pipeline` flag temporarily
- Comprehensive testing before making default
- Gradual rollout

### Risk 2: Performance Regression

**Mitigation**:
- Benchmark each phase
- Compare against current pipeline
- Rollback plan ready

### Risk 3: Missing Features

**Mitigation**:
- Feature parity checklist
- Test all build scenarios
- User feedback

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 2 | 1-2 weeks | None |
| Make Pipeline Default | 1 day | Phase 2 |
| Consolidate Memory Optimization | 2-3 days | Make Pipeline Default |
| Stream-Based Caching | 1 week | Make Pipeline Default |
| Incremental Builds | 1-2 weeks | Stream-Based Caching |
| Cleanup | 3-5 days | All above |

**Total Estimate**: 4-6 weeks

---

## Related Documents

- `plan/implemented/rfc-reactive-dataflow-pipeline.md` - Original RFC
- `architecture/core/pipeline.md` - Pipeline architecture docs
- `benchmarks/test_cold_build_permutations.py` - Performance benchmarks

---

## Notes

- Pipeline is already faster (1.9-3x) - this validates the architecture
- Focus on completing Phase 2 first (replace orchestrators)
- Then make pipeline default
- Then optimize (caching, incremental, streaming output)


