# Tests Steward

Tests protect behavior, not implementation trivia. They should make regressions
obvious, keep fixtures understandable, and avoid widening production contracts
just to satisfy mocks.

Related architecture docs:

- `../AGENTS.md`
- `../site/content/docs/reference/architecture/meta/testing.md`

## Point Of View

Tests represent the project's memory of intended behavior. They should make
real regressions obvious while keeping production contracts narrow and fixtures
easy to reason about.

## Protect

- Focused unit tests for interesting branches.
- Integration tests for user-visible workflows and build correctness.
- `tests/roots/` fixtures as intentional, minimal sites.
- Existing markers and parallel-safety expectations.

## Advocate

- Regression tests that describe user-visible failure modes, not implementation
  trivia.
- Small fixtures and explicit assertions before broad snapshots.
- Test doubles that adapt to public contracts instead of forcing production
  protocols wider.

## Serve Peers

- Give package stewards focused checks that defend their boundaries without
  making every change run the whole suite.
- Give docs and planning stewards evidence about covered behavior and risky
  gaps.
- Give protocol stewards feedback when mocks are drifting from real contracts.

## Do Not

- Patch production protocols because a test double lacks an attribute.
- Add broad snapshots where a small assertion would catch the behavior.
- Fold unrelated cleanup into a bug/regression test PR.
- Leave slow or parallel-unsafe tests unmarked.

## Own

- Own `site/content/docs/reference/architecture/meta/testing.md`.
- Keep `tests/README.md` and `tests/roots/README.md` accurate when fixture/test patterns change.
- Update docs when markers, shared mocks, or test-layer expectations change.
- `uv run pytest tests/unit -q`
- `uv run pytest tests/integration -q`
- `uv run ruff check tests`
