# Cache Steward

Cache code protects rebuild correctness and repeatability. A cache hit is a
claim that the rendered output is still trustworthy.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/cache.md`

## Protect

- Stable cache keys and schema compatibility.
- Atomic persistence and crash safety.
- Explicit migration paths for old cache shapes.
- Deterministic serialization for free-threaded builds.

## Do Not

- Write cache files directly with `Path.write_text()` or `open()`.
- Treat cache misses and corrupt cache files the same.
- Store mutable live domain objects when snapshots or records should be used.
- Add compression or persistence behavior without tests for fallback paths.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/core/cache.md`.
- Keep performance docs accurate when cache behavior changes rebuild speed or storage.
- Update migration notes when cache schema compatibility changes.

## Local Checks

- `uv run pytest tests/unit/cache tests/unit/discovery -q`
- `uv run pytest tests/integration/test_phase2b_cache_integration.py -q`
- `uv run ruff check bengal/cache tests/unit/cache`
