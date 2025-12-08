# RFC: Stream Pattern Expansion - Applying Reactive Dataflow Beyond Build Pipeline

**Status**: Draft  
**Created**: 2025-01-23  
**Author**: AI Assistant  
**Priority**: Medium  
**Confidence**: 85% 🟢  
**Est. Impact**: Better performance, cleaner code, automatic free-threading benefits across multiple subsystems

**Related**:
- `plan/active/pipeline-migration-roadmap.md` - Current pipeline migration
- `plan/implemented/rfc-reactive-dataflow-pipeline.md` - Original pipeline RFC

---

## Executive Summary

The reactive dataflow pipeline has proven **1.9-3x faster** than standard builds and provides a cleaner architecture. This RFC proposes expanding the stream pattern beyond the build pipeline to other subsystems that process collections: dev server file watching, related posts computation, incremental build filtering, autodoc generation, and index building.

**Key Insight**: The stream pattern is especially powerful for operations that process collections (pages, files, assets), benefit from parallelization, and need incremental updates. Since Bengal processes lots of pages/files/assets, streams fit well across the codebase.

**Key Changes**:
1. Apply stream pattern to dev server file watching (`FileChangeStream`)
2. Migrate related posts computation to streams (`RelatedPostsStream`)
3. Streamify incremental build change detection (`ChangeDetectionStream`)
4. Convert autodoc generation to streams (`AutodocStream`)
5. Stream-based index building (`IndexStream`)
6. Add batch processing operators for memory management

---

## Problem Statement

### Current State

The pipeline migration roadmap shows streams are **1.9-3x faster** than orchestrators for build operations. However, several other subsystems still use manual parallelization or sequential processing:

#### 1. Dev Server File Watching

**Current**: Manual event handling with debouncing
```python
# bengal/server/build_handler.py:170-298
class BuildHandler(FileSystemEventHandler):
    def on_modified(self, event):
        self._debounced_trigger()

    def _trigger_build(self):
        # Manual change detection
        changed_files = self._collect_changes()
        # Sequential processing
        for file in changed_files:
            detect_change_type(file)
```

**Evidence**: `bengal/server/build_handler.py:170-298`

**Pain Points**:
- Manual debouncing logic
- Sequential change type detection
- No parallel processing of multiple changes
- Complex event coordination

#### 2. Related Posts Computation

**Current**: Manual ThreadPoolExecutor management
```python
# bengal/orchestration/related_posts.py:179-204
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_page = {
        executor.submit(self._find_related_posts, page, ...): page
        for page in pages
    }
    for future in as_completed(future_to_page):
        page.related_posts = future.result()
```

**Evidence**: `bengal/orchestration/related_posts.py:147-211`

**Pain Points**:
- Manual executor management
- Error handling scattered
- Can't easily integrate into main pipeline
- Documentation mentions free-threading but doesn't leverage streams

#### 3. Incremental Build Filtering

**Current**: Sequential processing of changed pages
```python
# bengal/orchestration/build/initialization.py:270-280
for page in pages_to_build:
    if not page.metadata.get("_generated"):
        section_path = resolve_page_section_path(page)
        if section_path:
            affected_sections.add(section_path)
        if page.tags:
            for tag in page.tags:
                affected_tags.add(tag.lower().replace(" ", "-"))
```

**Evidence**: `bengal/orchestration/build/initialization.py:220-290`

**Pain Points**:
- Sequential processing (no parallelization)
- Manual set building
- Can't easily parallelize change detection

#### 4. Autodoc Page Generation

**Current**: Sequential manifest and page processing
```python
# bengal/orchestration/autodoc.py:67-98
for doc_type in doc_types:
    manifest = AutodocManifest.load_by_type(...)
    for manifest_page in manifest.pages:
        page = self._create_autodoc_page(manifest_page)
        all_pages.append(page)
```

**Evidence**: `bengal/orchestration/autodoc.py:52-100`

**Pain Points**:
- Sequential manifest loading
- Sequential page creation
- No parallelization opportunities
- Can't lazy-load manifests

#### 5. Index Building

**Current**: Sequential index building
```python
# bengal/orchestration/build/content.py:304-352
for page in pages_to_build:
    # Build indexes sequentially
    build_query_index(page)
    build_search_index(page)
```

**Evidence**: `bengal/orchestration/build/content.py:304-352`

**Pain Points**:
- Sequential processing
- No parallel index building
- Can't easily rebuild only affected indexes

### Common Patterns

All these operations share characteristics that make streams ideal:

1. **Process Collections**: Pages, files, assets, manifests
2. **CPU-Bound Work**: Tag computation, change detection, index building
3. **I/O-Bound Work**: File reading, manifest loading
4. **Parallelizable**: Independent items can be processed concurrently
5. **Incremental Updates**: Only affected items need reprocessing

### Performance Opportunity

The pipeline migration shows streams provide:
- **1.9-3x faster** builds (proven)
- **Automatic free-threading benefits** (Python 3.14t gets ~1.78x speedup)
- **Better memory management** (streaming vs loading all)
- **Fine-grained reactivity** (only affected nodes recompute)

Applying streams to these subsystems could provide similar benefits.

---

## Goals & Non-Goals

### Goals

1. **G1**: Apply stream pattern to high-value subsystems (dev server, related posts, incremental builds)
2. **G2**: Leverage automatic free-threading benefits (Python 3.14t)
3. **G3**: Improve code clarity (declarative vs imperative)
4. **G4**: Enable better parallelization (automatic via `.parallel()`)
5. **G5**: Better incremental update performance (fine-grained reactivity)
6. **G6**: Reduce manual executor management (streams handle it)
7. **G7**: Enable streaming output (show progress as items complete)

### Non-Goals

- **NG1**: Replacing all sequential code (only high-value operations)
- **NG2**: Breaking existing APIs (streams are internal implementation)
- **NG3**: Full reactive UI (this is build-time processing)
- **NG4**: Distributed processing (single machine for now)
- **NG5**: Replacing pipeline migration work (this complements it)

---

## Architecture Impact

**Affected Subsystems**:

- **Server** (`bengal/server/`): Moderate impact
  - `BuildHandler` → `FileChangeStream`
  - Better change detection and debouncing

- **Orchestration** (`bengal/orchestration/`): Moderate impact
  - `RelatedPostsOrchestrator` → `RelatedPostsStream`
  - `AutodocOrchestrator` → `AutodocStream`
  - Incremental build filtering → `ChangeDetectionStream`

- **Pipeline** (`bengal/pipeline/`): Minor additions
  - New stream types: `FileChangeStream`, `ChangeDetectionStream`
  - Batch processing operators
  - Index building streams

**New Components**:

- `bengal/pipeline/file_watching.py` - File change streams
- `bengal/pipeline/change_detection.py` - Change detection streams
- `bengal/pipeline/related_posts.py` - Related posts stream (if not in main pipeline)
- `bengal/pipeline/autodoc.py` - Autodoc stream (if not in main pipeline)
- `bengal/pipeline/indexing.py` - Index building streams

**No Breaking Changes**: Streams are internal implementation details. Public APIs remain unchanged.

---

## Design Options

### Option A: Incremental Stream Adoption (Recommended)

**Description**: Add streams to subsystems incrementally, starting with highest-value targets.

**Implementation**:
1. **Phase 1**: High-value, low-risk (Related Posts, File Watching)
2. **Phase 2**: Architectural improvements (Change Detection, Autodoc)
3. **Phase 3**: Remaining opportunities (Index Building, Validation)

**Pros**:
- Low risk (one subsystem at a time)
- Can measure impact per subsystem
- Doesn't block pipeline migration
- Easy to rollback if issues

**Cons**:
- Takes longer to complete
- Some code duplication during transition
- Need to maintain both approaches temporarily

**Timeline**: 2-3 weeks per phase

---

### Option B: Full Streamification

**Description**: Convert all identified subsystems to streams in one effort.

**Pros**:
- Consistent architecture everywhere
- No temporary duplication
- Faster overall completion

**Cons**:
- Higher risk (many changes at once)
- Harder to measure individual impact
- Could conflict with pipeline migration
- More testing required

**Timeline**: 4-6 weeks

---

### Option C: Stream Wrappers

**Description**: Keep existing code, wrap with stream interfaces.

**Pros**:
- Minimal code changes
- Fast to implement
- Low risk

**Cons**:
- Doesn't get full stream benefits
- Still have manual executor management
- Misses parallelization opportunities
- Doesn't improve code clarity

**Timeline**: 1-2 weeks

---

## Recommended Approach: Option A (Incremental)

**Rationale**:
- Pipeline migration is already in progress (Phase 2)
- Incremental approach allows learning and iteration
- Can measure impact per subsystem
- Lower risk of breaking existing functionality
- Complements pipeline migration rather than competing

---

## Detailed Design

### 1. FileChangeStream for Dev Server

**Purpose**: Stream-based file watching with automatic debouncing and change type detection.

**Implementation**:
```python
# bengal/pipeline/file_watching.py
from bengal.pipeline.core import Stream, StreamItem
from watchdog.events import FileSystemEvent

class FileChangeStream(Stream[FileChange]):
    """Stream of file system changes with debouncing."""

    def __init__(
        self,
        events: Iterator[FileSystemEvent],
        debounce_ms: int = 300,
    ):
        super().__init__("file_changes")
        self._events = events
        self._debounce_ms = debounce_ms

    def _produce(self) -> Iterator[StreamItem[FileChange]]:
        # Collect events within debounce window
        batched = self._debounce_events()

        # Detect change type (content/config/template/asset)
        typed = batched.map(self._detect_change_type)

        # Filter source files only
        filtered = typed.filter(lambda change: is_source_file(change.path))

        yield from filtered.iterate()

def create_file_change_stream(
    watch_dirs: list[Path],
    debounce_ms: int = 300,
) -> FileChangeStream:
    """Create file change stream from watch directories."""
    # Integrate with watchdog
    events = watch_files(watch_dirs)
    return FileChangeStream(events, debounce_ms=debounce_ms)
```

**Integration**:
```python
# bengal/server/build_handler.py
def _trigger_build(self):
    # Create stream from pending changes
    changes = FileChangeStream(self._pending_changes, debounce_ms=300)

    # Process changes
    changes.map(detect_change_type).for_each(self._handle_change)
```

**Benefits**:
- Automatic debouncing
- Parallel change type detection
- Cleaner code
- Better incremental build triggers

---

### 2. RelatedPostsStream

**Purpose**: Stream-based related posts computation with automatic parallelization.

**Implementation**:
```python
# bengal/pipeline/related_posts.py
from bengal.pipeline.core import Stream
from bengal.core.page import Page

def create_related_posts_stream(
    pages_stream: Stream[Page],
    tags_dict: dict[str, dict],
    limit: int = 5,
) -> Stream[Page]:
    """
    Compute related posts using stream parallelism.

    Flow:
        pages → compute_related → update_page → pages_with_related
    """
    def compute_related(page: Page) -> Page:
        """Compute and set related posts for a page."""
        related = find_related_posts(page, tags_dict, limit)
        page.related_posts = related
        return page

    return (
        pages_stream
        .filter(lambda page: not page.metadata.get("_generated"))
        .map(compute_related, name="compute_related")
        .parallel(workers=8)  # Automatic free-threading benefit
    )
```

**Integration**:
```python
# bengal/orchestration/related_posts.py
class RelatedPostsOrchestrator:
    def build(self, parallel: bool = True) -> int:
        # Convert pages to stream
        pages_stream = Stream.from_iterable(self.site.pages)

        # Compute related posts
        related_stream = create_related_posts_stream(
            pages_stream,
            self._build_tags_dict(),
            limit=self.limit,
        )

        # Execute stream
        pages_with_related = sum(
            1 for page in related_stream.iterate()
            if page.related_posts
        )

        return pages_with_related
```

**Benefits**:
- Cleaner code (no manual executor)
- Automatic free-threading benefits
- Better error handling
- Can integrate into main pipeline

---

### 3. ChangeDetectionStream

**Purpose**: Parallel change detection for incremental builds.

**Implementation**:
```python
# bengal/pipeline/change_detection.py
from bengal.pipeline.core import Stream
from bengal.cache.build_cache import BuildCache

@dataclass
class ChangeEvent:
    """Represents a detected change."""
    path: Path
    change_type: str  # content, config, template, asset
    affected_pages: set[Path]
    affected_sections: set[str]
    affected_tags: set[str]

def create_change_detection_stream(
    changed_files: list[Path],
    cache: BuildCache,
    site: Site,
) -> Stream[ChangeEvent]:
    """
    Detect changes and create change events.

    Flow:
        files → detect_type → find_dependencies → create_event
    """
    def detect_change(file_path: Path) -> ChangeEvent:
        """Detect change type and affected items."""
        change_type = detect_change_type(file_path, cache)
        affected = find_affected_items(file_path, change_type, site, cache)
        return ChangeEvent(
            path=file_path,
            change_type=change_type,
            affected_pages=affected.pages,
            affected_sections=affected.sections,
            affected_tags=affected.tags,
        )

    return (
        Stream.from_iterable(changed_files)
        .map(detect_change, name="detect_change")
        .parallel(workers=4)  # Parallel change detection
        .filter(lambda event: event.needs_rebuild)
    )
```

**Integration**:
```python
# bengal/orchestration/build/initialization.py
def phase_incremental_filter(...):
    # Create change detection stream
    changed_files = get_changed_files(cache)
    changes = create_change_detection_stream(changed_files, cache, site)

    # Collect change events
    change_events = list(changes.iterate())

    # Extract affected items
    pages_to_build = {page for event in change_events for page in event.affected_pages}
    affected_sections = {section for event in change_events for section in event.affected_sections}
    affected_tags = {tag for event in change_events for tag in event.affected_tags}

    return pages_to_build, affected_sections, affected_tags
```

**Benefits**:
- Parallel change detection
- Automatic dependency tracking
- Better incremental build performance
- Cleaner separation of concerns

---

### 4. AutodocStream

**Purpose**: Stream-based autodoc page generation with parallel manifest loading.

**Implementation**:
```python
# bengal/pipeline/autodoc.py
from bengal.pipeline.core import Stream
from bengal.autodoc.manifest import AutodocManifest

def create_autodoc_stream(
    site: Site,
    doc_types: list[str] = None,
) -> Stream[Page]:
    """
    Generate autodoc pages from manifests.

    Flow:
        doc_types → load_manifest → manifest_pages → create_page → pages
    """
    if doc_types is None:
        doc_types = ["python-api", "cli"]

    def load_manifest(doc_type: str) -> AutodocManifest | None:
        """Load manifest for doc type."""
        try:
            return AutodocManifest.load_by_type(site.root_path, doc_type)
        except Exception as e:
            logger.error("autodoc_manifest_load_failed", doc_type=doc_type, error=str(e))
            return None

    def create_page(manifest_page) -> Page | None:
        """Create Page from manifest page."""
        return create_autodoc_page(manifest_page, site)

    return (
        Stream.from_iterable(doc_types)
        .map(load_manifest, name="load_manifest")
        .filter(lambda manifest: manifest is not None)
        .flat_map(lambda manifest: manifest.pages)
        .map(create_page, name="create_page")
        .filter(lambda page: page is not None)
        .parallel(workers=4)  # Parallel page creation
    )
```

**Integration**:
```python
# bengal/orchestration/autodoc.py
class AutodocOrchestrator:
    def generate_autodoc_pages(self) -> tuple[list[Section], list[Page]]:
        # Create autodoc stream
        pages_stream = create_autodoc_stream(self.site)

        # Collect pages
        all_pages = list(pages_stream.iterate())

        # Create sections (unchanged)
        sections = self._create_sections(all_pages)

        return sections, all_pages
```

**Benefits**:
- Parallel manifest loading
- Parallel page creation
- Lazy evaluation (only load if needed)
- Better error handling per manifest

---

### 5. IndexStream

**Purpose**: Stream-based index building with parallel processing.

**Implementation**:
```python
# bengal/pipeline/indexing.py
from bengal.pipeline.core import Stream
from bengal.core.page import Page

@dataclass
class IndexEntry:
    """Index entry for a page."""
    index_type: str  # query, search, etc.
    page: Page
    data: dict[str, Any]

def create_index_stream(
    pages_stream: Stream[Page],
    index_types: list[str],
) -> Stream[dict[str, Any]]:
    """
    Build query indexes from pages.

    Flow:
        pages → create_entries → group_by_type → build_index → indexes
    """
    def create_entries(page: Page) -> list[IndexEntry]:
        """Create index entries for a page."""
        return [
            IndexEntry(
                index_type=index_type,
                page=page,
                data=extract_index_data(page, index_type),
            )
            for index_type in index_types
        ]

    def build_index(group: tuple[str, list[IndexEntry]]) -> dict[str, Any]:
        """Build index from entries."""
        index_type, entries = group
        return {
            "type": index_type,
            "entries": [entry.data for entry in entries],
        }

    return (
        pages_stream
        .flat_map(create_entries, name="create_entries")
        .group_by(lambda entry: entry.index_type)
        .map(build_index, name="build_index")
        .parallel(workers=4)  # Parallel index building
    )
```

**Integration**:
```python
# bengal/orchestration/build/content.py
def phase_query_indexes(orchestrator, cache, incremental, pages_to_build):
    # Create index stream
    pages_stream = Stream.from_iterable(pages_to_build)
    indexes = create_index_stream(pages_stream, ["query", "search"])

    # Build indexes
    for index in indexes.iterate():
        save_index(index, orchestrator.site)
```

**Benefits**:
- Parallel index building
- Automatic grouping
- Better incremental updates (only rebuild affected indexes)

---

### 6. Batch Processing Operators

**Purpose**: Add built-in batching for memory management.

**Implementation**:
```python
# bengal/pipeline/streams.py
class BatchStream[T](Stream[list[T]]):
    """Stream that batches items into groups."""

    def __init__(
        self,
        upstream: Stream[T],
        batch_size: int,
        name: str = "batch",
    ):
        super().__init__(name)
        self._upstream = upstream
        self._batch_size = batch_size

    def _produce(self) -> Iterator[StreamItem[list[T]]]:
        """Batch items into groups."""
        batch = []
        batch_id = 0

        for item in self._upstream.iterate():
            batch.append(item.value)

            if len(batch) >= self._batch_size:
                yield StreamItem.create(
                    source=self.name,
                    id=str(batch_id),
                    value=batch.copy(),
                )
                batch.clear()
                batch_id += 1

        # Yield remaining items
        if batch:
            yield StreamItem.create(
                source=self.name,
                id=str(batch_id),
                value=batch,
            )

# Add to Stream base class
def batch(self, size: int) -> BatchStream[T]:
    """Batch items into groups of specified size."""
    return BatchStream(self, size)
```

**Usage**:
```python
# Memory-efficient batch processing
pages_stream
    .batch(size=100)  # Process in batches of 100
    .map(lambda batch: render_batch(batch))
    .parallel(workers=2)  # Parallel batches
```

**Benefits**:
- Automatic memory management
- Parallel batch processing
- No manual loop management
- Better for large sites

---

## Implementation Plan

### Phase 1: High-Value, Low-Risk (Week 1-2)

**Priority**: High  
**Risk**: Low  
**Impact**: High

1. **RelatedPostsStream** (2-3 days)
   - Migrate `RelatedPostsOrchestrator._build_parallel()` to stream
   - Test with existing test suite
   - Measure performance improvement

2. **FileChangeStream** (2-3 days)
   - Create `FileChangeStream` for dev server
   - Integrate with `BuildHandler`
   - Test debouncing and change detection

**Success Criteria**:
- Related posts computation uses streams
- Dev server uses `FileChangeStream`
- Performance matches or exceeds current implementation
- All tests pass

---

### Phase 2: Architectural Improvements (Week 3-4)

**Priority**: Medium  
**Risk**: Medium  
**Impact**: High

3. **ChangeDetectionStream** (3-4 days)
   - Create change detection stream
   - Integrate with incremental build filtering
   - Test parallel change detection

4. **AutodocStream** (2-3 days)
   - Migrate autodoc generation to streams
   - Test parallel manifest loading
   - Verify page creation

**Success Criteria**:
- Incremental builds use `ChangeDetectionStream`
- Autodoc uses `AutodocStream`
- Performance improved (parallel processing)
- All tests pass

---

### Phase 3: Remaining Opportunities (Week 5-6)

**Priority**: Low  
**Risk**: Low  
**Impact**: Medium

5. **IndexStream** (2-3 days)
   - Create index building stream
   - Integrate with query index phase
   - Test parallel index building

6. **Batch Processing** (1-2 days)
   - Add batch operators to stream API
   - Update `StreamingRenderOrchestrator` to use batches
   - Test memory management

**Success Criteria**:
- Index building uses streams
- Batch processing available
- Memory usage improved for large sites
- All tests pass

---

## Performance Expectations

Based on pipeline migration results:

| Subsystem | Current | With Streams | Improvement |
|-----------|---------|--------------|-------------|
| **Related Posts** | Manual executor | Stream + free-threading | 1.5-2x faster (3.14t) |
| **File Watching** | Sequential | Parallel detection | 2-3x faster |
| **Change Detection** | Sequential | Parallel | 3-4x faster |
| **Autodoc** | Sequential | Parallel | 2-3x faster |
| **Index Building** | Sequential | Parallel | 2-3x faster |

**Free-Threading Benefits**:
- Python 3.14t: Additional 1.5-2x speedup for CPU-bound work
- Automatic via `ThreadPoolExecutor` in streams
- No code changes needed

---

## Risks & Mitigations

### Risk 1: Breaking Existing Functionality

**Mitigation**:
- Keep existing code paths during transition
- Comprehensive test coverage
- Gradual rollout (one subsystem at a time)
- Easy rollback (streams are internal)

### Risk 2: Performance Regression

**Mitigation**:
- Benchmark each subsystem before/after
- Compare against current implementation
- Rollback plan ready
- Measure with real sites

### Risk 3: Code Complexity

**Mitigation**:
- Streams are declarative (easier to read)
- Well-documented examples
- Consistent patterns across subsystems
- Code reviews focus on clarity

### Risk 4: Integration Conflicts

**Mitigation**:
- Coordinate with pipeline migration
- Share stream infrastructure
- Avoid duplicate implementations
- Clear ownership boundaries

---

## Success Criteria

### Phase 1 Complete ✅

- [ ] Related posts computation uses streams
- [ ] Dev server uses `FileChangeStream`
- [ ] Performance matches or exceeds current
- [ ] All tests pass
- [ ] Documentation updated

### Phase 2 Complete ✅

- [ ] Incremental builds use `ChangeDetectionStream`
- [ ] Autodoc uses `AutodocStream`
- [ ] Performance improved (parallel processing)
- [ ] All tests pass
- [ ] Documentation updated

### Phase 3 Complete ✅

- [ ] Index building uses streams
- [ ] Batch processing available
- [ ] Memory usage improved
- [ ] All tests pass
- [ ] Documentation updated

### Overall Success ✅

- [ ] Stream pattern applied to 5+ subsystems
- [ ] Performance improved across all subsystems
- [ ] Code clarity improved (declarative vs imperative)
- [ ] Free-threading benefits automatic
- [ ] No breaking changes to public APIs

---

## Open Questions

1. **Should streams be public API?**
   - **Recommendation**: No, keep internal for now
   - **Rationale**: Focus on implementation benefits, not API design
   - **Future**: Could expose for plugin authors if needed

2. **How to handle errors in streams?**
   - **Recommendation**: Stream-level error handling (log and continue)
   - **Rationale**: Matches current orchestrator behavior
   - **Future**: Could add error stream for better reporting

3. **Should we add stream operators incrementally?**
   - **Recommendation**: Yes, add as needed
   - **Rationale**: Avoid over-engineering
   - **Future**: Could standardize operator set

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 1-2 weeks | None |
| Phase 2 | 1-2 weeks | Phase 1 |
| Phase 3 | 1-2 weeks | Phase 2 |

**Total Estimate**: 3-6 weeks

**Note**: Can run in parallel with pipeline migration (Phase 2) since different subsystems.

---

## Related Documents

- `plan/active/pipeline-migration-roadmap.md` - Current pipeline migration
- `plan/implemented/rfc-reactive-dataflow-pipeline.md` - Original pipeline RFC
- `bengal/pipeline/` - Existing stream infrastructure
- `bengal/orchestration/` - Subsystems to migrate

---

## Appendix: Code Examples

### Example 1: Related Posts Stream

```python
# Before: Manual executor
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_page = {
        executor.submit(self._find_related_posts, page, ...): page
        for page in pages
    }
    for future in as_completed(future_to_page):
        page.related_posts = future.result()

# After: Stream-based
pages_stream = Stream.from_iterable(pages)
related_stream = create_related_posts_stream(pages_stream, tags_dict)
list(related_stream.iterate())  # Automatic parallelization
```

### Example 2: File Change Stream

```python
# Before: Manual event handling
def on_modified(self, event):
    self._pending_changes.append(event)
    self._debounced_trigger()

# After: Stream-based
changes = FileChangeStream(watchdog_events, debounce_ms=300)
changes.map(detect_change_type).for_each(self._handle_change)
```

### Example 3: Change Detection Stream

```python
# Before: Sequential processing
for page in pages_to_build:
    section_path = resolve_page_section_path(page)
    if section_path:
        affected_sections.add(section_path)

# After: Stream-based
changes = create_change_detection_stream(changed_files, cache, site)
affected_sections = {
    section for event in changes.iterate()
    for section in event.affected_sections
}
```

---

## Notes

- Stream pattern is proven (1.9-3x faster in pipeline)
- Free-threading benefits automatic (Python 3.14t)
- Incremental adoption reduces risk
- Complements pipeline migration (different subsystems)
- Focus on high-value targets first

