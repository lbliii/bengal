# RFC: Incremental Dependency Indexes

**Status**: Draft
**Created**: 2026-05-10
**Author**: Codex
**Related**: `rfc-effect-traced-incremental-builds.md`, `rfc-output-cache-architecture.md`, `rfc-incremental-build-observability.md`

## Problem

Bengal already records provenance and effects, but some warm-build paths still
rediscover affected pages by scanning effect records, page maps, or domain
objects. That is correct when the site is small, but it weakens the larger
contract Bengal wants:

- stale output must be prevented by explicit dependency edges;
- warm builds should explain why a page rebuilt or skipped;
- free-threaded builds should consume frozen facts instead of repeatedly walking
  mutable `Site` state.

The next step is not a new build phase. It is a normalized read model over
existing provenance: dependency-to-page and dependency-to-output indexes that
incremental detectors can query first.

## Goals

- Persist deterministic indexes for template, data, generated-page, track-data,
  asset, and output dependencies.
- Preserve conservative rebuild behavior when an index is missing, stale,
  corrupt, or ambiguous.
- Keep invalidation reasons distinct enough for diagnostics and tests.
- Build indexes from existing effect/provenance records before adding new hook
  surfaces or public APIs.
- Make warm-build lookup cost proportional to affected dependencies, not total
  pages.

## Non-Goals

- Replacing the effect tracer or provenance store.
- Introducing a new build phase without a separate design discussion.
- Changing plugin hook signatures.
- Skipping fallback scans until parity tests prove the index path is complete.
- Content-addressing every intermediate artifact in this RFC.

## Proposed Indexes

Use frozen records that can be serialized through the cache layer:

```python
@dataclass(frozen=True, slots=True)
class DependencyIndexEntry:
    dependency_kind: str
    dependency_key: str
    page_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    invalidation_reason: str
    producer: str
```

Indexes should be grouped by normalized dependency kind:

| Kind | Key | Query Result |
| --- | --- | --- |
| `template` | normalized template path | pages and generated outputs using it |
| `data` | normalized data file path | pages and generated outputs using it |
| `content` | source page path | rendered output plus aggregate dependents |
| `generated` | generated page key | output path and source dependencies |
| `track` | track/data item key | pages whose listings or route pages depend on it |
| `asset` | asset/source path | outputs whose HTML or manifests reference it |

The first implementation slice should be template/data/generated indexes because
those have the clearest existing provenance and user-visible stale-output risk.

## Detector Flow

1. Load cache/provenance.
2. Build or load the dependency index read model.
3. For each changed input, query the index for affected pages/outputs.
4. If the index cannot prove coverage, emit a specific fallback reason and use
   the existing broader rebuild path.
5. Record the final invalidation reasons for diagnostics and tests.

The fallback path is part of the contract. A fast miss is only valid when the
index proves that no affected output exists.

## Proof Matrix

| Surface | Required Proof |
| --- | --- |
| Unit | Index serialization, path normalization, missing/corrupt index fallback |
| Incremental | Template include chain, data-file edit, generated page dependency, deleted dependency |
| Integration | Warm build parity against current detector behavior |
| Performance | Before/after benchmark on representative large fixture |
| Free-threading | Repeated parallel warm-build smoke once index reads are shared |

## Steward Notes

- **Build/Cache/Incremental**: dependency edges must stay explicit, and cache
  uncertainty must rebuild with a named reason.
- **Core/Rendering**: indexes should point to render-owned facts without moving
  rendering behavior into core.
- **Protocols/Plugins**: do not widen `SiteLike`, `PageLike`, `SectionLike`, or
  plugin hooks for index convenience.
- **Tests/Performance**: measure complete required work, not skipped paths.

## Not Now

- Parallelizing fingerprinting or index writes.
- Removing existing scan fallbacks.
- Migrating cache schema without migration tests.
- Merging this with snapshot-and-swap build planning.
