# Integration Tests Steward

Integration tests protect workflows: content in, site out, cache behavior
preserved. They should catch what unit tests cannot see across subsystem seams.

## Protect

- Realistic site builds using focused `tests/roots/` fixtures.
- Output correctness for pages, assets, indexes, feeds, and incremental rebuilds.
- Regression tests for user-visible failures.
- Clear fixture ownership and cleanup.

## Do Not

- Add a new large fixture when a smaller root can demonstrate the behavior.
- Assert broad HTML blobs when a targeted output assertion is enough.
- Depend on test order or leftover build artifacts.
- Use integration tests for pure helper behavior.

## Documentation Ownership

- Keep integration-test guidance in `site/content/docs/reference/architecture/meta/testing.md` current.
- Own fixture documentation in `tests/roots/README.md` when roots are added or reshaped.

## Local Checks

- `uv run pytest tests/integration -q`
- `uv run ruff check tests/integration`
