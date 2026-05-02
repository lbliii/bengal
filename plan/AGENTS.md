# Planning Steward

Planning files turn steward signals, architecture risks, and roadmap intent into
work that can be executed without rediscovering the same context. This steward
protects decision quality and archive hygiene; it does not outrank the package
stewards that own implementation boundaries.

Related architecture docs:

- `../AGENTS.md`
- `README.md`
- `ROADMAP.md`

## Protect

- Clear problem statements, goals, non-goals, and decision records.
- Dependency order across epics, RFCs, stale work, and superseded proposals.
- Explicit ties back to Bengal's north star: pure Python, free-threading,
  measurable performance, and user-visible documentation correctness.
- Steward notes for cross-boundary work, especially public contracts,
  rendering behavior, incremental correctness, and free-threading safety.
- Archive status that stays truthful: drafted, evaluated, stale, superseded,
  or complete.

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
- Hide deferred work in vague "later" language; name the tradeoff or move it
  to a not-now section.

## Own

- Own `plan/README.md` and `plan/ROADMAP.md`.
- Keep RFC, epic, sprint, stale, superseded, evaluated, and complete buckets
  consistent with the actual implementation state.
- Carry steward consultation rollups into follow-up plans or PR descriptions
  when planning work crosses scoped steward areas.
- `rg "^\*\*Status\*\*" plan`
- `rg "bengal/build|dependency_tracker|PageCacheManager|ConfigService" plan`
- Re-read affected scoped `AGENTS.md` files before promoting a plan from draft
  to active work.
