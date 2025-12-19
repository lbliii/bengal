# RFC: Build Sharding for Parallel and Distributed SSG Builds

**Status**: Draft  
**Created**: 2025-12-19  
**Updated**: 2025-12-19  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High)  
**Related**: `plan/drafted/rfc-versioned-docs-pipeline-integration.md`  
**Confidence**: 87% 🟢

---

## Executive Summary

Sharding—partitioning work across independent workers—is a well-established distributed systems pattern that maps naturally to SSG builds. Bengal already uses thread-level parallelism; this RFC explores extending to **process-level and distributed sharding** for larger sites.

**Key Insight**: Most Bengal sites are **much larger than they appear**. A typical documentation project with 150 markdown files actually produces 900+ pages due to autodoc, taxonomies, and output formats. This "page multiplication" makes sharding valuable for nearly all Bengal users, not just enterprise-scale sites.

**Primary Use Case**: Sites with autodoc enabled (most Bengal users). When autodoc is enabled, page counts typically reach 500-2000+, crossing the threshold where sharding provides significant value.

---

## The Autodoc Multiplier: Why Bengal Sites Are Larger Than They Look

### The Iceberg Effect

Bengal users often underestimate their site size because they count markdown files, not output pages:

```
What users see:           What Bengal builds:
├── 156 markdown files    ├── 950 HTML pages
│                         │   ├── 452 API autodoc pages
│                         │   ├── 92 CLI autodoc pages
│                         │   ├── 126 content pages
│                         │   ├── 258 tag pages
│                         │   └── 22 other pages
│                         ├── 945 TXT files (llmtxt)
│                         └── 405 JSON files
│                         ────────────────────
│                         ~2,300 total outputs
```

### Evidence: Bengal's Own Documentation Site

| Component | Source | Pages | % of Total |
|-----------|--------|-------|------------|
| **API autodoc** | 455 Python modules | 452 | 48% |
| **CLI autodoc** | 1 Click app | 92 | 10% |
| **Tags** | Generated | 258 | 27% |
| **Content** | 156 markdown files | 126 | 13% |
| **Other** | Releases, authors, etc. | 22 | 2% |
| **Total** | — | **950** | 100% |

Plus output formats (×3 multiplier): HTML + JSON + TXT = **~2,900 total outputs**

### Why Autodoc Pages Are More Expensive

Autodoc pages have ~2-3x the processing cost of content pages:

```
Content page:  Read markdown → Parse → Render → Write     (~10ms)
Autodoc page:  Parse Python AST → Extract → Generate → Render → Write  (~25ms)
```

With 544 autodoc pages at 2.5x cost, that's equivalent to **~1,360 content pages**.

### Real-World Projections for Bengal Users

| Project Type | Markdown Files | Actual Pages | Recommended Sharding |
|--------------|---------------|--------------|---------------------|
| Docs-only blog | 100 | ~200 | None needed |
| Small library | 50 content + 100 modules | ~400 | Marginal benefit |
| Medium library | 100 content + 300 modules | ~800 | ✅ Autodoc sharding |
| Large framework | 200 content + 800 modules | ~2,000 | ✅ Full sharding stack |
| **Bengal (typical)** | 156 content + 455 modules | **~950** | ✅ Autodoc sharding |

**Bottom line**: If you enable autodoc (most Bengal users), you likely have 500+ pages and will benefit from sharding.

---

## Problem Statement

### Current State

Bengal uses `ThreadPoolExecutor` for parallel page rendering:

```python
# bengal/orchestration/render.py:568-572
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_page = {
        executor.submit(process_page_with_pipeline, page): page for page in pages
    }
```

**Existing Infrastructure** (accelerates implementation):

Bengal's dev server already has `ProcessPoolExecutor` infrastructure in `bengal/server/build_executor.py`:
- Serializable `BuildRequest`/`BuildResult` dataclasses
- Free-threading detection (`is_free_threaded()`)
- Spawn context for cross-platform compatibility
- Executor type auto-selection based on Python version

This means Phase 2 (Process Pool Rendering) has lower implementation risk than originally estimated.

**Limitations**:

1. **GIL contention** (Python ≤3.13) — Threads share GIL, limiting CPU parallelism
2. **Single-process memory** — All pages in one process address space
3. **No horizontal scaling** — Cannot distribute across machines
4. **Autodoc coupling** — Autodoc and content pages rebuild together
5. **Version coupling** — Versioned docs rebuild together even when independent

### Evidence: Large Site Performance

From `benchmarks/` suite (`benchmarks/test_build.py`, `benchmarks/README.md`):

**Current Performance (Python 3.14, GIL-limited threading)**:
- Baseline: ~256 pages/sec (parallel threading)
- Free-threading (Python 3.14t): ~373 pages/sec

| Site Size | Current (GIL-limited) | Theoretical (8-core, true parallel) | Speedup Potential |
|-----------|----------------------|-------------------------------------|-------------------|
| 100 pages | ~0.4s | ~0.1s | 4x |
| 1,000 pages | ~4s | ~0.5s | 8x |
| 10,000 pages | ~40s | ~5s | 8x |

**Note**: Current builds are already parallel via `ThreadPoolExecutor`, achieving ~256 pages/sec. The "theoretical" column assumes process-level parallelism eliminating GIL contention entirely. Actual speedup depends on I/O vs CPU balance.

The gap widens at scale because GIL contention increases with page count and CPU-bound operations (Jinja rendering, AST parsing) dominate.

### Evidence: Autodoc Dominates Build Time

For Bengal's own site (950 pages):
- Autodoc pages: 544 (57%) — CPU-intensive Python AST parsing
- Content pages: 126 (13%) — Markdown parsing
- Generated pages: 280 (30%) — Template-only (fast)

Autodoc consumes **~70% of build time** despite being ~57% of pages (due to higher per-page cost).

### Evidence: Versioned Docs Coupling

```python
# bengal/orchestration/build/initialization.py:417
# All versions build in same pass, no version-level sharding
pages_to_build = orchestrator.site.pages  # ALL pages, all versions
```

### Evidence: Existing Process Isolation

The dev server already uses process isolation for resilience (`bengal/server/build_executor.py:1-18`):

```python
"""
Process-isolated build execution for resilience.

Features:
    - Process isolation via ProcessPoolExecutor
    - Free-threading aware: Uses ThreadPoolExecutor on Python 3.14+ with GIL disabled
    - Configurable executor type via BENGAL_BUILD_EXECUTOR env var
    - Serializable BuildRequest/BuildResult for cross-process communication
"""
```

This existing infrastructure can be extended for build sharding, reducing Phase 2 implementation effort.

---

## Goals

1. **Autodoc sharding** — Build autodoc pages as an independent shard (highest impact)
2. **Process-level sharding** — Enable `ProcessPoolExecutor` for true CPU parallelism
3. **Version sharding** — Build doc versions as independent shards
4. **Section sharding** — Build content sections (blog, docs, api) in parallel
5. **Shard caching** — Cache completed shards for faster incremental rebuilds
6. **Future: Distributed builds** — Foundation for multi-machine builds

## Non-Goals

- Distributed storage (use existing filesystem)
- Kubernetes/container orchestration (use existing CI/CD)
- Real-time collaboration (build is batch operation)
- Sub-page sharding (page is atomic unit)

---

## Who Benefits

### Sharding Value by Site Profile

| Site Profile | Pages | Sharding Value | Recommended |
|--------------|-------|----------------|-------------|
| Blog (no autodoc) | <200 | ❌ Low | Skip sharding |
| Docs + small library | 200-500 | 🟡 Marginal | Optional |
| Docs + medium library | 500-1000 | ✅ Clear win | Autodoc sharding |
| Docs + large library | 1000+ | ✅ Strong win | Full sharding |
| Multi-version docs | Any | ✅ High | Version sharding |

### Key Threshold: 500 Pages

Below 500 pages, sharding overhead (process spawning, serialization) often exceeds gains. Above 500 pages, sharding provides 2-4x improvement.

**Most Bengal users with autodoc enabled cross this threshold.**

### Autodoc Is the Tipping Point

| Autodoc Status | Typical Page Count | Sharding? |
|----------------|-------------------|-----------|
| Disabled | 50-300 | Usually not needed |
| Python only | 300-1000 | ✅ Recommended |
| Python + CLI | 400-1500 | ✅ Recommended |
| Python + CLI + OpenAPI | 500-2000+ | ✅ Strongly recommended |

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

### Option 2: Autodoc Sharding (Recommended for Most Users) ⭐

**Approach**: Build autodoc pages as a separate shard from content pages.

```python
# Proposed: bengal/orchestration/autodoc_sharding.py

class AutodocShardOrchestrator:
    """Build autodoc and content as independent shards."""

    def build_sharded(self, site: Site) -> None:
        # Partition pages by type
        shards = {
            "autodoc": [p for p in site.pages if p.metadata.get("is_autodoc")],
            "content": [p for p in site.pages if not p.metadata.get("is_autodoc")
                        and not p.metadata.get("_generated")],
            "generated": [p for p in site.pages if p.metadata.get("_generated")],
        }

        # Build shards in parallel
        with ProcessPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._build_shard, name, pages): name
                for name, pages in shards.items()
            }
            for future in as_completed(futures):
                future.result()

        # Merge phase
        self._merge_outputs()
```

**Why Autodoc Is an Ideal Shard Boundary**:

1. **Self-contained** — Autodoc pages are generated from Python source, not markdown
2. **No cross-references** — Autodoc pages rarely link to content pages (and vice versa)
3. **Different source** — Python AST vs markdown = no cache sharing needed
4. **Expensive** — 2-3x cost per page, so parallelizing gives higher returns
5. **Stable** — API changes less frequently than docs during development

**Shard Independence Matrix**:

| Artifact | Autodoc ↔ Content? | Strategy |
|----------|-------------------|----------|
| Page rendering | No | Build independently |
| Navigation menu | Yes | Pre-compute nav tree, pass to shards |
| Search index | Yes | Merge post-build |
| Sitemap | Yes | Merge post-build |
| Cross-references | Minimal | Validate post-merge |

**Pros**:
- Highest ROI for most Bengal users (autodoc is the page count driver)
- Clean separation (different source types)
- Works for non-versioned sites
- Autodoc shard can be cached aggressively (Python source changes less often)

**Cons**:
- Navigation must be pre-computed (minor complexity)
- Search index merge required
- Three-way split adds merge complexity

**Complexity**: Medium  
**Performance gain**: 2-3x for sites with 50%+ autodoc pages

**Incremental Build Benefit**:

```
Scenario: Edit docs/guide.md

Without autodoc sharding:
  - Rebuild content pages + check all autodoc pages → 15s

With autodoc sharding:
  - Rebuild content shard only → 3s
  - Autodoc shard cached → 0s
```

---

### Option 3: Version Sharding (Recommended for Versioned Docs)

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

### Option 4: Section Sharding

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

### Option 5: Distributed Build (Future)

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

### Implementation Accelerators (Existing Infrastructure)

The following existing Bengal infrastructure reduces implementation risk and effort:

| Component | Location | Reusable For |
|-----------|----------|--------------|
| `ProcessPoolExecutor` setup | `bengal/server/build_executor.py:26` | Phase 2 |
| `BuildRequest` frozen dataclass | `bengal/server/build_executor.py:39-63` | Serialization patterns |
| `is_free_threaded()` detection | `bengal/server/build_executor.py:167-175` | Executor auto-selection |
| Spawn context | `bengal/server/build_executor.py:36` | Cross-platform safety |
| `is_autodoc` metadata | `bengal/autodoc/orchestration/page_builders.py:100` | Phase 1 partitioning |
| `_generated` metadata | `bengal/orchestration/incremental.py` | Phase 1 partitioning |
| Performance benchmarks | `benchmarks/test_build.py` | Validation |

**Estimated effort reduction**: ~30% for Phase 2 due to existing patterns.

---

### Phase 1: Autodoc Sharding (High Value, Most Users) ⭐

**Priority**: Highest — benefits most Bengal users immediately.

```bash
bengal build --shard-autodoc
```

**Implementation**:
1. Partition pages into autodoc vs content shards
2. Add `AutodocShardOrchestrator`
3. Pre-compute navigation tree before sharding
4. Implement merge phase for search index
5. Add shard-level cache for autodoc pages

**Estimated effort**: 1 week

**Why First**:
- Autodoc is the #1 driver of page count (50-80% of pages for typical users)
- Clean shard boundary (Python source vs markdown)
- Immediate benefit for dev server (edit docs → don't rebuild autodoc)
- Autodoc cache can be very aggressive (Python source changes infrequently)

### Phase 2: Process Pool Rendering (Low Risk, Additional Gains)

Add `--process-parallel` flag to use `ProcessPoolExecutor` for rendering within shards:

```bash
bengal build --process-parallel
```

**Implementation** (leveraging existing infrastructure):
1. Extend `BuildRequest`/`BuildResult` pattern from `bengal/server/build_executor.py`
2. Reuse `is_free_threaded()` detection for auto-selection
3. Make `Page` serializable (follow existing `BuildRequest` frozen dataclass pattern)
4. Add `ProcessPoolExecutor` path in `RenderOrchestrator`
5. Benchmark against thread pool
6. Auto-detect best strategy based on page count and Python version

**Estimated effort**: 2-3 days (reduced due to existing infrastructure)

**Why Low Risk**: `build_executor.py` already solves:
- Spawn context for cross-platform safety
- Free-threading detection
- Serializable dataclass patterns
- Executor lifecycle management

**Synergy with Phase 1**: Once shards exist, each shard can use process-parallel rendering internally for additional gains.

### Phase 3: Version Sharding (High Value for Versioned Sites)

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

**Synergy with Phases 1-2**: Version sharding + autodoc sharding = 2D partitioning:
- v1/autodoc, v1/content
- v2/autodoc, v2/content
- etc.

### Phase 4: Section Sharding (Optional, for Large Non-Versioned Sites)

**Implementation**:
1. Extend sharding to sections
2. Handle cross-section navigation
3. Rebalancing for uneven sections

**Estimated effort**: 1 week

### Phase 5: Distributed Builds (Future, If Needed)

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

### Current State: Bengal's Own Site (950 pages)

| Metric | Value |
|--------|-------|
| Full build | ~30-45s |
| Autodoc pages | 544 (57%) |
| Autodoc build time | ~25-30s (70% of total) |
| Content build time | ~8-12s |
| Incremental (1 file) | ~2-5s |

### With Autodoc Sharding (Phase 1)

| Scenario | Current | With Sharding | Improvement |
|----------|---------|---------------|-------------|
| Full build | 45s | 20s | **2.2x** |
| Edit docs only | 15s | 5s | **3x** |
| Edit Python source | 30s | 25s | 1.2x |
| Incremental (cached autodoc) | 5s | 2s | **2.5x** |

**Key insight**: Most dev server rebuilds are content edits, not Python changes. Autodoc sharding makes the common case fast.

### With Process Sharding (Phase 2)

| Site | Build Time | CPU Usage |
|------|-----------|-----------|
| 1K pages | 8s | ~600% (6 cores) |
| 10K pages | 60s | ~700% |

### With Version Sharding (Phase 3, 3 versions)

| Site | Build Time | Notes |
|------|-----------|-------|
| 3K pages (1K/version) | 10s | Parallel version builds |
| v1 change only | 4s | Only rebuild v1 shard |
| Shared content change | 12s | Rebuild all + merge |

### Combined: Autodoc + Version + Process Sharding

| Scenario | Current | Fully Sharded | Improvement |
|----------|---------|---------------|-------------|
| 3-version site, 1K pages/version | 90s | 15s | **6x** |
| Edit v2/docs only | 45s | 5s | **9x** |
| CI parallel build (3 workers) | 90s | 12s | **7.5x** |

---

## Risks and Mitigations

### Risk 1: Serialization Overhead

**Problem**: `ProcessPoolExecutor` requires serializable data.  
**Mitigation**:
- Follow existing `BuildRequest`/`BuildResult` frozen dataclass pattern from `build_executor.py`
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
- Use spawn context (already implemented in `build_executor.py:36`) for isolation
- Note: Spawn is safer than fork for threads; fork can cause deadlocks

### Risk 4: Debugging Complexity

**Problem**: Multi-process errors harder to trace.  
**Mitigation**:
- Structured logging with shard IDs
- Collect errors per shard, report in merge phase
- `--no-shard` flag for debugging

---

## Implementation Checklist

### Phase 1: Autodoc Sharding ⭐

- [ ] Create `AutodocShardOrchestrator`
- [ ] Implement page partitioning (autodoc vs content vs generated)
- [ ] Pre-compute navigation tree before shard dispatch
- [ ] Make autodoc pages serializable for process boundary
- [ ] Implement `ShardResult` data structure
- [ ] Implement merge phase for search index
- [ ] Implement merge phase for sitemap
- [ ] Add shard-level cache (`.bengal/shards/autodoc/`, `.bengal/shards/content/`)
- [ ] Add `--shard-autodoc` CLI flag
- [ ] Add `--no-shard` flag for debugging
- [ ] Update progress reporting for sharded builds
- [ ] Handle Python source change → autodoc shard invalidation
- [ ] Handle content change → content shard only invalidation

### Phase 2: Process Pool

- [ ] Extend `BuildRequest` pattern from `bengal/server/build_executor.py` for page-level requests
- [ ] Reuse `is_free_threaded()` for executor auto-selection
- [ ] Make `Page` serializable (follow `BuildRequest` frozen dataclass pattern)
- [ ] Create `render_page_worker()` standalone function
- [ ] Add process pool path to `RenderOrchestrator`
- [ ] Add `--process-parallel` CLI flag
- [ ] Benchmark: threading vs process pool
- [ ] Add `max_processes` config option
- [ ] Update progress reporting for multi-process

### Phase 3: Version Sharding

- [ ] Create `VersionShardOrchestrator`
- [ ] Implement version-scoped page collection
- [ ] Add shard-level cache (`.bengal/shards/{version}/`)
- [ ] Implement merge phase for version-specific artifacts
- [ ] Update incremental system for shard invalidation
- [ ] Add `--shard-versions` CLI flag
- [ ] Handle shared content → all version shards invalidation
- [ ] Integrate with autodoc sharding (2D partitioning)

### Phase 4: Section Sharding

- [ ] Extend sharding to arbitrary sections
- [ ] Handle cross-section navigation
- [ ] Implement shard rebalancing
- [ ] Add `--shard-sections` CLI flag

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/orchestration/test_sharding.py

def test_page_partitioning_autodoc_vs_content():
    """Pages correctly partitioned into autodoc and content shards."""

def test_page_serialization_roundtrip():
    """Page can be serialized and deserialized."""

def test_shard_assignment_deterministic():
    """Same page always goes to same shard."""

def test_shard_result_merge():
    """ShardResults merge correctly."""

def test_navigation_precomputed_before_sharding():
    """Nav tree available to all shards."""
```

### Integration Tests

```python
# tests/integration/test_sharded_build.py

def test_autodoc_sharding_produces_correct_output():
    """Autodoc shard builds correctly with full navigation."""

def test_content_change_only_rebuilds_content_shard():
    """Content edit doesn't trigger autodoc rebuild."""

def test_python_source_change_rebuilds_autodoc_shard():
    """Python source edit triggers autodoc shard rebuild."""

def test_process_parallel_matches_sequential():
    """Process parallel produces identical output."""

def test_version_sharding_produces_correct_output():
    """Each version shard builds correctly."""

def test_shared_content_invalidates_all_shards():
    """_shared/ change rebuilds all version shards."""

def test_search_index_merged_correctly():
    """Search index contains entries from all shards."""
```

### Performance Tests

```python
# tests/performance/test_sharding_performance.py

def test_autodoc_sharding_faster_for_content_edits():
    """Content-only edit is faster with autodoc sharding."""

def test_process_pool_faster_than_threads():
    """Process pool achieves better parallelism."""

def test_version_sharding_scales_linearly():
    """Build time decreases with version count."""

def test_combined_sharding_multiplicative_gains():
    """Autodoc + version sharding provides compounding benefits."""
```

---

## Open Questions

1. **Shard granularity**: Is per-version sharding sufficient, or do we need per-section within version?
   - *Preliminary answer*: Start with autodoc/content split (Phase 1), then version sharding (Phase 3). Per-section within version is Phase 4 and likely only needed for sites with very uneven section sizes.

2. **Cache sharing**: Should shards share the markdown parse cache, or each have their own?
   - *Preliminary answer*: Each shard should have its own cache due to process isolation. The autodoc shard uses Python AST cache (different from markdown cache), so no sharing needed for Phase 1.

3. **Error handling**: If one shard fails, should others continue or abort?
   - *Preliminary answer*: Follow existing `build_executor.py` pattern — collect errors per shard, report all in merge phase. Use `--fail-fast` flag for abort-on-first-error behavior.

4. **Progress reporting**: How to show progress across multiple parallel shards?
   - *Needs design*: Consider Rich multi-progress bars or aggregate progress.

5. **Memory limits**: How to prevent OOM when many shards run simultaneously?
   - *Preliminary answer*: Limit max workers based on available RAM (existing pattern in `build_executor.py`). Consider spawn context (already used) which doesn't inherit parent memory.

---

## References

- **Database sharding**: [MongoDB Sharding](https://www.mongodb.com/docs/manual/sharding/), [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- **Python multiprocessing**: [ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)
- **Related SSG**: [Gatsby Parallel Queries](https://www.gatsbyjs.com/docs/multi-core-builds/), [Hugo's parallel builds](https://gohugo.io/troubleshooting/build-performance/)
- **Bengal codebase**:
  - `bengal/orchestration/render.py:568` — Current ThreadPoolExecutor implementation
  - `bengal/server/build_executor.py` — Existing ProcessPoolExecutor infrastructure
  - `bengal/autodoc/orchestration/page_builders.py:100` — `is_autodoc` metadata flag
  - `bengal/orchestration/incremental.py` — `_generated` metadata usage
  - `benchmarks/test_build.py` — Performance benchmarks (~256 pps baseline)
- **Related RFC**: `plan/drafted/rfc-versioned-docs-pipeline-integration.md`

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

- 2025-12-19: **Revision 3** — Evaluation-based improvements
  - Elevated confidence to 87% (verified core claims against codebase)
  - Added evidence of existing `ProcessPoolExecutor` infrastructure in `build_executor.py`
  - Corrected performance numbers to match benchmark suite (~256 pps baseline)
  - Updated line number references to accurate locations
  - Added detailed Bengal codebase references section
  - Reduced Phase 2 risk assessment (existing infrastructure accelerates implementation)
  - Added "Existing Infrastructure" subsection in Problem Statement
- 2025-12-19: **Revision 2** — Major update based on Bengal site analysis
  - Elevated priority to P1 (High), confidence to 82%
  - Added "The Autodoc Multiplier" section explaining page count explosion
  - Added "Who Benefits" section with thresholds
  - Added **Autodoc Sharding** as new Phase 1 (highest priority)
  - Renumbered phases: Autodoc (1) → Process (2) → Version (3) → Section (4) → Distributed (5)
  - Updated performance estimates with Bengal-specific data
  - Key insight: Most Bengal users have 500+ pages due to autodoc, making sharding broadly applicable
- 2025-12-19: Initial draft
