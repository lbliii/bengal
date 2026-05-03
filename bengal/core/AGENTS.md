# Core Steward

This directory protects Bengal's passive domain model. Core objects describe
state, identity, relationships, and cacheable facts without performing I/O,
logging directly, or owning rendering behavior.

Related docs:
- root `../../AGENTS.md`
- `../../CLAUDE.md`
- `../../site/content/docs/reference/architecture/core/object-model.md`
- `../../site/content/docs/reference/architecture/design-principles.md`

## Point Of View

Core represents the stable domain model that other systems can trust. It should
make state and relationships clear without knowing how files are read, pages are
rendered, logs are emitted, or outputs are written.

## Protect

- Passive objects: `Site`, `Page`, `Section`, `PageCore`, records, registries,
  and value objects.
- Compatibility shims that preserve existing template/plugin access while
  delegating presentation elsewhere.
- Deferred imports where core reaches into rendering or orchestration only from
  a compatibility shim.
- The empty core mixin allow-list in `tests/unit/core/test_no_core_mixins.py`.
- Import-linter contracts that keep page/section coupled to `SiteContext`
  instead of concrete `Site`.

## Contract Checklist

- Unit and architecture guards: `tests/unit/core/`, `tests/core/`,
  `tests/unit/core/test_no_core_mixins.py`, `.importlinter`.
- Protocol impact: `bengal/protocols/`, `tests/unit/protocols/`, template-facing
  compatibility properties.
- Rendering impact: Page/Section shims must have rendering-side proof when
  derived content, URLs, TOCs, excerpts, or resource views change.
- Docs: core object-model and design-principle docs under `site/content/docs/`.
- Changelog: required when user-facing behavior under `bengal/` changes.

## Advocate

- Smaller passive records and clearer ownership when behavior starts collecting
  on `Site`, `Page`, or `Section`.
- Rendering, orchestration, or boundary services when a feature needs effects,
  validation, presentation, or diagnostics.
- Compatibility shims with tests and a retirement path instead of new core
  convenience surfaces.

## Serve Peers

- Give rendering stable, lazy access points for template-facing compatibility
  without importing rendering at module load time.
- Give protocols and tests narrow object contracts that are easy to mock.
- Give docs clear object-model boundaries so contributors know where behavior
  belongs.

## Do Not

- Add filesystem I/O, direct logging, rendering, parsing, or template behavior.
- Reintroduce inheritance mixins.
- Add fields to immutable pipeline records without a design conversation.
- Widen public protocols to make one core call site easier.

## Own

- `site/content/docs/reference/architecture/core/`
- `site/content/docs/reference/architecture/design-principles.md`
- `tests/unit/core/`, `tests/core/`, and core import-linter expectations
- Checks: `uv run pytest tests/unit/core tests/core -q`
- Checks: `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- Checks: `uv run ruff check bengal/core tests/unit/core tests/core`
