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

## Automatic Benchmark History Logging

### What It Does

Every time you run benchmarks, results are **automatically captured** with:
- ✅ Timestamp (when the benchmark ran)
- ✅ Git commit hash (which code version)
- ✅ Git branch (which branch)
- ✅ All metrics (mean, min, max, stddev, etc)

All data is appended to `.benchmarks/history.jsonl` (append-only log).

### Default Behavior

After running benchmarks, you'll see a summary:

```bash
$ pytest benchmarks/ -v

# ... test output ...

Benchmark History (last 3 runs):
================================================================================

1. 2025-10-16T15:23:45.123456
   Branch: feature/benchmark-suite-enhancements | Commit: 1956d96 | Version:

   test_build_performance[small_site]: 0.85
   test_build_performance[large_site]: 2.45
   test_incremental_single_page_change: 0.12

2. 2025-10-16T14:55:22.987654
   Branch: main | Commit: 6fc4866 | Version:

   test_build_performance[small_site]: 0.87
   test_build_performance[large_site]: 2.50
   test_incremental_single_page_change: 0.14

================================================================================
```

### Viewing History

```python
from pathlib import Path
from benchmarks.benchmark_history import BenchmarkHistoryLogger

logger = BenchmarkHistoryLogger()

# Print last 10 runs
logger.print_summary(last_n=10)

# Get all history as list
history = logger.get_history()

# Get most recent run
latest = logger.get_latest_results()
print(latest['timestamp'])
print(latest['git_commit'])
print(latest['results'])
```

### Export for Analysis

Export to CSV for graphing:

```python
from pathlib import Path
from benchmarks.benchmark_history import BenchmarkHistoryLogger

logger = BenchmarkHistoryLogger()

# Export mean times to CSV
logger.export_csv(Path('benchmark_trends.csv'), metric='mean')

# Output: CSV with columns: timestamp, test, metric, git_commit, git_branch
# Can be graphed in Excel, Sheets, matplotlib, etc
```

CSV format:
```
timestamp,test,metric,git_commit,git_branch
2025-10-16T15:23:45.123456,test_build_performance[small_site],0.85,1956d96,feature/benchmark-suite-enhancements
2025-10-16T15:23:45.123456,test_build_performance[large_site],2.45,1956d96,feature/benchmark-suite-enhancements
2025-10-16T14:55:22.987654,test_build_performance[small_site],0.87,6fc4866,main
```

### Measuring Across Patches

The append-only log enables trending:

```
Patch 1 (Oct 16, 10:00): Single-page incremental = 0.12s
Patch 2 (Oct 16, 11:00): Single-page incremental = 0.11s ✅ 8% faster!
Patch 3 (Oct 16, 12:00): Single-page incremental = 0.15s ❌ 36% slower (regression!)
```

### History File Location

```
bengal/
├── benchmarks/
│   ├── .benchmarks/
│   │   ├── history.jsonl              ← Append-only log (auto-updated)
│   │   ├── Linux-...-0001.json        ← Individual run data
│   │   ├── Linux-...-baseline.json
│   │   └── ...
```

### Format of history.jsonl

Each line is a JSON object:

```json
{
  "timestamp": "2025-10-16T15:23:45.123456",
  "git_commit": "1956d96f4b...",
  "git_branch": "feature/benchmark-suite-enhancements",
  "version": null,
  "metadata": {
    "benchmark_file": "Linux-3.12.0-qemu-0001.json",
    "exit_status": 0
  },
  "results": {
    "test_build_performance[small_site]": {
      "stats": {
        "mean": 0.85,
        "median": 0.83,
        "min": 0.79,
        "max": 0.92,
        "stddev": 0.04
      }
    },
    ...
  }
}
```

### Key Advantages

1. **Automatic** - No manual logging required
2. **Dated** - Every run is timestamped
3. **Immutable** - Append-only log can't lose data
4. **Traceable** - Git commit/branch stored with results
5. **Analyzable** - Export to CSV for graphing

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
