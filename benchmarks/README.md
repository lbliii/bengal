# Benchmarking

This directory contains the benchmark suite for the Bengal static site generator. The benchmarks are designed to be run using `pytest` and the `pytest-benchmark` plugin.

## Setup

To run the benchmarks, you first need to install the required dependencies:

```bash
pip install -r requirements.txt
```

You also need to install the `bengal` package in editable mode from the root of the project:

```bash
pip install -e .
```

## Running the Benchmarks

To run the benchmarks, simply run `pytest` from the `benchmarks` directory:

```bash
pytest
```

This will run the benchmarks for all the scenarios defined in the `scenarios` directory. The results will be displayed in the console.

## Benchmark Categories

### Full Build Performance
- **Baseline builds**: Standard builds for small/large sites
- **Fast mode**: Quiet output + guaranteed parallel (`--fast` flag)

### Incremental Builds
- **Single page change**: Most common developer workflow (15-50x speedup expected)
- **Multi-page change**: Batch edits (5 pages)
- **Config change**: Should trigger full rebuild
- **No changes**: Cache validation (<1s expected)

### Parallel Processing
- **Parallel vs Sequential**: Validates 2-4x speedup on multi-core systems
- **Fast mode impact**: Measures logging overhead reduction

### Memory Optimization
- **Memory-optimized builds**: Streaming builds for large sites (`--memory-optimized`)
- **Memory profiling**: Tracks peak memory usage across scenarios

## Expected Performance

**Python 3.14** (recommended):
- Full build: ~256 pages/sec
- Incremental: 15-50x speedup for single-page changes
- Parallel: 2-4x speedup on multi-core systems

**Python 3.14t Free-Threading** (optional):
- Full build: ~373 pages/sec
- True parallel rendering without GIL bottlenecks

## Recent Optimizations (2025-10-20)

- **Page list caching**: 75% reduction in equality checks
- **Parallel related posts**: 7.5x faster (10K pages: 120s → 16s)
- **Parallel taxonomy generation**: Automatic for 100+ page sites
- **Fast mode**: Quiet output + guaranteed parallel processing

## Cold Build Permutation Benchmarks

The `test_cold_build_permutations.py` suite provides comprehensive comparison of all build modes across multiple site sizes.

### Running Cold Build Permutations

```bash
# Run all permutations
pytest test_cold_build_permutations.py -v

# Run specific site size
pytest test_cold_build_permutations.py -k "100_pages" -v

# Run specific build mode across all sizes
pytest test_cold_build_permutations.py -k "fast_mode" -v
```

### Test Matrix

**Site Sizes**: 100, 500, 1000 pages

**Build Modes**:
- Standard (default parallel)
- Fast mode (`--fast`)
- Memory-optimized (`--memory-optimized`)
- Sequential (`--no-parallel`)
- Fast + Memory-optimized (`--fast --memory-optimized`) - 500+ pages only

**Total Tests**: 14 permutations (5 modes × 3 sizes, minus 1 mode that only runs on 500+ pages)

### Expected Insights

- **Fast mode impact**: Measures logging overhead reduction
- **Memory-optimized tradeoffs**: Speed vs memory usage for large sites
- **Parallel speedup**: Validates 2-4x improvement on multi-core systems
- **Scaling characteristics**: How each mode performs as site size increases

### Interpreting Results

After running benchmarks, use `pytest-benchmark` comparison features:

```bash
# Compare results
pytest test_cold_build_permutations.py --benchmark-compare

# Save results for comparison
pytest test_cold_build_permutations.py --benchmark-save=baseline
pytest test_cold_build_permutations.py --benchmark-compare=baseline
```

Look for:
- **Fast mode**: Should be similar or slightly faster than standard (reduced logging)
- **Memory-optimized**: May be slightly slower but uses constant memory
- **Sequential**: Should be 2-4x slower than parallel on multi-core systems

### Running Specific Benchmarks

You can run specific benchmarks using the `-k` flag or by specifying the test node ID:

```bash
# Run incremental build tests
pytest benchmarks/test_build.py -k "incremental" -v

# Run fast mode benchmarks
pytest benchmarks/test_build.py -k "fast_mode" -v
```

### Benchmark Types

- **Full Build**: Standard build with parallel processing enabled (default).
- **Incremental**: Tests single-page edits, batch edits, and config changes.

## 10k Page Site Benchmarks

The `test_10k_site.py` suite tests performance at scale with 10,000+ page sites.

### Running 10k Benchmarks

```bash
# Run all 10k benchmarks (slow, use for nightly CI)
pytest benchmarks/test_10k_site.py -v --benchmark

# Run without benchmark plugin (simpler output)
pytest benchmarks/test_10k_site.py -v

# Run the faster 1k variant
pytest benchmarks/test_10k_site.py -k "1k_site" -v
```

### Performance Gates

| Metric | 10k Pages | 1k Pages |
|--------|-----------|----------|
| Discovery Time | <30s | <5s |
| Peak Memory | <2GB | <500MB |
| Discovery Rate | >300 pages/sec | >200 pages/sec |

### Expected Baseline Performance

**M1 Pro (8-core)**:
- 10k page discovery: ~10-15s
- Peak memory: ~600MB-1GB
- Per-page overhead: ~60-100KB

**Intel i7 (8-core)**:
- 10k page discovery: ~12-20s
- Peak memory: ~700MB-1.2GB
- Per-page overhead: ~70-120KB

### Tests

1. **`test_10k_site_discovery_performance`**: Measures discovery time for 10k pages
2. **`test_10k_site_memory_usage`**: Tracks peak memory usage
3. **`test_1k_site_discovery_performance`**: Faster variant for regular CI
4. **`test_discovery_scaling`**: Verifies linear scaling behavior

### CI Integration

These tests are marked `@pytest.mark.slow` and should run in nightly CI:

```yaml
# .github/workflows/nightly.yml
- name: Run performance benchmarks
  run: pytest benchmarks/test_10k_site.py -v --benchmark
```

For regular CI, use the 1k variant:

```yaml
# .github/workflows/ci.yml
- name: Run quick performance check
  run: pytest benchmarks/test_10k_site.py -k "1k_site" -v
```

## Import Overhead Benchmarks

The `test_import_overhead.py` suite measures module startup latency and "import pollution" - when lightweight modules accidentally pull in heavy dependencies.

### Why Import Time Matters

- **CLI responsiveness**: Users notice if `bengal --help` takes 500ms+ to start
- **Dev server startup**: Fast restarts improve DX
- **Incremental builds**: Re-importing unchanged modules wastes time
- **Rosettes as library**: Users may import rosettes directly for highlighting

### Running Import Benchmarks

```bash
# Quick diagnostic report (no pytest)
python benchmarks/test_import_overhead.py

# Full test suite
pytest benchmarks/test_import_overhead.py -v

# Test specific modules
pytest benchmarks/test_import_overhead.py -k "rosettes" -v
pytest benchmarks/test_import_overhead.py -k "lightweight" -v
```

### What It Tests

| Category | Tests | Threshold |
|----------|-------|-----------|
| Lightweight modules | rosettes, kida, highlighting | <50ms, no heavy deps |
| Optional dependencies | uvloop, psutil, aiohttp | Only loaded when used |
| Error imports | bengal.errors | Only on error path |
| Package inits | `__init__.py` lazy exports | No eager heavy loading |
| Regression detection | Baselines from known good state | <1.5x baseline |

### Key Concepts

- **Heavy modules**: `bengal.errors`, `bengal.core.page`, `bengal.rendering.pipeline`
- **Optional deps**: `uvloop`, `psutil`, `aiohttp`, `tree_sitter`, `zstd`
- **Import pollution**: When importing module A accidentally loads unrelated module B

### Example Output

```
======================================================================
IMPORT OVERHEAD REPORT
======================================================================

✅ bengal.rendering.rosettes
   Time: 11.3ms

✅ bengal.rendering.kida
   Time: 7.3ms

❌ bengal.utils
   Time: 143.6ms
   Heavy deps: bengal.core.site, bengal.errors
   Optional deps: uvloop
```

### Design Patterns (from investigation)

1. **Lazy exports in `__init__.py`**: Use `__getattr__` for heavy re-exports
2. **Deferred error imports**: Import exceptions only in error-raising functions
3. **Optional deps on-demand**: Import `uvloop`, `psutil` etc. only when feature is used
4. **TYPE_CHECKING guards**: Keep type hints without runtime import cost

### CI Integration

```yaml
# .github/workflows/ci.yml
- name: Check import overhead
  run: pytest benchmarks/test_import_overhead.py -v
```

Failing tests indicate a performance regression that should block the PR.
