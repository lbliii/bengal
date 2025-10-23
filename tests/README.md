# Bengal Test Suite Guide

Bengal's test suite emphasizes high coverage on the critical path (76-96%) with 2,297 tests, including 115 property-based (Hypothesis) tests generating 11,600+ examples. The suite runs in ~40s total but can be optimized to <20s for local development via parallelism, markers, and shared fixtures.

## Quick Runs (~20s)
Use `pytest.ini` defaults for fast feedback: parallel execution (`-n auto`), quiet output (`-q`), and profiling of top 10 slowest tests (`--durations=10`).

- **Fast dev loop** (RECOMMENDED, ~20s):  
  `pytest -m "not slow" -n auto`  
  Skips showcase site builds and stateful tests for rapid feedback.

- **Unit only** (isolated, ~8s → ~3-4s parallel):  
  `pytest tests/unit -n auto`

- **Integration** (workflows, ~15s):  
  `pytest tests/integration -m "not slow"` (skips full-build heavies)

- **Full suite** (unit + integration, ~1 min):  
  `time pytest` (or `pytest -n auto --durations=10 -q`)  
  Run before committing to ensure all tests pass.

- **Ultra-fast dev** (skip slows + Hypothesis):  
  `pytest -m "not slow and not hypothesis"` (~15s)

## Markers
Markers help control execution. See `pytest.ini` for full list.

- `slow`: Full builds/integrations (e.g., showcase site with 292 pages, stateful workflows).  
  Run: `pytest -m slow` (only heavies) or `-m "not slow"` (skip them - RECOMMENDED for dev).  
  **Performance note**: Slow tests include the 292-page showcase build, which previously caused a frustrating long tail at 95% completion. These are now optimized but still take time.

- `hypothesis`: Property-based tests (115 tests, ~11s due to example generation).  
  Skip: `pytest -m "not hypothesis"` (~29s). Examples are auto-tuned: 20 in dev, 100 in CI via profiles.

- `serial`: Non-parallel tests (rare, e.g., stateful FS sims).  
  Run sequentially: `pytest -m serial -n 0`.

- `integration`: Multi-component workflows (e.g., full-to-incremental sequences).

- `parallel_unsafe`: Tests using `ThreadPoolExecutor`/`ProcessPoolExecutor` internally.  
  **Critical**: Mark tests with `@pytest.mark.parallel_unsafe` if they spawn their own thread/process pools.  
  Reason: pytest-xdist runs tests in parallel workers. If a test creates its own pool, this causes nested parallelism → worker crashes ("node down: Not properly terminated").  
  Examples: `TestThreadSafety`, `TestAssetDiscoveryWithRaceConditions`, `TestRealWorldScenarios`.

List markers: `pytest --markers`.

## Parallel Test Safety

⚠️ **Important**: When writing tests that use parallelism internally, mark them `@pytest.mark.parallel_unsafe`.

### Why This Matters
pytest uses xdist (`-n auto`) to run tests in parallel workers for faster execution. However, if a test itself spawns threads or processes (e.g., `ThreadPoolExecutor`), this creates **nested parallelism** that causes worker crashes.

### How to Mark Tests
```python
import concurrent.futures
import pytest

@pytest.mark.parallel_unsafe
class TestConcurrentOperations:
    """Tests that use ThreadPoolExecutor internally.

    Marked parallel_unsafe: Prevents pytest-xdist worker crashes from nested parallelism.
    """

    def test_concurrent_writes(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            # Test code that uses thread pool
            ...
```

### When to Mark Tests
- Uses `concurrent.futures.ThreadPoolExecutor`
- Uses `concurrent.futures.ProcessPoolExecutor`
- Uses `multiprocessing.Pool`
- Modifies global state accessed by other tests
- Creates temporary processes/threads

### What Happens Without Markers
Without `@pytest.mark.parallel_unsafe`:
- ❌ Worker crashes: "node down: Not properly terminated"
- ❌ Flaky test results
- ❌ CI failures requiring re-runs
- ❌ Hard-to-debug intermittent issues

With `@pytest.mark.parallel_unsafe`:
- ✅ Tests run sequentially on same worker (via `xdist_group`)
- ✅ No worker crashes
- ✅ Reliable CI results
- ✅ Clear documentation of test requirements

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
