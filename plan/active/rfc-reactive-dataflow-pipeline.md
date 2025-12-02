# RFC: Reactive Dataflow Pipeline

**Status**: Draft  
**Created**: 2025-12-02  
**Author**: AI Assistant  
**Priority**: High  
**Confidence**: 85% 🟢  
**Est. Impact**: Automatic dependency tracking, simplified incremental builds, foundation for future reactivity

---

## Executive Summary

This RFC proposes adopting a **Reactive Dataflow Pipeline** architecture inspired by Zensical's `zrx` scheduler. Instead of manually tracking dependencies for incremental builds, content flows through declarative transformation streams where changes automatically propagate to affected outputs.

**Key Changes**:
1. Define build as declarative dataflow graph, not imperative steps
2. Automatic dependency tracking through stream connections
3. Fine-grained reactivity: only recompute what changed
4. Foundation for watch mode and live reload

---

## Problem Statement

### Current State

Bengal's incremental build relies on explicit dependency tracking:

```python
# bengal/cache/dependency_tracker.py
class DependencyTracker:
    """Manual dependency tracking for incremental builds."""

    def __init__(self):
        self.page_to_templates: dict[str, set[str]] = {}
        self.template_to_pages: dict[str, set[str]] = {}
        self.taxonomy_to_pages: dict[str, set[str]] = {}
        # ... more manual tracking ...

    def record_template_dependency(self, page_path: str, template: str):
        """Manually record that page depends on template."""
        self.page_to_templates[page_path].add(template)
        self.template_to_pages[template].add(page_path)
```

**Evidence**: `bengal/cache/dependency_tracker.py:1-50`

### Pain Points

1. **Manual Tracking is Error-Prone**: Every new dependency type requires explicit tracking code. Missed dependencies cause stale builds.

2. **Scattered Dependency Logic**: Tracking spread across `DependencyTracker`, `BuildCache`, `IncrementalBuilder`, making it hard to reason about.

3. **Coarse Invalidation**: When a template changes, all pages using it are rebuilt - even if only an unrelated partial changed.

4. **Complex Watch Mode**: File watcher must understand all dependency relationships to know what to rebuild.

5. **No Streaming Output**: Can't show partial results during build; must wait for all pages to complete.

### Evidence from Zensical

Zensical's `workflow.rs` shows a cleaner approach:

```rust
// Declarative pipeline - dependencies implicit in data flow
let markdown = process_markdown(&config, &files);
let page = generate_page(&config, &markdown);
let nav = generate_nav(&config, &pages);
render_pages(&config, &page, &nav);
```

When `files` emits a change, it automatically flows through `process_markdown` → `generate_page` → potentially `generate_nav` if needed → `render_pages`. No manual tracking required.

---

## Goals & Non-Goals

### Goals

1. **G1**: Define builds as declarative dataflow graphs
2. **G2**: Automatic dependency tracking via stream connections
3. **G3**: Fine-grained incremental: only recompute affected nodes
4. **G4**: Enable streaming output (show pages as they complete)
5. **G5**: Simplify watch mode (changes flow automatically)
6. **G6**: Maintain compatibility with existing Page/Site models

### Non-Goals

- **NG1**: Full reactive UI framework (this is build-time only)
- **NG2**: Real-time content updates (SSG builds once)
- **NG3**: Replacing all existing code (incremental adoption)
- **NG4**: Distributed builds (single machine for now)
- **NG5**: Rust-level performance (Python has GIL limitations)

---

## Architecture Impact

**Affected Subsystems**:

- **Core** (`bengal/core/`): Minor impact
  - Adapters for Page/Site to work with streams

- **Orchestration** (`bengal/orchestration/`): Major refactor
  - Replace imperative orchestrators with pipeline definition
  - Deprecate manual dependency tracking

- **Cache** (`bengal/cache/`): Moderate impact
  - Integrate with stream memoization
  - Simpler invalidation (node-level)

- **Discovery** (`bengal/discovery/`): Minor impact
  - Discovery becomes stream source

- **Rendering** (`bengal/rendering/`): Moderate impact
  - Rendering becomes stream transformation

**New Components**:
- `bengal/pipeline/` - Core dataflow infrastructure
- `bengal/pipeline/streams.py` - Stream primitives
- `bengal/pipeline/scheduler.py` - Execution scheduler
- `bengal/pipeline/transforms.py` - Built-in transformations

---

## Design Options

### Option A: Custom Stream Implementation (Recommended)

**Description**: Build a lightweight reactive streams library tailored to SSG needs.

```python
# bengal/pipeline/streams.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Iterator, Any

T = TypeVar('T')
U = TypeVar('U')


@dataclass
class StreamItem(Generic[T]):
    """Item flowing through a stream."""
    key: str           # Unique identifier for caching
    value: T           # The actual data
    timestamp: float   # When this was produced


class Stream(Generic[T]):
    """
    A reactive stream of values.

    Streams are lazy - transformations define a computation graph
    but don't execute until materialized.
    """

    def __init__(self, source: Callable[[], Iterator[StreamItem[T]]] | None = None):
        self._source = source
        self._transforms: list[Callable] = []
        self._cache: dict[str, StreamItem] = {}

    def map(self, fn: Callable[[T], U]) -> Stream[U]:
        """Transform each item in the stream."""
        return MappedStream(self, fn)

    def filter(self, predicate: Callable[[T], bool]) -> Stream[T]:
        """Filter items based on predicate."""
        return FilteredStream(self, predicate)

    def flat_map(self, fn: Callable[[T], Iterator[U]]) -> Stream[U]:
        """Transform each item into multiple items."""
        return FlatMappedStream(self, fn)

    def collect(self) -> Stream[list[T]]:
        """Collect all items into a single list."""
        return CollectedStream(self)

    def combine(self, other: Stream[U]) -> Stream[tuple[T, U]]:
        """Combine with another stream."""
        return CombinedStream(self, other)

    def cache(self, key_fn: Callable[[T], str] | None = None) -> Stream[T]:
        """Cache results based on key."""
        return CachedStream(self, key_fn)

    def materialize(self) -> list[StreamItem[T]]:
        """Execute the stream and return all results."""
        return list(self._iterate())

    def _iterate(self) -> Iterator[StreamItem[T]]:
        """Internal iteration - override in subclasses."""
        if self._source:
            yield from self._source()
```

**Pros**:
- Tailored to SSG requirements
- Full control over caching/memoization
- No external dependencies
- Python-idiomatic API

**Cons**:
- Need to build and maintain
- May miss edge cases reactive experts would handle
- Performance limited by Python

**Complexity**: Medium-High

---

### Option B: Use RxPY (Reactive Extensions)

**Description**: Adopt existing reactive library.

```python
from rx import operators as ops
from rx.subject import Subject

files = Subject()

pages = files.pipe(
    ops.filter(lambda f: f.endswith('.md')),
    ops.map(parse_markdown),
    ops.map(create_page),
)

nav = pages.pipe(
    ops.to_list(),
    ops.map(build_navigation),
)
```

**Pros**:
- Mature, well-tested library
- Rich operator set
- Community support

**Cons**:
- Heavy dependency (~15MB)
- Overkill for SSG use case
- Learning curve for contributors
- May not integrate well with async

**Complexity**: Medium

---

### Option C: Async Generator Composition

**Description**: Use Python's async generators with composition helpers.

```python
async def build_pipeline(files: AsyncIterator[Path]) -> AsyncIterator[Page]:
    async for path in files:
        markdown = await parse_markdown(path)
        page = await create_page(markdown)
        yield page

async def with_navigation(pages: AsyncIterator[Page]) -> AsyncIterator[RenderedPage]:
    all_pages = [p async for p in pages]
    nav = build_navigation(all_pages)
    for page in all_pages:
        yield render_page(page, nav)
```

**Pros**:
- Uses standard Python features
- Simple to understand
- Good async support

**Cons**:
- No automatic caching
- Manual dependency tracking still needed
- Limited composition operators

**Complexity**: Low

---

### Recommended: Option A (Custom Streams)

A custom implementation gives us:

1. **Exact semantics needed** for SSG (file-based keys, incremental caching)
2. **Integration with existing cache** (`BuildCache`, content hashing)
3. **Control over execution** (parallel, ordered, streaming)
4. **Simple API** without reactive programming learning curve

---

## Detailed Design

### 1. Core Stream Primitives

```python
# bengal/pipeline/core.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar, Generic, Callable, Iterator, Any, Hashable
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time

T = TypeVar('T')
U = TypeVar('U')
K = TypeVar('K', bound=Hashable)


@dataclass(frozen=True)
class StreamKey:
    """Unique identifier for a stream item."""
    source: str      # Source stream name
    id: str          # Item identifier within source
    version: str     # Content hash or timestamp

    def __str__(self) -> str:
        return f"{self.source}:{self.id}@{self.version[:8]}"


@dataclass
class StreamItem(Generic[T]):
    """
    A single item flowing through the pipeline.

    Each item has a key for caching and the actual value.
    """
    key: StreamKey
    value: T
    produced_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, source: str, id: str, value: T, version: str | None = None) -> StreamItem[T]:
        """Create a stream item with automatic version from value hash."""
        if version is None:
            version = cls._compute_hash(value)
        return cls(
            key=StreamKey(source=source, id=id, version=version),
            value=value,
        )

    @staticmethod
    def _compute_hash(value: Any) -> str:
        """Compute hash of value for versioning."""
        if hasattr(value, '__hash__') and value.__hash__ is not None:
            return hashlib.sha256(str(hash(value)).encode()).hexdigest()[:16]
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]


class Stream(ABC, Generic[T]):
    """
    Base class for reactive streams.

    Streams are lazy - they define a computation graph but don't
    execute until `run()` or `materialize()` is called.
    """

    def __init__(self, name: str | None = None):
        self.name = name or self.__class__.__name__
        self._downstream: list[Stream] = []
        self._cache: dict[StreamKey, StreamItem] = {}
        self._cache_enabled = True

    @abstractmethod
    def _produce(self) -> Iterator[StreamItem[T]]:
        """Produce items from this stream."""
        ...

    def iterate(self) -> Iterator[StreamItem[T]]:
        """Iterate over stream items with caching."""
        for item in self._produce():
            if self._cache_enabled:
                if item.key in self._cache:
                    cached = self._cache[item.key]
                    if cached.key.version == item.key.version:
                        yield cached
                        continue
                self._cache[item.key] = item
            yield item

    def materialize(self) -> list[T]:
        """Execute stream and return values."""
        return [item.value for item in self.iterate()]

    # Transformation operators

    def map(self, fn: Callable[[T], U], name: str | None = None) -> Stream[U]:
        """Transform each item."""
        return MapStream(self, fn, name=name or f"{self.name}.map")

    def filter(self, predicate: Callable[[T], bool], name: str | None = None) -> Stream[T]:
        """Filter items."""
        return FilterStream(self, predicate, name=name or f"{self.name}.filter")

    def flat_map(self, fn: Callable[[T], Iterator[U]], name: str | None = None) -> Stream[U]:
        """Transform each item into multiple items."""
        return FlatMapStream(self, fn, name=name or f"{self.name}.flat_map")

    def collect(self, name: str | None = None) -> Stream[list[T]]:
        """Collect all items into a single list."""
        return CollectStream(self, name=name or f"{self.name}.collect")

    def combine(self, *others: Stream, name: str | None = None) -> Stream[tuple]:
        """Combine with other streams (cartesian product of collected)."""
        return CombineStream(self, *others, name=name or f"{self.name}.combine")

    def parallel(self, workers: int = 4) -> Stream[T]:
        """Mark stream for parallel execution."""
        return ParallelStream(self, workers)

    def cache_to_disk(self, cache_dir: str) -> Stream[T]:
        """Enable disk caching for this stream."""
        return DiskCachedStream(self, cache_dir)

    # Terminal operators

    def for_each(self, fn: Callable[[T], None]) -> None:
        """Execute function for each item (side effect)."""
        for item in self.iterate():
            fn(item.value)

    def run(self) -> int:
        """Execute stream, return count of items processed."""
        count = 0
        for _ in self.iterate():
            count += 1
        return count


class SourceStream(Stream[T]):
    """Stream that produces items from a source function."""

    def __init__(self, producer: Callable[[], Iterator[StreamItem[T]]], name: str = "source"):
        super().__init__(name)
        self._producer = producer

    def _produce(self) -> Iterator[StreamItem[T]]:
        yield from self._producer()


class MapStream(Stream[U], Generic[T, U]):
    """Stream that transforms items."""

    def __init__(self, upstream: Stream[T], fn: Callable[[T], U], name: str = "map"):
        super().__init__(name)
        self._upstream = upstream
        self._fn = fn

    def _produce(self) -> Iterator[StreamItem[U]]:
        for item in self._upstream.iterate():
            result = self._fn(item.value)
            yield StreamItem.create(
                source=self.name,
                id=item.key.id,
                value=result,
            )


class FilterStream(Stream[T]):
    """Stream that filters items."""

    def __init__(self, upstream: Stream[T], predicate: Callable[[T], bool], name: str = "filter"):
        super().__init__(name)
        self._upstream = upstream
        self._predicate = predicate

    def _produce(self) -> Iterator[StreamItem[T]]:
        for item in self._upstream.iterate():
            if self._predicate(item.value):
                yield item


class FlatMapStream(Stream[U], Generic[T, U]):
    """Stream that transforms items into multiple items."""

    def __init__(self, upstream: Stream[T], fn: Callable[[T], Iterator[U]], name: str = "flat_map"):
        super().__init__(name)
        self._upstream = upstream
        self._fn = fn

    def _produce(self) -> Iterator[StreamItem[U]]:
        for item in self._upstream.iterate():
            for i, result in enumerate(self._fn(item.value)):
                yield StreamItem.create(
                    source=self.name,
                    id=f"{item.key.id}:{i}",
                    value=result,
                )


class CollectStream(Stream[list[T]]):
    """Stream that collects all items into a list."""

    def __init__(self, upstream: Stream[T], name: str = "collect"):
        super().__init__(name)
        self._upstream = upstream

    def _produce(self) -> Iterator[StreamItem[list[T]]]:
        items = list(self._upstream.iterate())
        values = [item.value for item in items]

        # Version is hash of all item versions
        versions = ":".join(item.key.version for item in items)
        version = hashlib.sha256(versions.encode()).hexdigest()[:16]

        yield StreamItem(
            key=StreamKey(source=self.name, id="all", version=version),
            value=values,
        )


class CombineStream(Stream[tuple]):
    """Stream that combines multiple streams."""

    def __init__(self, *upstreams: Stream, name: str = "combine"):
        super().__init__(name)
        self._upstreams = upstreams

    def _produce(self) -> Iterator[StreamItem[tuple]]:
        # Collect all upstreams
        collected = [list(s.iterate()) for s in self._upstreams]

        # If any stream is empty, yield nothing
        if not all(collected):
            return

        # Single combined item with all values
        values = tuple([items[-1].value for items in collected])
        versions = ":".join(items[-1].key.version for items in collected)
        version = hashlib.sha256(versions.encode()).hexdigest()[:16]

        yield StreamItem(
            key=StreamKey(source=self.name, id="combined", version=version),
            value=values,
        )


class ParallelStream(Stream[T]):
    """Stream that executes upstream in parallel."""

    def __init__(self, upstream: Stream[T], workers: int = 4):
        super().__init__(f"{upstream.name}.parallel")
        self._upstream = upstream
        self._workers = workers

    def _produce(self) -> Iterator[StreamItem[T]]:
        # For now, just pass through - parallel execution handled by scheduler
        yield from self._upstream.iterate()
```

### 2. Pipeline Builder

```python
# bengal/pipeline/builder.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any
import logging

from .core import Stream, SourceStream, StreamItem

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Builder for constructing build pipelines.

    Example:
        pipeline = (
            Pipeline("bengal-build")
            .source("files", discover_files)
            .map("parse", parse_markdown)
            .map("page", create_page)
            .collect("all_pages")
            .map("nav", lambda pages: build_navigation(pages))
            .combine("render_context")
            .flat_map("render", render_pages)
            .for_each("write", write_output)
        )

        pipeline.run()
    """

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self._stages: list[tuple[str, Stream]] = []
        self._current: Stream | None = None

    def source(
        self,
        name: str,
        producer: Callable[[], list[Any]] | Callable[[], Any],
    ) -> Pipeline:
        """
        Add a source stage that produces initial items.

        Args:
            name: Stage name for debugging/caching
            producer: Function that returns items (list or generator)
        """
        def make_items():
            result = producer()
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                for i, item in enumerate(result):
                    yield StreamItem.create(
                        source=name,
                        id=self._get_item_id(item, i),
                        value=item,
                    )

        stream = SourceStream(make_items, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def map(self, name: str, fn: Callable) -> Pipeline:
        """Add a map transformation stage."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        stream = self._current.map(fn, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def filter(self, name: str, predicate: Callable) -> Pipeline:
        """Add a filter stage."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        stream = self._current.filter(predicate, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def flat_map(self, name: str, fn: Callable) -> Pipeline:
        """Add a flat_map stage."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        stream = self._current.flat_map(fn, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def collect(self, name: str = "collect") -> Pipeline:
        """Collect all items into a list."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        stream = self._current.collect(name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def combine(self, *other_pipelines: Pipeline, name: str = "combine") -> Pipeline:
        """Combine with other pipelines."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        other_streams = [p._current for p in other_pipelines if p._current]
        stream = self._current.combine(*other_streams, name=name)
        self._stages.append((name, stream))
        self._current = stream
        return self

    def parallel(self, workers: int = 4) -> Pipeline:
        """Enable parallel execution for current stage."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        self._current = self._current.parallel(workers)
        return self

    def for_each(self, name: str, fn: Callable) -> Pipeline:
        """Add a side-effect stage."""
        if self._current is None:
            raise ValueError("Pipeline has no source")

        # Store function for execution
        self._side_effects = getattr(self, '_side_effects', [])
        self._side_effects.append((name, fn))
        return self

    def run(self) -> PipelineResult:
        """Execute the pipeline."""
        if self._current is None:
            raise ValueError("Pipeline has no stages")

        logger.info(f"Running pipeline: {self.name}")
        start_time = __import__('time').time()

        count = 0
        errors = []

        try:
            for item in self._current.iterate():
                # Execute side effects
                for effect_name, fn in getattr(self, '_side_effects', []):
                    try:
                        fn(item.value)
                    except Exception as e:
                        errors.append((effect_name, item.key, e))
                        logger.error(f"Error in {effect_name}: {e}")
                count += 1
        except Exception as e:
            errors.append(("pipeline", None, e))
            logger.error(f"Pipeline error: {e}")

        elapsed = __import__('time').time() - start_time
        logger.info(f"Pipeline complete: {count} items in {elapsed:.2f}s")

        return PipelineResult(
            name=self.name,
            items_processed=count,
            elapsed_seconds=elapsed,
            errors=errors,
        )

    def _get_item_id(self, item: Any, index: int) -> str:
        """Get unique ID for an item."""
        if hasattr(item, 'path'):
            return str(item.path)
        if hasattr(item, 'id'):
            return str(item.id)
        if hasattr(item, 'slug'):
            return str(item.slug)
        return str(index)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    name: str
    items_processed: int
    elapsed_seconds: float
    errors: list[tuple[str, Any, Exception]]

    @property
    def success(self) -> bool:
        return len(self.errors) == 0
```

### 3. Bengal Build Pipeline

```python
# bengal/pipeline/build.py
from __future__ import annotations

from pathlib import Path
from typing import Iterator
import logging

from .builder import Pipeline
from ..core.page import Page
from ..core.site import Site
from ..discovery.content_discovery import ContentDiscovery
from ..rendering.renderer import Renderer

logger = logging.getLogger(__name__)


def create_build_pipeline(site: Site) -> Pipeline:
    """
    Create the main Bengal build pipeline.

    The pipeline flows:

    files → markdown → pages → [collect] → navigation
                          ↓           ↓
                       render ← ← ← ←┘
                          ↓
                       write
    """
    discovery = ContentDiscovery(site.content_dir)
    renderer = Renderer(site)

    # Content pipeline
    content_pipeline = (
        Pipeline("content")
        .source("discover", lambda: discovery.discover_files())
        .filter("markdown", lambda f: f.suffix == ".md")
        .map("parse", lambda f: discovery.parse_file(f))
        .map("page", lambda parsed: Page.from_parsed(site, parsed))
        .parallel(workers=4)
    )

    # Navigation pipeline (needs all pages)
    nav_pipeline = (
        Pipeline("navigation")
        .source("pages", lambda: content_pipeline._current.materialize())
        .collect("all")
        .map("build_nav", lambda pages: site.build_navigation(pages))
    )

    # Render pipeline (combines pages with navigation)
    render_pipeline = (
        Pipeline("render")
        .source("pages", lambda: content_pipeline._current.materialize())
        .map("with_nav", lambda page: (page, nav_pipeline._current.materialize()[0]))
        .map("render", lambda args: renderer.render_page(*args))
        .parallel(workers=4)
        .for_each("write", lambda rendered: write_output(site, rendered))
    )

    return render_pipeline


def create_incremental_pipeline(site: Site, changed_files: list[Path]) -> Pipeline:
    """
    Create an incremental build pipeline for changed files only.

    This pipeline:
    1. Only processes changed files
    2. Reuses cached pages for unchanged files
    3. Rebuilds navigation only if structure changed
    4. Re-renders only affected pages
    """
    discovery = ContentDiscovery(site.content_dir)
    renderer = Renderer(site)
    cache = site.build_cache

    def get_pages() -> Iterator[Page]:
        """Yield pages, using cache for unchanged files."""
        for file in discovery.discover_files():
            if file in changed_files:
                # Parse fresh
                parsed = discovery.parse_file(file)
                page = Page.from_parsed(site, parsed)
                cache.store_page(page)
                yield page
            else:
                # Use cached
                cached = cache.get_page(file)
                if cached:
                    yield cached
                else:
                    # Cache miss - parse
                    parsed = discovery.parse_file(file)
                    page = Page.from_parsed(site, parsed)
                    cache.store_page(page)
                    yield page

    def needs_nav_rebuild(pages: list[Page]) -> bool:
        """Check if navigation needs rebuilding."""
        # Rebuild if any changed file affects structure
        for page in pages:
            if page.source_path in changed_files:
                if page.weight_changed or page.title_changed:
                    return True
        return False

    pipeline = (
        Pipeline("incremental")
        .source("pages", get_pages)
        .collect("all")
        .map("maybe_nav", lambda pages: (
            pages,
            site.build_navigation(pages) if needs_nav_rebuild(pages) else cache.get_navigation()
        ))
        .flat_map("to_render", lambda args: (
            (page, args[1]) for page in args[0] if page.source_path in changed_files
        ))
        .map("render", lambda args: renderer.render_page(*args))
        .parallel(workers=4)
        .for_each("write", lambda rendered: write_output(site, rendered))
    )

    return pipeline


def write_output(site: Site, rendered: RenderedPage) -> None:
    """Write rendered page to disk."""
    output_path = site.output_dir / rendered.relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.html)
    logger.debug(f"Wrote: {rendered.relative_path}")
```

### 4. Integration with Existing Site

```python
# bengal/core/site.py (additions)

class Site:
    """Site with pipeline support."""

    def build(self, incremental: bool = True) -> BuildResult:
        """Build site using reactive pipeline."""
        from bengal.pipeline.build import create_build_pipeline, create_incremental_pipeline

        if incremental and self.build_cache.exists():
            changed = self._detect_changed_files()
            if changed:
                pipeline = create_incremental_pipeline(self, changed)
            else:
                logger.info("No changes detected, skipping build")
                return BuildResult(pages_built=0, cached=True)
        else:
            pipeline = create_build_pipeline(self)

        result = pipeline.run()

        return BuildResult(
            pages_built=result.items_processed,
            elapsed=result.elapsed_seconds,
            errors=result.errors,
        )

    def watch(self) -> None:
        """Watch for changes and rebuild incrementally."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class RebuildHandler(FileSystemEventHandler):
            def __init__(self, site: Site):
                self.site = site
                self._pending: set[Path] = set()
                self._debounce_timer = None

            def on_modified(self, event):
                if event.src_path.endswith('.md'):
                    self._pending.add(Path(event.src_path))
                    self._schedule_rebuild()

            def _schedule_rebuild(self):
                # Debounce rapid changes
                if self._debounce_timer:
                    self._debounce_timer.cancel()

                import threading
                self._debounce_timer = threading.Timer(0.5, self._rebuild)
                self._debounce_timer.start()

            def _rebuild(self):
                changed = list(self._pending)
                self._pending.clear()

                pipeline = create_incremental_pipeline(self.site, changed)
                result = pipeline.run()

                logger.info(f"Rebuilt {result.items_processed} pages")

        observer = Observer()
        observer.schedule(RebuildHandler(self), str(self.content_dir), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
```

### Data Flow Diagram

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

                          Automatic Dependency Flow

  When a file changes:

  file_change → parse → page → [automatic] → nav_rebuild? → render → write
                                    │              │
                                    └──────────────┘
                                    Only if needed
```

---

## Implementation Plan

### Phase 1: Core Stream Primitives (Week 1)

- [ ] Create `bengal/pipeline/` package
- [ ] Implement `StreamItem` and `StreamKey`
- [ ] Implement base `Stream` class
- [ ] Implement `MapStream`, `FilterStream`, `FlatMapStream`
- [ ] Implement `CollectStream`, `CombineStream`
- [ ] Unit tests for all stream types

### Phase 2: Pipeline Builder (Week 1-2)

- [ ] Implement `Pipeline` builder class
- [ ] Implement `PipelineResult`
- [ ] Add parallel execution support
- [ ] Add logging and debugging
- [ ] Unit tests for pipeline composition

### Phase 3: Bengal Integration (Week 2-3)

- [ ] Create `create_build_pipeline()` function
- [ ] Create `create_incremental_pipeline()` function
- [ ] Integrate with existing `Site.build()`
- [ ] Maintain backward compatibility with `--no-pipeline` flag
- [ ] Integration tests

### Phase 4: Caching Integration (Week 3)

- [ ] Integrate stream caching with `BuildCache`
- [ ] Add disk caching for streams
- [ ] Implement version-based cache invalidation
- [ ] Benchmark cache hit rates

### Phase 5: Watch Mode (Week 4)

- [ ] Implement `Site.watch()` with pipeline
- [ ] Add file change detection
- [ ] Add debouncing for rapid changes
- [ ] Test watch mode end-to-end

### Phase 6: Documentation & Migration (Week 4)

- [ ] Document pipeline architecture
- [ ] Add examples for custom pipelines
- [ ] Migration guide from imperative orchestrators
- [ ] Performance comparison documentation

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Automatic dependency tracking | Explicit control over rebuild order |
| Declarative pipeline definition | Familiar imperative code |
| Fine-grained incremental | Some cache overhead |
| Streaming output | Simpler mental model |

### Risks

#### Risk 1: Performance Overhead

**Description**: Stream abstraction adds overhead

- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Lazy evaluation (no overhead for unchanged items)
  - Optimize hot paths
  - Benchmark against current implementation
  - Parallel execution compensates

#### Risk 2: Debugging Complexity

**Description**: Stack traces harder to read

- **Likelihood**: High
- **Impact**: Low
- **Mitigation**:
  - Add stream names to errors
  - Implement `.debug()` operator for logging
  - Good error messages with context

#### Risk 3: Learning Curve

**Description**: Contributors unfamiliar with reactive patterns

- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Extensive documentation
  - Simple API (map/filter/collect)
  - Examples for common patterns
  - Keep imperative orchestrators as fallback

#### Risk 4: GIL Limitations

**Description**: Python's GIL limits parallelism

- **Likelihood**: High
- **Impact**: Medium
- **Mitigation**:
  - Use ProcessPoolExecutor for CPU-bound work
  - Async I/O for network operations
  - Document parallel limitations
  - Consider Rust acceleration for hot paths

---

## Future Considerations

1. **Async Streams**: Full async/await support for I/O-bound operations
2. **Distributed Execution**: Split pipeline across multiple processes
3. **Stream Visualization**: Debug tool showing dataflow graph
4. **Hot Module Reload**: Update pipeline without full rebuild
5. **Rust Core**: Accelerate stream primitives with Rust (like Zensical)

---

## Related Work

- [Zensical zrx Scheduler](../zensical/crates/zensical/src/workflow.rs)
- [RxPY](https://rxpy.readthedocs.io/) - Reactive Extensions for Python
- [Apache Beam](https://beam.apache.org/) - Unified batch/streaming
- [Dask](https://dask.org/) - Parallel computing with task graphs
- [Prefect](https://www.prefect.io/) - Dataflow automation

---

## Approval

- [ ] RFC reviewed
- [ ] Stream API approved
- [ ] Pipeline builder approved
- [ ] Implementation plan approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] At least 2 design options analyzed (3 provided)
- [x] Recommended option justified
- [x] Architecture impact documented
- [x] Risks identified with mitigations
- [x] Implementation phases defined (4 weeks)
- [x] Code examples provided
- [x] Confidence ≥ 85% (85%)
