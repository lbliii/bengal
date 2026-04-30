# Tests Steward

Tests protect behavior, not implementation trivia. They should make regressions
obvious, keep fixtures understandable, and avoid widening production contracts
just to satisfy mocks.

Related architecture docs:

- `../AGENTS.md`
- `../site/content/docs/reference/architecture/meta/testing.md`

## Protect

- Focused unit tests for interesting branches.
- Integration tests for user-visible workflows and build correctness.
- `tests/roots/` fixtures as intentional, minimal sites.
- Existing markers and parallel-safety expectations.

## Do Not

- Patch production protocols because a test double lacks an attribute.
- Add broad snapshots where a small assertion would catch the behavior.
- Fold unrelated cleanup into a bug/regression test PR.
- Leave slow or parallel-unsafe tests unmarked.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/meta/testing.md`.
- Keep `tests/README.md` and `tests/roots/README.md` accurate when fixture/test patterns change.
- Update docs when markers, shared mocks, or test-layer expectations change.

## Local Checks

- `uv run pytest tests/unit -q`
- `uv run pytest tests/integration -q`
- `uv run ruff check tests`
