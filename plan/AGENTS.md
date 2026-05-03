# Planning Steward

Planning files turn steward signals, architecture risks, and roadmap intent into
work that can be executed without rediscovering the same context. This steward
protects decision quality and archive hygiene; it does not outrank the package
stewards that own implementation boundaries.

Related docs:
- root `../AGENTS.md`
- `README.md`
- `ROADMAP.md`
- `maturity-assessment.md`

## Point Of View

Planning represents the future work queue and decision memory. It should keep
tradeoffs, dependencies, and stale assumptions visible before code changes
start.

## Protect

- Clear problem statements, goals, non-goals, and decision records.
- Dependency order across epics, RFCs, stale work, and superseded proposals.
- Explicit ties back to Bengal's north star: pure Python, free-threading,
  measurable performance, and user-visible documentation correctness.
- Steward notes for cross-boundary work, especially public contracts,
  rendering behavior, incremental correctness, and free-threading safety.
- Archive status that stays truthful: drafted, evaluated, stale, superseded, or
  complete.

## Contract Checklist

- `plan/README.md`, `plan/ROADMAP.md`, and active RFC/epic status lines.
- Code steward agreement before promoting implementation plans.
- Docs/tests/examples/changelog collateral listed in acceptance criteria.
- Verification notes for stale package names, deleted modules, and changed
  architecture boundaries.
- Not-now sections for tempting adjacent work.

## Advocate

- Plans that reduce stale-output risk, public contract risk, and free-threading
  risk before isolated polish.
- Smaller executable slices when an RFC tries to solve too many concerns.
- Explicit not-now calls when the tradeoff is real but the timing is wrong.

## Serve Peers

- Give package stewards dependency maps, sequencing notes, and known risks
  before implementation starts.
- Feed docs and theme stewards the user-facing story for shipped architecture
  work.
- Surface upstream blockers instead of turning them into vague roadmap items.

## Do Not

- Treat a plan as authoritative when the nearest code steward disagrees.
- Promote speculative config, new dependencies, or public API changes without
  routing through the root escape hatches.
- Let stale architecture names survive in active plans without a verification
  note.
- Hide deferred work in vague "later" language; name the tradeoff or move it to
  a not-now section.

## Own

- `plan/README.md` and `plan/ROADMAP.md`
- RFC, epic, sprint, stale, superseded, evaluated, and complete bucket hygiene
- Steward consultation rollups for planning work
- Checks: `rg "^\\*\\*Status\\*\\*" plan`
- Checks: `rg "bengal/build|dependency_tracker|PageCacheManager|ConfigService" plan`
- Re-read affected scoped `AGENTS.md` files before promoting a plan from draft
  to active work.
