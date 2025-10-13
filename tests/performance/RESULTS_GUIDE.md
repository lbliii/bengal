# Benchmark Results Guide

This guide explains how benchmark results are stored, viewed, and compared.

## Overview

All benchmark results are automatically saved in structured JSON format with timestamps, allowing you to:
- Track performance over time
- Compare runs to detect regressions
- Generate trend reports
- View historical data

## Directory Structure

```
tests/performance/
├── benchmark_results/          # Stored results (gitignored)
│   ├── incremental_scale/     # One directory per benchmark
│   │   ├── latest.json        # Symlink to most recent
│   │   ├── 20251012_143522.json
│   │   ├── 20251012_150133.json
│   │   └── ...
│   ├── stability/
│   └── template_complexity/
├── results_manager.py          # Storage and retrieval
├── view_results.py             # CLI for viewing/comparing
└── run_benchmarks.py           # Runner with auto-save
```

## Running Benchmarks with Auto-Save

All benchmarks now automatically save results:

```bash
# Quick validation - saves all results
python tests/performance/run_benchmarks.py --quick

# Single benchmark - saves result
python tests/performance/benchmark_incremental_scale.py

# Full suite - saves all results
python tests/performance/run_benchmarks.py --full
```

Results are saved to `tests/performance/benchmark_results/` with timestamps.

## Viewing Results

### List All Available Results

```bash
cd tests/performance
python view_results.py list
```

Output:
```
================================================================================
AVAILABLE BENCHMARK RESULTS
================================================================================

incremental_scale
  Latest: 2025-10-12 14:35:22
  Total runs: 5

stability
  Latest: 2025-10-12 15:01:33
  Total runs: 3

template_complexity
  Latest: 2025-10-12 15:45:18
  Total runs: 2
```

### Show Latest Result for a Benchmark

```bash
python view_results.py show incremental_scale
```

Shows the complete data from the most recent run.

### Generate Summary Report

```bash
python view_results.py report
```

Shows key metrics from all benchmarks:
```
================================================================================
BENCHMARK SUMMARY REPORT
================================================================================
Generated: 2025-10-12 16:30:45

incremental_scale
--------------------------------------------------------------------------------
Latest run: 2025-10-12T14:35:22
Total runs: 5
Speedup range: 18.3x - 42.1x
Average speedup: 28.4x
Largest scale: 10,000 pages
Status: ✅ PASS

stability
--------------------------------------------------------------------------------
Latest run: 2025-10-12T15:01:33
Total runs: 3
Builds tested: 100
Performance change: +2.3%
Memory growth: +12.5MB
Status: ✅ STABLE
```

## Comparing Results

### Compare Latest Two Runs

```bash
python view_results.py compare incremental_scale
```

Shows:
- Timestamp of each run
- Side-by-side metrics
- Deltas with percentage changes
- Visual indicators (✅ improvement, ⚠️ regression)

Example output:
```
================================================================================
BENCHMARK COMPARISON: incremental_scale
================================================================================

Current:  2025-10-12T14:35:22
Previous: 2025-10-11T10:22:15

Detailed Comparison by Scale:
--------------------------------------------------------------------------------
Scale      Metric                         Current      Previous     Change
--------------------------------------------------------------------------------
1000       Full Build                        1.23s        1.45s     ✅ -0.22s (-15.2%)
           Incr Speedup                     28.3x        26.1x     ✅ +2.2x (+8.4%)
           Cache Size                       15.32MB      15.28MB    +0.04MB (+0.3%)

5000       Full Build                        6.78s        7.12s     ✅ -0.34s (-4.8%)
           Incr Speedup                     32.1x        31.5x     ✅ +0.6x (+1.9%)
           Cache Size                       78.45MB      78.22MB    +0.23MB (+0.3%)

10000      Full Build                       14.56s       15.23s     ✅ -0.67s (-4.4%)
           Incr Speedup                     35.2x        34.8x     ✅ +0.4x (+1.1%)
           Cache Size                      156.89MB     156.45MB    +0.44MB (+0.3%)
```

### Compare Specific Runs

```bash
python view_results.py compare incremental_scale --files 20251012_143522.json 20251011_102215.json
```

## Tracking Trends

### View Trend for a Metric

```bash
# Full build time at 1K pages
python view_results.py trend incremental_scale "scales.0.full_build_time" --limit 10

# Incremental speedup at 10K pages
python view_results.py trend incremental_scale "scales.2.incr_single_speedup" --limit 10
```

Output:
```
================================================================================
TREND: incremental_scale - scales.0.full_build_time
================================================================================

Timestamp                 Value
--------------------------------------------------------------------------------
2025-10-12 14:35:22           1.230
2025-10-11 10:22:15           1.450
2025-10-10 16:45:33           1.380
2025-10-09 14:12:08           1.510
2025-10-08 11:33:22           1.490

Statistics:
  Min:    1.230
  Max:    1.510
  Mean:   1.412
  Latest: 1.230
  Change: -0.260 (-17.4%)
```

## Result Data Format

Results are stored as JSON with this structure:

```json
{
  "benchmark": "incremental_scale",
  "timestamp": "2025-10-12T14:35:22.123456",
  "date": "2025-10-12",
  "time": "14:35:22",
  "data": {
    "scales": [
      {
        "pages": 1000,
        "full_build_time": 1.234,
        "full_build_pages_per_sec": 810.4,
        "incr_single_time": 0.045,
        "incr_single_speedup": 27.4,
        "cache_size_mb": 15.32
      },
      // ... more scales
    ],
    "summary": {
      "min_speedup": 18.3,
      "max_speedup": 42.1,
      "avg_speedup": 28.4,
      "all_passed": true
    }
  },
  "metadata": {
    "git_commit": "abc1234",
    "python_version": "3.12.0",
    "system": "Darwin"
  }
}
```

## Use Cases

### Detecting Performance Regressions

Run benchmarks before and after changes:

```bash
# Before changes
python tests/performance/benchmark_incremental_scale.py

# Make your changes
git commit -m "Optimize rendering"

# After changes
python tests/performance/benchmark_incremental_scale.py

# Compare
python view_results.py compare incremental_scale
```

### CI/CD Integration

```bash
# In CI pipeline
python tests/performance/run_benchmarks.py --quick

# Check if latest run passed
python view_results.py show incremental_scale | grep "all_passed"
```

### Tracking Long-Term Performance

```bash
# Weekly benchmarks
crontab -e
0 2 * * 1 cd /path/to/bengal && python tests/performance/run_benchmarks.py --full

# View trends monthly
python view_results.py trend incremental_scale "scales.2.incr_single_speedup" --limit 20
```

### Validating Optimization Claims

After optimizing something:

```bash
# Run benchmarks
python tests/performance/benchmark_incremental_scale.py

# Get specific metrics
python view_results.py show incremental_scale | jq '.data.summary'

# Compare with baseline
python view_results.py compare incremental_scale --files latest.json baseline_20251001_120000.json
```

## Advanced Usage

### Programmatic Access

```python
from results_manager import BenchmarkResults

manager = BenchmarkResults()

# Load latest result
result = manager.load_result("incremental_scale")
speedup = result["data"]["summary"]["avg_speedup"]

# Get trend data
trend = manager.get_trends("incremental_scale", "scales.0.full_build_time", limit=10)

# Save custom result
manager.save_result("custom_benchmark", {
    "metric1": 123.45,
    "metric2": "success"
})
```

### Export to CSV

```bash
# Export trend data
python -c "
from results_manager import BenchmarkResults
import json
manager = BenchmarkResults()
trend = manager.get_trends('incremental_scale', 'scales.0.full_build_time', 20)
for point in trend:
    print(f\"{point['timestamp']},{point['value']}\")
" > trend.csv
```

## Tips

1. **Run benchmarks regularly** to catch regressions early
2. **Keep baseline results** from important releases (save the JSON files)
3. **Use `--limit` flag** on trends to avoid clutter
4. **Check trends** before claiming performance improvements
5. **Compare against previous release** not just previous commit

## Troubleshooting

**Q: No results found**
```bash
# Make sure you've run benchmarks first
python tests/performance/benchmark_incremental_scale.py
```

**Q: Can't compare - need 2 results**
```bash
# Run the benchmark at least twice
python tests/performance/benchmark_incremental_scale.py
sleep 60  # Wait a minute
python tests/performance/benchmark_incremental_scale.py
```

**Q: Results directory not found**
```bash
# It's created automatically on first benchmark run
ls tests/performance/benchmark_results/  # Should exist after first run
```

## Files

- `results_manager.py` - Core storage/retrieval logic
- `view_results.py` - CLI for viewing/comparing results
- `run_benchmarks.py` - Benchmark runner with auto-save
- `benchmark_results/` - Stored results (gitignored, not committed)
- `.gitignore` - Excludes `benchmark_results/` from git
