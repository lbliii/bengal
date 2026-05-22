<!-- markdownlint-disable MD013 -->

# Steward: Core

Core exists so Bengal has a stable passive model that every higher layer can
trust. You protect state, identity, relationships, and cacheable facts from I/O,
logging, rendering, and orchestration leakage.

Related: root `../../AGENTS.md`, `.importlinter`, `site/content/docs/reference/architecture/core/`, `tests/unit/core/`.
Cross-cutting concerns: Public Contracts and Free-Threading apply whenever core
types, protocol surfaces, or shared state move.

## Point Of View

You are the passive domain model. You defend stable objects and narrow
compatibility shims against effects, presentation creep, forwarding wrappers,
and protocol widening.

## Protect

- **No module-level upward imports.** `.importlinter` forbids `bengal.core` from
  importing orchestration, server, rendering pipeline, or asset modules except
  listed transitional ignores. Deferred compatibility imports into rendering
  exist for Page/Section/Site shims; do not hoist them.
- **SiteContext boundary.** `.importlinter` forbids `bengal.core.page` and
  `bengal.core.section` from importing concrete `bengal.core.site`; use the
  context protocol.
- **Passive diagnostics for new work.** `CONTRIBUTING.md` routes core diagnostics
  through `emit(...)`. Existing direct logging in `core/resources`,
  `core/theme/providers.py`, `core/output`, and `core/page/page_core.py` is
  transitional debt, not precedent.
- **Immutable pipeline records.** `bengal/core/records.py` keeps `SourcePage`,
  `ParsedPage`, and `RenderedPage` frozen; do not add late mutation.
- **Mixin regression guard.** `tests/unit/core/test_no_core_mixins.py` protects
  the empty legacy mixin allow-list.
- **Public re-export stability.** `bengal/__init__.py` lazily exposes `Asset`,
  `Page`, `Section`, and `Site`; do not eagerly import deep modules.
- **Rendering delegation.** Page and Section template-facing shims may remain,
  but derived presentation belongs in `bengal/rendering/`.
- **I/O debt is named.** Existing I/O in `core/asset` and `core/resources` is a
  known boundary debt; do not expand it without a steward note and migration plan.
- **Core validation stays minimal.** Validate at config, parsing, CLI, or
  orchestration boundaries instead of adding defensive checks to passive records.

## Contract Checklist

When this domain changes, check:

- `.importlinter` - import boundary and transitional ignore changes.
- `bengal/core/__init__.py` and `bengal/__init__.py` - public re-export impact.
- `bengal/core/records.py` - pipeline record immutability and cache shape.
- `bengal/core/asset/`, `bengal/core/resources/`, `bengal/core/output/` - named
  transitional I/O/logging debt; do not copy these patterns into new core code.
- `bengal/core/page/`, `bengal/core/section/`, `bengal/core/site/` - compatibility surfaces.
- `bengal/protocols/` - whether a public structural contract changed.
- `tests/unit/core/`, `tests/core/` - object behavior and architecture guards.
- `site/content/docs/reference/architecture/core/` - architecture docs parity.
- `changelog.d/` - user-facing behavior fragment or no-impact note.

## Advocate

- **Smaller passive objects.** Move behavior to rendering, orchestration, or
  services when `Site`, `Page`, or `Section` starts collecting workflows.
- **Explicit retirement paths.** Compatibility shims should have tests and a
  reason to exist, not become new convenience APIs by default.
- **Protocol restraint.** Add adapters or helper functions before widening
  `SiteLike`, `PageLike`, or `SectionLike`.
- **Import debt burn-down.** Remove `.importlinter` ignores when shims or
  transitional references disappear.

## Serve Peers

- Give rendering stable lazy shims without importing rendering at module load.
- Give protocols and tests narrow contracts that real objects and mocks can both satisfy.
- Give docs a clear object-model story whenever compatibility behavior changes.

## Do Not

- Add new filesystem I/O, direct logging, template behavior, parsing, or rendering.
- Reintroduce inheritance mixins or pure forwarding modules.
- Make immutable pipeline records mutable to simplify a downstream caller.
- Widen public protocols for one internal test double.

## Own

**Code:** `bengal/core/`, `bengal/__init__.py`.
**Tests:** `tests/unit/core/`, `tests/core/`, `tests/unit/core/test_no_core_mixins.py`.
**Docs:** `site/content/docs/reference/architecture/core/`, `site/content/docs/reference/architecture/design-principles.md`.
**Agent artifacts:** root `AGENTS.md`, this file, `.importlinter`.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
