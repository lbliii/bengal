<!-- markdownlint-disable MD013 MD060 -->

# Bengal Roadmap - Active Plan Set

**Created**: 2026-04-12  
**Updated**: 2026-06-03  
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
  diagnostic floor. Full-suite runs now pass all Page-relevant coverage. The
  unrelated directive migration parity failures (once attributed to "parser
  state leakage after list directives") were **resolved by #298** (correction
  recorded 2026-06-03; not part of the 2026-05-30 machine check) — the root
  cause was an incomplete directive render-cache key, not a parser state leak.

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
| 10 | `epic-performance.md` | Active | Free-threading is the North Star, but published numbers (README `~256/373 pps`) contradict committed baselines (`~18–20 pps`) and there is no benchmark CI gate. Measurement integrity first, then the rendering hot path. |

This file is the eleventh root planning file and owns sequencing.

---

## Current Sequencing

| Priority | Work | Proof Before Close |
|----------|------|--------------------|
| P0 ✅ | Performance measurement integrity (`epic-performance.md` Wave 1) — **DONE 2026-06-02** | Shipped: README `256/373 pps` prose replaced with committed baselines; site-doc tables labeled; `gil_speedup` harness now captures the full phase ledger; phase-accounting audit committed (`phase_attribution.json`); dead import guards repaired + psutil pollution fixed. **Clean attribution (idle machine):** rendering 45%→68%, asset_audit ~11%, free-threading 1.78x→**2.50x**. (Self-correction: an earlier asset_audit "41%/22.7s" figure was load-inflated ~14x — re-measured idle; lesson recorded.) |
| P1 | Performance render hot path + CI gate (`epic-performance.md` Wave 2) | **Rendering is the real lever (~68%).** Diagnosed 2026-06-02: it **plateaus at ~1.7x** — a per-page lock/bandwidth ceiling (FIX C), not the scheduler barrier (one dominant group) or worker count (FT worker-profile tweak investigated + **reverted** as scale-dependent/variance-adding). Shipped: **builds are now byte-reproducible** (fixed non-deterministic related-posts tiebreak, tag ordering, and `hash()`-based tag accent); `asset_audit` exists-memoized (serial; threadpool reverted — bare `ThreadPoolExecutor` banned); **asset_extractor rewritten as a faithful single-pass scanner** (byte-identical, ~4.1x faster extraction, 47-case parity + real-build verified). **Plateau diagnosed 2026-06-02:** cpu/wall=4.29 at 8 workers → cores BUSY, not idle, so it is **NOT lock contention** (FIX C ruled out — not implemented). Parallel burns **2.6x CPU for the same work, per-page** → **free-threading atomic-refcount/coherency overhead** on shared objects. The ~1.7x ceiling is Python 3.14t's coherency tax. Real lever (xl, architectural): minimize cross-thread shared-object access in render (T13/snapshot handoff, immortalize hot shared immutables, cut per-page allocation); next diagnostic is a refcount/coherency profile. **Reframed 2026-06-04 as epic #343** "Render scaling — measure clean, then un-share the world" (sagas #344–#349, superseding the parked #308/#309): a process-isolation ceiling probe (`benchmarks/probe_render_ceiling.py`) already fired a preliminary GO (~2.95x processes vs 1.57x threads → coherency tax, likely fixable); clean-box confirmation + native attribution gated on an idle Linux box (#344, `benchmarks/run_clean_box.sh`). Open: kida `inspect.signature` memoization (external pin); 21-opens/page file-I/O lead; docs/autodoc-archetype profile. |
| P1 | Re-measure and reduce `ty` floor | Current count is 531 diagnostics; close with a lower recorded count and no new suppressions. |
| P1 | OpenAPI REST autodoc polish | Focused autodoc tests cover Python, CLI, OpenAPI, and layout output. |
| P1 | Snapshot build-plan handoff | Worker paths consume frozen plans/snapshots instead of live mutable objects. |
| P1 ✅ | Directive migration parser state leak — **RESOLVED by #298** | Root cause was an incomplete directive render-cache key (lists store items in `.items`, not `.children`), not a parser state leak. `--randomly-seed=314926607` and a seed sweep now pass; regression coverage in `tests/migration/test_directive_cache_key.py`. |
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
the recorded 531 diagnostic floor. The unrelated directive migration parity
failure exposed by clean full-suite runs at `ba37930b3` — accepted at the time
as outside the Page saga closure criteria — was **resolved by #298**.

| Priority | Saga | Source Plan | Notes |
|----------|------|-------------|-------|
| 1 | Performance measurement integrity | `epic-performance.md` Wave 1 | Pull ahead of engineering work: it is docs/harness/tests only (low risk) and gates honest scoring of every other perf task. Fixes the README `~256/373 pps` credibility gap, adds phase capture + a phase-accounting audit, repairs the dead import guards. |
| 2 | OpenAPI REST polish | `epic-openapi-rest-layout-upgrade.md` | User-facing docs/templates; include visual/output proof and changelog. |
| 3 | Ty floor reduction | Roadmap P1 | No suppressions or public API widening just to satisfy ty. |
| 4 | Snapshot build-plan handoff | `rfc-snapshot-build-plan-handoff.md` | Worker-safe execution now follows naturally after mutable Page deletion. Also `epic-performance.md` Wave 4 T13 — the free-threading scaling lever beyond 1.94x. |
| 5 ✅ | Directive migration parser state leak — **DONE (#298)** | Roadmap P1 / `epic-ux-sharp-edges.md` | Migration parity is now order-stable across seeds; the cache-key fix unblocks treating parity as a release gate. |

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
