# RFC: Build Sharding for Parallel and Distributed SSG Builds

**Status**: Draft  
**Created**: 2025-12-19  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `plan/drafted/rfc-versioned-docs-pipeline-integration.md`  
**Confidence**: 75% 🟡

---

## Executive Summary

Sharding—partitioning work across independent workers—is a well-established distributed systems pattern that maps naturally to SSG builds. Bengal already uses thread-level parallelism; this RFC explores extending to **process-level and distributed sharding** for larger sites and multi-version documentation.

**Key Insight**: SSG pages are largely independent units, making them ideal sharding candidates. The main challenge is handling **cross-shard dependencies** (navigation, search indexes, tag aggregation).

---

## Problem Statement

### Current State

Bengal uses `ThreadPoolExecutor` for parallel page rendering:

```python
# bengal/orchestration/render.py:568-575
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_page = {
        executor.submit(process_page_with_pipeline, page): page for page in pages
    }
```

**Limitations**:

1. **GIL contention** (Python ≤3.13) — Threads share GIL, limiting CPU parallelism
2. **Single-process memory** — All pages in one process address space
3. **No horizontal scaling** — Cannot distribute across machines
4. **Version coupling** — Versioned docs rebuild together even when independent

### Evidence: Large Site Performance

From `tests/performance/` benchmarks:

| Site Size | Current Build | Theoretical (8-core, true parallel) |
|-----------|---------------|-------------------------------------|
| 100 pages | 2.1s | ~0.4s |
| 1,000 pages | 18.4s | ~2.5s |
| 10,000 pages | 180s+ | ~25s |

The gap widens because threading doesn't achieve true parallelism on CPU-bound rendering.

### Evidence: Versioned Docs Coupling

```python
# bengal/orchestration/build/initialization.py:416-431
# All versions build in same pass, no version-level sharding
pages_to_build = orchestrator.site.pages  # ALL pages, all versions
```

---

## Goals

1. **Process-level sharding** — Enable `ProcessPoolExecutor` for true CPU parallelism
2. **Version sharding** — Build doc versions as independent shards
3. **Section sharding** — Build content sections (blog, docs, api) in parallel
4. **Shard caching** — Cache completed shards for faster incremental rebuilds
5. **Future: Distributed builds** — Foundation for multi-machine builds

## Non-Goals

- Distributed storage (use existing filesystem)
- Kubernetes/container orchestration (use existing CI/CD)
- Real-time collaboration (build is batch operation)
- Sub-page sharding (page is atomic unit)

---

## Sharding Concepts Applied to SSG

### Database → SSG Mapping

| Database Sharding | SSG Equivalent | Bengal Implementation |
|-------------------|----------------|----------------------|
| Shard key | Partition function | Section path, version, language |
| Horizontal partitioning | Page assignment | Pages split across workers |
| Shard | Worker unit | Process or remote worker |
| Consistent hashing | Deterministic assignment | Hash of source path |
| Cross-shard join | Global aggregation | Sitemap, search index, navigation |
| Shard invalidation | Incremental rebuild | Only rebuild changed shards |
| Rebalancing | Dynamic allocation | Adjust workers based on shard size |

### Natural Shard Boundaries in Bengal

```
content/
├── docs/           # Shard A (500 pages)
├── blog/           # Shard B (200 pages)
├── api/            # Shard C (800 pages, autodoc)
└── _versions/
    ├── v1/         # Shard D.1 (archived, rarely changes)
    ├── v2/         # Shard D.2 (stable)
    └── v3/         # Shard D.3 (development)
```

---

## Design Options

### Option 1: Process Pool Sharding (Recommended First Step)

**Approach**: Use `ProcessPoolExecutor` instead of `ThreadPoolExecutor` for page rendering.

```python
# Proposed: bengal/orchestration/render.py

def _render_process_parallel(self, pages: list[Page], ...):
    """Render pages in separate processes for true parallelism."""
    
    # Serialize pages to shareable format
    page_data = [page.to_serializable() for page in pages]
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(render_page_worker, data): data 
            for data in page_data
        }
        for future in as_completed(futures):
            result = future.result()
            # Merge results back
```

**Pros**:
- True CPU parallelism (no GIL)
- Minimal architecture change
- Works with existing incremental system
- Memory isolation between workers

**Cons**:
- Serialization overhead (~5-10% for small pages)
- No shared Jinja environment (must recreate per worker)
- IPC overhead for large pages

**Complexity**: Medium  
**Performance gain**: 2-4x on multi-core (vs threading on GIL Python)

### Option 2: Version Sharding (Recommended for Versioned Docs)

**Approach**: Build each documentation version as an independent shard.

```python
# Proposed: bengal/orchestration/version_sharding.py

class VersionShardOrchestrator:
    """Build doc versions as independent shards."""
    
    def build_sharded(self, site: Site) -> None:
        versions = site.version_config.get("versions", [])
        
        # Each version is a shard
        shards = {
            v["id"]: self._collect_version_pages(v["id"])
            for v in versions
        }
        
        # Build shards in parallel (process pool)
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(self._build_shard, shard_id, pages): shard_id
                for shard_id, pages in shards.items()
            }
            
            for future in as_completed(futures):
                shard_id = futures[future]
                future.result()  # Raises on error
        
        # Merge phase: global artifacts
        self._merge_sitemaps(shards.keys())
        self._merge_search_indexes(shards.keys())
```

**Shard Independence Matrix**:

| Artifact | Cross-Version? | Strategy |
|----------|---------------|----------|
| Page content | No | Build independently |
| Version nav | No | Build per-shard |
| Global search | Yes | Merge post-build |
| Sitemap | Yes | Merge post-build |
| Version switcher | Yes | Template-time (static list) |
| Cross-version links | Yes | Validate post-merge |

**Pros**:
- Natural shard boundary (versions are logically isolated)
- Archived versions rarely change (cache entire shard)
- Scales well with version count
- Aligns with `rfc-versioned-docs-pipeline-integration.md`

**Cons**:
- Requires version-aware cache invalidation
- Cross-version links need post-merge validation
- Merge phase adds complexity

**Complexity**: Medium-High  
**Performance gain**: Linear with version count (3 versions = ~3x faster)

### Option 3: Section Sharding

**Approach**: Build content sections as independent shards.

```python
# Proposed partitioning
shards = {
    "docs": site.get_section("docs").pages,
    "blog": site.get_section("blog").pages,
    "api": site.get_section("api").pages,
}
```

**Pros**:
- Works for non-versioned sites
- Natural content organization
- Section menus are local

**Cons**:
- Cross-section navigation (breadcrumbs, global nav) needs coordination
- Uneven shard sizes (API might have 80% of pages)
- Tags span sections

**Complexity**: Medium  
**Performance gain**: 1.5-3x depending on balance

### Option 4: Distributed Build (Future)

**Approach**: Distribute shards across multiple machines.

```yaml
# Hypothetical: bengal.toml
[build.distributed]
enabled = true
coordinator = "redis://localhost:6379"
workers = 4
shard_by = "section"  # or "version", "hash"
```

**Architecture**:
```
┌─────────────────────────────────────────────────────┐
│                   Coordinator                        │
│  - Assigns shards to workers                        │
│  - Collects results                                 │
│  - Runs merge phase                                 │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
┌───────┐   ┌───────┐     ┌───────┐     ┌───────┐
│Worker1│   │Worker2│     │Worker3│     │Worker4│
│ docs/ │   │ blog/ │     │ api/  │     │  v1/  │
└───────┘   └───────┘     └───────┘     └───────┘
    │             │             │             │
    └─────────────┴──────┬──────┴─────────────┘
                         ▼
                  ┌─────────────┐
                  │ Merge Phase │
                  │ - Sitemap   │
                  │ - Search    │
                  │ - RSS       │
                  └─────────────┘
```

**Pros**:
- Horizontal scaling for massive sites
- Cloud-native (CI/CD integration)
- Build time bounded by largest shard

**Cons**:
- Significant complexity
- Network/storage coordination
- Overkill for most sites

**Complexity**: High  
**Performance gain**: Near-linear with machine count

---

## Recommendation

### Phase 1: Process Pool Rendering (Low Risk, Quick Win)

Add `--process-parallel` flag to use `ProcessPoolExecutor` for rendering:

```bash
bengal build --process-parallel
```

**Implementation**:
1. Make `Page` and rendering context serializable
2. Add `ProcessPoolExecutor` path in `RenderOrchestrator`
3. Benchmark against thread pool
4. Auto-detect best strategy based on page count

**Estimated effort**: 2-3 days

### Phase 2: Version Sharding (Medium Risk, High Value for Versioned Sites)

Integrate with versioned docs pipeline:

```bash
bengal build --shard-versions
```

**Implementation**:
1. Create `VersionShardOrchestrator`
2. Add version-scoped cache
3. Implement merge phase for global artifacts
4. Update incremental system for shard-level invalidation

**Estimated effort**: 1-2 weeks

### Phase 3: Section Sharding (Optional, for Large Non-Versioned Sites)

**Implementation**:
1. Extend sharding to sections
2. Handle cross-section navigation
3. Rebalancing for uneven sections

**Estimated effort**: 1 week

### Phase 4: Distributed Builds (Future, If Needed)

Only if demand exists for sites >50K pages.

---

## Cross-Shard Dependencies (The Hard Problem)

### Problem

Some artifacts require knowledge of ALL pages:

| Artifact | Pages Needed | Strategy |
|----------|-------------|----------|
| Sitemap | All | Post-merge generation |
| RSS feed | Recent N | Post-merge, filter by date |
| Search index | All | Parallel index per shard, merge |
| Tag pages | All with tag | Map: collect tags, Reduce: generate pages |
| Navigation | All (for menus) | Pre-compute nav tree, pass to shards |
| Prev/Next | Section pages | Section-local, no cross-shard |

### Proposed Solution: Two-Phase Build

```
Phase 1: Shard Build (Parallel)
├── Shard A builds pages, outputs:
│   ├── rendered HTML
│   ├── local sitemap fragment
│   ├── local search index
│   └── tag manifest (page → tags)
├── Shard B builds pages, outputs: ...
└── Shard C builds pages, outputs: ...

Phase 2: Merge (Sequential)
├── Combine sitemap fragments → sitemap.xml
├── Merge search indexes → search.json
├── Aggregate tag manifests → generate tag pages
└── Validate cross-shard links
```

### Data Flow

```python
@dataclass
class ShardResult:
    """Output from a shard build."""
    shard_id: str
    rendered_pages: list[Path]  # Output file paths
    sitemap_entries: list[SitemapEntry]
    search_entries: list[SearchEntry]
    tag_manifest: dict[str, list[str]]  # tag → [page_urls]
    errors: list[BuildError]
```

---

## Performance Estimates

### Current (Threading, GIL Python)

| Site | Build Time | CPU Usage |
|------|-----------|-----------|
| 1K pages | 18s | ~120% (1.2 cores effective) |
| 10K pages | 180s | ~130% |

### With Process Sharding (Phase 1)

| Site | Build Time | CPU Usage |
|------|-----------|-----------|
| 1K pages | 8s | ~600% (6 cores) |
| 10K pages | 60s | ~700% |

### With Version Sharding (Phase 2, 3 versions)

| Site | Build Time | Notes |
|------|-----------|-------|
| 3K pages (1K/version) | 10s | Parallel version builds |
| v1 change only | 4s | Only rebuild v1 shard |
| Shared content change | 12s | Rebuild all + merge |

---

## Risks and Mitigations

### Risk 1: Serialization Overhead

**Problem**: `ProcessPoolExecutor` requires serializable data.  
**Mitigation**: 
- Cache serialized page data
- Use `pickle` protocol 5 for efficiency
- Only serialize what's needed (not full Page object)

### Risk 2: Template Environment Recreation

**Problem**: Jinja environment has macros, filters, globals that must exist in each worker.  
**Mitigation**:
- Create lightweight "worker environment" initialization
- Cache compiled templates (Jinja bytecode cache already exists)
- Pass environment config, not environment instance

### Risk 3: Memory Overhead

**Problem**: Each process has full Python interpreter.  
**Mitigation**:
- Limit max workers based on available RAM
- Use `--memory-optimized` for streaming within each shard
- Consider `fork` start method on Unix (shares memory initially)

### Risk 4: Debugging Complexity

**Problem**: Multi-process errors harder to trace.  
**Mitigation**:
- Structured logging with shard IDs
- Collect errors per shard, report in merge phase
- `--no-shard` flag for debugging

---

## Implementation Checklist

### Phase 1: Process Pool

- [ ] Make `Page` serializable (implement `__reduce__` or use dataclass)
- [ ] Create `render_page_worker()` standalone function
- [ ] Add process pool path to `RenderOrchestrator`
- [ ] Add `--process-parallel` CLI flag
- [ ] Benchmark: threading vs process pool
- [ ] Add `max_processes` config option
- [ ] Update progress reporting for multi-process

### Phase 2: Version Sharding

- [ ] Create `VersionShardOrchestrator`
- [ ] Implement version-scoped page collection
- [ ] Add shard-level cache (`.bengal/shards/{version}/`)
- [ ] Implement `ShardResult` data structure
- [ ] Implement merge phase for sitemap
- [ ] Implement merge phase for search index
- [ ] Update incremental system for shard invalidation
- [ ] Add `--shard-versions` CLI flag
- [ ] Handle shared content → all shards invalidation

### Phase 3: Section Sharding

- [ ] Extend sharding to arbitrary sections
- [ ] Handle cross-section navigation
- [ ] Implement shard rebalancing
- [ ] Add `--shard-sections` CLI flag

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/orchestration/test_sharding.py

def test_page_serialization_roundtrip():
    """Page can be serialized and deserialized."""
    
def test_shard_assignment_deterministic():
    """Same page always goes to same shard."""
    
def test_shard_result_merge():
    """ShardResults merge correctly."""
```

### Integration Tests

```python
# tests/integration/test_sharded_build.py

def test_process_parallel_matches_sequential():
    """Process parallel produces identical output."""
    
def test_version_sharding_produces_correct_output():
    """Each version shard builds correctly."""
    
def test_shared_content_invalidates_all_shards():
    """_shared/ change rebuilds all version shards."""
```

### Performance Tests

```python
# tests/performance/test_sharding_performance.py

def test_process_pool_faster_than_threads():
    """Process pool achieves better parallelism."""
    
def test_version_sharding_scales_linearly():
    """Build time decreases with version count."""
```

---

## Open Questions

1. **Shard granularity**: Is per-version sharding sufficient, or do we need per-section within version?

2. **Cache sharing**: Should shards share the markdown parse cache, or each have their own?

3. **Error handling**: If one shard fails, should others continue or abort?

4. **Progress reporting**: How to show progress across multiple parallel shards?

5. **Memory limits**: How to prevent OOM when many shards run simultaneously?

---

## References

- **Database sharding**: [MongoDB Sharding](https://www.mongodb.com/docs/manual/sharding/), [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- **Python multiprocessing**: [ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)
- **Related SSG**: [Gatsby Parallel Queries](https://www.gatsbyjs.com/docs/multi-core-builds/), [Hugo's parallel builds](https://gohugo.io/troubleshooting/build-performance/)
- **Bengal**: `bengal/orchestration/render.py`, `plan/drafted/rfc-versioned-docs-pipeline-integration.md`

---

## Appendix: Serialization Strategy

### Option A: Pickle (Simple)

```python
# Works if Page is a dataclass with simple fields
import pickle
serialized = pickle.dumps(page, protocol=5)
page = pickle.loads(serialized)
```

### Option B: Explicit Serialization (Control)

```python
@dataclass
class PageData:
    """Serializable page representation for worker processes."""
    source_path: str
    content: str
    frontmatter: dict
    template: str
    output_path: str
    # Exclude: parent Section, Site reference, etc.

def to_page_data(page: Page) -> PageData:
    return PageData(
        source_path=str(page.source_path),
        content=page.raw_content,
        frontmatter=dict(page.frontmatter),
        template=page.template,
        output_path=str(page.output_path),
    )
```

### Option C: Shared Memory (Advanced)

```python
# Python 3.8+ shared memory for large content
from multiprocessing import shared_memory

# Pre-load all content into shared memory
shm = shared_memory.SharedMemory(create=True, size=total_content_size)
# Workers access via name, avoid copying
```

---

## Changelog

- 2025-12-19: Initial draft

