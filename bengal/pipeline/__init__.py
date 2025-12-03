"""
Reactive Dataflow Pipeline for Bengal.

This package provides a declarative dataflow architecture for building
sites. Instead of manually tracking dependencies for incremental builds,
content flows through transformation streams where changes automatically
propagate to affected outputs.

Key Components:
    - Stream: Base class for reactive streams
    - StreamItem: Items flowing through streams with caching metadata
    - Pipeline: Builder for constructing build pipelines
    - Operators: map, filter, flat_map, collect, combine

Architecture:
    Builds are defined as declarative dataflow graphs, not imperative steps.
    Dependencies are implicit in stream connections - no manual tracking.
    Fine-grained reactivity ensures only affected nodes recompute.

Example:
    >>> from bengal.pipeline import Pipeline
    >>> pipeline = (
    ...     Pipeline("build")
    ...     .source("files", discover_files)
    ...     .filter("markdown", lambda f: f.suffix == ".md")
    ...     .map("parse", parse_markdown)
    ...     .map("page", create_page)
    ...     .parallel(workers=4)
    ...     .for_each("write", write_output)
    ... )
    >>> result = pipeline.run()

Related:
    - bengal/orchestration/ - Legacy imperative orchestrators (being replaced)
    - bengal/cache/ - Integrates with stream memoization
    - plan/active/rfc-reactive-dataflow-pipeline.md - Full RFC
"""

from __future__ import annotations

# Bengal-specific streams and factories
from bengal.pipeline.bengal_streams import (
    ContentDiscoveryStream,
    FileChangeStream,
    ParsedContent,
    RenderedPage,
    create_content_stream,
    create_page_stream,
    create_render_stream,
    write_output,
)
from bengal.pipeline.build import (
    create_build_pipeline,
    create_incremental_pipeline,
    create_simple_pipeline,
)
from bengal.pipeline.builder import (
    Pipeline,
    PipelineResult,
)

# Cache integration (extends Stream with disk_cache method)
from bengal.pipeline.cache import (
    DiskCachedStream,
    StreamCache,
    StreamCacheEntry,
)
from bengal.pipeline.core import (
    Stream,
    StreamItem,
    StreamKey,
)
from bengal.pipeline.streams import (
    CachedStream,
    CollectStream,
    CombineStream,
    FilterStream,
    FlatMapStream,
    MapStream,
    ParallelStream,
    SourceStream,
)

# File watching for watch mode
from bengal.pipeline.watcher import (
    ChangeType,
    FileWatcher,
    PipelineWatcher,
    WatchBatch,
    WatchEvent,
)

__all__ = [
    # Core
    "Stream",
    "StreamItem",
    "StreamKey",
    # Stream types
    "SourceStream",
    "MapStream",
    "FilterStream",
    "FlatMapStream",
    "CollectStream",
    "CombineStream",
    "CachedStream",
    "ParallelStream",
    # Builder
    "Pipeline",
    "PipelineResult",
    # Bengal streams
    "ContentDiscoveryStream",
    "FileChangeStream",
    "ParsedContent",
    "RenderedPage",
    "create_content_stream",
    "create_page_stream",
    "create_render_stream",
    "write_output",
    # Build factories
    "create_build_pipeline",
    "create_incremental_pipeline",
    "create_simple_pipeline",
    # Cache
    "StreamCache",
    "StreamCacheEntry",
    "DiskCachedStream",
    # Watcher
    "FileWatcher",
    "PipelineWatcher",
    "WatchEvent",
    "WatchBatch",
    "ChangeType",
]
