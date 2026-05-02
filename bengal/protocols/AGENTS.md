# Protocols Steward

Protocols and plugin hook shapes are public contracts. They are read by plugin
developers and mocked throughout tests, so casual widening is expensive.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/meta/protocols.md`
- `../../site/content/docs/reference/architecture/meta/extension-points.md`

## Point Of View

Protocols represent the smallest public shape Bengal asks plugins, tests, and
internal adapters to rely on. They should make extension possible without
turning private convenience into permanent API.

## Protect

- The `Plugin` protocol and the 9 supported hook surfaces.
- Narrow `PageLike`, `SectionLike`, and `SiteLike` contracts.
- Test-double compatibility.
- Backward-compatible evolution through adapters where possible.

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

- Own `site/content/docs/reference/architecture/meta/protocols.md`.
- Own plugin-contract material in `site/content/docs/reference/architecture/meta/extension-points.md`.
- Update migration docs/changelog notes for public protocol or hook changes.
- `uv run pytest tests/unit/protocols tests/core/test_type_safety.py -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- `uv run ruff check bengal/protocols tests/unit/protocols`
