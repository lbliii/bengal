<!-- markdownlint-disable MD013 MD060 -->

# Bengal Roadmap - Active Plan Set

**Created**: 2026-04-12  
**Updated**: 2026-05-30
**Baseline**: current `main` at `ab0f22339` plus source/test checks listed below
**Version Target**: v0.4.0 beta  
**Planning Rule**: root `plan/` keeps only the active agenda. Completed,
superseded, stale, and evaluated plans live in their status directories.

---

## Verification Snapshot

Machine-checked on 2026-05-30:

- `pyproject.toml` reports Bengal `0.3.3`.
- `bengal/core/page/__init__.py` no longer exports `Page`, and
  `bengal/core/page/legacy.py` has been deleted.
- Frozen `SourcePage`, `ParsedPage`, and `RenderedPage` records exist in
  `bengal/core/records.py`.
- Frozen `SiteSnapshot`, `PageSnapshot`, `SectionSnapshot`, `NavigationPlan`,
  and `TaxonomyPlan` exist in `bengal/snapshots/types.py`.
- Protocol annotation counts are still mixed: `site: Site` 296 vs
  `site: SiteLike` 274, `page: Page` 120 vs `page: PageLike` 253,
  `section: Section` 82 vs `section: SectionLike` 63.
- `uv run ty check bengal/` reports 531 diagnostics.
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
- The mutable Page deletion saga is complete. Direct production
  `from bengal.core.page import Page` imports are gone, public `bengal.Page`
  and `bengal.core.Page` compatibility re-exports are retired, obsolete
  Page-specific fixtures were removed or migrated to SourcePage/page-like
  helpers, and `page_from_source_page()` now returns SourcePage-backed
  `RuntimePage` instances.
- Clean proof worktree `/private/tmp/bengal-page-proof` at `ba37930b3` passed
  focused Page gates, broader Page/source/rendering gates, ruff, ruff format,
  dependency layers, `git diff --check`, and `ty` with the recorded 531
  diagnostic floor. Full-suite runs now pass all Page-relevant coverage; the
  only remaining failures are unrelated directive migration parity tests caused
  by legacy parser state leakage after list directives.

---

## Active Root Plans

| # | Plan | Status | Why It Stays Root |
|---|------|--------|-------------------|
| 1 | `epic-delete-forwarding-wrappers.md` | Active | Shrink compatibility wrappers after Page/Site boundaries are clearer. |
| 2 | `epic-openapi-rest-layout-upgrade.md` | Active | Autodoc/API docs remain a production-readiness gap. |
| 3 | `epic-ux-sharp-edges.md` | Active | Consolidates user-visible CLI, error, directive, and scaffold polish. |
| 4 | `rfc-effect-traced-incremental-builds.md` | Active | Long-term warm-build correctness and template HMR direction. |
| 5 | `rfc-incremental-dependency-indexes.md` | Active / partially implemented | Narrow read-model needed before broader effect-traced rebuild work. |
| 6 | `rfc-snapshot-build-plan-handoff.md` | Active | Free-threaded handoff from mutable build planning to worker execution. |
| 7 | `rfc-template-view-model-contracts.md` | Active | Theme and rendering contract for Chirp UI and future themes. |
| 8 | `rfc-theme-library-assets.md` | Active | Library asset contract for Chirp UI parity in static and dev output. |
| 9 | `rfc-health-diagnostics-audit.md` | Active implementation | Artifact audit and health diagnostics are still being separated. |

This file is the tenth root planning file and owns sequencing.

---

## Current Sequencing

| Priority | Work | Proof Before Close |
|----------|------|--------------------|
| P1 | Re-measure and reduce `ty` floor | Current count is 531 diagnostics; close with a lower recorded count and no new suppressions. |
| P1 | OpenAPI REST autodoc polish | Focused autodoc tests cover Python, CLI, OpenAPI, and layout output. |
| P1 | Snapshot build-plan handoff | Worker paths consume frozen plans/snapshots instead of live mutable objects. |
| P1 | Directive migration parser state leak | Reproduce with `pytest tests/migration/test_directive_edge_cases.py::test_edge_case_parity --randomly-seed=314926607 -n0`; close with list edge cases passing in seed/order-sensitive runs. |
| P2 | Incremental dependency indexes | Warm-build tests prove dependency-to-output invalidation without broad scans. |
| P2 | Effect-traced template HMR | Template edits rebuild only affected pages and record explainable effects. |
| P2 | Template view model contracts | Directives, shortcodes, autodoc, indexes, and themes consume stable data contracts. |
| P2 | Theme library assets | Chirp UI provider assets have static/dev parity and artifact audit coverage. |
| P2 | Health diagnostics audit | Health, artifact audit, and terminal reporting have separated ownership and tests. |
| P3 | Delete forwarding wrappers | Remove compatibility forwarding only after callers and tests prove the narrower API. |
| P3 | UX sharp edges | Use as a holding epic for confirmed user-visible polish, not architecture drift. |

## Saga Queue

These are the next sensible thematic PRs, in order, if a new session asks what
to pick up. A runtime Codex goal should map to a saga-level objective, not a
single commit. Individual commits are tasks inside that goal and should remain
well-scoped.

### Completed Saga: Mutable Page Deletion

**Archived plan:** `complete/epic-immutable-page-pipeline.md`.
**Outcome:** the mutable `Page` compatibility class is deleted from production
architecture. Public `bengal.Page` and `bengal.core.Page` re-exports were
retired after the 2026-05-29 approval, and the discovery adapter now returns
SourcePage-backed `RuntimePage` instances instead of constructing a legacy
mutable `Page`.

**Proof:** direct class/import greps return no hits; focused boundary,
public-export, Page record, core page, content-discovery, autodoc, rendering,
initializer, and frontmatter gates pass; the broader Page/source/rendering gate
passes; ruff, ruff format, dependency layers, `git diff --check`, and ty pass at
the recorded 531 diagnostic floor. Clean full-suite runs at `ba37930b3` now
expose only an unrelated directive migration parser state leak, recorded above
as follow-up and accepted as outside the Page saga closure criteria.

| Priority | Saga | Source Plan | Notes |
|----------|------|-------------|-------|
| 1 | OpenAPI REST polish | `epic-openapi-rest-layout-upgrade.md` | User-facing docs/templates; include visual/output proof and changelog. |
| 2 | Ty floor reduction | Roadmap P1 | No suppressions or public API widening just to satisfy ty. |
| 3 | Snapshot build-plan handoff | `rfc-snapshot-build-plan-handoff.md` | Worker-safe execution now follows naturally after mutable Page deletion. |
| 4 | Directive migration parser state leak | Roadmap P1 / `epic-ux-sharp-edges.md` | Fix the unrelated full-suite parity failure before relying on migration parity as a release gate. |

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
