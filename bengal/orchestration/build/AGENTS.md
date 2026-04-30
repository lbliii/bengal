# Build Phase Steward

The numbered build pipeline is intentionally explicit. Phase changes affect
cache correctness, plugin hook timing, user output, and incremental rebuilds.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/orchestration.md`

## Protect

- The existing phase order and hook timing.
- Clear inputs and outputs for each phase.
- Atomic finalization and output safety.
- Explicit callbacks for observability instead of hidden side effects.

## Do Not

- Insert or reorder phases casually.
- Add behavior that bypasses existing plugin hook surfaces.
- Mix rendering implementation details into phase coordinators.
- Treat a passing fast test as proof that incremental behavior is correct.

## Documentation Ownership

- Own build-phase descriptions in `site/content/docs/reference/architecture/core/orchestration.md`.
- Keep `site/content/docs/reference/architecture/core/pipeline.md` aligned with phase inputs/outputs.
- Update user-facing build docs when phase behavior affects command output or artifacts.

## Local Checks

- `uv run pytest tests/unit/orchestration/build -q`
- `uv run pytest tests/integration/test_incremental_invariants.py -q`
- `uv run ruff check bengal/orchestration/build`
