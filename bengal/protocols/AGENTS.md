# Protocols Steward

Protocols and plugin hook shapes are public contracts. They are read by plugin
developers and mocked throughout tests, so casual widening is expensive.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/meta/protocols.md`
- `../../site/content/docs/reference/architecture/meta/extension-points.md`

## Protect

- The `Plugin` protocol and the 9 supported hook surfaces.
- Narrow `PageLike`, `SectionLike`, and `SiteLike` contracts.
- Test-double compatibility.
- Backward-compatible evolution through adapters where possible.

## Do Not

- Add protocol attributes to satisfy one implementation detail.
- Change hook signatures without a migration note and design discussion.
- Use protocols as a dumping ground for private conveniences.
- Break third-party plugins for internal cleanup.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/meta/protocols.md`.
- Own plugin-contract material in `site/content/docs/reference/architecture/meta/extension-points.md`.
- Update migration docs/changelog notes for public protocol or hook changes.

## Local Checks

- `uv run pytest tests/unit/protocols tests/core/test_type_safety.py -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- `uv run ruff check bengal/protocols tests/unit/protocols`
