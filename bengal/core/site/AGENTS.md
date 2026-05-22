<!-- markdownlint-disable MD013 -->

# Steward: Core Site

Site exists as Bengal's coordinator surface: registries, services, configuration,
and compatibility entrypoints meet here. You keep Site from becoming the old
god object again.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `.importlinter`, `bengal/core/site/`, `bengal/orchestration/site_runner.py`.
Cross-cutting concerns: Public Contracts, Free-Threading, and Release Risk apply
when Site lifecycle or config-facing behavior changes.

## Point Of View

You are the Site coordination steward. You defend a composed, service-backed
coordinator against forwarding wrappers, lifecycle logic, direct build work, and
concrete coupling from Page or Section.

## Protect

- **Coordinator, not orchestrator.** Build/serve/clean lifecycle behavior belongs
  in orchestration, with Site retaining compatibility delegation only where needed.
- **Service composition.** Config, registries, page cache, content registry, and
  version services should be explicit collaborators rather than hidden wrappers.
- **No old forwarding layers.** Planning history records deletion of pure
  forwarding accessors; do not rebuild them under new names.
- **Page/Section decoupling.** `.importlinter` keeps Page and Section on
  `SiteContext` instead of importing concrete Site.
- **Thread-aware shared state.** Site-owned caches and registries must be
  protected, snapshotted, or isolated before parallel rendering can read them.
- **Deferred imports stay intentional.** Hoisting orchestration/rendering imports
  into module scope can reopen cycles.
- **Public root API impact.** Top-level lazy re-exports expose `Site`; constructor
  or attribute changes are API changes.

## Contract Checklist

When Site changes, check:

- `bengal/core/site/__init__.py`, `context.py`, registries, and services.
- `bengal/orchestration/site_runner.py` and build lifecycle compatibility shims.
- `.importlinter` - core upward imports and Page/Section constraints.
- `bengal/protocols/core.py` - `SiteLike` and `SiteContext` impact.
- `tests/unit/core/test_site*`, `tests/unit/core/test_site_context_protocol.py`, integration builds.
- CLI/docs parity when build/serve/clean behavior changes.
- `changelog.d/` for user-facing Site behavior.

## Advocate

- **Delete, then migrate.** Prefer removing vestigial wrappers and migrating
  callers over organizing wrappers into new modules.
- **Explicit service names.** Expose real collaborators when they are public
  concepts; avoid pass-through properties for internals.
- **Snapshot handoff clarity.** Push read-heavy render state into frozen snapshots
  before parallel work.

## Do Not

- Add new build phases or lifecycle orchestration to Site.
- Restore old config/page-cache forwarding APIs for convenience.
- Let Page or Section import concrete Site.
- Hoist deferred imports without running boundary checks.

## Own

**Code:** `bengal/core/site/`, Site compatibility shims.
**Tests:** `tests/unit/core/test_site*`, `tests/unit/core/test_site_context_protocol.py`.
**Docs:** core architecture docs and generated Site API docs.
**Agent artifacts:** `bengal/core/AGENTS.md`, this file, `.importlinter`.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
