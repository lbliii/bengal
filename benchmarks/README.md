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
- **Pipeline mode**: Reactive dataflow pipeline (`--pipeline` flag)
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
- Pipeline mode (`--pipeline`)
- Memory-optimized (`--memory-optimized`)
- Sequential (`--no-parallel`)
- Fast + Pipeline (`--fast --pipeline`)
- Fast + Memory-optimized (`--fast --memory-optimized`) - 500+ pages only

**Total Tests**: 20 permutations (7 modes × 3 sizes, minus 1 mode that only runs on 500+ pages)

### Expected Insights

- **Fast mode impact**: Measures logging overhead reduction
- **Pipeline vs Standard**: Compares reactive dataflow vs batch orchestrator
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
- **Pipeline**: May be faster or slower depending on site characteristics
- **Memory-optimized**: May be slightly slower but uses constant memory
- **Sequential**: Should be 2-4x slower than parallel on multi-core systems

### Running Specific Benchmarks

You can run specific benchmarks using the `-k` flag or by specifying the test node ID:

```bash
# Run incremental build tests
pytest benchmarks/test_build.py -k "incremental" -v

# Run the experimental pipeline benchmark
pytest benchmarks/test_build.py::test_pipeline_build -v
```

### Benchmark Types

- **Full Build**: Standard build with parallel processing enabled (default).
- **Incremental**: Tests single-page edits, batch edits, and config changes.
- **Pipeline**: Tests the experimental `--pipeline` reactive dataflow mode.
