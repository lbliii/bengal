# Protocols Steward

Protocols and plugin hook shapes are public contracts. They are read by plugin
developers and mocked throughout tests, so casual widening is expensive.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/meta/protocols.md`
- `../../site/content/docs/reference/architecture/meta/extension-points.md`
- `../../site/content/docs/extending/plugins.md`

## Point Of View

Protocols represent the smallest public shape Bengal asks plugins, tests, and
internal adapters to rely on. They should make extension possible without
turning private convenience into permanent API.

## Protect

- The `Plugin` protocol and the 9 supported hook surfaces.
- Narrow `PageLike`, `SectionLike`, and `SiteLike` contracts.
- Template, parser, and syntax-highlighting engine protocols.
- Test-double compatibility and backward-compatible evolution.

## Contract Checklist

- Protocol tests in `tests/unit/protocols/` and type-safety tests in
  `tests/core/test_type_safety.py`.
- Plugin docs, extension-point docs, and migration notes for signature changes.
- Mocks/fakes under `tests/_testing/` and downstream test fixtures.
- Changelog for public protocol or hook behavior changes.
- Parity matrix when a contract spans CLI, plugin hook, programmatic API, and
  docs.

## Advocate

- Internal adapters, helper functions, or rendering services before protocol
  widening.
- Migration notes, changelog fragments, and compatibility tests when public
  contracts must change.
- Contract tests that prove plugins can keep working across internal cleanup.

## Serve Peers

- Give core, rendering, and orchestration stable minimal interfaces instead of
  broad object coupling.
- Give tests mocks and fakes that model public contracts rather than internal
  implementation detail.
- Give docs exact extension-point language that plugin developers can trust.

## Do Not

- Add protocol attributes to satisfy one implementation detail.
- Change hook signatures without a migration note and design discussion.
- Use protocols as a dumping ground for private conveniences.
- Break third-party plugins for internal cleanup.

## Own

- `site/content/docs/reference/architecture/meta/protocols.md`
- `site/content/docs/reference/architecture/meta/extension-points.md`
- Public protocol migration notes and changelog collateral
- Checks: `uv run pytest tests/unit/protocols tests/core/test_type_safety.py -q`
- Checks: `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- Checks: `uv run ruff check bengal/protocols tests/unit/protocols`
