# Cache Steward

Cache code protects rebuild correctness and repeatability. A cache hit is a
claim that the rendered output is still trustworthy.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/cache.md`
- `../../plan/rfc-output-cache-architecture.md`

## Point Of View

Cache code represents the durable memory of prior builds. It should be boring,
atomic, deterministic, and honest about whether a hit can be trusted.

## Protect

- Stable cache keys and schema compatibility.
- Atomic persistence and crash safety.
- Explicit migration paths for old cache shapes.
- Deterministic serialization for free-threaded builds.
- Distinct behavior for misses, stale entries, corruption, and migration.

## Contract Checklist

- Cache tests under `tests/unit/cache/` plus warm-build and incremental
  integration tests.
- Provenance/build-cache docs and migration notes when schemas or keys change.
- Performance notes when cache behavior changes rebuild speed or storage.
- Changelog for user-visible cache behavior, invalidation, or diagnostics.
- Atomic write proof for every persisted file path.

## Advocate

- Conservative misses when cache shape, provenance, or dependencies are
  uncertain.
- Schema/version tests before persistence formats change.
- Clear corruption, migration, and fallback diagnostics instead of treating all
  cache failures alike.

## Serve Peers

- Give incremental rebuilds trustworthy keys, snapshots, and migration behavior.
- Give build phases atomic persistence helpers and predictable failure modes.
- Give tests fixtures that distinguish cache miss, stale cache, corrupt cache,
  and schema migration behavior.

## Do Not

- Write cache files directly with `Path.write_text()` or `open()`.
- Treat cache misses and corrupt cache files the same.
- Store mutable live domain objects when snapshots or records should be used.
- Add compression or persistence behavior without tests for fallback paths.

## Own

- `site/content/docs/reference/architecture/core/cache.md`
- Cache migration and performance notes
- Tests: `tests/unit/cache/`, warm-build cache integrations
- Checks: `uv run pytest tests/unit/cache tests/unit/discovery -q`
- Checks: `uv run pytest tests/integration/test_phase2b_cache_integration.py -q`
- Checks: `uv run ruff check bengal/cache tests/unit/cache`
