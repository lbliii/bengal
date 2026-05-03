# Performance Tests Steward

Performance tests protect Bengal's claim that pure Python can scale with cores.
Treat regressions as product risk, not benchmark trivia.

Related docs:
- root `../../AGENTS.md`
- `README.md`
- `../../benchmarks/README.md`
- `../../site/content/docs/building/performance/`
- `../../site/content/docs/about/benchmarks.md`

## Point Of View

Performance tests represent Bengal's public speed, memory, and free-threading
claims. They should distinguish measured regressions from noisy environments.

## Protect

- Stable benchmark setup and repeatable fixture sizes.
- Clear distinction between smoke checks and measured comparisons.
- Incremental rebuild and parallel rendering hot paths.
- Notes when a benchmark result is noisy or environment-sensitive.

## Contract Checklist

- Performance tests under `tests/performance/` and benchmark suite overlap under
  `benchmarks/`.
- Docs that publish speed, scaling, memory, or incremental claims.
- Changelog/performance notes for hot-path behavior changes.
- Free-threading notes for parallelism or shared mutable state changes.
- Baselines/results when thresholds or fixture sizes change.

## Advocate

- Benchmarks that measure complete required work, not skipped paths.
- Separate setup from measured loops.
- Confidence intervals, saved baselines, and environment notes for comparisons.

## Serve Peers

- Give orchestration/rendering/cache evidence for hot-path changes.
- Give docs honest benchmark claims and caveats.
- Give planning credible performance risk signals.

## Do Not

- Mix correctness assertions with expensive benchmark loops when setup can be
  separated.
- Add broad sleeps or machine-specific thresholds.
- Delete historical fixtures without explaining what claim changed.
- Treat a faster result as good if it skips required work.

## Own

- `site/content/docs/reference/architecture/meta/testing.md`
- `site/content/docs/building/performance/`
- `site/content/docs/about/benchmarks.md`
- Tests under `tests/performance/`
- Checks: `uv run pytest tests/performance -q`
- Checks: relevant benchmark scripts under `tests/performance/`
- Checks: `make test-cov` only when coverage impact matters
