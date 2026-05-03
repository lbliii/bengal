# Development Server Steward

The server owns local author feedback: watching files, rebuilding safely,
serving stable output, and reloading browsers without making production build
semantics fuzzy.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/tooling/server.md`
- `../../docs/live-reload-pipeline-review.md`
- `../../plan/reload-tier-architecture.md`

## Point Of View

The dev server represents the editing loop. It should be fast and calm while
never serving half-written output or hiding rebuild failures.

## Protect

- Watcher scope, debounce behavior, rebuild trigger classification, and CSS hot
  reload semantics.
- Double-buffered output and atomic active-directory swaps.
- SSE reload protocol and browser injection safety.
- Clean lifecycle behavior for Ctrl+C, stale processes, and port fallback.

## Contract Checklist

- Tests under `tests/unit/server/` and warm-build/dev-server integration tests.
- Server architecture docs, live-reload docs, and build performance docs.
- Config/CLI docs for serve flags and watcher settings.
- Incremental/cache collateral when file changes alter rebuild decisions.
- Changelog for user-visible server behavior.

## Advocate

- Rebuild explanations that distinguish content, template, asset, config, and
  theme changes.
- Small reproducible tests for race conditions and lifecycle bugs.
- Fast-path improvements that keep full-build fallback correct.

## Serve Peers

- Give orchestration exact rebuild requests and lifecycle boundaries.
- Give incremental/cache stewards file-change evidence.
- Give CLI/docs stable serve behavior and troubleshooting language.

## Do Not

- Serve directly from a directory while it is being written.
- Add browser-side behavior that requires npm or a JS build step.
- Hide rebuild failures behind reload success.
- Use sleeps as synchronization without a testable reason.

## Own

- `bengal/server/`
- `site/content/docs/reference/architecture/tooling/server.md`
- Live reload and dev-server planning docs
- Tests: `tests/unit/server/`, warm-build integration tests
- Checks: `uv run pytest tests/unit/server tests/integration/warm_build -q`
- Checks: `uv run ruff check bengal/server tests/unit/server`
