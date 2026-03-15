# RFC: Shared Cache Generation ID

**Status**: Draft  
**Created**: 2026-03-14  
**Category**: Build / Cache / Provenance  
**Context**: `plan/cache-provenance-evaluation.md` §2.3

---

## Summary

**Problem**: BuildCache and ProvenanceCache are independent stores that can diverge. If one is stale (e.g., ProvenanceCache cleared but BuildCache warm), behavior is undefined. The recovery path in `provenance_filter.py` (lines 467–570) uses ~100 lines of sample-based validation and conditional clearing — complexity that masks the root cause.

**Solution**: Introduce a shared **build generation ID** (UUID) written to both caches at save time. On load, compare IDs to detect divergence. When mismatch is detected, apply a defined policy (e.g., clear both, clear the stale one, or full rebuild).

**Estimated Effort**: 1–2 days

---

## Problem Statement

### Dual Cache Architecture

Bengal has two cache systems that ProvenanceFilter uses together:

| Cache | Location | Purpose |
|-------|----------|---------|
| **BuildCache** | `.bengal/cache.json[.zst]` | Fingerprints, dependencies, taxonomy, parsed/rendered output, output_sources |
| **ProvenanceCache** | `.bengal/provenance/` | Content-addressed page hashes, subvenance index |

**Flow**: `phase_incremental_filter_provenance` uses ProvenanceFilter (ProvenanceCache) for page filtering, but calls `_expand_forced_changed` which uses BuildCache (dependencies, taxonomy_deps) for data/template/taxonomy triggers.

### Divergence Scenarios

1. **ProvenanceCache cleared, BuildCache warm**: User deletes `.bengal/provenance/` or index corrupts. BuildCache still has dependencies and rendered_output. ProvenanceFilter treats all pages as "never built" → full rebuild. BuildCache dependencies may reference pages that provenance doesn't know about.

2. **BuildCache cleared, ProvenanceCache warm**: User deletes `.bengal/cache.json` or version migration wipes it. ProvenanceCache has page hashes. BuildCache is fresh → no dependencies, no output_sources. `_get_pages_for_template()` returns empty; `output_sources` missing-output check does nothing. Incremental filter may skip pages that should rebuild.

3. **Partial save failure**: BuildCache saves successfully; ProvenanceCache save fails (disk full, permission). Next build loads mismatched state.

4. **Manual / tool interference**: Scripts or IDEs clear one cache but not the other.

### Current Recovery Logic

`provenance_filter.py:467–570` handles "no pages discovered" by:

- Re-running full discovery
- Sampling provenance cache entries against recovered pages
- Conditionally clearing provenance cache if mismatch
- ~100 lines of branching logic

This recovers one specific failure mode but doesn't address general divergence. There is no check that BuildCache and ProvenanceCache belong to the same build.

### Existing Timestamps (Not Sufficient)

| Cache | Field | Format |
|-------|-------|--------|
| ProvenanceCache | `last_build_time` | `float` (epoch) in `index.json` |
| BuildCache | `last_build` | ISO datetime string |

These are **not comparable** (different formats) and **not identical** (written at different moments). A shared UUID is deterministic and comparable.

---

## Proposed Design

### 1. Build Generation ID

A UUID v4 generated once per successful build, written to both caches at save time.

```python
# At build completion (orchestrator)
import uuid
build_id = str(uuid.uuid4())
cache.last_build_id = build_id
provenance_cache.set_build_id(build_id)
```

### 2. Schema Changes

**BuildCache** (`core.py`):

- Add `build_id: str | None = None` (serialized)
- Write in `_save_to_file`; read in `_load_from_file`
- Tolerant: missing `build_id` → `None` (backward compatible)

**ProvenanceCache** (`store.py`):

- Add `build_id` to `index.json` (alongside `last_build_time`)
- `_load_index_data` returns `(pages, input_paths, last_build, build_id)`
- `save()` writes `build_id` into index

### 3. Divergence Detection

At start of `phase_incremental_filter_provenance` (or when loading caches):

```python
cache_id = getattr(cache, "build_id", None)
provenance_id = provenance_cache.get_build_id()

if cache_id is not None and provenance_id is not None and cache_id != provenance_id:
    # Divergence detected
    handle_cache_divergence(cache_id, provenance_id, ...)
```

### 4. Policy When Divergence Detected

**Options** (to be decided):

| Option | Action | Pros | Cons |
|--------|--------|------|------|
| **A. Clear both** | Delete both caches, proceed with full build | Simple, always correct | Loses all cache; slow next build |
| **B. Clear stale, keep newer** | Compare timestamps; clear the older cache | Preserves one cache | Requires reliable timestamp; complex |
| **C. Clear BuildCache only** | Always clear BuildCache, keep ProvenanceCache | Provenance is source of truth for "what's fresh" | BuildCache has more data; may lose dependency info |
| **D. Clear ProvenanceCache only** | Always clear ProvenanceCache | BuildCache has deps, output_sources | ProvenanceFilter will full-rebuild anyway |
| **E. Log and proceed** | Log warning, continue with both (current behavior) | No user-visible change | Divergence persists; undefined behavior |

**Recommendation**: **Option A (Clear both)** for initial implementation. It is the safest and simplest. A future RFC can add heuristics (e.g., Option B) if needed.

### 5. When to Generate and Write

- **Generate**: At start of build (or at successful completion, before save)
- **Write**: When `CacheManager.save()` and `save_provenance_cache()` run — both receive the same `build_id` from the orchestrator

The orchestrator (or a new `CacheCoordinator`-style service) generates the ID once per build and passes it to both save paths.

### 6. Backward Compatibility

- **Load**: If `build_id` is missing in either cache, treat as `None`. No divergence check when either is `None`.
- **Save**: Always write `build_id` when present. Old caches without `build_id` will not trigger divergence on first run after upgrade.

---

## Implementation Plan

### Phase 1: Add build_id Field (0.5 day)

1. Add `build_id: str | None = None` to BuildCache; include in save/load.
2. Add `build_id` to ProvenanceCache index.json; extend `_load_index_data` and `save()`.
3. Add `get_build_id()` to ProvenanceCache (or return from `_load_index_data`).

### Phase 2: Orchestrator Integration (0.5 day)

1. In `BuildOrchestrator` (or equivalent), generate `build_id = str(uuid.uuid4())` at build start.
2. Pass `build_id` to `CacheManager.save(cache, build_id=build_id)`.
3. Pass `build_id` to `save_provenance_cache(orchestrator)` (orchestrator holds build_id).
4. Ensure both saves use the same ID.

### Phase 3: Divergence Detection and Policy (0.5 day)

1. In `phase_incremental_filter_provenance`, after loading both caches, compare `build_id`.
2. If mismatch: clear both caches, log `cache_divergence_detected`, proceed with full build.
3. Add `logger.warning("cache_divergence_detected", build_cache_id=..., provenance_id=..., action="cleared_both")`.

### Phase 4: Tests (0.5 day)

1. Unit test: BuildCache and ProvenanceCache save/load `build_id`.
2. Integration test: Divergent caches (manually set different IDs) trigger clear and full rebuild.
3. Regression: Normal build produces matching IDs in both caches.

---

## Open Questions

1. **Generate at start vs. at completion?** Start is simpler (ID available for whole build). Completion would avoid assigning an ID to failed builds, but failed builds typically don't save.
2. **Should we add `--force-cache-reset`?** A CLI flag to clear both caches could help users recover from corruption. Out of scope for this RFC.
3. **Observability**: Should `build_id` be included in `--explain` or build logs for debugging? Low cost, high value.

---

## Related Documents

- `plan/cache-provenance-evaluation.md` — Source of §2.3
- `plan/rfc-cache-invalidation-architecture.md` — CacheCoordinator (different layer)
- `plan/rfc-incremental-build-dependency-gaps.md` — Dependency tracking context
- `bengal/build/provenance/store.py` — ProvenanceCache implementation
- `bengal/cache/build_cache/core.py` — BuildCache implementation
