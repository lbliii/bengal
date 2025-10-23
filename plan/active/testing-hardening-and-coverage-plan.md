### Title
Testing Hardening and Coverage Improvements (Validators, CLI, Rendering)

### Owners
- Dev Lead: TBD
- Reviewers: Core/Rendering/CLI module owners

### Goals (What we want)
- Increase reliability of health validators, CLI, and rendering error paths with stable, documented seams that are easy to test.
- Reduce brittleness in tests caused by environment/version drift (e.g., Jinja2 exception signatures).
- Establish a small, intentional public surface for programmatic CLI usage and for validator dependencies.

### Non-Goals (What we won’t do)
- No broad refactors of orchestration/build pipeline.
- No new end-user features; all changes are developer-experience, testability, and quality.

### Scope
- Health validators: Navigation, Taxonomy, Connectivity
- CLI commands: assets, theme, graph (pagerank/communities/suggest), site/project
- Rendering error diagnostics: error classification, suggestion helpers
- Config loader: consistent, assertable error messaging

### Deliverables
- Public, documented seams:
  - Connectivity: `KnowledgeGraphProvider` (DI) or equivalent injection mechanism
  - Section access: `get_section_pages(section)` helper used by all validators
  - CLI: stable `*_command` exports and `__all__` entries in CLI modules
- `bengal.testing` module with focused helpers for tests (optional but recommended)
- Docs: `TESTING_STRATEGY.md` updates with mocking/import guidance and supported APIs
- CI: Pin Jinja2 (and any other version-sensitive deps) for predictable signatures

### High-Level Approach
1) Introduce minimal DI and accessors to make validators test-friendly without module-patching internals.
2) Normalize CLI exports for programmatic invocation.
3) Make rendering classification tolerant; provide test helper for Jinja2 exceptions.
4) Document and enforce a stable mocking/patching pattern in tests; remove brittle assumptions.
5) Land as small PRs with passing CI at each step.

### Implementation Steps (Phased PRs)

PR 1: CLI and Docs (low risk)
- Export compatibility aliases in CLI modules and add them to `__all__`:
  - `assets.assets_command`, `theme.theme_list`, `graph.pagerank.pagerank_command`, `graph.communities.communities_command`, `graph.suggest.suggest_command`
- Update `TESTING_STRATEGY.md` with programmatic CLI patterns and imports.
- Acceptance: Programmatic CLI tests pass; no behavior changes.

PR 2: Validators Accessors + DI (medium risk)
- Add `bengal.health.utils` (or similar) with `get_section_pages(section) -> list[Page]`.
- Replace all direct `section.pages`/`children` reads in Navigation/Taxonomy with accessor.
- Connectivity:
  - Add `KnowledgeGraphProvider` protocol/class with `create(site) -> KnowledgeGraphLike`.
  - `ConnectivityValidator` accepts provider in constructor (defaults to real import) and uses it.
- Acceptance: Validator unit tests pass with mocks; no regressions in integration tests.

PR 3: Rendering Error Helpers + Version Pins (low risk)
- Add `bengal.testing.rendering.make_assertion_error(msg, lineno=1)` helper for tests.
- Ensure `_classify_error` handles unknown-filter patterns and missing attributes.
- Pin Jinja2 in CI; document the required constructor signature in `TESTING_STRATEGY.md`.
- Acceptance: Rendering edge-case unit tests pass under pinned versions.

PR 4: Config Loader Messaging (low risk)
- Ensure parse errors include the term "config" in the raised message (already partly implemented).
- Acceptance: Integration test asserting config parse messaging passes.

### API Changes (internal/public)
- New (internal-public) helper: `get_section_pages(section)`
- New DI seam: `KnowledgeGraphProvider` injectable into `ConnectivityValidator`
- Exported CLI aliases: `*_command` names are part of programmatic API
- Optional: `bengal.testing` package (explicitly marked for test/dev usage)

### Risks & Mitigations
- Risk: DI and accessors leak test concerns into runtime
  - Mitigation: Keep DI minimal and generally useful (not test-only); document as supported extension points.
- Risk: CLI alias exports change discoverability
  - Mitigation: Backwards-compatible; documented; covered by tests.
- Risk: Jinja2 pin diverges from some environments
  - Mitigation: Only pin in CI; classifier remains tolerant; tests rely on helper.

### Testing Plan
- Unit:
  - Validators: positive/negative cases for breadcrumbs, archive pages, orphans/hubs; dict/object metrics.
  - CLI: Click runner smoke tests via exported aliases.
  - Rendering: extraction/classification/suggestion with constructed exceptions via helper.
- Integration:
  - Config parse error path asserts on message containing "config".
  - Basic build smoke to ensure validators don’t regress runtime.

### Rollout & Migration
- Land PRs sequentially with CI green; publish changelog notes for test/public API exports.
- Coordinate with contributors who authored new tests; adjust any remaining brittle expectations.

### Acceptance Criteria (must have)
- All unit and integration tests pass under pinned CI environment.
- Validators use accessors/DI; no direct reliance on mock-internal shapes.
- CLI programmatic imports stable and documented.
- Rendering error tests no longer depend on version-specific constructor quirks.

### Follow-ups (nice to have)
- Add simple type Protocols for `KnowledgeGraphLike` used by the validator.
- Expand `bengal.testing` with factories for common content structures.

### Timeline
- PR 1: 0.5 day
- PR 2: 1.5–2 days
- PR 3: 0.5 day
- PR 4: 0.25 day

Total: ~3 days including reviews.
