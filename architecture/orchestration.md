# Orchestration System

Bengal's orchestration system coordinates the build process through specialized orchestrator classes, each responsible for a specific phase of the build pipeline.

## Overview

The orchestration subsystem (`bengal/orchestration/`) implements the delegation pattern where the `Site` object delegates build coordination to specialized orchestrators. This design avoids "God objects" and provides clear separation of concerns.

**Key Principle**: Site is a data container; orchestrators handle the build logic.

## Orchestrators

### Build Orchestrator (`bengal/orchestration/build.py`)

**Purpose**: Main coordinator that orchestrates the entire build process

**Responsibilities**:
- Coordinates all build phases in correct order
- Manages BuildContext creation and threading
- Handles parallel vs sequential execution
- Collects build statistics
- Integrates with health check system

**Build Phases**:
```python
def build(site, parallel=True, incremental=False):
    # Phase 0: Initialization
    ctx = BuildContext(site=site)

    # Phase 1: Content Discovery
    ContentOrchestrator.discover(site)

    # Phase 2: Section Finalization
    SectionOrchestrator.finalize(site)

    # Phase 3: Taxonomies & Dynamic Pages
    TaxonomyOrchestrator.collect_and_generate(site)

    # Phase 4: Menus
    MenuOrchestrator.build(site)

    # Phase 5: Incremental Filtering (if enabled)
    pages_to_build, assets_to_process = IncrementalOrchestrator.find_work(site)

    # Phase 6: Rendering
    RenderOrchestrator.process(ctx, pages_to_build, parallel)

    # Phase 7: Assets
    AssetOrchestrator.process(site, assets_to_process, parallel)

    # Phase 8: Post-Processing
    PostprocessOrchestrator.run(site, ctx, parallel)

    # Phase 9: Cache Update
    IncrementalOrchestrator.save_cache(site)

    # Phase 10: Health Check
    health_report = HealthCheck(site).run(stats)

    return BuildStats(...)
```

**Features**:
- BuildContext threading through phases
- Parallel execution support
- Build statistics collection
- Error handling and reporting
- Progress tracking integration

### Content Orchestrator (`bengal/orchestration/content.py`)

**Purpose**: Manages content discovery and organization

**Responsibilities**:
- Delegates to ContentDiscovery for file scanning
- Sets up page navigation references (next/prev, parent/ancestors)
- Applies cascade metadata inheritance
- Builds cross-reference index for `[[...]]` links
- Organizes section hierarchy

**Key Methods**:
```python
def discover(site):
    # 1. Discover content files
    pages, sections = ContentDiscovery.discover(site.content_dir)

    # 2. Setup page references
    setup_page_references(pages, sections)

    # 3. Apply cascades
    apply_cascades(sections, pages)

    # 4. Build xref index
    build_xref_index(pages)

    site.pages = pages
    site.sections = sections
```

**Integration**:
- Uses `ContentDiscovery` from `bengal/discovery/`
- Works with `CascadeEngine` from `bengal/core/`
- Builds navigation via `bengal/utils/sections.py`

### Section Orchestrator (`bengal/orchestration/section.py`)

**Purpose**: Finalizes section structure and generates index pages

**Responsibilities**:
- Ensures all sections have index pages (`_index.md`)
- Validates section structure
- Generates automatic section pages if missing
- Applies section templates

**Key Methods**:
```python
def finalize(site):
    for section in site.sections:
        if not section.index_page:
            # Generate automatic index page
            section.index_page = create_section_index(section)

        # Validate structure
        validate_section(section)
```

### Taxonomy Orchestrator (`bengal/orchestration/taxonomy.py`)

**Purpose**: Manages taxonomies (tags, categories) and generates taxonomy pages

**Responsibilities**:
- Collects taxonomies from page frontmatter
- Generates taxonomy term pages (e.g., `/tags/python/`)
- Generates taxonomy list pages (e.g., `/tags/`)
- Handles pagination for large taxonomies
- Supports incremental taxonomy rebuilds

**Key Features**:
- Inverted index integration with BuildCache
- Only rebuilds affected taxonomy pages in incremental mode
- Supports custom taxonomy templates
- Automatic slug generation for taxonomy terms

**Incremental Mode**:
```python
def collect_and_generate(site, cache):
    if incremental:
        # Detect affected tags
        affected_tags = cache.detect_affected_tags()

        # Rebuild only affected tag pages
        for tag in affected_tags:
            generate_tag_page(tag)
    else:
        # Full rebuild
        all_tags = collect_all_taxonomies(site.pages)
        generate_all_taxonomy_pages(all_tags)
```

### Menu Orchestrator (`bengal/orchestration/menu.py`)

**Purpose**: Builds hierarchical navigation menus

**Responsibilities**:
- Parses menu configuration from `bengal.toml`
- Integrates page frontmatter menu entries
- Builds hierarchical menu structure
- Stores built menus in `site.menu` for template access

**Menu Building**:
```python
def build(site):
    menus = {}

    # Build from config
    for menu_name, config_items in site.config.get('menus', {}).items():
        builder = MenuBuilder(menu_name)
        builder.add_from_config(config_items)

        # Add from page frontmatter
        for page in site.pages:
            if menu_name in page.metadata.get('menus', []):
                builder.add_from_page(page)

        menus[menu_name] = builder.build_hierarchy()

    site.menu = menus
    site.menu_builders = {name: builder for name, builder in builders.items()}
```

**Storage**:
- `site.menu`: Dict[str, List[MenuItem]] - Built menu hierarchies
- `site.menu_builders`: Dict[str, MenuBuilder] - Builders for active marking

### Render Orchestrator (`bengal/orchestration/render.py`)

**Purpose**: Coordinates page rendering with parallelization support

**Responsibilities**:
- Manages parallel rendering when enabled
- Integrates with RenderingPipeline
- Handles rendering errors gracefully
- Tracks rendering progress
- Uses BuildContext for dependency injection

**Rendering Flow**:
```python
def process(ctx, pages, parallel=True):
    if parallel and len(pages) > PARALLEL_THRESHOLD:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(render_page, ctx, page)
                for page in pages
            ]
            wait(futures)
    else:
        for page in pages:
            render_page(ctx, page)

def render_page(ctx, page):
    # Get menu data for this page
    mark_active_menu_items(ctx.site, page)

    # Render via pipeline
    pipeline = RenderingPipeline(ctx)
    pipeline.process_page(page)

    # Write output
    write_page_output(page)
```

**Features**:
- Smart parallelization (threshold-based)
- Thread-safe error handling
- Menu active state per page
- Progress reporting via BuildContext

### Asset Orchestrator (`bengal/orchestration/asset.py`)

**Purpose**: Processes and copies static assets

**Responsibilities**:
- Processes site assets and theme assets
- Handles minification (CSS/JS)
- Manages image optimization
- Supports parallel processing
- Integrates with asset pipeline

**Processing Flow**:
```python
def process(site, assets, parallel=True):
    if parallel and len(assets) > PARALLEL_THRESHOLD:
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_asset, asset)
                for asset in assets
            ]
            wait(futures)
    else:
        for asset in assets:
            process_asset(asset)

def process_asset(asset):
    if asset.needs_minification():
        asset.minify()
    if asset.needs_optimization():
        asset.optimize()
    asset.copy_to_output()
```

### Postprocess Orchestrator (`bengal/orchestration/postprocess.py`)

**Purpose**: Coordinates post-build processing tasks

**Responsibilities**:
- Generates special pages (404, search index)
- Generates sitemap.xml
- Generates RSS feed
- Validates links
- Generates output formats (JSON, etc.)
- Supports parallel task execution

**Task Execution**:
```python
def run(site, ctx, parallel=True):
    tasks = [
        (generate_special_pages, site),
        (generate_sitemap, site),
        (generate_rss, site),
        (generate_output_formats, site),
        (validate_links, site),
    ]

    if parallel:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(func, *args) for func, *args in tasks]
            wait(futures)
    else:
        for func, *args in tasks:
            func(*args)
```

**Impact**: 2x speedup measured when tasks run in parallel

### Incremental Orchestrator (`bengal/orchestration/incremental.py`)

**Purpose**: Manages incremental build logic and caching

**Responsibilities**:
- Loads and saves build cache
- Detects file changes via SHA256 hashing
- Queries dependency graph for affected pages
- Determines minimal work needed
- Updates cache after successful build

**Change Detection**:
```python
def find_work(site, cache):
    # Check config changes (forces full rebuild)
    if cache.is_changed('bengal.toml'):
        return site.pages, site.assets

    # Check content changes
    changed_pages = [
        page for page in site.pages
        if cache.is_changed(page.source_path)
    ]

    # Check template changes
    changed_templates = detect_template_changes(cache)
    affected_by_templates = cache.get_pages_using_templates(changed_templates)

    # Check taxonomy changes
    affected_by_taxonomies = cache.get_pages_for_affected_tags()

    # Union of all affected pages
    pages_to_build = set(changed_pages) | affected_by_templates | affected_by_taxonomies

    # Similar for assets
    assets_to_process = detect_changed_assets(site, cache)

    return list(pages_to_build), assets_to_process
```

**Cache Management**:
```python
def save_cache(site, pages_built, assets_processed):
    for page in pages_built:
        cache.update_hash(page.source_path)
        cache.update_dependencies(page, page.template_dependencies)
        cache.update_page_tags(page.source_path, page.tags)

    for asset in assets_processed:
        cache.update_hash(asset.source_path)

    cache.save()
```

### Related Posts Orchestrator (`bengal/orchestration/related_posts.py`)

**Purpose**: Computes related post suggestions based on content similarity

**Responsibilities**:
- Computes content similarity scores
- Generates related post suggestions per page
- Uses taxonomy overlap and keyword matching
- Caches results for performance

**Algorithm**:
```python
def compute_related_posts(page, all_pages, limit=5):
    scores = []
    for other in all_pages:
        if other == page:
            continue

        # Compute similarity
        score = 0
        score += tag_overlap(page.tags, other.tags) * 3.0
        score += category_overlap(page.categories, other.categories) * 2.0
        score += keyword_overlap(page.keywords, other.keywords) * 1.0

        scores.append((other, score))

    # Sort by score and return top N
    scores.sort(key=lambda x: x[1], reverse=True)
    return [page for page, score in scores[:limit]]
```

### Streaming Orchestrator (`bengal/orchestration/streaming.py`)

**Purpose**: Implements streaming/progressive rendering for large sites

**Status**: Planned feature for future optimization

**Concept**:
- Render high-priority pages first (hub pages, home, top-level sections)
- Stream results to output as they complete
- Continue rendering lower-priority pages in background
- Useful for very large sites (10K+ pages)

**Priority Calculation**:
- PageRank scores
- URL depth (shallower = higher priority)
- Section importance
- Manual priority hints in frontmatter

### Full-to-Incremental Orchestrator (`bengal/orchestration/full_to_incremental.py`)

**Purpose**: Converts full build results into initial incremental cache

**Responsibilities**:
- Captures initial state after first full build
- Populates cache with file hashes
- Records dependency graph
- Enables subsequent incremental builds

**Usage**:
```python
def initialize_incremental_cache(site, build_stats):
    cache = BuildCache()

    # Record all file hashes
    for page in site.pages:
        cache.update_hash(page.source_path)

    # Record dependencies
    for page in site.pages:
        cache.add_dependencies(page, page.template_dependencies)

    # Record taxonomies
    for page in site.pages:
        cache.update_page_tags(page.source_path, page.tags)

    cache.save()
```

## Architecture Patterns

### Delegation Pattern
- Site delegates to BuildOrchestrator
- BuildOrchestrator delegates to specialized orchestrators
- Each orchestrator has single responsibility
- No "God objects"

### BuildContext Threading
- BuildContext created in BuildOrchestrator
- Passed through all phases that need it
- Contains shared state (site, pages, assets, reporter, services)
- Enables dependency injection without globals

### Parallel Execution
- Most orchestrators support parallel mode
- Smart thresholds avoid overhead for small workloads
- Thread-safe error handling and progress reporting
- Configurable worker count

### Incremental Intelligence
- IncrementalOrchestrator acts as decision maker
- Other orchestrators focus on their core responsibility
- Cache managed centrally
- Dependency tracking integrated throughout

## Integration Points

**With Core**:
- Orchestrators operate on Site, Page, Section, Asset objects
- BuildContext carries core objects through pipeline

**With Rendering**:
- RenderOrchestrator coordinates rendering
- Uses RenderingPipeline for actual work
- Integrates menu active state marking

**With Cache**:
- IncrementalOrchestrator manages BuildCache
- Taxonomy and menu orchestrators update cache
- Cache queries used for filtering

**With Discovery**:
- ContentOrchestrator delegates to ContentDiscovery
- AssetOrchestrator delegates to AssetDiscovery
- Results integrated into Site object

**With Health**:
- BuildOrchestrator runs health checks after build
- Validates orchestration correctness
- Reports issues in unified format

## Performance Characteristics

**Parallel Speedup**:
- Rendering: 2-4x faster with parallelization
- Assets: 2-3x faster for 10+ assets
- Post-processing: 2x faster for parallel tasks

**Incremental Speedup**:
- Single file change: 15-50x faster (measured)
- Template change: Only affected pages rebuilt
- Taxonomy change: Only affected tag pages rebuilt

**Memory Usage**:
- Orchestrators are lightweight (no state retention)
- BuildContext holds references (not copies)
- Parallel execution adds thread overhead (minimal)

## Future Enhancements

1. **Streaming Builds**: Progressive rendering of high-priority pages
2. **Distributed Builds**: Split work across multiple machines
3. **Watch Mode Optimization**: Smarter change detection for dev server
4. **Build Profiling**: Per-orchestrator timing and bottleneck detection
5. **Plugin System**: Hooks for custom orchestration logic

## Testing

Each orchestrator has dedicated unit tests:
- `tests/unit/test_build_orchestrator.py`
- `tests/unit/test_content_orchestrator.py`
- `tests/unit/test_taxonomy_orchestrator.py`
- etc.

Integration tests cover full pipeline:
- `tests/integration/test_full_build.py`
- `tests/integration/test_incremental_build.py`

**Coverage**: 78-91% across orchestration modules
