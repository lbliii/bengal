# Cache Steward

Cache code protects rebuild correctness and repeatability. A cache hit is a
claim that the rendered output is still trustworthy.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/cache.md`

## Point Of View

Cache code represents the durable memory of prior builds. It should be boring,
atomic, deterministic, and honest about whether a hit can be trusted.

## Protect

- Stable cache keys and schema compatibility.
- Atomic persistence and crash safety.
- Explicit migration paths for old cache shapes.
- Deterministic serialization for free-threaded builds.

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

- Own `site/content/docs/reference/architecture/core/cache.md`.
- Keep performance docs accurate when cache behavior changes rebuild speed or storage.
- Update migration notes when cache schema compatibility changes.
- `uv run pytest tests/unit/cache tests/unit/discovery -q`
- `uv run pytest tests/integration/test_phase2b_cache_integration.py -q`
- `uv run ruff check bengal/cache tests/unit/cache`
