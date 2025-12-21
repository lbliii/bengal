---
title: Reactive Dataflow Pipeline
nav_title: Pipeline
description: Declarative dataflow architecture for Bengal builds with automatic dependency
  tracking
weight: 25
type: doc
draft: false
lang: en
tags:
- pipeline
- dataflow
- streams
- reactive
- architecture
keywords:
- reactive pipeline
- dataflow
- streams
- incremental builds
- caching
category: architecture
---

Bengal's reactive dataflow pipeline provides a declarative approach to site building where content flows through transformation streams, and changes automatically propagate to affected outputs.

## Overview

Instead of manually tracking dependencies for incremental builds, the pipeline system uses a functional, stream-based architecture:

```python
from bengal.pipeline import Pipeline

pipeline = (
    Pipeline("build")
    .source("files", discover_files)
    .filter("markdown", lambda f: f.suffix == ".md")
    .map("parse", parse_markdown)
    .map("page", create_page)
    .parallel(workers=4)
    .for_each("write", write_output)
)

result = pipeline.run()
```

## Key Components

### StreamItem and StreamKey

Every item flowing through the pipeline is wrapped in a `StreamItem` with a unique `StreamKey`:

```python
@dataclass(frozen=True)
class StreamKey:
    source: str      # Which stream produced this item
    id: str          # Unique identifier within stream
    version: str     # Content hash for cache invalidation

@dataclass
class StreamItem[T]:
    key: StreamKey
    value: T
    produced_at: float
```

The `version` field enables automatic cache invalidation—when content changes, its hash changes, invalidating cached results.

### Stream Transformations

The pipeline provides several stream operators:

| Operator | Description | Example |
|----------|-------------|---------|
| `map` | Transform each item | `.map("parse", parse_fn)` |
| `filter` | Keep items matching predicate | `.filter("md", lambda f: f.suffix == ".md")` |
| `flat_map` | Transform and flatten | `.flat_map("split", split_fn)` |
| `collect` | Gather all items into list | `.collect("all_pages")` |
| `combine` | Merge two streams | `.combine(other_stream)` |
| `parallel` | Process in parallel | `.parallel(workers=4)` |
| `cache` | In-memory memoization | `.cache()` |
| `disk_cache` | Persistent caching | `.disk_cache(cache)` |

### Pipeline Builder

The `Pipeline` class provides a fluent API for constructing dataflow graphs:

```python
pipeline = (
    Pipeline("my_build")
    .source("content", lambda: discover_content(site.content_dir))
    .map("parse", lambda item: parse_frontmatter(item))
    .filter("published", lambda page: not page.draft)
    .parallel(workers=4)
    .for_each("render", lambda page: render_and_write(page))
)

result = pipeline.run()
print(f"Processed {result.items_processed} items in {result.elapsed:.2f}s")
```

## Bengal-Specific Streams

Bengal provides pre-built streams for common operations:

### ContentDiscoveryStream

Discovers and parses content files with frontmatter:

```python
from bengal.pipeline import ContentDiscoveryStream

stream = ContentDiscoveryStream(
    discovery=ContentDiscovery(content_dir),
    content_dir=content_dir,
)

for item in stream.iterate():
    # item.value is ParsedContent with:
    # - file_path: Path
    # - content: str (markdown body)
    # - metadata: dict (frontmatter)
    # - content_hash: str (for versioning)
    print(f"Found: {item.value.file_path}")
```

### FileChangeStream

Emits changed files for incremental builds:

```python
from bengal.pipeline import FileChangeStream

changed_files = [Path("content/post.md"), Path("content/guide.md")]
stream = FileChangeStream(changed_files)

for item in stream.iterate():
    print(f"Changed: {item.value}")
```

## Build Pipeline Factories

Bengal provides factory functions for common build scenarios:

### Full Build Pipeline

```python
from bengal.pipeline import create_build_pipeline

pipeline = create_build_pipeline(site, parallel=True, workers=4)
result = pipeline.run()
```

### Incremental Build Pipeline

```python
from bengal.pipeline import create_incremental_pipeline

changed_files = [Path("content/updated-post.md")]
pipeline = create_incremental_pipeline(site, changed_files)
result = pipeline.run()
```

### Simple Render Pipeline

```python
from bengal.pipeline import create_simple_pipeline

# Render a specific list of pages
pipeline = create_simple_pipeline(site, pages_to_render)
result = pipeline.run()
```

## Caching

### In-Memory Caching

Use `.cache()` for within-build memoization:

```python
pipeline = (
    Pipeline("build")
    .source("files", discover_files)
    .map("expensive", expensive_operation)
    .cache()  # Results memoized by StreamKey
    .for_each("use", use_result)
)
```

### Disk Caching

Use `.disk_cache()` for cross-build persistence:

```python
from bengal.pipeline import StreamCache

cache = StreamCache(Path(".bengal/pipeline"))

pipeline = (
    Pipeline("build")
    .source("files", discover_files)
    .map("parse", parse_content)
    .disk_cache(cache)  # Persists to disk
    .for_each("render", render_page)
)

result = pipeline.run()
cache.save()  # Persist cache to disk
```

On subsequent builds, items with matching `StreamKey.version` are loaded from cache without recomputation.

### Cache Statistics

```python
stats = cache.get_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Entries by source: {stats['entries_by_source']}")
```

## Watch Mode

The pipeline integrates with file watching for development:

### FileWatcher

Watches directories with debouncing:

```python
from bengal.pipeline import FileWatcher, WatchBatch

watcher = FileWatcher(
    watch_dirs=[content_dir, templates_dir],
    debounce_ms=300,  # Batch rapid changes
)

def on_changes(batch: WatchBatch):
    if batch.needs_full_rebuild:
        # Config or template changed
        run_full_build()
    else:
        # Content-only change
        run_incremental_build(batch.content_paths)

watcher.on_change(on_changes)
watcher.start()
```

### PipelineWatcher

Combines file watching with pipeline-based rebuilds:

```python
from bengal.pipeline import PipelineWatcher

watcher = PipelineWatcher(site, debounce_ms=300)
watcher.start()  # Watches and rebuilds automatically
```

### Change Classification

`WatchBatch` automatically classifies changes:

```python
batch.has_content_changes   # .md files changed
batch.has_template_changes  # .html/.jinja files changed
batch.has_config_changes    # bengal.toml changed
batch.needs_full_rebuild    # True if config/templates changed
batch.content_paths         # List of changed content files
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Bengal Build Pipeline                            │
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐   │
│  │ discover │───▶│  filter  │───▶│  parse   │───▶│   create page    │   │
│  │  files   │    │   .md    │    │ markdown │    │    (parallel)    │   │
│  └──────────┘    └──────────┘    └──────────┘    └────────┬─────────┘   │
│                                                           │              │
│                                                           ▼              │
│                                                  ┌──────────────────┐    │
│                                                  │     collect      │    │
│                                                  │   (all pages)    │    │
│                                                  └────────┬─────────┘    │
│                                                           │              │
│                         ┌─────────────────────────────────┤              │
│                         │                                 │              │
│                         ▼                                 ▼              │
│                ┌──────────────────┐              ┌──────────────────┐    │
│                │ build navigation │              │  render pages    │    │
│                │                  │─────────────▶│   (parallel)     │    │
│                └──────────────────┘              └────────┬─────────┘    │
│                                                           │              │
│                                                           ▼              │
│                                                  ┌──────────────────┐    │
│                                                  │   write output   │    │
│                                                  │    (for_each)    │    │
│                                                  └──────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Stream overhead | ~1µs per item | Minimal wrapper cost |
| Cache lookup | ~10µs | Hash-based lookup |
| Disk cache read | ~1ms | JSON deserialization |
| Parallel speedup | ~Nx | N = worker threads |

### Benchmarks

For a 1,000 page site:

| Build Type | Time | Notes |
|------------|------|-------|
| Full build | ~15s | All pages rendered |
| Incremental (1 file) | ~0.3s | Only changed file |
| Incremental (cached) | ~0.1s | Cache hit |

## Migration from Orchestrators

The pipeline system complements (and can replace) the existing orchestrator-based build system.

### When to Use Pipeline

- **New builds**: Prefer pipeline for cleaner architecture
- **Custom workflows**: Pipeline is more flexible
- **Watch mode**: Better incremental support

### When to Use Orchestrators

- **Existing code**: Orchestrators are stable and battle-tested
- **Complex dependencies**: Manual control over rebuild order
- **Legacy integration**: Works with existing hooks

### Migration Example

**Before (Orchestrator)**:

```python
# Manual orchestration
content_orchestrator = ContentOrchestrator(site)
pages = content_orchestrator.discover_pages()

render_orchestrator = RenderOrchestrator(site)
for page in pages:
    render_orchestrator.render_page(page)
```

**After (Pipeline)**:

```python
# Declarative pipeline
pipeline = create_build_pipeline(site, parallel=True)
result = pipeline.run()
```

## API Reference

### Core Types

- `StreamKey` - Unique identifier for stream items
- `StreamItem[T]` - Item wrapper with key and value
- `Stream[T]` - Base class for all streams
- `Pipeline` - Builder for constructing pipelines
- `PipelineResult` - Execution result with metrics

### Stream Types

- `SourceStream` - Creates stream from producer function
- `MapStream` - Transforms items
- `FilterStream` - Filters items by predicate
- `FlatMapStream` - Transforms and flattens
- `CollectStream` - Gathers items into list
- `CombineStream` - Merges two streams
- `ParallelStream` - Parallel processing
- `CachedStream` - In-memory memoization
- `DiskCachedStream` - Persistent caching

### Bengal Streams

- `ContentDiscoveryStream` - Discovers content files
- `FileChangeStream` - Emits changed files
- `ParsedContent` - Parsed file data
- `RenderedPage` - Rendered output

### Watcher Types

- `FileWatcher` - File system watcher
- `PipelineWatcher` - Watch + rebuild
- `WatchEvent` - Single change event
- `WatchBatch` - Batched changes
- `ChangeType` - Change type enum

:::{seealso}
- [[docs/reference/architecture/core/orchestration|Orchestration]] - Build coordination
- [[docs/reference/architecture/core/cache|Cache]] - Cache system details
:::
