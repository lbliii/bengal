# Site Steward

`Site` holds the site graph and coordinates through registries, services, and
orchestration. It is not a place to reacquire forwarding wrappers just because a
service exists.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/core/orchestration.md`

## Protect

- Site state, registries, and lookup surfaces used by orchestration/rendering.
- Stable compatibility behavior expected by themes and plugins.
- The post-mixin shape of `bengal/core/site/`.
- Clear handoff to orchestration for build work.

## Do Not

- Add build-phase logic, output writes, rendering behavior, or logging here.
- Add broad forwarding methods to mirror internal services.
- Expand `SiteLike` as a shortcut for one implementation detail.
- Reintroduce Site mixins.

## Documentation Ownership

- Own Site sections in `site/content/docs/reference/architecture/core/object-model.md`.
- Keep `site/content/docs/reference/architecture/core/orchestration.md` honest about what Site delegates.
- Update `site/content/docs/reference/architecture/core/data-flow.md` when Site state handoffs change.

## Local Checks

- `uv run pytest tests/unit/core tests/core -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- `uv run ruff check bengal/core/site`
