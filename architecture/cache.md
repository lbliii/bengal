# Cache System

Bengal implements an intelligent caching system for incremental builds, providing faster rebuilds.

## Build Cache (`bengal/cache/build_cache.py`)

### Purpose
Tracks file changes between builds using SHA256 hashing and dependency graphs. Persisted as `.bengal-cache.json`.

### Key Methods

| Method | Description |
|--------|-------------|
| `is_changed(path)` | Check if file has changed since last build |
| `add_dependency(source, dependency)` | Record file dependencies (page → template/partial) |
| `get_affected_pages(changed_file)` | Find all pages needing rebuild based on dependency graph |
| `update_page_tags(path, tags)` | Update taxonomy inverted index, returns affected tags |
| `get_pages_for_tag(tag)` | Get all page paths for a specific tag (O(1) lookup) |
| `get_all_tags()` | Get all known tags from previous build |
| `save()` / `load()` | Persist cache between builds |

### Inverted Index Pattern

The cache stores a bidirectional mapping between pages and tags:
- **Forward index**: `page_tags` (page path → set of tags)
- **Inverted index**: `tag_to_pages` (tag slug → set of page paths)

This enables efficient taxonomy reconstruction without persisting object references:

```python
# Only paths stored in cache, never object references
cache.tag_to_pages['python'] = {'content/post1.md', 'content/post2.md'}

# During build: Reconstruct with current Page objects
current_page_map = {p.source_path: p for p in site.pages}
pages_for_tag = [current_page_map[path] for path in cache.get_pages_for_tag('python')]
```

### Key Design Principle
"Never persist object references across builds" - cache stores paths and hashes, relationships are reconstructed from current objects each build.

## Dependency Tracker (`bengal/cache/dependency_tracker.py`)

### Purpose
Tracks dependencies during the build process

### Tracks
- Page → template dependencies
- Page → partial dependencies
- Page → config dependencies
- Taxonomy (tag) → page relationships

### Usage
Integrated with rendering pipeline to build dependency graph

## Incremental Build Flow

```mermaid
flowchart TD
    Start[Start Build] --> LoadCache[Load .bengal-cache.json]
    LoadCache --> CheckConfig{Config<br/>changed?}

    CheckConfig -->|Yes| FullRebuild[Full Rebuild]
    CheckConfig -->|No| CheckFiles[Compare SHA256 Hashes]

    CheckFiles --> Changed[Identify Changed Files]
    Changed --> DepGraph[Query Dependency Graph]

    DepGraph --> Affected{Find Affected Pages}
    Affected --> Templates[Templates changed?]
    Affected --> Content[Content changed?]
    Affected --> Assets[Assets changed?]

    Templates -->|Yes| AffectedPages[Rebuild pages<br/>using template]
    Content -->|Yes| ContentPages[Rebuild<br/>changed pages]
    Assets -->|Yes| AssetPages[Process<br/>changed assets]

    AffectedPages --> TrackDeps[Track New Dependencies]
    ContentPages --> TrackDeps
    AssetPages --> TrackDeps
    FullRebuild --> TrackDeps

    TrackDeps --> UpdateCache[Update Cache<br/>with new hashes]
    UpdateCache --> SaveCache[Save .bengal-cache.json]
    SaveCache --> Done[Build Complete]

    style CheckConfig fill:#fff3e0
    style Affected fill:#fff3e0
    style FullRebuild fill:#ffebee
    style TrackDeps fill:#e8f5e9
    style SaveCache fill:#e3f2fd
```

## Cache Decision Logic

1. **Load cache** from `.bengal-cache.json` (or create if first build)
2. **Check config** - if `bengal.toml` changed → full rebuild
3. **Compare hashes** - SHA256 of all tracked files
4. **Query dependency graph** - find pages affected by changes
5. **Selective rebuild** - only pages that changed or depend on changed files
6. **Track dependencies** - during rendering, record what each page uses
7. **Update cache** - save new hashes and dependency graph
8. **Save cache** - persist to disk for next build

## Implemented Features

- Template dependency tracking (pages → templates/partials)
- Taxonomy dependency tracking (tags → pages) with inverted index pattern
- Config change detection (forces full rebuild)
- Verbose mode (`--verbose` flag shows what changed)
- Asset change detection (selective processing)
- Object reference safety (cache stores paths, not objects)

## CLI Usage

```bash
# Incremental build
bengal site build --incremental

# With detailed change information
bengal site build --incremental --verbose
```

## Build Pipeline Flow

```mermaid
sequenceDiagram
    participant CLI
    participant Site
    participant BuildOrch as BuildOrchestrator
    participant ContentOrch as ContentOrchestrator
    participant TaxonomyOrch as TaxonomyOrchestrator
    participant MenuOrch as MenuOrchestrator
    participant IncrementalOrch as IncrementalOrchestrator
    participant RenderOrch as RenderOrchestrator
    participant AssetOrch as AssetOrchestrator
    participant PostprocessOrch as PostprocessOrchestrator
    participant Cache

    Note over CLI,Cache: Phase 0: Initialization
    CLI->>Site: build(parallel, incremental)
    Site->>BuildOrch: BuildOrchestrator.build()
    BuildOrch->>IncrementalOrch: initialize(incremental)
    IncrementalOrch->>Cache: load cache
    IncrementalOrch-->>BuildOrch: cache, tracker

    Note over BuildOrch,Cache: Phase 1: Content Discovery
    BuildOrch->>ContentOrch: discover()
    ContentOrch->>ContentOrch: discover_content()
    ContentOrch->>ContentOrch: discover_assets()
    ContentOrch->>ContentOrch: setup_page_references()
    ContentOrch->>ContentOrch: apply_cascades()
    ContentOrch->>ContentOrch: build_xref_index()
    ContentOrch-->>BuildOrch: content ready

    Note over BuildOrch,Cache: Phase 2: Section Finalization
    BuildOrch->>BuildOrch: finalize_sections()
    BuildOrch->>BuildOrch: validate_sections()

    Note over BuildOrch,TaxonomyOrch: Phase 3: Taxonomies & Dynamic Pages
    BuildOrch->>TaxonomyOrch: collect_and_generate()
    alt Incremental Build
        TaxonomyOrch->>Cache: detect affected tags
        TaxonomyOrch->>Cache: rebuild taxonomy from paths
        TaxonomyOrch->>TaxonomyOrch: generate only affected tag pages
    else Full Build
        TaxonomyOrch->>TaxonomyOrch: collect_taxonomies()
        TaxonomyOrch->>TaxonomyOrch: generate_dynamic_pages()
        TaxonomyOrch->>Cache: update inverted index
    end
    TaxonomyOrch-->>BuildOrch: taxonomies built

    Note over BuildOrch,MenuOrch: Phase 4: Menus
    BuildOrch->>MenuOrch: build()
    MenuOrch->>MenuOrch: build from config
    MenuOrch->>MenuOrch: add from page frontmatter
    MenuOrch-->>BuildOrch: menus ready (stored in site.menu)

    Note over BuildOrch,Cache: Phase 5: Incremental Filtering
    alt Incremental Build Enabled
        BuildOrch->>IncrementalOrch: find_work()
        IncrementalOrch->>Cache: check file changes
        IncrementalOrch->>Cache: check template changes
        IncrementalOrch->>Cache: check taxonomy changes
        IncrementalOrch-->>BuildOrch: pages_to_build, assets_to_process
    else Full Build
        BuildOrch->>BuildOrch: build all pages/assets
    end

    Note over BuildOrch,RenderOrch: Phase 6: Render Pages
    BuildOrch->>RenderOrch: process(pages_to_build, parallel)
    par Parallel Rendering (if enabled)
        RenderOrch->>RenderOrch: render page 1
        RenderOrch->>RenderOrch: render page 2
        RenderOrch->>RenderOrch: render page N
    end
    Note right of RenderOrch: Each page:<br/>1. Parse markdown<br/>2. Apply plugins<br/>3. Get menu data<br/>4. Render template<br/>5. Write output
    RenderOrch-->>BuildOrch: all pages rendered

    Note over BuildOrch,AssetOrch: Phase 7: Process Assets
    BuildOrch->>AssetOrch: process(assets_to_process, parallel)
    par Parallel Asset Processing (if enabled)
        AssetOrch->>AssetOrch: copy asset 1
        AssetOrch->>AssetOrch: copy asset 2
        AssetOrch->>AssetOrch: copy asset N
    end
    AssetOrch-->>BuildOrch: assets processed

    Note over BuildOrch,PostprocessOrch: Phase 8: Post-processing
    BuildOrch->>PostprocessOrch: run(parallel)
    par Parallel Post-processing (if enabled)
        PostprocessOrch->>PostprocessOrch: generate_special_pages()
        PostprocessOrch->>PostprocessOrch: generate_sitemap()
        PostprocessOrch->>PostprocessOrch: generate_rss()
        PostprocessOrch->>PostprocessOrch: generate_output_formats()
        PostprocessOrch->>PostprocessOrch: validate_links()
    end
    PostprocessOrch-->>BuildOrch: post-processing complete

    Note over BuildOrch,Cache: Phase 9: Update Cache
    BuildOrch->>IncrementalOrch: save_cache(pages_built, assets_processed)
    IncrementalOrch->>Cache: update file hashes
    IncrementalOrch->>Cache: update dependencies
    IncrementalOrch->>Cache: save to disk

    Note over BuildOrch,Cache: Phase 10: Health Check
    BuildOrch->>BuildOrch: run_health_check()
    BuildOrch-->>Site: BuildStats
    Site-->>CLI: build complete
```

## Pipeline Phases

0. **Initialization**: Load cache, set up dependency tracker
1. **Content Discovery**: Find pages/sections/assets, setup references, apply cascades, build xref index
2. **Section Finalization**: Ensure all sections have index pages, validate structure
3. **Taxonomies**: Collect tags/categories (incremental: detect affected tags + rebuild from cache paths), generate tag pages and pagination
4. **Menus**: Build navigation from config + page frontmatter (stored in `site.menu`)
5. **Incremental Filtering**: Determine what needs rebuilding (pages, assets, affected dependencies)
6. **Rendering**: Parse markdown → apply plugins → render templates (uses `site.menu`) → write HTML
7. **Assets**: Copy/process static files from site and theme
8. **Post-processing**: Generate sitemap, RSS, output formats, validate links (can run in parallel)
9. **Cache Update**: Save file hashes, dependencies, and taxonomy inverted index for next incremental build
10. **Health Check**: Validate build output, check for broken links, performance metrics

## Key Architecture Patterns

- **Delegation**: `Site.build()` immediately delegates to `BuildOrchestrator.build()`
- **Specialized Orchestrators**: Each build concern has a dedicated orchestrator class
- **Bulk Filtering**: Incremental builds filter upfront (Phase 5), then process filtered lists
- **Parallelization**: Phases 6, 7, and 8 can process items in parallel for performance
- **Menu Access**: Menus built once in Phase 4, accessed from `site.menu` during rendering
