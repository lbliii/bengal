<!-- markdownlint-disable MD013 -->

# Superseded Plan Archive

Updated: 2026-05-28

Superseded bodies were removed after this distillation pass. Their useful
direction has been folded into the active root roadmap.

## Superseded Threads

- Broad Bengal v2 architecture and snapshot-engine sketches are now represented
  by `rfc-snapshot-build-plan-handoff.md`,
  `rfc-effect-traced-incremental-builds.md`, and
  `rfc-incremental-dependency-indexes.md`.
- Build orchestrator phase-group plans are now historical; current build work
  should use `bengal/orchestration/build/` and active roadmap priorities.
- Config v2, cache generation ID, and old ty/orchestration type plans require a
  fresh source audit before any implementation.
- SiteContext protocol work shipped enough to inform current code; future work
  should start from `bengal/core/site/context.py`, not the old RFC.

Do not cite this directory as shipped behavior.
