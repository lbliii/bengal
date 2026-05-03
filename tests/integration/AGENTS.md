# Integration Tests Steward

Integration tests protect workflows: content in, site out, cache behavior
preserved. They should catch what unit tests cannot see across subsystem seams.

Related docs:
- root `../../AGENTS.md`
- `../README.md`
- `../roots/README.md`
- `../../site/content/docs/reference/architecture/meta/testing.md`

## Point Of View

Integration tests represent users running Bengal across real directories,
commands, configs, and generated artifacts. They should prove seams and avoid
testing pure helpers twice.

## Protect

- Realistic site builds using focused `tests/roots/` fixtures.
- Output correctness for pages, assets, indexes, feeds, and incremental rebuilds.
- Regression tests for user-visible failures.
- Clear fixture ownership, isolation, and cleanup.
- CI shard duration hygiene via `.test_durations`.

## Contract Checklist

- A minimal `tests/roots/` fixture or existing root that demonstrates the
  workflow.
- Unit proof for local logic before adding large workflow coverage.
- Output docs/examples when generated artifacts or CLI workflows change.
- Marker and shard updates for slow, stateful, or parallel-unsafe tests.
- `.test_durations` refresh when integration timing materially changes.

## Advocate

- Workflow tests that follow real author commands and file layouts.
- Targeted artifact assertions instead of whole-site snapshots.
- Warm-build parity proof when caches or invalidation are involved.

## Serve Peers

- Give build/cache/rendering stewards proof across subsystem seams.
- Give docs stewards runnable examples backed by fixtures.
- Give CI owners clear marker and shard expectations.

## Do Not

- Add a new large fixture when a smaller root can demonstrate the behavior.
- Assert broad HTML blobs when a targeted output assertion is enough.
- Depend on test order or leftover build artifacts.
- Use integration tests for pure helper behavior.

## Own

- Integration-test guidance in `site/content/docs/reference/architecture/meta/testing.md`
- Fixture documentation in `tests/roots/README.md`
- Tests under `tests/integration/`
- Checks: `uv run pytest tests/integration -q`
- Checks: `uv run ruff check tests/integration`
- Refresh durations with `poe test-integration-durations` after material shard impact.
