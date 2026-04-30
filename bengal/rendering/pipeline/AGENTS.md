# Rendering Pipeline Steward

The rendering pipeline protects the phase where pages become output-ready
content. This is free-threading sensitive: avoid hidden shared state, late
mutation surprises, and cache writes that depend on task timing.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/pipeline.md`
- `../../../site/content/docs/reference/architecture/rendering/rendering.md`

## Protect

- Deterministic page rendering under parallel execution.
- Clear use of build context and accumulated output data.
- Separation between immutable pipeline records and mutable compatibility pages.
- Cache/provenance updates that are explicit and testable.

## Do Not

- Add global mutable caches without locks or a written reason.
- Mutate frozen `SourcePage`, `ParsedPage`, or `RenderedPage` records.
- Swallow rendering errors without diagnostics and context.
- Make output writes directly from ad hoc code paths.

## Documentation Ownership

- Own pipeline details in `site/content/docs/reference/architecture/core/pipeline.md`.
- Keep `site/content/docs/reference/architecture/rendering/rendering.md` current.
- Update cache/provenance docs when pipeline scheduling changes invalidation behavior.

## Local Checks

- `uv run pytest tests/unit/rendering tests/unit/orchestration -q`
- `uv run pytest tests/integration/test_incremental_invariants.py -q`
- `uv run ruff check bengal/rendering/pipeline bengal/orchestration/build`
