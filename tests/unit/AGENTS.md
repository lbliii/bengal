# Unit Tests Steward

Unit tests should pin small contracts and architectural boundaries. They are
the fast feedback loop contributors should trust while editing.

Related docs:
- root `../../AGENTS.md`
- `../README.md`
- `../../site/content/docs/reference/architecture/meta/testing.md`

## Point Of View

Unit tests represent local behavioral contracts. They should prove the branch,
boundary, and failure mode with the smallest useful setup.

## Protect

- Tests that name the behavior and the boundary being guarded.
- Small fixtures and shared mocks from `tests/_testing` where possible.
- Architectural guards for core/rendering/protocol drift.
- Deterministic assertions that run well in parallel.

## Contract Checklist

- The package steward for the code under test.
- Shared mock/helper updates when public contracts change.
- Marker safety for tests that create threads/processes or mutate globals.
- Docs/testing guidance when new patterns become standard.
- Regression tests for failure paths and malformed input when relevant.

## Advocate

- Direct helper tests before full site setup.
- Property tests for parsers, serializers, URL normalization, and other broad
  input spaces.
- Named fixtures that express contract intent.

## Serve Peers

- Give implementation stewards fast targeted proof.
- Give protocols feedback when fakes need unrealistic attributes.
- Give integration tests confidence about which seam still needs workflow proof.

## Do Not

- Spin up full sites when a direct helper test would prove the behavior.
- Overfit assertions to private implementation details unless guarding
  architecture.
- Add sleeps or timing assumptions.
- Use private mutation in tests when a public constructor/API exists.

## Own

- Unit-test guidance in `site/content/docs/reference/architecture/meta/testing.md`
- Shared-mock guidance when `tests/_testing` patterns change
- Tests under `tests/unit/`
- Checks: `uv run pytest tests/unit -q`
- Checks: `uv run ruff check tests/unit`
