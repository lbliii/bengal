# GitHub Pages Build Optimization Guide

Quick reference for running comprehensive build option benchmarks under GitHub Pages worker constraints.

## Quick Start

```bash
# 1. Install dependencies
pip install -r benchmarks/requirements.txt

# 2. Verify Python 3.14t is available
python --version  # Should show 3.14.x

# 3. Run comprehensive benchmark suite
pytest benchmarks/test_github_pages_optimization.py -v --benchmark

# 4. Save results for analysis
pytest benchmarks/test_github_pages_optimization.py --benchmark-json=results.json

# 5. Analyze results
python benchmarks/analyze_github_pages_results.py results.json
```

## What Gets Tested

### Build Option Combinations (~25 configurations)

- **Baseline**: Default parallel, auto-incremental
- **Sequential**: `--no-parallel` (baseline for parallel speedup)
- **Fast mode**: `--fast` (quiet + guaranteed parallel)
- **Memory-optimized**: `--memory-optimized` (streaming for large sites)
- **Profiles**: `--profile writer/theme-dev/dev`
- **CI combinations**: `--fast --strict --clean-output`
- **Edge cases**: Sequential + incremental, sequential + memory-optimized

### Site Sizes

- **50 pages**: Small blog/documentation
- **200 pages**: Medium documentation site
- **500 pages**: Large comprehensive docs
- **1000 pages**: Very large site (stress test)

### Resource Constraints (GitHub Pages Worker)

- **CPU**: 2 cores (emulated via CPU affinity)
- **RAM**: 7GB limit (emulated via resource limits)
- **Python**: 3.14t free-threading (no GIL)

## Expected Results

### Parallel Speedup (2-core system)

With Python 3.14t free-threading, expect:
- **1.5-2x speedup** for parallel vs sequential on 2-core systems
- Better scaling than CPython GIL (which would show minimal speedup)

### Fast Mode Impact

- **5-15% speedup** from reduced logging overhead
- More noticeable on constrained systems (GitHub Pages workers)

### Memory-Optimized Tradeoffs

- **Slightly slower** (~5-10%) but uses constant memory
- **Recommended** for sites with 500+ pages on constrained workers
- Prevents OOM (Out of Memory) errors

### Optimal CI Configuration

Expected best configuration for GitHub Actions:
```bash
bengal build --fast --strict --clean-output
```

For large sites (500+ pages):
```bash
bengal build --fast --memory-optimized --strict
```

## Running Specific Tests

```bash
# Test specific site size
pytest benchmarks/test_github_pages_optimization.py -k "50_pages" -v

# Test optimal CI build
pytest benchmarks/test_github_pages_optimization.py -k "optimal_ci_build" -v

# Test large site optimization
pytest benchmarks/test_github_pages_optimization.py -k "large_site_optimal" -v

# Compare parallel vs sequential on 2-core
pytest benchmarks/test_github_pages_optimization.py -k "parallel_vs_sequential" -v
```

## Understanding Results

The analysis script (`analyze_github_pages_results.py`) provides:

1. **Best configuration per site size**: Fastest build time
2. **Top 5 configurations**: Ranked by performance
3. **Speedup analysis**: How much faster vs baseline
4. **Recommendations**: Actionable insights for GitHub Pages builds

### Example Output

```
🏆 Best Configuration per Site Size
--------------------------------------------------------------------------------

50 pages:
  Config: fast_strict_clean
  Time: 2.34s (mean)
  Pages/sec: 21.4
  Speedup vs baseline: 1.12x

200 pages:
  Config: fast_memory_optimized
  Time: 8.76s (mean)
  Pages/sec: 22.8
  Speedup vs baseline: 1.18x

💡 Recommendations for GitHub Pages
--------------------------------------------------------------------------------
  ✅ Use --fast flag: 1.15x average speedup (reduces logging overhead)
  ✅ Use --memory-optimized for sites with 500+ pages (prevents OOM)
  ✅ Parallel processing helps: 1.75x average speedup on 2-core system
  ✅ For CI/CD: Use --fast --strict --clean-output (optimal for GitHub Actions)
```

## Troubleshooting

### CPU Affinity Not Working

If CPU limiting doesn't work (e.g., on macOS without proper permissions), the tests will still run but without CPU constraints. This is OK for development, but for accurate GitHub Pages emulation, ensure:

- `psutil` is installed: `pip install psutil`
- On Linux: Run with appropriate permissions
- On macOS: May require running in Docker or VM

### Memory Limits Not Applied

Memory limits use `resource.setrlimit()` which works on Unix systems. On Windows, memory limiting is skipped (tests still run).

### Python 3.14t Not Available

If Python 3.14t is not available, tests will still run but may show different performance characteristics:

- CPython 3.14: Will show GIL contention, less parallel speedup
- Python 3.14t: True parallelism, better scaling on multi-core

To get Python 3.14t:
- Download from python.org (if available)
- Build from source with `--enable-free-threading`
- Use `PYTHON_GIL=0` environment variable (if supported)

## Next Steps

After running benchmarks:

1. **Review recommendations** from analysis script
2. **Update CI/CD workflows** with optimal flags
3. **Document findings** in project documentation
4. **Track regressions** by comparing against baseline

## Related Documentation

- `benchmarks/README.md`: Full benchmark suite documentation
- `benchmarks/test_cold_build_permutations.py`: Similar suite without resource constraints
- `plan/drafted/rfc-benchmark-refresh-and-worker-optimization.md`: Worker scaling analysis
