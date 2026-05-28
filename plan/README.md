<!-- markdownlint-disable MD013 MD060 -->

# Bengal Plan & RFC Index

Updated: 2026-05-28

Root `plan/` is intentionally small. It contains `AGENTS.md`, this index, the
current roadmap, and the ten active plans that still describe work Bengal
intends to do. Everything else belongs in an archive directory and should not
be treated as the agenda.

## Active Root Set

| File | Status | Notes |
|------|--------|-------|
| `ROADMAP.md` | Active | Sequencing and verification snapshot for the current plan set. |
| `epic-immutable-page-pipeline.md` | Active | Mutable `Page` deletion remains pending. |
| `epic-delete-forwarding-wrappers.md` | Active | Keep as follow-on architecture cleanup after Page/Site boundaries shrink. |
| `epic-openapi-rest-layout-upgrade.md` | Active | Autodoc/API docs polish remains a production gap. |
| `epic-ux-sharp-edges.md` | Active | User-visible CLI/error/directive/scaffold polish bucket. |
| `rfc-effect-traced-incremental-builds.md` | Active | Long-term effect graph and template HMR direction. |
| `rfc-health-diagnostics-audit.md` | Active implementation | Health, artifact audit, and reporting separation. |
| `rfc-incremental-dependency-indexes.md` | Active | Narrow dependency-to-output read model for warm-build correctness. |
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

## Current Architecture Snapshot

- Build pipeline: `bengal/orchestration/build/`.
- Incremental state: `bengal/orchestration/incremental/`,
  `bengal/cache/build_cache/`, and `bengal/cache/page_artifact_store.py`.
- Snapshot records: `bengal/snapshots/types.py`.
- Immutable page records: `bengal/core/records.py`.
- There is still no general-purpose `bengal/build/` package for new
  orchestration behavior; use current ownership boundaries from root
  `AGENTS.md`.
