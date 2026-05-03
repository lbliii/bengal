# Build Phase Steward

The numbered build pipeline is intentionally explicit. Phase changes affect
cache correctness, plugin hook timing, user output, and incremental rebuilds.

Related docs:
- root `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/orchestration.md`
- `../../../site/content/docs/reference/architecture/core/pipeline.md`

## Point Of View

Build phases represent the ordered contract that turns inputs into trustworthy
outputs. They should make effects, hook timing, and observability explicit
without hiding behavior in phase coordinators.

## Protect

- The existing phase order and hook timing.
- Clear inputs and outputs for each phase.
- Atomic finalization and output safety.
- Explicit callbacks for observability instead of hidden side effects.

## Contract Checklist

- Unit tests in `tests/unit/orchestration/build/`.
- Integration tests for full build, incremental parity, artifact inventory, and
  finalization.
- Docs for phase order, pipeline inputs/outputs, and plugin hook timing.
- Cache/provenance collateral when phases add, remove, or rename artifacts.
- Changelog for user-visible output or command behavior.

## Advocate

- Observable phase inputs, outputs, timing, and diagnostics when authors need to
  understand what happened.
- Plugin hook usage over custom phase additions when extension behavior is
  needed mid-build.
- Integration tests for phase changes that affect caches, generated artifacts,
  command output, or incremental rebuilds.

## Serve Peers

- Give incremental and cache stewards precise invalidation and provenance
  events instead of inferred side effects.
- Give rendering clear handoff points and avoid mixing presentation work into
  orchestration.
- Give CLI and site docs stable build output behavior to explain.

## Do Not

- Insert or reorder phases casually.
- Add behavior that bypasses existing plugin hook surfaces.
- Mix rendering implementation details into phase coordinators.
- Treat a passing fast test as proof that incremental behavior is correct.

## Own

- Build-phase descriptions in `site/content/docs/reference/architecture/core/orchestration.md`
- `site/content/docs/reference/architecture/core/pipeline.md`
- User-facing build docs when phases affect command output or artifacts
- Checks: `uv run pytest tests/unit/orchestration/build -q`
- Checks: `uv run pytest tests/integration/test_incremental_invariants.py -q`
- Checks: `uv run ruff check bengal/orchestration/build`
