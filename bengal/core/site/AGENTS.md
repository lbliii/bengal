# Site Steward

`Site` holds the site graph and coordinates through registries, services, and
orchestration. It is not a place to reacquire forwarding wrappers just because a
service exists.

Related docs:
- root `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../site/content/docs/reference/architecture/core/object-model.md`
- `../../../site/content/docs/reference/architecture/core/orchestration.md`
- `../../../site/content/docs/reference/architecture/core/data-flow.md`

## Point Of View

Site represents the assembled project graph and public compatibility surface.
It should coordinate durable state while leaving build execution, rendering,
and presentation to their owning layers.

## Protect

- Site state, registries, and lookup surfaces used by orchestration/rendering.
- Stable compatibility behavior expected by themes and plugins.
- The post-mixin shape of `bengal/core/site/`.
- Clear handoff to orchestration for build/serve/clean behavior.

## Contract Checklist

- Site lifecycle and registry tests under `tests/unit/core/` and `tests/core/`.
- Import-linter contracts and `test_no_core_mixins.py`.
- Programmatic API docs for `Site.from_config()`, build, serve, and graph access.
- Protocol impact on `SiteLike`, plugin hooks, and test mocks.
- CLI/docs impact if user-visible lifecycle behavior changes.

## Advocate

- Composed services for real subsystems, not forwarding wrappers.
- Migration of build and server work into orchestration/server modules.
- Narrow protocols and adapters when downstream callers need a smaller surface.

## Serve Peers

- Give orchestration a clear graph and service handoff.
- Give rendering and themes stable lookup surfaces without owning presentation.
- Give protocols/tests realistic but narrow site contracts.

## Do Not

- Add build-phase logic, output writes, rendering behavior, or logging here.
- Add broad forwarding methods to mirror internal services.
- Expand `SiteLike` as a shortcut for one implementation detail.
- Reintroduce Site mixins.

## Own

- Site sections in `site/content/docs/reference/architecture/core/object-model.md`
- `site/content/docs/reference/architecture/core/orchestration.md`
- `site/content/docs/reference/architecture/core/data-flow.md`
- Checks: `uv run pytest tests/unit/core tests/core -q`
- Checks: `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- Checks: `uv run ruff check bengal/core/site`
