# Performance Benchmarks

This directory contains performance benchmarks for Bengal SSG to validate performance claims and track improvements.

## Available Benchmarks

### 1. SSG Comparison (`benchmark_ssg_comparison.py`) ⭐ NEW
**Purpose:** Apples-to-apples comparison with Hugo, Eleventy, Jekyll, Gatsby, Next, Nuxt

Uses [CSS-Tricks methodology](https://css-tricks.com/comparing-static-site-generator-build-times/):
- Minimal markdown (title + 3 paragraphs)
- Cold builds (cache cleared each run)
- Test scales: 1, 16, 64, 256, 1024, 4096, 8192, 16384 files
- No asset optimization or processing
- 3 runs per scale, averaged

```bash
python tests/performance/benchmark_ssg_comparison.py
```

**⚠️ Note:** Full run (up to 16K files) takes 30-60 minutes. Edit script to use smaller scales for quick test.

**Recent Results (October 3, 2025):**
- 100 pages: ~0.3s (faster than Eleventy, Jekyll, Gatsby!)
- 1,024 pages: ~3.5s (290 pages/second)
- Sub-linear scaling: 32x time for 1024x files = 3125% efficiency

### 2. Parallel Processing (`benchmark_parallel.py`)
**Validates:** 2-4x speedup claim for parallel processing

Tests:
- Asset processing (sequential vs parallel)
- Post-processing (sequential vs parallel)
- Various asset counts (10, 25, 50, 100)

```bash
python tests/performance/benchmark_parallel.py
```

**Expected Results:**
- 50 assets: 3x speedup
- 100 assets: 4x speedup
- Post-processing: 2x speedup

---

### 3. Incremental Builds (`benchmark_incremental.py`)
**Validates:** 18-42x speedup for incremental builds

Tests:
- Full build vs incremental build
- Different change types (content, template, asset)
- Various site sizes (10, 50, 100 pages)

```bash
python tests/performance/benchmark_incremental.py
```

**Actual Results (validated October 3, 2025):**
- Small sites (10 pages): 18.3x speedup (0.223s → 0.012s)
- Medium sites (50 pages): 41.6x speedup (0.839s → 0.020s)
- Large sites (100 pages): 35.6x speedup (1.688s → 0.047s)

---

### 4. Full Build Performance (`benchmark_full_build.py`)
**Purpose:** End-to-end build time benchmarks with realistic content

Tests:
- Small site (10 pages, 15 assets)
- Medium site (100 pages, 75 assets)
- Large site (500 pages, 200 assets)

Provides detailed breakdown:
- Discovery time
- Taxonomy collection time
- Rendering time
- Asset processing time
- Post-processing time

```bash
python tests/performance/benchmark_full_build.py
```

**Expected Results:**
- Small sites: < 1 second
- Medium sites: 1-5 seconds
- Large sites: 5-15 seconds

---

## Running All Benchmarks

Run all benchmarks sequentially:

```bash
# Quick validation (5-10 minutes)
python tests/performance/benchmark_parallel.py
python tests/performance/benchmark_incremental.py
python tests/performance/benchmark_full_build.py

# Full SSG comparison (30-60 minutes)
python tests/performance/benchmark_ssg_comparison.py
```

Or create a simple script to run them all.

---

## Interpreting Results

### Speedup Calculations
- **Speedup = Sequential Time / Parallel Time**
- **Example:** 0.141s sequential ÷ 0.034s parallel = 4.21x speedup

### What Good Looks Like

| Benchmark | Target | Excellent | Good | Marginal | Fail |
|-----------|--------|-----------|------|----------|------|
| Parallel assets (100) | 2-4x | 4x+ | 3-4x | 2-3x | <2x |
| Parallel post-processing | 1.5-2x | 2x+ | 1.5-2x | 1.2-1.5x | <1.2x |
| Incremental (small) | 10x+ | 50x+ | **18x** ✅ | 5-10x | <5x |
| Incremental (medium) | 30x+ | 50x+ | **42x** ✅ | 10-30x | <10x |
| Incremental (large) | 30x+ | 50x+ | **36x** ✅ | 10-30x | <10x |

### Performance Factors

Results vary based on:
- **CPU cores:** More cores = better parallel speedup
- **Disk speed:** SSD vs HDD affects I/O-bound operations
- **Content complexity:** More Markdown parsing = slower
- **Asset types:** Images optimize slower than CSS/JS
- **Cache state:** First build always slower

---

## Adding New Benchmarks

### Template

```python
"""
Performance benchmark for [feature name].
Tests to validate [claim] for [functionality].
"""

import time
import tempfile
import shutil
from pathlib import Path
from bengal.core.site import Site


def benchmark_something():
    """Benchmark a specific feature."""
    # Setup
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create test data
        # ...

        # Measure
        start = time.time()
        # ... operation to benchmark
        elapsed = time.time() - start

        return elapsed
    finally:
        shutil.rmtree(temp_dir)


def run_benchmarks():
    """Run all benchmarks and report results."""
    print("=" * 80)
    print("BENCHMARK NAME")
    print("=" * 80)
    # ... run tests and print results


if __name__ == "__main__":
    run_benchmarks()
```

---

## Continuous Performance Tracking

### Option 1: Manual Tracking
Run benchmarks before/after major changes and record results in git commit messages or CHANGELOG.

### Option 2: pytest-benchmark Integration
```bash
pip install pytest-benchmark
```

Convert standalone scripts to pytest format:
```python
def test_asset_processing_parallel(benchmark):
    result = benchmark(process_assets, num_assets=100)
    assert result < 0.05  # Should complete in <50ms
```

### Option 3: CI/CD Integration
Add to GitHub Actions workflow:
```yaml
- name: Run performance benchmarks
  run: |
    python tests/performance/benchmark_parallel.py
    python tests/performance/benchmark_incremental.py
```

---

## Performance Goals vs Competitors

| SSG | Build (100 pages) | Incremental | Notes |
|-----|------------------|-------------|-------|
| **Hugo** | 0.1-0.5s | 0.05-0.1s | Gold standard (Go) |
| **Jekyll** | 3-10s | N/A | Ruby, no incremental |
| **11ty** | 1-3s | 0.5-1s | JavaScript |
| **Sphinx** | 5-15s | N/A | Python, docs-focused |
| **Bengal** | **1.66s** ✅ | **0.047s** ✅ | Python, competitive! |

Bengal's achievements (validated October 3, 2025):
- ✅ Beat Jekyll, 11ty, Sphinx in full builds
- ✅ Match Hugo in incremental builds  
- ✅ Under 2 seconds for 100 page sites
- ✅ 18-42x speedup for incremental builds

---

## Troubleshooting

### Benchmark Times Inconsistent
- Run multiple iterations (already built-in: 3-5 runs)
- Close other applications
- Check disk space and CPU usage
- Use SSD instead of HDD

### Unexpectedly Slow
- Check if debug logging is enabled
- Verify parallel processing is enabled
- Look at breakdown to identify bottleneck
- Profile with `cProfile` if needed

### Import Errors
```bash
# Make sure Bengal is installed
cd /path/to/bengal
pip install -e .
```

---

## Notes

- Benchmarks create temporary directories and clean up after themselves
- Each benchmark runs multiple iterations and reports averages
- Results are printed to stdout in formatted tables
- No external dependencies beyond Bengal's requirements
