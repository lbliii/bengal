# Phase 1 Testing Guide

**Branch**: `feature/benchmark-suite-enhancements`  
**Status**: Ready for validation and testing

---

## Quick Validation (5 minutes)

Test that Phase 1 infrastructure works without running full benchmarks:

```bash
# 1. Navigate to project
cd /Users/llane/Documents/github/python/bengal

# 2. Install dependencies
pip install -r benchmarks/requirements.txt

# 3. Verify Bengal is installed
bengal --version

# 4. List available benchmarks
pytest benchmarks/ --collect-only

# Expected output should show:
# - test_build_performance[small_site]
# - test_build_performance[large_site]
# - test_incremental_single_page_change
# - test_incremental_multi_page_change
# - test_incremental_config_change
# - test_incremental_no_changes
# - test_memory_usage_small_site
# - test_memory_usage_large_site
# - test_incremental_memory_tracking
```

---

## Full Benchmark Run (30-60 minutes)

Complete performance baseline:

```bash
# Run all benchmarks with memory tracking
pytest benchmarks/ -v -s --benchmark-verbose

# This will:
# 1. Full build small_site (3 pages)
# 2. Full build large_site (100 pages)
# 3. Test incremental single-page change
# 4. Test incremental multi-page batch
# 5. Test incremental config change
# 6. Test cache validation
# 7. Profile memory for both scenarios
# 8. Run memory tracking during incremental build

# Save results for later comparison
pytest benchmarks/ --benchmark-save=baseline
```

---

## Focus Tests by Phase

### Test Incremental Builds ONLY

```bash
# Run only incremental build tests (quick: ~20 seconds)
pytest benchmarks/ -k "incremental" -v

# Expected to see:
# - test_incremental_single_page_change
# - test_incremental_multi_page_change
# - test_incremental_config_change
# - test_incremental_no_changes
# - test_incremental_memory_tracking
```

### Test Memory Profiling ONLY

```bash
# Run only memory tests (with output: ~15 seconds)
pytest benchmarks/ -k "memory" -s

# Expected output:
# Small Site Memory Profile:
#   Peak Memory: XX.XX MB
#   Current Memory: XX.XX MB
#   Memory per Page: X.XXXX MB
#
# Large Site Memory Profile:
#   Peak Memory: XXX.XX MB
#   Current Memory: XXX.XX MB
#   Memory per Page: X.XXXX MB
```

### Test Full Builds ONLY

```bash
# Run only full build performance tests
pytest benchmarks/ -k "test_build_performance" -v --benchmark-verbose
```

---

## What to Look For

### Incremental Build Performance

**GOOD SIGN** ✅:
```
test_incremental_single_page_change
  Full build:      10.2 sec
  Single page:     0.45 sec
  Speedup:         22.7x
```

**RED FLAG** ❌:
```
test_incremental_single_page_change
  Full build:      10.2 sec
  Single page:     9.8 sec
  Speedup:         1.04x  <- BROKEN!
```

### Memory Profile Analysis

**GOOD SIGN** ✅ (memory per page DECREASES):
```
Small site (3 pages):    15.08 MB/page
Large site (100 pages):  1.43 MB/page
Trend: Decreasing ✅
```

**RED FLAG** ❌ (memory per page INCREASES):
```
Small site (3 pages):    15.08 MB/page
Large site (100 pages):  14.85 MB/page
Trend: Increasing ❌ Possible leak!
```

---

## Regression Detection Testing

### Establish Baseline

```bash
# First run saves baseline
pytest benchmarks/ --benchmark-save=baseline

# Verify file was created
ls -la .benchmarks/ | grep baseline
# Should show: Linux-...-baseline.json
```

### Compare to Baseline

```bash
# Run comparison without threshold
pytest benchmarks/ --benchmark-compare=baseline

# Run with failure threshold
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%

# Expected: All tests pass unless >10% regression detected
```

### Create Test Regression (optional)

To test regression detection actually works:

```bash
# 1. Create baseline
pytest benchmarks/ --benchmark-save=baseline

# 2. Artificially slow down a test:
#    Edit benchmarks/test_build.py
#    Add: time.sleep(1) inside test_build_performance

# 3. Run comparison
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%

# Expected: Should FAIL with "10% regression detected"
```

---

## Troubleshooting During Testing

### Issue: "bengal: command not found"

```bash
# Solution
pip install -e .
bengal --version
```

### Issue: Tests timeout or take forever

```bash
# You might be running profiling or large scenarios
# Run just incremental tests instead:
pytest benchmarks/ -k "incremental" -v
```

### Issue: Memory tests show zero MB

```bash
# The subprocess memory tracking might not work on your system
# This is OK - the infrastructure is there
# The important tests are incremental builds and full build performance
```

### Issue: Regression detection shows no saved baseline

```bash
# Generate baseline first:
pytest benchmarks/ --benchmark-save=baseline
```

---

## Expected Timing

| Test | Duration | Notes |
|------|----------|-------|
| Full build small_site | 0.5-2s | 3 pages |
| Full build large_site | 1-5s | 100 pages |
| Incremental single-page | 0.1-2s | Modified 1 page |
| Incremental multi-page | 0.2-3s | Modified 5 pages |
| Config change test | 1-5s | Full rebuild |
| No changes test | 0.05-1s | Cache only |
| Memory small site | 0.5-2s | Profiling overhead |
| Memory large site | 1-5s | Profiling overhead |
| **Total (all tests)** | **5-30 minutes** | Depends on system |

---

## Interpreting Results

### Full Benchmark Output Example

```
benchmarks/test_build.py::test_build_performance[small_site]
  ... PASSED [  7%]

  name                                            | 0.850 ms ±  65 ms

benchmarks/test_build.py::test_incremental_single_page_change
  ... PASSED [ 14%]

  name                                            | 478 ms ±  12 ms

# This shows:
# - Small site: 0.85 seconds
# - Single-page incremental: 0.478 seconds
# - Speedup: 0.85 / 0.478 = 1.77x (should be 5x+)
```

### Memory Output Example

```
Small Site Memory Profile:
  Peak Memory: 45.23 MB
  Current Memory: 12.45 MB
  Memory per Page: 15.0767 MB

Large Site Memory Profile:
  Peak Memory: 142.67 MB
  Current Memory: 38.92 MB
  Memory per Page: 1.4267 MB

Analysis:
✅ Per-page memory decreases (15.08 → 1.43)
✅ This indicates good amortization at scale
✅ Not a memory leak
```

---

## Next Steps After Testing

1. **If incremental builds are FAST** (5x+ speedup):
   - ✅ Incremental system is working
   - Move to Phase 2: Enhanced scenarios

2. **If incremental builds are SLOW** (1.1x speedup):
   - ❌ Confirms the bug from BENCHMARK_RESULTS_ANALYSIS.md
   - Investigate: bengal/orchestration/incremental.py
   - Check: bengal/cache/build_cache.py
   - Create GitHub issue with benchmark results

3. **If memory per-page INCREASES at scale**:
   - ⚠️ Possible memory leak
   - Profile with Phase 3: CPU profiling & flame graphs

---

## Reference Documentation

- `benchmarks/SETUP_GUIDE.md` - Detailed setup instructions
- `plan/active/PHASE1_COMPLETION_SUMMARY.md` - What was built
- `plan/active/BENCHMARK_SUITE_ENHANCEMENTS.md` - Overall roadmap
- `plan/active/BENCHMARK_RESULTS_ANALYSIS.md` - Original analysis

---

## Questions?

Refer to:
1. `benchmarks/SETUP_GUIDE.md` - Most comprehensive guide
2. Test function docstrings - Explain what each test does
3. `benchmarks/memory_profiler.py` - Memory profiling implementation

---

**Branch Status**: Ready for testing and validation  
**Next Phase**: Phase 2 - Dynamic scenario generation when complete
