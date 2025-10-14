Title: Bengal Decoupling Roadmap

Status: Draft

Owner: Platform

Last updated: 2025-10-14

Objective

- Reduce cross-layer coupling to improve maintainability, testability, and performance evolution.
- Enable safer parallelism and iterative feature work without regressions.

Why this is a good long-term strategic play

- Stability and velocity: Decoupled modules allow localized changes and faster iteration with fewer integration bugs.
- Testability: Interfaces let us unit test subsystems in isolation, reducing reliance on end-to-end tests.
- Performance: Clear boundaries enable targeted optimizations (e.g., free-threaded Python, parallel pipelines) without touching unrelated code.
- Extensibility: Pluggable contracts (e.g., progress reporting, validation) let us add modes (CI, TUI, server) with minimal code churn.
- Developer experience: Easier to reason about ownership and responsibilities; fewer circular import risks.

Scope and principles

- No behavioral changes in Phase 1; introduce interfaces and adapters side-by-side, migrate call sites, then remove old paths.
- Preserve existing logs/UX; route messages through injectable reporters.
- Avoid global state mutations across phases; prefer context objects.

Decoupling Targets and Actions

1) Core ↔ Rendering and Orchestration

- Issue: `bengal/core/site.py` imports rendering and orchestration internals.
- Action:
  - Extract link/path resolution helpers used by `Site` into `bengal/utils/link_resolution.py` (thin wrapper shared by rendering).
  - Remove direct imports of `TemplateEngine`/orchestrators from core; have CLI/server own build orchestration.
- Value: Prevents circular dependencies and keeps domain model pure.

2) Orchestration ↔ Presentation (CLI/prints)

- Issue: `BuildOrchestrator` initializes CLI output and streaming orchestrator uses `print`.
- Action:
  - Define `ProgressReporter` protocol in `bengal/utils/progress.py` with methods: add_phase, start_phase, update_phase, complete_phase, log.
  - Provide implementations: `CLIRichReporter`, `QuietReporter`, `NoopReporter`.
  - Inject reporter into orchestrators; remove direct `print` and CLI wiring.
- Value: Unified output pathways, easier to test and reuse in server/CI.

3) Server ↔ Site internals

- Issue: `bengal/server/build_handler.py` mutates `Site` fields directly to clear ephemeral state.
- Action:
  - Add `Site.reset_ephemeral_state()` encapsulating the current logic.
  - Replace server code to call the method.
- Value: Encapsulation prevents drift; one source of truth for rebuild hygiene.

4) Globals/Singletons (CLI output, directive cache, API doc enhancer)

- Issue: Hidden global state complicates tests and parallelism.
- Action:
  - Keep factory accessors but allow override via optional parameters/context.
  - Accept instances via constructors for pipelines/renderers; fall back to global if not provided.
- Value: Better test isolation; deterministic behavior under concurrency.

5) Rendering state and page selection

- Issue: `BuildOrchestrator` temporarily reassigns `site.pages` when rendering a subset.
- Action:
  - Introduce `BuildContext(site, pages_to_build, tracker, profile, reporter)` passed through to renderers.
  - Avoid mutating `site.pages` during render; render functions take explicit page lists.
- Value: Reduces side effects; safer incremental and parallel builds.

6) CLI ↔ Rendering validation

- Issue: CLI imports concrete `TemplateEngine`/`TemplateValidator` directly.
- Action:
  - Add `TemplateValidationService` interface in `bengal/services/validation.py` with `validate(site) -> ValidationResult`.
  - CLI depends on the interface; default implementation wraps current validator.
- Value: Clean separation for headless/CI usage; simplifies future engine swaps.

Phased Plan

- Phase 1 (1–2 days):
  - Add `ProgressReporter` interface and Noop/CLI impls; adapt Streaming/Render/Build orchestrators to use it.
  - Add `Site.reset_ephemeral_state()` and switch server to call it.
  - Extract link resolution helpers; update `Site` to use them.

- Phase 2 (2–3 days):
  - Introduce `BuildContext` and thread through rendering; remove `site.pages` swapping.
  - Make caches/enhancers injectable with sane defaults; update pipelines to accept optional instances.

- Phase 3 (2 days):
  - Add `TemplateValidationService` interface; refactor CLI to depend on it.
  - Remove deprecated direct imports and dead code paths.

Risks and mitigations

- Risk: Interface drift causes subtle logging/UX regressions.
  - Mitigation: Keep CLI reporter as default; integration tests compare summaries.
- Risk: Hidden dependencies surface during refactor.
  - Mitigation: Incremental PRs; strong typing for new interfaces; unit tests for adapters.

Success metrics

- Reduced cross-imports between `core`, `orchestration`, `rendering`, and `server` (grep-based checklists).
- No mutation of `site.pages` during render in code search.
- New unit tests cover reporters, reset, and validation service.
- CI: stable test runtime; simpler mocks in tests touching orchestrators.

Immediate quick wins (proposed PR order)

1. Add `Site.reset_ephemeral_state()` and adopt in server.
2. Introduce `ProgressReporter` and remove prints from streaming orchestrator.
3. Extract link resolution helper to utils and decouple core from template engine.

Ownership and review

- Core boundaries: Core/Platform.
- Orchestrators/reporters: Build & DevEx.
- Validation service: Rendering.
