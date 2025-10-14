# Feature Solidification Plan for Bengal SSG v1.0

## Goals
- Achieve 90%+ test coverage on critical paths (core, orchestration, rendering, health) to ensure stability.
- Complete decoupling initiatives (e.g., full adoption of BuildContext, ProgressReporter, theme resolution) to eliminate mutations and globals.
- Implement core extensibility features (plugin hooks for build phases, custom extractors for autodoc) to enable user extensions without core changes.
- Optimize for Python 3.14+ (free-threading support, JIT-friendly patterns) and validate scalability to 10K+ pages.
- Solidify CLI, dev server, and analysis tools for production use, including documentation and examples.
- Prepare for v1.0 release: changelog updates, migration guides, and backward compatibility guarantees.

## Non-Goals
- Rewrite existing features (e.g., rendering pipeline or object model)—focus on refinement and integration.
- Support legacy Python (<3.13); deprecate non-essential backward compat (e.g., old parser engines if unmaintained).
- Add new content types or themes; prioritize core solidification over expansions.

## Current State (as of enh/feature-solidificaiton branch)
- **Strengths**: Modular architecture (orchestrators, utilities consolidated); incremental builds (18-50x speedup); autodoc (AST-based, integrated); analysis suite (PageRank, communities); health system (14 validators); performance at 289-515 pps (Python 3.14/3.14t).
- **Gaps**:
  - Testing: 68% overall coverage; CLI/dev server at 0%; health validators 13-98%; integration/e2e partial.
  - Decoupling: Recent wins (BuildContext threading, ProgressReporter adapter) but lingering mutations (e.g., site.pages swaps in some paths); CLI still couples to rendering internals.
  - Extensibility: Plugin hooks planned but unimplemented; autodoc extractors limited (Python/Click partial; OpenAPI pending).
  - Performance/Scalability: Free-threading validated but not default; batch I/O and memory mapping opportunities untapped; 10K-page limit tested but not hardened.
  - UX/Stability: Active plans (e.g., cache invalidation fixes, cascade incremental support) indicate ongoing bugs; git ahead by 12 commits with minor unstaged changes (themes, tests).
  - Docs: ARCHITECTURE.md comprehensive; but user migration guides (e.g., from Sphinx) and CLI refs need expansion.
- Branch: enh/feature-solidificaiton; untracked tests/README.md suggests test doc work in progress.

## Principles
- **Backward Compatibility**: No breaking changes; use deprecation warnings for removals (e.g., raw prints → logger).
- **Test-First**: Every feature/refactor adds/tests; aim for property-based (Hypothesis) where variability high (e.g., caching, parallelism).
- **Performance Parity**: Changes must not regress build speeds (benchmark before/after); leverage Python 3.14 features (structural pattern matching, free-threading).
- **Modularity**: Favor composition (e.g., protocols for hooks) over inheritance; keep phases independent.
- **Developer Ergonomics**: Improve CLI flags/docs; integrate analysis into builds (e.g., optional post-build insights).

## Phases and Tasks

### Phase 1: Testing Solidification (2-3 weeks)
Focus: Close coverage gaps to 90%+ on critical paths; add integration/e2e suites.
- **Tasks**:
  - Unit: Cover CLI (commands, flags, typo detection) and dev server (watching, SSE reload, request handling)—target 80%+.
  - Integration: Test full pipelines (discovery → render → post-process) with varied configs (incremental, parallel, strict); use fixtures from examples/showcase.
  - E2E: Automate builds of showcase + synthetic sites (1K/10K pages); verify outputs (HTML validity, links, search index).
  - Property-Based: Expand Hypothesis for caches (dependency graphs), navigation (hierarchies), and parsers (edge Markdown).
  - Performance: Benchmark free-threading vs. standard; add memory profiling for large sites.
- **Acceptance**: pytest --cov >=90% for bengal/core, /orchestration, /rendering, /health; 100% passing tests; coverage report in CI.

### Phase 2: Decoupling Completion (2 weeks)
Focus: Eliminate remaining mutations/globals; full adoption of recent utils (BuildContext, ThemeResolution, TemplateValidationService).
- **Tasks**:
  - Audit: Scan for site.assets/pages mutations; replace with explicit lists in all orchestrators/post-process.
  - CLI: Route all validation through TemplateValidationService; remove direct renderer coupling.
  - Server: Thread BuildContext into handlers; use ProgressReporter for build-triggered reloads.
  - Cache: Ensure inverted index rebuilds use paths only (no refs); add tests for invalidation edge cases (e.g., cascade changes).
  - Utils: Mandate utilities (file_io, dates, text) in all modules; deprecate duplicates.
- **Acceptance**: No mutations in core objects (static analysis or manual audit); 100% util adoption; passing integration tests for decoupled flows.

### Phase 3: Extensibility Implementation (3 weeks)
Focus: Add plugin hooks and expand autodoc for v1.0 extensibility.
- **Tasks**:
  - Hooks: Define protocol for pre/post-phase events (e.g., @hook('pre_discovery'), @hook('post_render')); integrate into BuildOrchestrator.
  - Autodoc: Implement OpenAPIExtractor (from specs/FastAPI apps); add GraphQL support; config for custom extractors via entry points.
  - Content Types: Registry for custom parsers (e.g., RST via docutils); pluggable via [content_types] in TOML.
  - Themes: Full chain resolution with fallbacks; add theme validation in health checks.
- **Acceptance**: Sample plugin (e.g., custom post-processor) works without core changes; autodoc generates OpenAPI docs from example; e2e test for extensible build.

### Phase 4: Performance and Scalability Hardening (2 weeks)
Focus: Leverage Python 3.14; push beyond 10K pages.
- **Tasks**:
  - Free-Threading: Default to GIL=0 in docs/CLI; vend/test deps (e.g., fallback for incompatible C exts); benchmark 515 pps target.
  - Optimizations: Implement batch I/O (concurrent reads in discovery); memory-mapped for large MD (>100KB); JIT patterns (avoid deep recursion).
  - Scalability: Stress test 20K pages (synthetic data); tune parallelism thresholds; add cache compression for large inverted indexes.
  - Analysis Integration: Optional --analyze flag in build (runs PageRank/communities post-build; outputs JSON/insights).
- **Acceptance**: 515 pps on 3.14t; <2s incremental at 10K pages; no regressions in benchmarks; analysis flag generates actionable report (e.g., orphans, suggestions).

### Phase 5: UX, Docs, and Release Prep (1-2 weeks)
Focus: Polish CLI/server; expand docs; cut release.
- **Tasks**:
  - CLI: Add --analyze, --hooks-list; improve help (subcommands, examples); integrate with uv for themes.
  - Server: Add hot-reload for themes/assets; request logging via unified logger.
  - Docs: Update README/QUICKSTART with 3.14t guide; migration from Sphinx/Hugo; full CLI ref in docs.
  - Release: Update CHANGELOG.md with atomic entries; tag v1.0; publish to PyPI; add release notes.
- **Acceptance**: CLI passes e2e (all flags); docs build via autodoc; PyPI upload succeeds; zero critical issues in health checks.

## Migration Strategy
- **Incremental**: Phases build on each other; merge to main after each with benchmarks/tests.
- **Deprecations**: Warn on old patterns (e.g., direct site mutations); provide shims for 6 months.
- **User Impact**: No config changes; new features opt-in (e.g., [plugins] section).

## Risks and Mitigations
- **Risk: Free-Threading Incompat**: Some deps fail—Mitigation: Fallback to standard Python; document workarounds; prioritize pure-Python alts.
- **Risk: Test Overhead**: Coverage push slows CI—Mitigation: Parallel pytest-xdist; focus on critical paths first.
- **Risk: Decoupling Regressions**: Breaks incremental—Mitigation: Full integration tests per phase; rollback if benchmarks regress >5%.
- **Risk: Scope Creep**: Extensibility delays—Mitigation: MVP hooks first (3-5 events); defer advanced (e.g., full plugin marketplace).

## Done Criteria
- 90%+ coverage on core; all phases tested/integrated; benchmarks meet/exceed current (515 pps, 50x incremental).
- No open critical bugs (health checks pass); changelog updated; v1.0 tagged; user guide for new features.
- Branch merged; plan moved to plan/implemented/; post-release perf analysis in plan/analysis/.
