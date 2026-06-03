<!-- markdownlint-disable MD013 MD060 -->

# Bengal Plan & RFC Index

Updated: 2026-06-03

Root `plan/` is intentionally small. It contains `AGENTS.md`, this index, the
current roadmap, and the nine active plans that still describe work Bengal
intends to do. Everything else belongs in an archive directory and should not
be treated as the agenda.

For "what should we work on next?", read `ROADMAP.md` first, then the open
**GitHub issues** — active, in-flight work is tracked as issues (each saga maps
to one), while `ROADMAP.md` owns sequencing and the proof gate. Do not rely on
chat memory to know what is in progress. Use the saga workflow in `AGENTS.md`
(branch/worktree hygiene, the clean proof workflow, and the end-of-saga
roadmap-pruning checklist) to turn one active roadmap slice into a thematic PR
with scoped commits, steward consultation, proof commands, and an end-of-saga
plan update. If the user asks to start the saga as a goal, the goal tracks the
active session mission; this index and `ROADMAP.md` remain the durable source of
truth.

## Active Root Set

| File | Status | Notes |
|------|--------|-------|
| `ROADMAP.md` | Active | Sequencing and verification snapshot for the current plan set. |
| `epic-delete-forwarding-wrappers.md` | Active | Keep as follow-on architecture cleanup after Page/Site boundaries shrink. |
| `epic-openapi-rest-layout-upgrade.md` | Active | Autodoc/API docs polish remains a production gap. |
| `epic-performance.md` | Active | Prioritized performance goal/workflow. Measurement integrity first (published numbers contradict committed baselines; no benchmark CI gate), then the free-threading rendering hot path. |
| `epic-ux-sharp-edges.md` | Active | User-visible CLI/error/directive/scaffold polish bucket. |
| `rfc-effect-traced-incremental-builds.md` | Active | Long-term effect graph and template HMR direction. |
| `rfc-health-diagnostics-audit.md` | Active implementation | Health, artifact audit, and reporting separation. |
| `rfc-incremental-dependency-indexes.md` | Active / partially implemented | Dependency-index contracts, provenance persistence, conservative detector consultation, and template/data producer coverage exist; fallback removal still needs proof. |
| `rfc-snapshot-build-plan-handoff.md` | Active | Frozen build-plan handoff for worker-safe execution. |
| `rfc-template-view-model-contracts.md` | Active | Stable rendering contracts for themes and template engines. |
| `rfc-theme-library-assets.md` | Active | Static/dev parity for package-provided theme assets. |

## Status Directories

| Directory | Meaning |
|-----------|---------|
| `complete/` | Work has shipped or the remaining idea is already covered by source/docs/changelog. |
| `evaluated/` | Historical assessment or audit evidence; not current work. |
| `drafted/` | Early drafts not yet promoted to active planning. |
| `stale/` | Potentially useful idea, but paths/status/architecture need re-verification. |
| `superseded/` | Replaced by a newer active plan or implemented architecture. |

## 2026-05-28 Triage Notes

- Root active planning files were reduced to 11: `ROADMAP.md` plus 10 active
  plans/RFCs.
- Finished or effectively shipped RFCs were moved to `complete/`, including CI
  cache inputs/hash, theme ecosystem phase 1, output cache architecture,
  pipeline input/output contracts, dev-server buffer hardening, Agent DX polish,
  template error code/overlay work, and CLI upgrade notifications.
- Broad v2 architecture sketches were moved to `superseded/` because the active
  work now lives in snapshot handoff, effect-traced incremental builds,
  dependency indexes, and wrapper deletion.
- Older product/feature drafts were moved to `stale/` or `evaluated/` until a
  fresh source audit promotes them back.
- Standalone investigations, proof notes, reload/output-collector proposals,
  and ChirpUI prototypes were also moved out of root. Draft prototypes live
  under `drafted/`; historical analysis lives under `evaluated/`; stale
  follow-up plans live under `stale/`.
- Second cleanup pass distilled the completed, stale, superseded, evaluated,
  and drafted archives into directory READMEs. Long historical bodies were
  removed unless they remain durable references. The plan tree now has 21
  markdown files total, plus a few CSS examples under `plan/examples/`.

## 2026-05-29 Triage Notes

- `main` was fast-forwarded to `ab0f22339`, bringing in the SourcePage test
  migration, narrowed performance-evidence enforcement, and notebook H1 title
  preservation.
- Roadmap evidence was refreshed against source: the mutable `Page` class still
  exists, the ty floor is 558 diagnostics, and protocol annotation counts have
  moved since the 2026-05-28 snapshot.
- `rfc-health-diagnostics-audit.md` was updated because `bengal audit` now
  exists as a Milo command with artifact audit primitives and Kida/JSON output.
- `docs/live-reload-pipeline-review.md` was marked as historical where it
  contradicted Bengal's Python 3.14 / PEP 758 exception syntax policy.

## 2026-05-30 Triage Notes

- `epic-immutable-page-pipeline.md` moved to `complete/` after Sprint 6 deleted
  the mutable `Page` compatibility class, retired the public `bengal.Page` and
  `bengal.core.Page` re-exports, and updated Page construction to return
  SourcePage-backed `RuntimePage` instances.
- Full-suite proof for the Page saga ran in a clean worktree at `ba37930b3`.
  Page/source/rendering gates, ruff, dependency checks, and ty passed. The only
  remaining full-suite failures were an unrelated directive migration parity
  state leak reproducible with `--randomly-seed=314926607`, since **resolved by
  #298** (the cause was an incomplete directive render-cache key, not a parser
  state leak; see `changelog.d/directive-cache-key-collision.fixed.md`).

## 2026-06-03 Triage Notes

- Documented the full saga lifecycle in `AGENTS.md`: branch/dirty-worktree
  hygiene, the clean proof workflow (widening gate rings + failure
  classification), and the end-of-saga roadmap-pruning checklist.
- Applied the pruning checklist: the "directive migration parser state leak"
  P1/saga rows in `ROADMAP.md` were marked resolved by #298 (it was a
  render-cache-key bug, not a parser state leak), and the stale "open blocker"
  prose in this index and the roadmap was corrected.

## Current Architecture Snapshot

- Build pipeline: `bengal/orchestration/build/`.
- Build contracts and provenance helpers: `bengal/build/contracts/` and
  `bengal/build/provenance/`.
- Incremental state: `bengal/orchestration/incremental/`,
  `bengal/cache/build_cache/`, and `bengal/cache/page_artifact_store.py`.
- Snapshot records: `bengal/snapshots/types.py`.
- Immutable page records: `bengal/core/records.py`.
- New orchestration behavior still belongs in `bengal/orchestration/` unless a
  current active plan and steward review say otherwise.
