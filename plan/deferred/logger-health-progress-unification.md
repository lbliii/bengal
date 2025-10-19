# Logger, Health Check, and Progress Reporting Unification Plan

> **Status: DEFERRED** (October 19, 2025)
>
> This plan was never implemented. While it was placed in `plan/completed/`, an audit revealed:
> - 25 files still contain raw `print()` statements in production code
> - No integration between logger, health checks, and progress systems
> - Foundation (~60%) exists but comprehensive cleanup was not done
>
> **Recommendation:** Deprioritize this comprehensive refactoring. Current `print()` statements provide good UX and work well. If revisited, focus only on:
> 1. Health check integration (for testability)
> 2. Critical error path logging (for better log capture)
> 3. Add linter rule to prevent NEW prints (grandfather existing ones)
>
> Skip the comprehensive cleanup unless there's a specific user-facing bug or feature need. The dev server's pretty colored output is intentional UX and should not be sacrificed for architectural purity.

## Goals
- Establish a single, configurable logging facade for all human and machine-readable output.
- Integrate health checks with structured logging and remove ad-hoc prints.
- Harmonize live progress reporting with logging (no duplicate/noisy output; great TTY UX; CI-friendly fallback).

## Non-goals
- Change user-facing theme templates or site content semantics.
- Replace the existing health validators or their core logic.

## Current State (as of this plan)
- Logging: `bengal.utils.logger` provides `BengalLogger` with phases, JSON file output, Rich console formatting, memory/timing summaries; scattered `print(...)` remain in modules like `orchestration/*`, `server/*`, `rendering/pipeline.py`, `config/loader.py`.
- Health: `bengal.health.HealthCheck` orchestrates validators; prints in verbose paths and in `run_and_print()`.
- Progress: `bengal.utils.live_progress.LiveProgressManager` for TTY live output; `bengal.utils.progress.ProgressReporter` protocol and `LiveProgressReporterAdapter` currently `print()`s in `log()` fallback.
- Server: `bengal.server.request_logger.RequestLogger` uses `BengalLogger` for structured events but still `print()`s the pretty line.

## Principles
- Single source of truth for events: always emit via `BengalLogger`; presentation (live progress, pretty request lines) should be opt-in shells around the same events.
- Zero raw prints in production modules; tests may use prints for fixtures/debug.
- TTY-friendly by default, CI-friendly automatically (detect and degrade gracefully).

## Deliverables
1) No raw prints in production code paths (exceptions: guarded fallbacks inside logger itself).
2) HealthCheck emits structured events for validator lifecycle; `run_and_print()` uses logger for presentation.
3) Live progress and logger do not compete: when live progress is active, console logging is quieted; file/JSON logging remains.
4) CLI/server flags to control verbosity, JSON/file logging, and live progress.

## Phases and Tasks

### Phase 1 — Logging Consolidation (foundation)
- Add a narrow allowlist-based check to prevent `print(` in non-test Python modules (pre-commit or CI linter rule). Scope exceptions to `bengal/utils/logger.py` fallback and `tests/**`.
- Replace raw prints with logger in:
  - `bengal/orchestration/{asset,postprocess,streaming}.py`
  - `bengal/rendering/pipeline.py`
  - `bengal/server/{build_handler.py,request_handler.py}` (retain pretty line via controlled channel)
  - `bengal/config/loader.py`
  - `bengal/utils/live_progress.py` fallback and `bengal/utils/progress.py` adapter
- Provide `get_logger(__name__)` in each touched module and pick appropriate level and context.
- Add `--log-file` and `--json-logs` wiring if not already; ensure `configure_logging()` truncates file once per run and is initialized early in CLI entrypoints.

Acceptance: `rg "^\\s*print\("` returns zero matches in `bengal/**` excluding `tests/**` and sanctioned fallbacks.

### Phase 2 — HealthCheck ↔ Logger Integration
- In `HealthCheck.run()`:
  - Emit `logger.info("validator_start", validator=..., description=...)` before execute.
  - On success, emit `logger.info("validator_complete", validator=..., duration_ms=..., problems=..., warnings=...)`.
  - On exception, emit `logger.error("validator_error", validator=..., error=str(e))` and continue.
- In `run_and_print()`, replace direct `print(...)` with `logger.info("health_report", ...)`; pretty console rendering is handled by logger.
- Ensure `HealthReport.format_console()` can be printed by the CLI command using Rich when desired, but default path still goes through the logger so file logs are complete.

Acceptance: Running health in verbose mode yields structured events in the log file and concise, deduplicated console output.

### Phase 3 — Progress Harmonization
- Introduce a small orchestration utility:
  - On entering live progress context: `set_console_quiet(True)`; on exit: restore to `False`.
  - Live progress still updates TTY; logger continues file/JSON logging silently.
- Update `LiveProgressReporterAdapter.log()` to route to `get_logger("progress").info(...)` instead of `print()`.
- Encourage use of `logger.phase("rendering", ...)` inside orchestrators; on phase start/complete, also update `LiveProgressManager` via adapter. Align phase ids/names between logger and live progress for consistent summaries.

Acceptance: During builds, users see compact live progress with no duplicate lines; logs capture full structured events and phase timings.

### Phase 4 — CLI/Server UX
- CLI flags (validate and document): `--verbose`, `--quiet`, `--log-file`, `--json-logs`, `--no-live-progress`, `--profile {writer,theme-dev,dev}`.
- Dev server: replace pretty request `print()` with a call that goes through logger when console is not quiet; keep the single-line pretty output but guard it behind TTY detection and verbosity.
- Ensure non-TTY (CI) disables live progress and uses concise line logs only.

Acceptance: Flags produce expected combinations; e2e tests verify CI behavior (no ANSI live UI) and TTY behavior.

### Phase 5 — Tests and Guardrails
- Unit tests:
  - Logger: levels, phase context, quiet mode, JSON event shape.
  - HealthCheck: emits start/complete/error events; `run_and_print()` does not raw print.
  - Progress: adapter routes to logger; quieting behavior toggles console correctly.
  - RequestLogger: no double logging; pretty output suppressed in CI.
- Add a CI check that fails on new raw prints in `bengal/**` (excluding sanctioned files/tests).

## Migration Strategy
- Mechanical replacement of `print(...)` in targeted modules with `logger.info/warning/error` and minimal context; avoid behavioral changes where possible.
- For modules that intentionally produce pretty human output, wrap via logger formatting helpers and/or only render when TTY + appropriate verbosity.

## Risks and Mitigations
- Risk: Over-quiet console during failures. Mitigation: Always allow WARNING+ to bypass quiet console in `BengalLogger` (already supported).
- Risk: Duplicated output (live + logger). Mitigation: enforce `set_console_quiet(True)` while live progress is active.
- Risk: Performance overhead with Rich/JSON. Mitigation: keep Rich formatting on console only; file writes are buffered; avoid deep context dicts in hot loops.

## Done Criteria
- No raw prints in production; consolidated logger usage; health checks and progress integrated; flags documented; tests passing; developer ergonomics improved with phase summaries and clean CI logs.
