# RFC: Snapshot Build Plan Handoff

**Status**: Draft
**Created**: 2026-05-10
**Author**: Codex
**Related**: `rfc-bengal-snapshot-engine.md`, `rfc-template-view-model-contracts.md`, `rfc-incremental-dependency-indexes.md`

## Problem

Bengal has immutable page records, snapshot types, and some snapshot-aware
rendering paths, but build and incremental orchestration can still fall back to
mutable live `Site`, `Page`, and `Section` objects during planning and worker
execution.

That fallback preserves compatibility, but it limits the free-threading story:

- workers may read mutable state whose lifecycle is owned elsewhere;
- `@cached_property` compatibility values can hide rebuild invalidation;
- plugin phase hooks can couple third-party code to mutable internal objects;
- repeated lazy lookups make performance improvements harder to measure.

The target design is a build-scoped immutable handoff: assemble a frozen
`BuildPlan` or `IncrementalPlan`, then let render/build workers consume the plan
instead of rediscovering mutable state.

## Goals

- Define the frozen facts each worker needs before rendering starts.
- Keep `SourcePage -> ParsedPage -> RenderedPage` immutable.
- Move hot template-facing facts toward rendering-owned precompute tables.
- Provide plugin-facing read-only context before changing hook internals.
- Preserve existing public `Page`, `Section`, `Site`, and plugin behavior while
  the plan path proves parity.

## Non-Goals

- Removing compatibility shims in the first implementation.
- Adding new build phases.
- Changing plugin hook signatures without migration notes.
- Hoisting deferred imports across core/rendering boundaries.
- Replacing all `cached_property` usage at once.

## Proposed Records

```python
@dataclass(frozen=True, slots=True)
class BuildPlan:
    config_hash: str
    content_snapshot_id: str
    pages: tuple[PagePlan, ...]
    sections: tuple[SectionPlan, ...]
    template_dependencies: Mapping[str, tuple[str, ...]]
    generated_outputs: tuple[GeneratedOutputPlan, ...]
    plugin_context: PluginBuildContext
```

`BuildPlan` should be assembled after content discovery and before parallel
render execution. For warm builds, an `IncrementalPlan` can wrap the full plan
with affected page/output sets and named invalidation reasons.

```python
@dataclass(frozen=True, slots=True)
class IncrementalPlan:
    build_plan: BuildPlan
    changed_inputs: tuple[str, ...]
    affected_pages: tuple[str, ...]
    affected_outputs: tuple[str, ...]
    fallback_reasons: tuple[str, ...]
```

The first slice should not require every consumer to migrate. It should add a
plan path for one narrow render/incremental workflow, compare output parity, and
leave the existing mutable path as the fallback.

## Plugin Context

Snapshot-and-swap is incomplete if plugins still receive broad mutable internals
at the same boundary. Future plugin-facing context should be narrow and
read-only:

```python
class PluginBuildContext(Protocol):
    @property
    def config(self) -> Mapping[str, object]: ...

    @property
    def pages(self) -> Sequence[PagePlan]: ...

    @property
    def outputs(self) -> Sequence[GeneratedOutputPlan]: ...
```

Existing phase hooks must remain compatible until a separate protocol migration
lands. New context adapters should be additive, contract-tested, and documented
before any hook signature changes.

## Migration Shape

1. Add internal plan records and construction tests.
2. Route one measured hot path through the plan behind existing orchestration
   boundaries.
3. Prove output parity for cold build, warm build, template edit, and content
   edit.
4. Add plugin read-only context adapters without changing existing callback
   forms.
5. Expand plan consumers only after benchmarks show reduced lock contention or
   repeated lookup work.

## Proof Matrix

| Surface | Required Proof |
| --- | --- |
| Unit | Frozen plan construction, no late mutation, serialization where needed |
| Rendering | Rendered-output parity fixture and template compatibility fixture |
| Incremental | Cold/warm/content-edit/template-edit parity |
| Plugins | Existing hook compatibility plus read-only context adapter tests |
| Performance | Worker-scaling and phase-breakdown benchmark before/after |
| Free-threading | Repeated parallel render smoke with shared plan reads |

## Steward Notes

- **Core**: `Page`, `Section`, and `Site` remain compatibility/coordinator
  surfaces; do not move rendering behavior into core.
- **Rendering**: template-facing URLs, excerpts, TOCs, references, and listing
  facts belong in rendering-owned plan/read-model data.
- **Build/Cache/Incremental**: plans must carry explicit invalidation reasons
  and conservative fallback paths.
- **Protocols/Plugins**: prefer adapters and capability protocols over widened
  `SiteLike`, `PageLike`, `SectionLike`, or hook signatures.
- **Tests/Performance**: benchmark complete work, not a path that skipped
  required output or dependency checks.

## Not Now

- Deleting mutable compatibility state.
- Making plugin hooks receive only `PluginBuildContext`.
- Broad `cached_property` removal.
- Async rewrite or executor redesign.
- Content-addressed intermediate artifact migration.
