Build Pipeline Soundness – Implementation Plan

Goals
- Ensure post-processing error reporting never crashes and routes via reporter/quiet-aware CLI output.
- Respect quiet mode in memory-optimized streaming orchestrator; avoid direct prints unless explicitly allowed.
- (Optional) Improve incremental time-saved estimation using post-render metrics.
- Strengthen unit tests around reporter output and quiet behavior.
- Update docs and changelog to reflect behavior and guarantees.

Non-Goals
- No public API changes to CLI flags or major orchestration contracts.

Proposed Changes
1) PostprocessOrchestrator error reporting
   - Problem: Parallel error reporting references an out-of-scope variable, risking runtime errors when no progress manager is used.
   - Action:
     - Thread `build_context` (or a `reporter`) into `_run_parallel`/`_run_sequential` helpers.
     - Use `reporter.log()` when available; otherwise route through existing CLI output helper; avoid bare `print` in quiet contexts.
     - Never reference variables not in scope.

2) StreamingRenderOrchestrator quiet mode compliance
   - Problem: Informational messages are printed directly even when `quiet=True` and no reporter is present.
   - Action:
     - If `quiet` is True and no `reporter`, suppress output entirely.
     - If `reporter` exists, route messages to `reporter.log()` regardless of quiet.
     - Prefer CLI output abstraction when appropriate for consistency.

3) Incremental time-saved estimate (optional)
   - Problem: Early estimate defaults to a constant if `rendering_time_ms` not yet set.
   - Action:
     - After rendering completes, recompute a more accurate `time_saved_ms` using measured stats when incremental mode is on.

Testing Plan
- Postprocess reporter path:
  - Extend `tests/unit/orchestration/test_postprocess_reporter.py` to simulate task errors (e.g., raise in a task) and assert messages are logged via reporter without crashing.
- Streaming quiet behavior:
  - New test to invoke `StreamingRenderOrchestrator.process(quiet=True, reporter=None)` and assert no stdout (capture with `capsys`).
- Rendering pipeline reporter output:
  - Keep existing assertions verifying that writes route to reporter; adjust only if necessary.
- Integration sanity:
  - Run a minimal example site build in quiet and non-quiet modes to confirm no stray prints and that progress/reporting still appears when enabled.

Implementation Steps (atomic commits)
1) core(orchestration): fix PostprocessOrchestrator error reporting; route via reporter/CLI; remove out-of-scope reference
2) core(orchestration): respect quiet in StreamingRenderOrchestrator; suppress prints; use reporter when present
3) tests: add/extend unit tests for postprocess error path and streaming quiet mode
4) core(orchestration): refine time-saved estimation post-render (incremental only)
5) docs: update ARCHITECTURE.md and CHANGELOG with behavior clarifications

Risk & Mitigation
- Risk: Changing logging pathways may alter console output formatting.
  - Mitigation: Guard with reporter presence and quiet flag; keep existing CLI output code paths.
- Risk: Threading build context deeper could introduce circular imports.
  - Mitigation: Pass primitives (reporter) rather than importing build context types where not needed.

Acceptance Criteria
- No NameError or crash when postprocess tasks fail without a progress manager.
- No stdout from streaming orchestrator when `quiet=True` and no reporter.
- Unit tests pass and validate reporter routing.
- Example build runs cleanly with expected output modes.

Timeline (estimate)
- Postprocess fix: 1 hour
- Streaming quiet compliance: 45 minutes
- Tests: 1.5 hours
- Docs/Changelog: 30 minutes

Rollback Strategy
- Changes are isolated to orchestrators and tests; revert individual commits if regressions occur.
