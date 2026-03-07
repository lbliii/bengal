# RFC: Provenance mtime Short-Circuit

**Status**: Draft  
**Created**: 2026-03-07  
**Category**: Build / Performance / Provenance

---

## Summary

**Problem**: On every incremental build, Bengal computes provenance (content hash + cascade hashes + config) for **every page** to verify cache validity. This is O(n) work even when nothing changed.

**Solution**: Store input file paths per page and `last_build_time`. Before hashing, check if any input file has `mtime > last_build_time`. If not, skip provenance computation entirely (cache hit).

**Expected impact**: "No changes" incremental builds become O(1) instead of O(n). For Chirp (342 pages), filter phase drops from ~hundreds of ms to ~tens of ms when nothing changed.

---

## Current Behavior

### Filter Flow (`bengal/build/provenance/filter.py`)

1. **Phase 1**: For each page, if forced or no stored hash → add to `pages_to_build`
2. **Phase 2**: For remaining pages, call `_verify_page_provenance(page, stored_hash)`:
   - Content pages: `_compute_provenance_fast()` → hash content + cascade + config
   - Virtual pages: `_compute_provenance()` → hash autodoc source / taxonomy / etc.
   - Compare computed hash to stored hash

### Bottleneck

`_verify_page_provenance` is called for **every** page that has a stored hash (except forced). Each call:
- Reads and hashes the content file
- Reads and hashes each cascade source (_index.md files)
- Hashes config (cached, cheap)

For 342 pages with no changes: 342 content reads + ~500+ cascade reads + 342 hash computations. All of it unnecessary when nothing changed.

### Existing Optimizations

- **Cold build**: Skip verification entirely when output is missing
- **Parallel**: Use ThreadPoolExecutor when ≥100 pages to verify
- **Fast path**: `_compute_provenance_fast` for content pages (avoids full provenance for virtual)

---

## Proposed Design

### Core Idea

If no input file has been modified since the last build, the page is fresh. No need to hash.

### New Data

| Data | Location | Format |
|------|----------|--------|
| `last_build_time` | `index.json` | ISO timestamp (float epoch also ok) |
| `input_paths` | `index.json` | `{page_path: [rel_path, ...]}` |

### Input Path Resolution

From `InputRecord` (in `ProvenanceRecord.provenance.inputs`):

| input_type | path example | Resolves to file? | mtime-check? |
|------------|--------------|-------------------|--------------|
| `content` | `content/docs/foo.md` | Yes | Yes |
| `cascade_N` | `cascade:content/docs/_index.md` | Yes (strip `cascade:`) | Yes |
| `autodoc_source` | `src/chirp/routing/router.py` | Yes | Yes |
| `cli_source` | `src/chirp/cli.py` | Yes | Yes |
| `config` | `site_config` | No single file | No |
| `taxonomy` | `tag:deployment` | No (implicit list) | No |
| `virtual` | page path | No | No |

**Rule**: Only store paths that resolve to real files. Skip config, taxonomy, virtual.

### Index Format (Extended)

```json
{
  "version": 2,
  "last_build_time": 1709827353.834,
  "pages": {
    "content/docs/foo.md": "abc123",
    ".bengal/generated/tags/deployment/page_1/index.md": "def456"
  },
  "input_paths": {
    "content/docs/foo.md": ["content/docs/foo.md", "content/docs/_index.md", "content/_index.md"],
    ".bengal/generated/tags/deployment/page_1/index.md": []
  }
}
```

- `input_paths` may be empty `[]` for pages we can't mtime-check (taxonomy, virtual)
- `last_build_time` is written when `ProvenanceCache.save()` is called (end of build)
- Version bump to 2 for backward compatibility

### Verification Flow (New)

```
_verify_page_provenance(page, stored_hash):
  1. page_path = _get_page_key(page)
  2. input_paths = cache.get_input_paths(page_path)
  3. last_build = cache.get_last_build_time()
  4. IF input_paths AND last_build:
       FOR each rel_path in input_paths:
         full_path = site.root_path / rel_path
         IF full_path.exists() AND full_path.stat().st_mtime > last_build:
           → BREAK, do full verification
       IF no path was newer:
         → RETURN (None, page, ...)  # Cache hit, skip
  5. Full verification (existing logic)
```

### When to Populate input_paths

In `ProvenanceCache.store()` and `store_batch()`, when we have a `ProvenanceRecord`:
- Extract file paths from `record.provenance.inputs`
- Resolve each to a relative path (from site root)
- Store in `_input_paths[record.page_path]`

Helper: `_extract_input_paths(record, site_root) -> list[str]`:
- For each InputRecord with type in (content, cascade_*, autodoc_source, cli_source)
- Resolve path: content/cascade use path as-is (cascade: strip prefix); autodoc/cli may need root or parent
- Return list of relative path strings

### Backward Compatibility

- **Old index (version 1)**: No `last_build_time`, no `input_paths` → skip mtime short-circuit, use existing full verification
- **New index (version 2)**: Use mtime short-circuit when data available
- **Missing input_paths for a page**: Fall back to full verification (e.g. after migration, or for pages stored before this change)

---

## Implementation Plan

### Phase 1: Store Extension

**File**: `bengal/build/provenance/store.py`

1. Add `_input_paths: dict[CacheKey, list[str]]` and `_last_build_time: float | None`
2. Update `_load_index_data()` to read `last_build_time`, `input_paths` (version 2)
3. Add `get_input_paths(page_path) -> list[str]` and `get_last_build_time() -> float | None`
4. Extend `store(record, input_paths: list[str] | None = None)` — when input_paths provided, update `_input_paths`
5. In `save()`, write `last_build_time` (time.time()) and `input_paths` to index
6. Store does NOT extract paths (no site_root). Filter extracts and passes them.

### Phase 2: Filter Integration

**File**: `bengal/build/provenance/filter.py`

1. Add `_mtime_short_circuit(page, stored_hash) -> bool`:
   - Returns True if we can skip (cache hit)
   - Returns False if we need full verification
   - Gets input_paths, last_build_time from cache
   - If either missing, return False
   - For each path, resolve to Path (try site.root_path / path, then site.root_path.parent / path), stat, compare mtime
   - If any mtime > last_build_time, return False
   - Return True
2. In `_verify_page_provenance`, call `_mtime_short_circuit` first (before _compute_provenance_fast)
3. In `record_build`, before `cache.store(record)`: extract input_paths, call `cache.store(record, input_paths)`

### Phase 3: Path Extraction Helper

**File**: `bengal/build/provenance/filter.py`

Add `_extract_input_paths_for_mtime(record: ProvenanceRecord) -> list[str]`:
- For each inp in record.provenance.inputs:
  - If inp.input_type in ("content", "autodoc_source", "cli_source"): path = inp.path
  - If inp.input_type.startswith("cascade_"): path = inp.path.replace("cascade:", "", 1)
  - Else: skip (config, taxonomy, virtual)
- For each path, resolve to file: try site.root_path / path, then site.root_path.parent / path
- If file exists, include path in result (use path as stored for mtime lookup)
- Return list of path strings

### Phase 4: Tests

1. **Unit**: `test_mtime_short_circuit_skips_when_no_changes` — build, build again with no changes, verify filter skips
2. **Unit**: `test_mtime_short_circuit_rebuilds_when_content_changed` — build, touch content file, build, verify page rebuilt
3. **Unit**: `test_mtime_short_circuit_rebuilds_when_cascade_changed` — build, touch _index.md, build, verify
4. **Unit**: `test_backward_compat_old_index` — index without last_build_time, verify full verification
5. **Unit**: `test_taxonomy_pages_full_verification` — taxonomy pages have empty input_paths, always full verify
6. **Integration**: Chirp site, two back-to-back builds, measure filter time

### Phase 5: Observability

- Log when mtime short-circuit triggers: `mtime_short_circuit_hits` count
- Add to `--explain` or verbose: show "skipped (mtime)" vs "skipped (hash match)"
- Optional: `BENGAL_PROVENANCE_MTIME=0` to disable for debugging

---

## Edge Cases

| Case | Handling |
|------|----------|
| Clock skew | mtime is filesystem time; last_build_time is process time. Minor skew could cause rare false negative (rebuild when not needed). Acceptable. |
| File deleted | If input path doesn't exist, treat as changed (rebuild) |
| New page | No stored hash → build (existing) |
| Taxonomy page | input_paths = [] → always full verification |
| Config-only change | No file paths for config → mtime check passes → hash check fails (config hash different) → rebuild. Correct. |
| First build after upgrade | Old index, no input_paths → full verification. Correct. |

---

## Files to Modify

| File | Changes |
|------|---------|
| `bengal/build/provenance/store.py` | Add input_paths, last_build_time; extend index format; get_input_paths, get_last_build_time |
| `bengal/build/provenance/filter.py` | Add _mtime_short_circuit, _extract_input_paths_for_mtime; call before full verify; pass input_paths to store |
| `bengal/orchestration/build/provenance_filter.py` | No changes (filter is self-contained) |

---

## Success Criteria

- [ ] Chirp "no changes" incremental build: filter phase < 50ms (vs current ~200–500ms)
- [ ] All existing provenance tests pass
- [ ] New tests for mtime short-circuit
- [ ] Backward compatible with existing provenance caches

---

## Future Work

- **Event-based invalidation**: When file watcher reports changes, skip verification for unaffected pages entirely (stronger than mtime)
- **Consolidated storage**: SQLite or single JSONL to reduce file count
- **Global fingerprint**: Single hash of all (path, mtime) for instant "nothing changed" detection
