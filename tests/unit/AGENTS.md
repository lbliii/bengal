# Unit Tests Steward

Unit tests should pin small contracts and architectural boundaries. They are
the fast feedback loop contributors should trust while editing.

## Protect

- Tests that name the behavior and the boundary being guarded.
- Small fixtures and shared mocks from `tests/_testing` where possible.
- Architectural guards for core/rendering/protocol drift.
- Deterministic assertions that run well in parallel.

## Do Not

- Spin up full sites when a direct helper test would prove the behavior.
- Overfit assertions to private implementation details unless guarding architecture.
- Add sleeps or timing assumptions.
- Use private mutation in tests when a public constructor/API exists.

## Documentation Ownership

- Keep unit-test guidance in `site/content/docs/reference/architecture/meta/testing.md` current.
- Update shared-mock guidance when `tests/_testing` patterns change.

## Local Checks

- `uv run pytest tests/unit -q`
- `uv run ruff check tests/unit`
