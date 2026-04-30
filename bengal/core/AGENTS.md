# Core Steward

This directory protects Bengal's passive domain model. Core objects describe
state, identity, relationships, and cacheable facts. They do not perform I/O,
log directly, or own rendering behavior.

Start with the root guidance in `../../AGENTS.md`, then use this file for the
local boundary.

## Protect

- Passive objects: `Site`, `Page`, `Section`, `PageCore`, records, registries.
- Compatibility shims that preserve existing template/plugin access.
- Deferred imports where core reaches into rendering only from a shim.
- The empty core mixin allow-list in `tests/unit/core/test_no_core_mixins.py`.

## Do Not

- Add filesystem I/O, direct logging, rendering, parsing, or template behavior.
- Reintroduce inheritance mixins.
- Add fields to immutable pipeline records without a design conversation.
- Widen public protocols to make one core call site easier.

## Documentation Ownership

- Keep `site/content/docs/reference/architecture/core/` aligned with core boundaries.
- Update `site/content/docs/reference/architecture/design-principles.md` when core's role changes.
- Keep object model docs honest when `Page`, `Section`, `Site`, or records move behavior.

## Local Checks

- `uv run pytest tests/unit/core tests/core -q`
- `uv run pytest tests/unit/core/test_no_core_mixins.py -q`
- `uv run ruff check bengal/core tests/unit/core tests/core`
