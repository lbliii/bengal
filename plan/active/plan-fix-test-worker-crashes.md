## 📋 Implementation Plan: Fix Test Worker Crashes in CI

### Executive Summary
GitHub CI test suite is experiencing worker crashes due to nested parallelism: pytest-xdist workers running tests that internally use ThreadPoolExecutor. Multiple unit tests use ThreadPoolExecutor for testing parallel behavior but lack `parallel_unsafe` markers, causing "node down: Not properly terminated" errors.

### Plan Details
- **Total Tasks**: 8
- **Estimated Time**: 1-2 hours
- **Complexity**: Moderate
- **Confidence Gates**: All tests must pass with `-n auto` without worker crashes

---

## Root Cause Analysis

**Issue**: pytest-xdist workers crash with "Not properly terminated"

**Evidence**:
1. ❌ `tests/unit/core/test_parallel_processing.py` - Uses ThreadPoolExecutor, NO markers
2. ❌ `tests/unit/discovery/test_asset_discovery.py` - Uses ThreadPoolExecutor, NO markers
3. ❌ `tests/unit/utils/test_atomic_write.py` - Uses ThreadPoolExecutor, NO markers
4. ✅ `tests/integration/test_concurrent_builds.py` - Uses ThreadPoolExecutor, HAS markers
5. ✅ `tests/performance/test_process_parallel.py` - Uses ProcessPoolExecutor, HAS markers

**Why this causes crashes**:
- pytest-xdist spawns worker processes/threads
- Worker runs test that creates its own ThreadPoolExecutor
- Nested parallelism causes resource conflicts, deadlocks, or crashes
- Workers terminate unexpectedly with "Not properly terminated"

---

## Phase 1: Add Missing Markers (3 tasks)

### Tests (`tests/unit/core/`)

#### Task 1.1: Mark parallel-unsafe tests in test_parallel_processing.py
- **Files**: `tests/unit/core/test_parallel_processing.py`
- **Action**: Add `@pytest.mark.parallel_unsafe` to TestThreadSafety class
- **Reason**: Uses ThreadPoolExecutor (lines 319, 343, 392)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `tests(core): mark parallel processing tests as parallel_unsafe`

---

### Tests (`tests/unit/discovery/`)

#### Task 1.2: Mark parallel-unsafe tests in test_asset_discovery.py
- **Files**: `tests/unit/discovery/test_asset_discovery.py`
- **Action**: Add `@pytest.mark.parallel_unsafe` to TestAssetDiscoveryWithRaceConditions class
- **Reason**: Uses ThreadPoolExecutor (line 211)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `tests(discovery): mark asset discovery race tests as parallel_unsafe`

---

### Tests (`tests/unit/utils/`)

#### Task 1.3: Mark parallel-unsafe tests in test_atomic_write.py
- **Files**: `tests/unit/utils/test_atomic_write.py`
- **Action**: Add `@pytest.mark.parallel_unsafe` to TestRealWorldScenarios class
- **Reason**: Uses ThreadPoolExecutor (lines 266, 294)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `tests(utils): mark atomic write concurrent tests as parallel_unsafe`

---

## Phase 2: Enhance CI Configuration (2 tasks)

### CI Config (`.github/workflows/`)

#### Task 2.1: Add max-worker-restart to fast-check job
- **Files**: `.github/workflows/tests.yml`
- **Action**: Add `--max-worker-restart=3` to fast-check pytest command
- **Reason**: Allow workers to restart on transient failures (Python 3.14 compatibility)
- **Dependencies**: None
- **Status**: pending
- **Commit**: `ci: add max-worker-restart for xdist robustness`

#### Task 2.2: Add dist=worksteal to fast-check job
- **Files**: `.github/workflows/tests.yml`
- **Action**: Add `--dist worksteal` to fast-check pytest command
- **Reason**: Better load balancing, serial_group tests stay on same worker
- **Dependencies**: Task 2.1
- **Status**: pending
- **Commit**: `ci: use worksteal distribution for better xdist scheduling`

---

## Phase 3: Documentation (2 tasks)

### Docs (`tests/`)

#### Task 3.1: Add parallel safety guidelines to tests/README.md
- **Files**: `tests/README.md`
- **Action**: Add section on "Parallel Test Safety" with marker guidelines
- **Dependencies**: Tasks 1.1-1.3
- **Status**: pending
- **Commit**: `docs(tests): add parallel safety guidelines for test authors`

#### Task 3.2: Update pytest.ini with parallel_unsafe clarification
- **Files**: `pytest.ini`
- **Action**: Enhance `parallel_unsafe` marker description with examples
- **Dependencies**: Task 3.1
- **Status**: pending
- **Commit**: `tests: clarify parallel_unsafe marker usage in pytest.ini`

---

## Phase 4: Validation (1 task)

### Integration Testing

#### Task 4.1: Run full test suite with xdist locally
- **Action**: Execute `pytest -n auto -v` and verify no worker crashes
- **Success Criteria**:
  - All tests pass
  - No "node down" errors
  - No "Not properly terminated" warnings
- **Dependencies**: All previous tasks
- **Status**: pending

---

## 📊 Task Summary

| Area | Tasks | Status |
|------|-------|--------|
| Core Tests | 1 | pending |
| Discovery Tests | 1 | pending |
| Utils Tests | 1 | pending |
| CI Config | 2 | pending |
| Documentation | 2 | pending |
| Validation | 1 | pending |

---

## Expected Impact

**Before**:
- Worker crashes in ~3-5% of CI runs
- "node down: Not properly terminated" errors
- Flaky test results requiring re-runs
- Developer frustration with CI reliability

**After**:
- ✅ Zero worker crashes
- ✅ Reliable CI runs
- ✅ Proper isolation of parallel-unsafe tests
- ✅ Clear guidelines for future test authors
- ✅ Better Python 3.14 compatibility

---

## 📋 Next Steps
- [x] Research root cause (COMPLETED)
- [ ] Begin Phase 1: Add missing markers
- [ ] Begin Phase 2: Enhance CI config
- [ ] Begin Phase 3: Update documentation
- [ ] Begin Phase 4: Validation

---

**Confidence**: 95% 🟢
**Reasoning**: Root cause clearly identified with specific line numbers. Solution is well-understood (marker pattern already used successfully for other tests). Low risk, high impact fix.
