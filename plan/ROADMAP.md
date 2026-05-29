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
- `uv run ty check bengal/` reports 545 diagnostics.
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
  `bengal/content/discovery/page_adapter.py`. Public `bengal.Page` and
  `bengal.core.Page` compatibility re-exports are retired, and the remaining
  `bengal/` + `tests/` direct concrete `Page` import count is 1 import site:
  the adapter.
  `tests/unit/content/test_page_construction_boundary.py` now locks production
  constructor/direct-import isolation to the SourcePage adapter and blocks
  concrete `Page` imports in tests. The SourcePage adapter now returns
  `PageLike` at its type boundary while keeping the remaining mutable
  construction isolated inside the adapter.

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
to pick up. A runtime Codex goal should map to a saga-level objective, not a
single commit. Individual commits are tasks inside that goal and should remain
well-scoped.

### Active Saga: Mutable Page Deletion

**Source plan:** `epic-immutable-page-pipeline.md` Sprint 6.
**Goal:** remove the mutable `Page` compatibility class from Bengal's
production architecture while preserving behavior. The public export retirement
decision was approved on 2026-05-29, so the remaining saga work is adapter and
class deletion rather than public compatibility preservation.

**Epics inside the saga:**

1. **Production boundary closure:** keep production `Page` construction and
   direct imports isolated to `bengal/content/discovery/page_adapter.py`, then
   remove that adapter when downstream consumers no longer need it.
2. **Test fixture migration:** migrate tests that only need page-like fixtures
   to SourcePage/page-record helpers; keep tests that intentionally prove
   retired `Page` compatibility surfaces absent.
3. **Protocol/type convergence:** move concrete `Page` annotations and
   fixtures toward `PageLike` or immutable records without widening public
   protocols just to satisfy `ty`.
4. **Public compatibility decision:** recorded 2026-05-29; public
   `bengal.Page` and `bengal.core.Page` re-exports are retired. Stop and ask
   only before changing plugin-facing behavior or another documented public API.
5. **Class deletion:** delete `class Page` and obsolete mixins only after
   production, protocols, and non-compatibility tests no longer depend on them.
6. **Collateral closure:** keep the roadmap, epic status, changelog, and proof
   commands current after each task slice.

**Completed slices:**

- `ee3427abd docs: codify saga planning workflow`
- `f50073af1 core: isolate page compatibility boundary`
- `76a8eee30 tests: migrate analysis page fixtures`
- `tests: migrate health and cache page fixtures`
- `tests: migrate orchestration page fixtures`
- `tests: migrate utility and template page fixtures`
- `tests: migrate nav tree page fixtures`
- `tests: migrate discovery and redirect page fixtures`
- `tests: migrate autodoc virtual page fixtures`
- `tests: migrate section page fixtures`
- `tests: migrate core page-like behavior fixtures`
- `tests: migrate page behavior fixtures`
- `tests: migrate page bundle fixtures`
- `content: type source page adapter as page-like`
- `core: retire public page exports`
- `core: remove page virtual constructor`
- `content: move i18n discovery state into source records`

**Proof before saga close:** `rg '^class Page\\b' bengal/core/page` returns no
hits; `rg 'from bengal\\.core\\.page import Page\\b' bengal` returns no hits;
public compatibility decision is recorded; boundary tests are either removed as
obsolete or rewritten for the new invariant; focused page/source tests and the
appropriate broader suite pass; `uv run ty check bengal/` does not regress the
recorded floor.

| Priority | Saga | Source Plan | Notes |
|----------|------|-------------|-------|
| 1 | Mutable Page deletion | `epic-immutable-page-pipeline.md` Sprint 6 | Active. Continue with scoped task commits under the saga goal above. |
| 2 | Health/audit ownership closure | `rfc-health-diagnostics-audit.md` | `bengal audit` exists; remaining work is separation and duplicate-report control. |
| 3 | OpenAPI REST polish | `epic-openapi-rest-layout-upgrade.md` | User-facing docs/templates; include visual/output proof and changelog. |
| 4 | Ty floor reduction | Roadmap P1 | No suppressions or public API widening just to satisfy ty. |

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
