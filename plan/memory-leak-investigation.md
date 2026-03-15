# Memory Leak Investigation

**Status**: Investigation  
**Context**: Content phase hang on dev server (Python 3.14t / macOS). User suspects memory leak causes GC thrash or OOM, leading to apparent hang.

## Quick Diagnostics

Run with memory profiling:

```bash
BENGAL_DEBUG_MEMORY=1 bengal s
# or
BENGAL_DEBUG_MEMORY=1 bengal build
```

This will:
- Run `gc.collect()` before the content phase
- Start `tracemalloc` at build start
- Print top 10 allocations after the content phase completes

If the build hangs before completing the content phase, tracemalloc output won't appear. In that case, try running with `BENGAL_BUILD_EXECUTOR=process` (dev server already forces this) so the build runs in a subprocess — memory is freed when the subprocess exits.

## Suspects

### 1. Content Phase Data Structures

| Location | Structure | Risk |
|----------|-----------|------|
| `related_posts.py` | `page_tags_map: dict[Page, set[str]]` | N entries, Page as key — bounded by page count |
| `related_posts.py` | `id_to_page: dict[int, Page]` | N entries — bounded |
| `related_posts.py` | `tag_to_page_ids: dict[str, frozenset[int]]` | Bounded by tag count |
| `taxonomy.py` | `site.taxonomies['tags'][slug]['pages']` | Refs to same Page objects — bounded |
| `content.py` | `content_hash_lookup: dict[str, str]` | path → hash, bounded by pages |

All are O(n) or O(tags). No obvious unbounded growth.

### 2. Module-Level Caches

| Cache | Cleared? | Notes |
|-------|----------|-------|
| `_global_context_cache` | BUILD_START (when BuildContext used as ctx mgr) | Keyed by site id; subprocess = fresh |
| `_parser_cache` | TEST_CLEANUP only | Thread-local; one parser per worker |
| `_created_dirs` | Per build start | Cleared in build __init__ |
| `nav_tree` cache | CONFIG_CHANGED, etc. | Registered |
| `version_url` cache | BUILD_START | Registered |

**Note**: BuildContext is created but not used as `with BuildContext(...) as ctx`. So `BUILD_START` may not fire at build start. RenderOrchestrator calls it during render phase. For ProcessPoolExecutor builds, each run is a fresh subprocess — no cross-build leakage.

### 3. ThreadPoolExecutor (when not using process executor)

When `BENGAL_BUILD_EXECUTOR=thread` (e.g. on 3.14t without override), builds run in the main process. Worker threads may retain references. Dev server forces `BENGAL_BUILD_EXECUTOR=process`, so this doesn't apply to `bengal s`.

### 4. Taxonomy / Related Posts Parallelism

With `force_sequential=False` (not dev server), `phase_related_posts` uses `ThreadPoolExecutor`. Each worker receives `page_tags_map`, `tag_to_page_ids`, `id_to_page` — shared read-only. No per-worker accumulation. Dev server forces `force_sequential=True`, so parallelism is disabled.

### 5. Circular References

Page objects reference sections, sections reference pages. Python's GC handles cycles. Unlikely unless a new cycle was introduced.

### 6. Discovery Phase

`ContentOrchestrator.discover()` builds `site.xref_index` with `by_path`, `by_slug`, `by_id`, `by_heading`, `by_anchor`. All keyed by strings or (page, anchor) tuples. Bounded by content.

## Verification Steps

1. **Confirm RSS growth** (single build):
   ```bash
   BENGAL_DEBUG_MEMORY=1 bengal build 2>&1 | tee build.log
   ```
   If it hangs, use another terminal: `ps aux | grep bengal` and watch RSS over time.

2. **Repeated builds** (dev server hot reload):
   With ProcessPoolExecutor, each build is a new subprocess — memory resets. If the hang happens on the *first* validation build, the leak is within a single build.

3. **Reduce scope**:
   - Disable taxonomies (no tags in content)
   - Disable related_posts (no tags)
   - Use a minimal site (few pages)
   If hang disappears, the leak is in taxonomy/related_posts path.

4. **tracemalloc diff** (if build completes):
   Take a snapshot at content phase start and end, compare:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... content phase ...
   snapshot = tracemalloc.take_snapshot()
   top = snapshot.statistics("lineno")[:20]
   ```

## Mitigations Already in Place

- **Dev server**: `BENGAL_BUILD_EXECUTOR=process` — builds in subprocess, memory freed on exit
- **Dev server**: `force_sequential=True` — no ThreadPoolExecutor in content phase
- **get_created_dirs().clear()** at build start
- **Cache registry** with BUILD_START/BUILD_END invalidation

## Next Steps

1. Run `BENGAL_DEBUG_MEMORY=1 bengal build` on the affected site (lbliii) and capture output
2. If it hangs: run `bengal build` in one terminal, monitor `ps`/`top` RSS in another
3. If RSS grows without bound before hang: true leak; use `objgraph` or `tracemalloc` to find retainers
4. If RSS is stable but CPU high: GC thrash — check for excessive allocation in hot loops
