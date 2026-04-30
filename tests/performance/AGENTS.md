# Performance Tests Steward

Performance tests protect Bengal's claim that pure Python can scale with cores.
Treat regressions as product risk, not benchmark trivia.

## Protect

- Stable benchmark setup and repeatable fixture sizes.
- Clear distinction between smoke checks and measured comparisons.
- Incremental rebuild and parallel rendering hot paths.
- Notes when a benchmark result is noisy or environment-sensitive.

## Do Not

- Mix correctness assertions with expensive benchmark loops when setup can be separated.
- Add broad sleeps or machine-specific thresholds.
- Delete historical fixtures without explaining what claim changed.
- Treat a faster result as good if it skips required work.

## Documentation Ownership

- Own performance testing guidance in `site/content/docs/reference/architecture/meta/testing.md`.
- Keep `site/content/docs/building/performance/` honest when benchmark claims or hot paths change.

## Local Checks

- `uv run pytest tests/performance -q`
- Relevant benchmark scripts under `tests/performance/`
- `make test-cov` only when coverage impact matters.
