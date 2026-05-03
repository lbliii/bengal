# Benchmarks Steward

The `benchmarks/` suite measures Bengal's build, parsing, rendering,
highlighting, cache, and free-threading claims outside the fast test loop.
Benchmarks should be reproducible enough to guide engineering decisions without
blocking ordinary development.

Related docs:
- root `../AGENTS.md`
- `README.md`
- `../tests/performance/README.md`
- `../site/content/docs/about/benchmarks.md`
- `../site/content/docs/building/performance/`

## Point Of View

Benchmarks represent Bengal's published performance story. They should measure
real work at realistic sizes and make environment assumptions explicit.

## Protect

- Scenario generation, site sizes, and benchmark categories.
- Comparability of saved baselines.
- Parser/template/highlighter comparisons that still reflect current supported
  engines.
- Memory and scaling measurements for 3.14 and 3.14t.

## Contract Checklist

- Benchmark docs and performance docs when numbers, scenarios, or supported
  engines change.
- Tests/performance steward when benchmark logic overlaps regression tests.
- Setup instructions for standalone and b-stack workspace installs.
- Baseline save/compare notes for claims used in PRs or docs.

## Advocate

- Removing stale comparisons only after preserving the claim they used to test.
- Scenario fixtures that model docs-heavy, directive-heavy, and large-site
  workloads.
- Clear commands for quick vs full measurement.

## Serve Peers

- Give rendering, orchestration, cache, and parser stewards measured evidence.
- Give planning realistic estimates and regression risk.
- Give docs performance claims with dated, reproducible context.

## Do Not

- Let stale engine names or deleted backends remain in active benchmark claims.
- Compare runs without noting Python version, threading mode, and hardware.
- Treat benchmark-only speedups as valid if correctness work disappeared.
- Add dependencies just for a benchmark convenience without asking.

## Own

- `benchmarks/`
- `benchmarks/README.md`
- Performance docs that cite benchmark results
- Checks: `uv run pytest benchmarks -q --benchmark-disable` for import/smoke coverage
- Checks: `uv run pytest benchmarks/ tests/performance/ -v --benchmark-only` for measured runs
