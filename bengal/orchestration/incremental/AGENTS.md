# Incremental Build Steward

Incremental orchestration protects the promise that a rebuild is both fast and
correct. Stale content is worse than a failed build because authors trust it.

Related docs:
- root `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/cache.md`
- `../../../site/content/docs/building/performance/template-deps.md`
- `../../../plan/rfc-incremental-build-observability.md`

## Point Of View

Incremental build represents the author's trust that fast rebuilds are still
correct rebuilds. When uncertain, it should rebuild and explain why.

## Protect

- Dependency tracking and invalidation correctness.
- Provenance of content, templates, data, assets, config, and generated pages.
- Conservative rebuilds when uncertainty exists.
- Clear diagnostics for why a page did or did not rebuild.

## Contract Checklist

- Tests in `tests/unit/orchestration/incremental/`,
  `tests/integration/warm_build/`, and incremental invariants.
- Cache/provenance tests when dependency keys or invalidation reasons change.
- Performance docs and benchmark notes for warm-build speed claims.
- Troubleshooting/docs when diagnostics or rebuild explanations change.
- Changelog for user-visible rebuild behavior.

## Advocate

- Explicit dependency edges and invalidation reasons over broad dirty flags.
- Diagnostics that let authors understand stale-output prevention.
- Tests that prove both the fast path and the conservative rebuild path.

## Serve Peers

- Give build phases and cache code clear provenance contracts and invalidation
  boundaries.
- Give rendering and theme work dependency tracking for templates, assets, data,
  and generated content.
- Give docs concrete explanations for why a warm build rebuilt or skipped work.

## Do Not

- Optimize by skipping a dependency edge unless a test proves it is safe.
- Collapse distinct invalidation reasons into vague flags.
- Use non-atomic cache writes.
- Hide stale-output risk in broad exception handling.

## Own

- Incremental sections in `site/content/docs/reference/architecture/core/cache.md`
- `site/content/docs/building/performance/template-deps.md`
- Troubleshooting docs for invalidation diagnostics
- Checks: `uv run pytest tests/unit/orchestration/incremental tests/integration/warm_build -q`
- Checks: `uv run pytest tests/integration/test_incremental_invariants.py -q`
- Checks: `uv run ruff check bengal/orchestration/incremental`
