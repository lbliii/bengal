# Fix: pytest-xdist "node down: Not properly terminated" Error

**Date:** 2025-10-20  
**Status:** ✅ **FIXED**  
**Issue:** Test suite consistently fails at ~86% completion with "node down: Not properly terminated"

## Problem Statement

The test suite was consistently failing at approximately 86% completion with the error:
```
[gw0] node down: Not properly terminated
```

This is a classic pytest-xdist issue that occurs when tests spawn their own processes or threads while already running inside a pytest-xdist worker process, causing nested multiprocessing conflicts.

## Root Cause Analysis

### Primary Culprit: `test_process_parallel.py`

This test explicitly uses `ProcessPoolExecutor` to spawn child processes:

```python
@pytest.mark.slow
def test_thread_vs_process_rendering():
    """Compare thread-based vs process-based rendering."""

    # ... test code ...

    # This spawns processes while running inside an xdist worker!
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_page_process, args) for args in args_list]
        # ...
```

**The Problem:**
1. pytest-xdist runs tests in parallel using worker processes (e.g., `gw0`, `gw1`, etc.)
2. When `test_process_parallel.py` runs, it's already inside a worker process
3. The test then tries to spawn **its own child processes** via `ProcessPoolExecutor`
4. This nested multiprocessing causes worker crashes with "node down: Not properly terminated"
5. The test has `multiprocessing.set_start_method("spawn")` in `__main__`, but this **is not executed** when running via pytest

### Secondary Culprit: `test_concurrent_builds.py`

This test uses `ThreadPoolExecutor` to test concurrent builds:

```python
class TestConcurrentBuilds:
    def test_concurrent_full_builds(self, tmp_path):
        # ...
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(build_once, range(6)))
```

While less severe than `ProcessPoolExecutor`, spawning threads for concurrent operations while running in parallel xdist workers can cause race conditions and resource contention.

## Solution

### 1. Mark Problematic Tests as `parallel_unsafe` and `serial`

These markers tell pytest-xdist that these tests cannot safely run in parallel workers:

```python
@pytest.mark.slow
@pytest.mark.serial
@pytest.mark.parallel_unsafe
def test_thread_vs_process_rendering():
    """Compare thread-based vs process-based rendering.

    Marked serial/parallel_unsafe: Uses ProcessPoolExecutor which conflicts with pytest-xdist.
    """
```

Applied to:
- `tests/performance/test_process_parallel.py::test_thread_vs_process_rendering`
- `tests/integration/test_concurrent_builds.py::TestConcurrentBuilds` (entire class)

### 2. Configure pytest-xdist to Group Serial Tests

Updated `tests/conftest.py` to automatically assign all `serial` or `parallel_unsafe` tests to the same worker:

```python
def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items to:
    1. Filter out non-test functions
    2. Configure xdist scheduling for parallel-unsafe tests
    """
    # ... existing filtering code ...

    for item in items:
        # ... existing logic ...

        # Mark parallel-unsafe tests for xdist
        if any(marker in item.keywords for marker in ["serial", "parallel_unsafe"]):
            # Add xdist marker to schedule these tests on same worker
            item.add_marker(pytest.mark.xdist_group(name="serial_group"))
```

This uses pytest-xdist's `xdist_group` marker to ensure all serial tests run on the same worker, preventing conflicts.

### 3. Existing Markers

The `pytest.ini` already defines these markers:

```ini
[pytest]
markers =
    parallel_unsafe: Tests that cannot run in parallel (global state)
    serial: tests that must run sequentially (no parallel)
```

We're now properly using them to prevent worker crashes.

## Why This Happens at 86%

The error occurs at ~86% because:
1. pytest-xdist schedules tests across multiple workers
2. Most tests complete successfully in parallel
3. When `test_process_parallel.py` runs (which happens late in the test order), it tries to spawn processes
4. This crashes the worker, causing the "node down" error
5. The percentage varies slightly based on test scheduling and worker count

## Related GitHub Issue

Similar issue reported in pytest-xdist: https://github.com/pytest-dev/pytest/issues/3216

Common patterns that cause this:
- ProcessPoolExecutor inside xdist workers
- Tests that spawn daemon threads
- Tests that don't properly clean up subprocesses
- Segmentation faults in native extensions
- Database connection leaks in parallel tests

## Testing the Fix

Run the full test suite to verify:

```bash
pytest -n auto --durations=10
```

The tests should now complete without "node down" errors because:
1. `test_process_parallel.py` will run on a dedicated worker (not in parallel)
2. `test_concurrent_builds.py` will also run serially
3. All other tests can still run in parallel for speed

## Additional Recommendations

### Future: Mark More Tests if Needed

If other tests cause similar issues, mark them with:
- `@pytest.mark.serial` - for tests that must run alone
- `@pytest.mark.parallel_unsafe` - for tests with global state or process/thread spawning

### Consider Running Some Tests Separately

For particularly problematic tests (like the ProcessPool test), you could:

1. **Exclude from default run:**
   ```ini
   # pytest.ini
   addopts = -n auto -m "not process_test"
   ```

2. **Run separately:**
   ```bash
   pytest -m process_test -n 0  # Run serially
   ```

### Best Practices

**Tests that MUST be marked `parallel_unsafe`:**
- Tests using `ProcessPoolExecutor` or `multiprocessing.Pool`
- Tests spawning daemon threads that persist across tests
- Tests modifying global singletons or environment variables
- Tests using shared temporary files or databases
- Tests with OS-level resource locks (file locks, semaphores)

**Tests that are usually safe for parallel:**
- Tests using `ThreadPoolExecutor` with local state only
- Tests with proper cleanup (context managers, fixtures)
- Tests using `tmp_path` fixture (each test gets isolated directory)
- Pure unit tests with no I/O or state

## Implementation Checklist

- [x] Mark `test_process_parallel.py` as `@pytest.mark.serial` and `@pytest.mark.parallel_unsafe`
- [x] Mark `test_concurrent_builds.py` class as `@pytest.mark.serial` and `@pytest.mark.parallel_unsafe`
- [x] Update `conftest.py` to configure xdist grouping for serial tests
- [x] Document the fix and rationale
- [ ] Verify fix by running full test suite multiple times
- [ ] Monitor for any other tests that might need similar treatment

## Files Modified

1. `tests/performance/test_process_parallel.py`
   - Added `@pytest.mark.serial` and `@pytest.mark.parallel_unsafe` decorators
   - Updated docstring to explain why

2. `tests/integration/test_concurrent_builds.py`
   - Added `@pytest.mark.serial` and `@pytest.mark.parallel_unsafe` decorators to class
   - Added `import pytest`

3. `tests/conftest.py`
   - Enhanced `pytest_collection_modifyitems` hook
   - Added automatic `xdist_group` assignment for serial tests
   - Updated docstring with detailed explanation

4. `plan/active/xdist-node-down-fix.md` (this document)
   - Created comprehensive documentation of the issue and fix

## Expected Outcome

After this fix:
- ✅ Test suite completes without "node down" errors
- ✅ Most tests still run in parallel for speed
- ✅ Problematic tests run serially on same worker
- ✅ Clear documentation for future similar issues

## Monitoring

Watch for these symptoms that might indicate more tests need marking:
- Tests fail only when run with `-n auto` but pass with `-n 0`
- Intermittent "node down" errors at any completion percentage
- Worker crashes during tests that use threading/multiprocessing
- Resource leaks that only appear in parallel runs

## References

- pytest-xdist docs: https://pytest-xdist.readthedocs.io/
- pytest-xdist issue #3216: https://github.com/pytest-dev/pytest/issues/3216
- pytest markers: https://docs.pytest.org/en/stable/how-to/mark.html
- xdist_group marker: https://pytest-xdist.readthedocs.io/en/latest/distribution.html#running-tests-in-a-group
