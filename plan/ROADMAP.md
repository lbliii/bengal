<!-- markdownlint-disable MD013 MD060 -->

# Bengal Roadmap - Active Plan Set

**Created**: 2026-04-12  
**Updated**: 2026-05-29
**Baseline**: current `main` at `ab0f22339` plus source/test checks listed below
**Version Target**: v0.4.0 beta  
**Planning Rule**: root `plan/` keeps only the active agenda. Completed,
superseded, stale, and evaluated plans live in their status directories.

---

## Verification Snapshot

Machine-checked on 2026-05-29:

- `pyproject.toml` reports Bengal `0.3.3`.
- `bengal/core/page/__init__.py` still defines mutable `class Page`.
- Frozen `SourcePage`, `ParsedPage`, and `RenderedPage` records exist in
  `bengal/core/records.py`.
- Frozen `SiteSnapshot`, `PageSnapshot`, `SectionSnapshot`, `NavigationPlan`,
  and `TaxonomyPlan` exist in `bengal/snapshots/types.py`.
- Protocol annotation counts are still mixed: `site: Site` 296 vs
  `site: SiteLike` 274, `page: Page` 120 vs `page: PageLike` 253,
  `section: Section` 82 vs `section: SectionLike` 63.
- `uv run ty check bengal/` reports 558 diagnostics.
- Bundled themes are `default` and `chirpui`; `bengal theme preview`,
  swizzle commands, library assets, and Chirp UI integration tests exist.
- Plugin wiring exists for directives, roles, template extensions, and phase
  hooks; the old "four stubs are never called" claim is obsolete.
- Search supports the explicit `lunr` backend only. Pagefind and Algolia are
  not implemented.
- Version lifecycle status exists as `VersionStatus = Literal["current",
  "legacy", "deprecated", "preview", "eol"]`; the old "add VersionStatus"
  roadmap item is complete.
- CI cache inputs/hash commands and autodoc cache self-validation exist.
- `bengal audit` is registered as a Milo command and returns
  `bengal.audit.v1` envelopes; health/audit ownership is still not fully
  separated.
- SourcePage adapter tests and notebook-title tests landed, reducing Sprint 6
  risk for the immutable page pipeline but not deleting the `Page` class.
- Page deletion proof has started: direct production
  `from bengal.core.page import Page` imports are isolated to
  `bengal/content/discovery/page_adapter.py`, while public `bengal.Page` and
  `bengal.core.Page` exports are lazy compatibility surfaces. The remaining
  `bengal/` + `tests/` direct import count is 71, all but the adapter in tests.
  `tests/unit/content/test_page_construction_boundary.py` now locks production
  constructor and direct-import isolation to the SourcePage adapter.

No full test suite was run for this planning pass.

---

## Active Root Plans

| # | Plan | Status | Why It Stays Root |
|---|------|--------|-------------------|
| 1 | `epic-immutable-page-pipeline.md` | Active | Delete mutable `Page`; this is still the largest architecture blocker. |
| 2 | `epic-delete-forwarding-wrappers.md` | Active | Shrink compatibility wrappers after Page/Site boundaries are clearer. |
| 3 | `epic-openapi-rest-layout-upgrade.md` | Active | Autodoc/API docs remain a production-readiness gap. |
| 4 | `epic-ux-sharp-edges.md` | Active | Consolidates user-visible CLI, error, directive, and scaffold polish. |
| 5 | `rfc-effect-traced-incremental-builds.md` | Active | Long-term warm-build correctness and template HMR direction. |
| 6 | `rfc-incremental-dependency-indexes.md` | Active / partially implemented | Narrow read-model needed before broader effect-traced rebuild work. |
| 7 | `rfc-snapshot-build-plan-handoff.md` | Active | Free-threaded handoff from mutable build planning to worker execution. |
| 8 | `rfc-template-view-model-contracts.md` | Active | Theme and rendering contract for Chirp UI and future themes. |
| 9 | `rfc-theme-library-assets.md` | Active | Library asset contract for Chirp UI parity in static and dev output. |
| 10 | `rfc-health-diagnostics-audit.md` | Active implementation | Artifact audit and health diagnostics are still being separated. |

This file is the eleventh root planning file and owns sequencing.

---

## Current Sequencing

| Priority | Work | Proof Before Close |
|----------|------|--------------------|
| P1 | Delete mutable `Page` compatibility class | `rg '^class Page\\b' bengal/core/page` returns no hits; full tests pass. |
| P1 | Re-measure and reduce `ty` floor | Current count is 558 diagnostics; close with a lower recorded count and no new suppressions. |
| P1 | OpenAPI REST autodoc polish | Focused autodoc tests cover Python, CLI, OpenAPI, and layout output. |
| P1 | Snapshot build-plan handoff | Worker paths consume frozen plans/snapshots instead of live mutable objects. |
| P2 | Incremental dependency indexes | Warm-build tests prove dependency-to-output invalidation without broad scans. |
| P2 | Effect-traced template HMR | Template edits rebuild only affected pages and record explainable effects. |
| P2 | Template view model contracts | Directives, shortcodes, autodoc, indexes, and themes consume stable data contracts. |
| P2 | Theme library assets | Chirp UI provider assets have static/dev parity and artifact audit coverage. |
| P2 | Health diagnostics audit | Health, artifact audit, and terminal reporting have separated ownership and tests. |
| P3 | Delete forwarding wrappers | Remove compatibility forwarding only after callers and tests prove the narrower API. |
| P3 | UX sharp edges | Use as a holding epic for confirmed user-visible polish, not architecture drift. |

## Saga Queue

These are the next sensible thematic PRs, in order, if a new session asks what
to pick up. Once the user asks to begin one, create a runtime goal for that saga
with the source plan, commit shape, proof commands, and closure criteria from
this table.

| Priority | Saga | Source Plan | Commit Shape | Stop/Proof Notes |
|----------|------|-------------|--------------|------------------|
| 1 | Page deletion proof slice | `epic-immutable-page-pipeline.md` Sprint 6 | Production imports, test factories, protocol/export cleanup, docs/changelog | Continue migrating tests that only need page-like fixtures; stop before changing public `Page` exports. Prove with `rg '^class Page\\b' bengal/core/page`, direct-import counts, boundary tests, focused page/source tests, `uv run ty check bengal/`, then broader test run. |
| 2 | Health/audit ownership closure | `rfc-health-diagnostics-audit.md` | Resolver ownership, audit/check overlap tests, CLI/docs parity | `bengal audit` exists; remaining work is separation and duplicate-report control. |
| 3 | OpenAPI REST polish | `epic-openapi-rest-layout-upgrade.md` | Endpoint/schema rendering, CSS polish, integration/performance proof | User-facing docs/templates; include visual/output proof and changelog. |
| 4 | Ty floor reduction | Roadmap P1 | One diagnostic family per commit | No suppressions or public API widening just to satisfy ty. |

---

## Archived In This Pass

Moved out of root on 2026-05-28:

- `plan/complete/`: shipped or effectively complete work such as Agent DX
  polish, CI cache inputs/hash, dev-server buffer hardening, output cache,
  template error codes, and theme ecosystem phase 1.
- `plan/superseded/`: old architecture designs now replaced by the active
  snapshot, incremental, and wrapper plans.
- `plan/stale/`: older drafts that may contain useful ideas but need a fresh
  source audit before implementation.
- `plan/evaluated/`: historical maturity assessments and audits retained as
  baseline evidence, not current agenda.

The goal is a small active surface: if a plan is not one of the root files
above, it is background evidence, not next work.
