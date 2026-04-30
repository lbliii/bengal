# Incremental Build Steward

Incremental orchestration protects the promise that a rebuild is both fast and
correct. Stale content is worse than a failed build because authors trust it.

Related architecture docs:

- `../../../AGENTS.md`
- `../../../site/content/docs/reference/architecture/core/cache.md`

## Protect

- Dependency tracking and invalidation correctness.
- Provenance of content, templates, data, assets, and config.
- Conservative rebuilds when uncertainty exists.
- Clear diagnostics for why a page did or did not rebuild.

## Do Not

- Optimize by skipping a dependency edge unless a test proves it is safe.
- Collapse distinct invalidation reasons into vague flags.
- Use non-atomic cache writes.
- Hide stale-output risk in broad exception handling.

## Documentation Ownership

- Own incremental sections in `site/content/docs/reference/architecture/core/cache.md`.
- Keep `site/content/docs/building/performance/template-deps.md` accurate for dependency behavior.
- Update troubleshooting docs when invalidation diagnostics change.

## Local Checks

- `uv run pytest tests/unit/orchestration/incremental tests/integration/warm_build -q`
- `uv run pytest tests/integration/test_incremental_invariants.py -q`
- `uv run ruff check bengal/orchestration/incremental`
