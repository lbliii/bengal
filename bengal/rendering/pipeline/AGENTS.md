# Rendering Pipeline Steward

The rendering pipeline protects the phase where pages become output-ready
content. This is free-threading sensitive: avoid hidden shared state, late
mutation surprises, and cache writes that depend on task timing.

Related docs:
- root `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/pipeline.md`
- `../../../site/content/docs/reference/architecture/rendering/rendering.md`

## Point Of View

The pipeline represents the handoff from parsed content to render-ready output.
It should make inputs, outputs, dependencies, and errors explicit enough for
parallel execution and incremental reuse.

## Protect

- Deterministic page rendering under parallel execution.
- Clear use of build context and accumulated output data.
- Separation between immutable pipeline records and mutable compatibility pages.
- Cache/provenance updates that are explicit and testable.

## Contract Checklist

- Pipeline, rendering, orchestration, and incremental tests that prove full and
  warm build parity.
- Docs for `SourcePage -> ParsedPage -> RenderedPage` and build pipeline handoff.
- Cache/provenance collateral when dependency or output-hash behavior changes.
- Threading notes for shared mutable state, contextvars, task-local caches, and
  worker exception handling.

## Advocate

- Explicit dependency capture over inferred global state.
- Early, contextual error reporting for template/parser failures.
- Tests that compare sequential and parallel outputs for hot paths.

## Serve Peers

- Give incremental/cache stewards trustworthy provenance and output-hash data.
- Give rendering helpers a deterministic execution context.
- Give tests small fixtures that prove task ordering does not affect output.

## Do Not

- Add global mutable caches without locks or a written reason.
- Mutate frozen `SourcePage`, `ParsedPage`, or `RenderedPage` records.
- Swallow rendering errors without diagnostics and context.
- Make output writes directly from ad hoc code paths.

## Own

- `site/content/docs/reference/architecture/core/pipeline.md`
- `site/content/docs/reference/architecture/rendering/rendering.md`
- Cache/provenance docs when pipeline scheduling changes invalidation behavior
- Checks: `uv run pytest tests/unit/rendering tests/unit/orchestration -q`
- Checks: `uv run pytest tests/integration/test_incremental_invariants.py -q`
- Checks: `uv run ruff check bengal/rendering/pipeline bengal/orchestration/build`
