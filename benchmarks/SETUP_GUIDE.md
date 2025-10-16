# Benchmark Suite Setup Guide

## Overview

This guide covers the Phase 1 enhancements to the Bengal benchmarking suite:
1. **Incremental Build Benchmarking** - Validate incremental build optimization
2. **Memory Profiling** - Track peak memory usage across scenarios
3. **Regression Detection** - Catch performance degradation automatically

## Installation

### 1. Install Benchmark Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Bengal in Editable Mode

```bash
pip install -e /path/to/bengal
```

## Phase 1: Incremental Build Benchmarking

### Why This Matters

Your `BENCHMARK_RESULTS_ANALYSIS.md` revealed that incremental builds are **broken**:
- Expected speedup: 15-50x
- Actual speedup: 1.1x (single page), 0.97x (5K pages)

This is the critical test to validate if fixes work.

### Running Incremental Benchmarks

```bash
# Run all incremental benchmarks
pytest test_build.py::test_incremental_single_page_change -v

# Run specific scenario
pytest test_build.py -k "incremental" -v

# Run with detailed timing
pytest test_build.py -k "incremental" -v --benchmark-verbose
```

### Incremental Build Tests

| Test | Purpose | Expected |
|------|---------|----------|
| `test_incremental_single_page_change` | Most common workflow | >5x speedup |
| `test_incremental_multi_page_change` | Batch edits (5 pages) | >3x speedup |
| `test_incremental_config_change` | Config modification | Full rebuild |
| `test_incremental_no_changes` | Cache validation | <1 second |

### Interpretation

```
Fast incremental (GOOD):
  Full build: 10s
  Single page: 0.5s
  Speedup: 20x ✅

Broken incremental (BAD - current state):
  Full build: 10s
  Single page: 9.5s
  Speedup: 1.05x ❌
```

---

## Phase 1: Memory Profiling

### Why This Matters

Performance degrades significantly at scale:
- 1K pages: 141 pages/sec
- 5K pages: 71 pages/sec (50% degradation)
- 10K pages: 29 pages/sec (79% degradation)

Memory pressure is one possible cause. These tests identify if memory is the bottleneck.

### Running Memory Tests

```bash
# Profile small site
pytest test_build.py::test_memory_usage_small_site -s

# Profile large site (100 pages)
pytest test_build.py::test_memory_usage_large_site -s

# Profile memory during incremental builds
pytest test_build.py::test_incremental_memory_tracking -v --benchmark-verbose
```

### Memory Test Output

```
Small Site Memory Profile:
  Peak Memory: 45.23 MB
  Current Memory: 12.45 MB
  Memory per Page: 15.0767 MB

Large Site Memory Profile:
  Peak Memory: 142.67 MB
  Current Memory: 38.92 MB
  Memory per Page: 1.4267 MB
```

### Analysis

**Good sign** - memory per page decreases at scale (amortization):
```
Small site: 15.08 MB/page
Large site: 1.43 MB/page  ✅
```

**Red flag** - memory per page increases at scale (possible leak):
```
Small site: 15.08 MB/page
Large site: 14.85 MB/page
Result: Likely memory leak ❌
```

---

## Phase 1: Regression Detection

### Baseline Establishment

On first run, establish a baseline:

```bash
# Save results as baseline
pytest benchmarks/ --benchmark-save=baseline

# Files saved to .benchmarks/Linux-<version>-baseline.json
```

### Running Subsequent Tests

Compare against baseline:

```bash
# Compare to baseline (fail if >10% regression)
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%

# Compare to last run
pytest benchmarks/ --benchmark-compare=0001
```

### Understanding Results

```
test_build_performance[small_site]
  PASSED
  MIN:     1.23 sec (100%)
  MAX:     1.45 sec (105%)
  MEAN:    1.34 sec (102%)  # 2% slower than baseline

test_incremental_single_page_change
  FAILED
  MEAN:    4.56 sec vs 0.89 sec baseline (-412%)  ❌
  Problem: Incremental builds got MUCH slower!
```

### Regression Detection Setup

Enable automatic regression detection:

```bash
# In pytest.ini, uncomment:
; --benchmark-compare-fail=mean:10%

# This makes tests fail if performance drops >10%
```

---

## Full Benchmark Run

### Complete Phase 1 Validation

```bash
# 1. Run all benchmarks with memory profiling
pytest benchmarks/ -v -s --benchmark-verbose

# 2. Compare to baseline and fail on regressions
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%

# 3. Generate comparison report
pytest benchmarks/ --benchmark-compare=baseline --benchmark-json=results.json
```

### Expected Output

```
benchmarks/test_build.py::test_build_performance[small_site]
  Full build (3 pages): 0.85s ✅

benchmarks/test_build.py::test_build_performance[large_site]
  Full build (100 pages): 2.45s ✅

benchmarks/test_build.py::test_incremental_single_page_change
  Single page change: 0.12s (7x speedup) ✅

benchmarks/test_build.py::test_incremental_multi_page_change
  5-page batch: 0.34s (7x speedup) ✅

benchmarks/test_build.py::test_incremental_config_change
  Config change triggers full rebuild: 2.43s ✅

benchmarks/test_build.py::test_incremental_no_changes
  Cache validation: 0.08s ✅

benchmarks/test_build.py::test_memory_usage_small_site
  Peak: 45.23 MB, Per-page: 15.08 MB ✅

benchmarks/test_build.py::test_memory_usage_large_site
  Peak: 142.67 MB, Per-page: 1.43 MB ✅
```

---

## Troubleshooting

### Issue: Tests Fail Due to Missing Bengal Command

```bash
# Solution: Install bengal in editable mode
pip install -e /path/to/bengal

# Verify:
bengal --version
```

### Issue: Memory Tests Are Slow

```bash
# Skip memory tests, run only benchmarks
pytest benchmarks/ -k "benchmark"

# Skip benchmarks, run only memory tests
pytest benchmarks/ -k "memory"
```

### Issue: Incremental Tests Show Full Rebuild (1.1x speedup)

**This confirms the bug!** The incremental system is performing full rebuilds.

Next steps:
1. Document the issue
2. Create a GitHub issue
3. Investigate `bengal/orchestration/incremental.py`
4. Check `bengal/cache/build_cache.py` for cache validation issues

### Issue: Results Files Growing Large

```bash
# Clean old benchmark results
rm -rf .benchmarks/

# Or keep only recent runs
ls -lt .benchmarks/ | head -5
```

---

## Performance Targets (Phase 1)

### Incremental Builds
- ✅ Single page: >5x speedup vs full build
- ✅ Multi-page: >3x speedup vs full build
- ✅ Config change: Triggers full rebuild
- ✅ No changes: <1 second

### Memory Usage
- ✅ Small site (3 pages): <100 MB peak
- ✅ Large site (100 pages): <200 MB peak
- ✅ Memory per page: Decreases at scale (indicates amortization)

### Regression Detection
- ✅ Baseline established
- ✅ Regressions detected automatically
- ✅ Failure threshold: >10% performance drop

---

## Next Steps (Phase 2-4)

After Phase 1 validation:

1. **Phase 2**: Dynamic scenario generation (1K/5K/10K pages)
2. **Phase 3**: CPU profiling and flame graphs
3. **Phase 4**: HTML reporting and GitHub Actions CI

See `plan/active/BENCHMARK_SUITE_ENHANCEMENTS.md` for details.

---

## Quick Reference

```bash
# Run all benchmarks
pytest benchmarks/ -v

# Run specific test
pytest benchmarks/test_build.py::test_incremental_single_page_change -v

# Save baseline
pytest benchmarks/ --benchmark-save=baseline

# Compare to baseline
pytest benchmarks/ --benchmark-compare=baseline

# Fail on regression >10%
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%

# Verbose output
pytest benchmarks/ -v --benchmark-verbose

# Memory profiling
pytest benchmarks/ -k "memory" -s

# Generate JSON report
pytest benchmarks/ --benchmark-json=results.json
```
