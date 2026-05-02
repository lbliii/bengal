# Core Steward

This directory protects Bengal's passive domain model. Core objects describe
state, identity, relationships, and cacheable facts. They do not perform I/O,
log directly, or own rendering behavior.

Start with the root guidance in `../../AGENTS.md`, then use this file for the
local boundary.

## Point Of View

Core represents the stable domain model that other systems can trust. It should
make state and relationships clear without knowing how files are read, pages are
rendered, logs are emitted, or outputs are written.

## Protect

- Passive objects: `Site`, `Page`, `Section`, `PageCore`, records, registries.
- Compatibility shims that preserve existing template/plugin access.
- Deferred imports where core reaches into rendering only from a shim.
- The empty core mixin allow-list in `tests/unit/core/test_no_core_mixins.py`.

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

- Keep `site/content/docs/reference/architecture/core/` aligned with core boundaries.
- Update `site/content/docs/reference/architecture/design-principles.md` when core's role changes.
- Keep object model docs honest when `Page`, `Section`, `Site`, or records move behavior.
- `uv run pytest tests/unit/core tests/core -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- `uv run ruff check bengal/core tests/unit/core tests/core`
