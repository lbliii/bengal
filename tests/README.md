# Bengal Test Suite Guide

Bengal's test suite emphasizes high coverage on the critical path (76-96%) with 2,297 tests, including 115 property-based (Hypothesis) tests generating 11,600+ examples. The suite runs in ~40s total but can be optimized to <20s for local development via parallelism, markers, and shared fixtures.

## Quick Runs (~20s)
Use `pytest.ini` defaults for fast feedback: parallel execution (`-n auto`), quiet output (`-q`), and profiling of top 10 slowest tests (`--durations=10`).

- **Unit only** (isolated, ~8s → ~3-4s parallel):  
  `pytest tests/unit -n auto`

- **Integration** (workflows, ~15s):  
  `pytest tests/integration -m "not slow"` (skips full-build heavies)

- **Full suite** (unit + integration, ~30s parallel):  
  `time pytest` (or `pytest -n auto --durations=10 -q`)

- **Ultra-fast dev** (skip slows + Hypothesis):  
  `pytest -m "not slow and not hypothesis"` (~15s)

## Markers
Markers help control execution. See `pytest.ini` for full list.

- `slow`: Full builds/integrations (e.g., site.build()—~15s total; skip for dev).  
  Run: `pytest -m slow` (only heavies) or `-m "not slow"` (skip them).

- `hypothesis`: Property-based tests (115 tests, ~11s due to example generation).  
  Skip: `pytest -m "not hypothesis"` (~29s). Limit examples in dev: Add `from hypothesis import settings; settings(max_examples=50)`.

- `serial`: Non-parallel tests (rare, e.g., stateful FS sims).  
  Run sequentially: `pytest -m serial -n 0`.

- `integration`: Multi-component workflows (e.g., full-to-incremental sequences).

List markers: `pytest --markers`.

## Fixtures for Efficiency
Fixtures reduce redundant setups like site builds (1-2s each).

- **`shared_site_class`** (class-scoped, new in recent updates): Builds a 10-page site once per class (discovery + build). Ideal for read-only tests (URLs, navigation).  
  Example in a test class:  
  ```python
  class TestURLs:
      def test_url_generation(self, shared_site_class):
          site = shared_site_class
          assert len(site.pages) == 10  # Pre-built
          page = site.pages[0]
          assert page.url == "/"  # Test without re-building
  ```  
  - Modifiable copy: `pytest test_file.py::TestClass::test --fixture-param=shared_site_class=modifiable` (duplicates for changes).  
  - Prefer over `tmp_site` (function-scoped, fresh each test) for shared reads.

- **`tmp_site(tmp_path)`**: Function-scoped temp dir—use for modifications (e.g., file changes in integrations).

- **`sample_config`**: Session-scoped read-only config—mutate copies only.

## Benchmarks (Separate from Pytest, ~10-60 min)
Benchmarks are scripts in `tests/performance/`—not run in `pytest`. Use for perf validation, not unit tests.

- **Quick suite** (~10-15 min): Parallel, incremental, full-build, template complexity.  
  `python tests/performance/run_benchmarks.py --quick`

- **Full suite** (~60-90 min): Adds scale (1K-10K pages), stability (100 builds), realistic content.  
  `python tests/performance/run_benchmarks.py --full`

- **Specific**: `--benchmarks parallel,incremental` (comma-separated).  
  View results: `python tests/performance/view_results.py list`

See `tests/performance/README.md` for details (e.g., 18-42x incremental speedup validated).

## Coverage & Profiling
- **Coverage**: `pytest --cov=bengal --cov-report=html` (opens htmlcov/index.html; targets 85%+ critical path).  
  XML for CI: `--cov-report=xml`.

- **Profile Suite**: `pytest --durations=20` (shows top 20 slows—refactor these first).  
  Per-test: Install `pytest-profiling` and run `pytest --profile`.

- **Hypothesis Tuning**: For dev, limit examples globally in `conftest.py` or per-test:  
  ```python
  from hypothesis import settings
  settings(max_examples=50)  # Default 100
  ```

## CI Notes
- **PRs**: Unit + integration (not slow/hypothesis) for fast feedback (~20s).
- **Main/Release**: Full suite + benchmarks (--quick for PRs, --full for tags).
- **Cache**: .pytest_cache/ and venv for speed.
- **Timeout**: 300s default (thread-based; prevents hangs).

For issues, check `tests/performance/PROFILING_GUIDE.md` or run `pytest --help`.

Last Updated: October 14, 2025
