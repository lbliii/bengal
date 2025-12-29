---
title: Reactive Dataflow Pipeline
nav_title: Pipeline
description: Declarative dataflow architecture with automatic dependency tracking
weight: 25
---

# Reactive Dataflow Pipeline

Bengal's pipeline provides a declarative, stream-based approach to site building where changes automatically propagate to affected outputs.

## Overview

```python
from bengal.pipeline import Pipeline

pipeline = (
    Pipeline("build")
    .source("files", discover_files)
    .filter("markdown", lambda f: f.suffix == ".md")
    .map("parse", parse_markdown)
    .parallel(workers=4)
    .for_each("write", write_output)
)

result = pipeline.run()
```

## Stream Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `map` | Transform each item | `.map("parse", parse_fn)` |
| `filter` | Keep matching items | `.filter("md", lambda f: f.suffix == ".md")` |
| `flat_map` | Transform and flatten | `.flat_map("split", split_fn)` |
| `collect` | Gather into list | `.collect("all_pages")` |
| `combine` | Merge two streams | `.combine(other_stream)` |
| `parallel` | Process in parallel | `.parallel(workers=4)` |
| `cache` | In-memory memoization | `.cache()` |
| `disk_cache` | Persistent caching | `.disk_cache(cache)` |

## Pipeline Factories

```python
from bengal.pipeline import create_build_pipeline, create_incremental_pipeline

# Full build
pipeline = create_build_pipeline(site, parallel=True, workers=4)
result = pipeline.run()

# Incremental build
changed = [Path("content/updated.md")]
pipeline = create_incremental_pipeline(site, changed)
result = pipeline.run()
```

## Caching

### In-Memory

```python
pipeline = Pipeline("build").map("expensive", fn).cache()
```

### Disk (Cross-Build)

```python
from bengal.pipeline import StreamCache

cache = StreamCache(Path(".bengal/pipeline"))
pipeline = Pipeline("build").map("parse", fn).disk_cache(cache)
result = pipeline.run()
cache.save()
```

Items with matching `StreamKey.version` (content hash) skip recomputation.

## Watch Mode

```python
from bengal.pipeline import PipelineWatcher

watcher = PipelineWatcher(site, debounce_ms=300)
watcher.start()  # Watches and rebuilds automatically
```

`WatchBatch` classifies changes:

| Property | Description |
|----------|-------------|
| `has_content_changes` | `.md` files changed |
| `has_template_changes` | `.html` files changed |
| `has_config_changes` | `bengal.toml` changed |
| `needs_full_rebuild` | Config/templates changed |
| `content_paths` | Changed content files |

## Performance

| Operation | Time |
|-----------|------|
| Stream overhead | ~1µs per item |
| Cache lookup | ~10µs |
| Disk cache read | ~1ms |
| Parallel speedup | ~Nx (N workers) |

For a 1,000 page site:

| Build Type | Time |
|------------|------|
| Full build | ~15s |
| Incremental (1 file) | ~0.3s |
| Incremental (cached) | ~0.1s |

## Pipeline vs Orchestrators

| Use Pipeline | Use Orchestrators |
|--------------|-------------------|
| New builds (cleaner architecture) | Existing code |
| Custom workflows | Complex dependencies |
| Watch mode | Legacy integration |

## Key Types

| Type | Purpose |
|------|---------|
| `StreamKey` | Unique item identifier (source, id, version) |
| `StreamItem[T]` | Item wrapper with key and value |
| `Pipeline` | Builder for constructing pipelines |
| `ContentDiscoveryStream` | Discovers content files |
| `FileChangeStream` | Emits changed files |
| `PipelineWatcher` | Watch + rebuild |

:::{seealso}
- [Orchestration](orchestration/) — Build coordination
- [Cache](cache/) — Cache system details
:::
