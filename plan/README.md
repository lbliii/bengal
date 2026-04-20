# Bengal Plan & RFC Index

Quick reference for RFC status. Run `rg "^\*\*Status\*\*" plan/rfc-*.md` to refresh.

## Status Legend

| Status | Meaning |
|--------|---------|
| Implemented | Done |
| Partially Implemented | In progress; some parts done |
| Draft | Not started |
| Evaluated | Reviewed; may need path/context updates |
| Stale | References outdated architecture; re-verify before use |
| Superseded | Replaced by another RFC |

## Key RFCs (Architecture & Scaling)

| RFC | Status | Notes |
|-----|--------|------|
| rfc-pipeline-input-output-contracts | Partially Implemented | BuildInput, Discovery phase, reload hint done |
| rfc-incremental-build-contracts | Evaluated | Paths updated; dependency_tracker removed |
| rfc-incremental-build-dependency-gaps | Stale | References non-existent bengal/build/tracking/ |
| rfc-build-system-package | Draft | bengal/build/ never created; uses orchestration/build/ |
| rfc-bengal-v2-architecture | Draft | Large; protocol-first, composition |
| rfc-remaining-coupling-fixes | Draft | Depends on module-coupling-reduction (unverified) |

## Implemented

- rfc-contextvar-config-implementation
- rfc-contextvar-downstream-patterns
- rfc-build-performance-optimizations
- rfc-ty-type-checker-adoption
- rfc-error-handling-consolidation

## Deleted (superseded or redundant)

- rfc-patitas-extraction — superseded by rfc-patitas-external-migration
- plan-section-protocol-migration — superseded by rfc-bengal-snapshot-engine
- rfc-aggressive-cleanup — duplicate; kept evaluated/rfc-aggressive-cleanup.md

## Archive Structure

- `plan/complete/` — RFCs/epics whose work has shipped.
- `plan/evaluated/` — Reviewed and validated; kept as historical analysis.
- `plan/drafted/` — Early-stage drafts not yet promoted.
- `plan/stale/` — References outdated architecture; re-verify before use.
- `plan/superseded/` — Replaced by another RFC.

Archived 2026-04-20 (epic-agent-dx-polish S5):

- `plan/evaluated/rfc-contextvar-config-analysis.md` — benchmark validated; implementation in `plan/complete/rfc-contextvar-config-implementation.md`.
- `plan/evaluated/rfc-free-threading-hardening.md` — evaluation complete; fixes landed via `foundation-leaf-hygiene.md` Sprint 4.
- `plan/complete/rfc-kida-reserved-keyword-subscript.md` — closed as documentation; no code change shipped.
- `plan/complete/sprint-0-ty-triage.md` — triage feeds `plan/complete/epic-ty-diagnostic-reduction.md`.

## Current Architecture (2026-02-14)

- **Build pipeline**: `bengal/orchestration/build/` (BuildOrchestrator, phases, coordinator)
- **Incremental**: `bengal/orchestration/incremental/` (EffectBasedDetector, CacheManager)
- **Cache**: `bengal/cache/build_cache/` (file_tracking, core)
- **No** `bengal/build/` package
