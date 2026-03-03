# RFC: Automatic Stale Output Purge

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-03-03 |
| **Author** | Bengal Core Team |
| **Priority** | P2 (Medium) |
| **Related** | `bengal/orchestration/incremental/cleanup.py`, `bengal/cache/build_cache/`, `bengal/rendering/pipeline/output.py` |
| **Confidence** | 90% |

---

## Executive Summary

Bengal currently requires `--clean-output` for correct deploys (e.g. GitHub Pages) to avoid 404s when posts are removed or URLs change. This RFC proposes **automatic stale output purge** so incremental builds correctly remove outputs that are no longer produced, eliminating the need for `--clean-output` in CI.

**Goal**: Every build (incremental or full) leaves the output directory in a correct state—no stale files—without requiring `--clean-output`.

---

## Deep Dive: Current Architecture

### 1. Output Tracking

**`output_sources`** (`bengal/cache/build_cache/file_tracking.py:253-271`):

```python
# output_sources: dict[rel_output_path, source_cache_key]
# e.g. {"blog/first-post/index.html": "content/blog/first-post.md"}
def track_output(self, source_path: Path, output_path: Path, output_dir: Path) -> None:
    rel_output = str(output_path.relative_to(output_dir))
    self.output_sources[rel_output] = self._cache_key(source_path)
```

- Populated by `write_output()` in `bengal/rendering/pipeline/output.py:251-259`
- Only for content pages: skips `_generated` and `is_autodoc` pages
- Persisted in BuildCache, survives across builds

### 2. Existing Cleanup: `cleanup_deleted_files`

**Location**: `bengal/orchestration/incremental/cleanup.py`

**Logic**:
1. For each `(output_path, source_path)` in `output_sources`
2. If `source_path` does not exist on disk → delete `output_path`
3. Remove from cache

**When it runs**: Phase 5 (config check), BEFORE cache clear (`initialization.py:564-566`)

**What it handles**:
- ✅ Source file deleted → output deleted
- ✅ Autodoc source deleted → autodoc output deleted

**What it does NOT handle**:
- ❌ **Slug/URL change**: `first-post.md` → slug `second-post` → old `blog/first-post/` stays
- ❌ **Cache miss (CI)**: `output_sources` empty → no cleanup
- ❌ **Generated pages**: taxonomy, section indices, sitemap, RSS—never tracked
- ❌ **Assets**: separate flow via `asset-manifest.json` (already has stale cleanup)

### 3. Why `--clean-output` Works

**Flow** (`bengal/cli/commands/build.py:275-281`):
1. `site.clean()` wipes entire output directory
2. Sets `_clean_output_this_run` hint
3. Build writes fresh; no stale files possible

**Trade-off**: Simple and correct, but discards incremental output benefits for deploy.

### 4. EffectTracer and Output Index

**Location**: `bengal/effects/tracer.py`

- `_output_index: dict[Path, Effect]` — output path → effect that produces it
- Populated by `SnapshotEffectBuilder` from `SiteSnapshot` (pre-build)
- Used for invalidation: "what needs rebuild when X changes?"
- **Not used for purge**: EffectTracer is built from snapshot *before* render; it knows *intended* outputs, not *actual* writes

### 5. Write Flow Summary

| Output Type | Written By | track_output? | In output_sources? |
|-------------|------------|---------------|---------------------|
| Content pages | `write_output` | Yes (if not _generated/autodoc) | Yes |
| Autodoc pages | `autodoc_renderer` | No | No (autodoc_tracker) |
| Taxonomy pages | taxonomy orchestrator | No | No |
| Section indices | render pipeline | No | No |
| Sitemap, RSS, search | index generation | No | No |
| Assets | asset pipeline | No | asset-manifest.json |

---

## Problem Statement

1. **Slug/URL change**: When frontmatter `slug` or URL strategy changes, the old output path is never removed. `output_sources` maps output→source; we add new entry for new path, but old path remains (source still exists).

2. **Cache miss**: CI with cold cache has empty `output_sources`. `cleanup_deleted_files` does nothing. Stale files from previous deploy artifact can persist.

3. **Generated pages**: Taxonomy, section indices, sitemap, etc. are never tracked. If a tag is removed, its page stays.

4. **Architectural gap**: Current model is "source deleted → delete output." We need "output not in this build's manifest → delete."

---

## Proposed Solution: Output Manifest + Post-Build Purge

### Option A: Output Manifest (Recommended)

**Idea**: Build an **output manifest** during the build—the set of all paths we write. After rendering completes, purge any file in `output_dir` that is not in the manifest.

**Implementation**:

1. **OutputManifest** (or extend OutputCollector): Thread-safe set of `rel_output_path` strings. Every write calls `manifest.add(rel_path)`.

2. **Purge phase**: After all rendering (and assets) complete:
   - Walk `output_dir` (or use `Path.rglob`)
   - For each file: if `rel_path` not in manifest → delete
   - Respect `output_dir` boundary (no escape)
   - Skip `.git`, `.nojekyll`, other well-known keep files

3. **Integration point**: Add to `BuildOrchestrator` as final phase (after Phase 17 "Write outputs", before Phase 18 "Save cache").

**Pros**:
- Handles all cases: deleted source, slug change, generated pages, cache miss
- Single source of truth: "we wrote these"
- No dependency on cache structure

**Cons**:
- Must ensure every write path registers (easy to miss)
- Walk cost for large sites (mitigate: only purge when not `--clean-output`)

### Option B: Extend output_sources + Reverse Purge

**Idea**: Keep `output_sources` but add a **reverse purge**: at end of build, for each path in `output_sources`, if we did NOT write it this build, delete it.

**Implementation**:
1. At build start: snapshot `output_sources` keys as "previous outputs"
2. During build: track "outputs written this run" (same as Option A manifest)
3. At build end: `stale = previous_outputs - outputs_written`; delete each

**Pros**:
- Reuses existing structure
- Only deletes paths we know we produced before

**Cons**:
- Misses generated pages (taxonomy, etc.) that were never in output_sources
- Cache miss → previous_outputs empty → no purge

### Option C: Hybrid—Manifest + Cleanup Enhancement

**Idea**: Implement Option A (manifest + purge) but also fix `cleanup_deleted_files` to handle slug changes by maintaining source→output mapping.

**Implementation**:
1. Add `output_manifest: set[str]` built during render
2. Add purge phase using manifest
3. Optionally: change `output_sources` to `source_path → output_path` (1:1) so when we write a page we can remove old output for same source. (More invasive.)

**Recommendation**: Option A is sufficient. Option C's source→output refinement is only needed if we want to avoid walking the output dir; the walk is acceptable for typical site sizes.

---

## Detailed Design: Option A

### 1. Output Manifest

```python
# bengal/core/output.py (extend OutputCollector or new OutputManifest)

class OutputManifest:
    """Thread-safe set of output paths written this build."""
    def __init__(self) -> None:
        self._paths: set[str] = set()
        self._lock = threading.Lock()

    def add(self, rel_path: str) -> None:
        with self._lock:
            self._paths.add(rel_path)

    def paths(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._paths)
```

### 2. Registration Points

Every write must call `manifest.add(rel_path)`:

| Location | Current | Add |
|----------|---------|-----|
| `write_output` | `cache.track_output(...)` | `manifest.add(rel_output)` |
| `autodoc_renderer` | — | `manifest.add(...)` |
| Taxonomy page write | — | `manifest.add(...)` |
| Section index write | — | `manifest.add(...)` |
| Sitemap/RSS/search | — | `manifest.add(...)` |
| Asset copy | — | Use asset-manifest or add to manifest |

**Note**: Assets already have `asset-manifest.json` and `_cleanup_old_fingerprints_prepare`. We can either (a) add asset output paths to the same manifest, or (b) run asset cleanup before purge. Prefer (a) for consistency.

### 3. Purge Algorithm

```python
def purge_stale_outputs(output_dir: Path, manifest: OutputManifest) -> int:
    """
    Remove files in output_dir that are not in the manifest.
    Returns count of deleted files.
    """
    allowed = manifest.paths()
    keep_files = {".git", ".nojekyll", ".gitignore"}  # Never delete
    deleted = 0

    for path in output_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = str(path.relative_to(output_dir))
        # Normalize for comparison (e.g. backslash on Windows)
        rel_posix = rel.replace("\\", "/")

        if rel_posix in allowed:
            continue
        if path.name in keep_files:
            continue

        path.unlink(missing_ok=True)
        deleted += 1
        # Optionally: rmdir empty parents

    return deleted
```

### 4. When to Run Purge

- **Always** when not `--clean-output` (clean output means empty dir, nothing to purge)
- **After** all rendering and asset writing
- **Before** cache save (so cache reflects actual state)

### 5. Edge Cases

| Case | Handling |
|------|----------|
| User adds file to `public/` manually | Purged (considered stale). Document: don't put manual files in output_dir. |
| `.nojekyll` | In keep_files, never deleted |
| Nested dirs | `rglob` finds all; delete files, optionally rmdir empty dirs |
| Concurrent build | Out of scope (separate RFC) |
| Symlinks | `path.unlink()` removes symlink, not target. Acceptable. |

### 6. Config Option

```toml
[build]
# Purge outputs not produced this build (default: true for correctness)
# Set false to preserve manually added files in output_dir
purge_stale_outputs = true
```

---

## Migration and Rollback

1. **Phase 1**: Implement manifest + purge behind `build.purge_stale_outputs = true` (default).
2. **Phase 2**: CI workflows can remove `--clean-output` once verified.
3. **Rollback**: Set `purge_stale_outputs = false` or revert to `--clean-output`.

---

## Success Criteria

- [ ] Incremental build with deleted source → output removed (already works)
- [ ] Incremental build with slug change → old output removed (new)
- [ ] Full build with cache miss → no stale files (new)
- [ ] Taxonomy term removed → term page removed (new)
- [ ] `--clean-output` remains valid (no regression)
- [ ] CI can omit `--clean-output` and get correct deploys

---

## Open Questions

1. **Performance**: For 10k+ page sites, is `rglob` + set lookup acceptable? Alternative: maintain manifest as we write, then only check paths from previous build's manifest (requires loading old manifest from cache).

2. **Manual files**: Should we support a `public/keep/` or similar for user files that must persist? Or document that output_dir is build-managed only?

3. **Assets**: Unify with asset-manifest or keep separate? Asset manifest already has cleanup logic; we could add asset output paths to the main manifest for consistency.

---

## Related Documents

- `bengal/orchestration/incremental/cleanup.py` — existing cleanup
- `bengal/rendering/pipeline/output.py` — write_output, track_output
- `bengal/core/asset/asset_core.py` — `_cleanup_old_fingerprints_prepare`
- `plan/rfc-deployment-edge-cases.md` — deployment robustness
- Changelog: "add `--clean-output` to pages build to fix 404s on `/api/` and `/cli/`"
