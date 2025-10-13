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

### 5. Incremental Build Scaling ⭐ NEW (`benchmark_incremental_scale.py`)
**Purpose:** Validate incremental build performance at documentation site scale

Tests:
- 1,000 pages: Large blog, medium docs site
- 5,000 pages: Large documentation (framework docs)
- 10,000 pages: Enterprise docs (Kubernetes, AWS, Python)

For each scale:
- Full build time
- Single page change rebuild time
- Template change rebuild time
- Cache size and memory usage
- Speedup validation

```bash
python tests/performance/benchmark_incremental_scale.py
```

**Expected Results:**
- Incremental speedup: ≥15x at all scales
- 10K pages full build: < 120 seconds
- Cache size: < 20KB per page
- Linear memory scaling

**⚠️ Note:** Full run takes 30-60 minutes. Edit script to test single scale for quick validation.

---

### 6. Build Stability ⭐ NEW (`benchmark_build_stability.py`)
**Purpose:** Validate build system remains stable over many consecutive builds

Tests:
- 100 consecutive incremental builds
- Memory usage tracking
- Cache size monitoring
- Build time consistency
- Cache integrity validation

```bash
python tests/performance/benchmark_build_stability.py
```

**Expected Results:**
- No performance degradation (< 10% change)
- No memory leaks (< 50MB growth)
- No cache bloat (< 5MB growth)
- Consistent build times (CV < 20%)
- Cache produces identical output to full builds

---

### 7. Template Complexity Impact ⭐ NEW (`benchmark_template_complexity.py`)
**Purpose:** Measure how template complexity affects build performance

Tests:
- Baseline: Minimal template (just content)
- Light: Basic template with functions
- Medium: Multiple templates with inheritance
- Heavy: Complex templates with many functions
- Extreme: 50+ templates with deep nesting

```bash
python tests/performance/benchmark_template_complexity.py
```

**Expected Results:**
- Light templates: < 10% overhead
- Medium templates: 10-20% overhead
- Heavy templates: 20-40% overhead
- Extreme templates: < 100% overhead (not 2x slower)

---

## Running All Benchmarks

### Quick Validation Suite (10-15 minutes)

```bash
# Core performance validation
python tests/performance/benchmark_parallel.py
python tests/performance/benchmark_incremental.py
python tests/performance/benchmark_full_build.py
python tests/performance/benchmark_template_complexity.py
```

### Scale Testing Suite (60-90 minutes)

```bash
# Large-scale validation
python tests/performance/benchmark_incremental_scale.py
python tests/performance/benchmark_build_stability.py
python tests/performance/benchmark_realistic_scale.py
```

### Comparison Benchmarks (30-60 minutes each)

```bash
# Against other SSGs
python tests/performance/benchmark_ssg_comparison.py
```

### Automated Runner

Use the provided runner script to execute all benchmarks:

```bash
# Quick validation only
python tests/performance/run_benchmarks.py --quick

# Full suite including scale tests
python tests/performance/run_benchmarks.py --full

# Specific benchmarks
python tests/performance/run_benchmarks.py --benchmarks parallel,incremental,scale
```

---

## Results Storage and Comparison

**All benchmark results are automatically saved** in structured JSON format with timestamps. This allows you to track performance over time, compare runs, and detect regressions.

### View Results

```bash
# List all stored results
python tests/performance/view_results.py list

# Show latest result for a benchmark
python tests/performance/view_results.py show incremental_scale

# Compare latest two runs (detect regressions)
python tests/performance/view_results.py compare incremental_scale

# View trend for a metric
python tests/performance/view_results.py trend incremental_scale "scales.0.full_build_time"

# Generate summary report of all benchmarks
python tests/performance/view_results.py report
```

### Result Format

Results are stored in `tests/performance/benchmark_results/` (gitignored) with this structure:

```
benchmark_results/
├── incremental_scale/
│   ├── latest.json              # Most recent run
│   ├── 20251012_143522.json     # Timestamped results
│   └── 20251012_150133.json
├── stability/
└── template_complexity/
```

Each result includes:
- Timestamp and metadata
- Complete benchmark data
- Summary statistics
- Pass/fail status

### Use Cases

**Detect regressions:**
```bash
# Before and after a change
python benchmark_incremental_scale.py
# ... make changes ...
python benchmark_incremental_scale.py
python view_results.py compare incremental_scale
```

**Track long-term trends:**
```bash
# View last 10 runs
python view_results.py trend incremental_scale "scales.2.incr_single_speedup" --limit 10
```

**Validate optimization claims:**
```bash
# Run benchmark and get summary
python benchmark_incremental_scale.py
python view_results.py show incremental_scale | grep "summary"
```

See [RESULTS_GUIDE.md](RESULTS_GUIDE.md) for complete documentation.

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

## Profiling

### Quick Start

```bash
# Profile a site build
python tests/performance/profile_site.py examples/showcase

# Generate flame graph (interactive)
python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats

# Analyze profile with recommendations
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats

# Compare with baseline to detect regressions
python tests/performance/analyze_profile.py current.stats --compare baseline.stats

# Fail CI if >15% regression
python tests/performance/analyze_profile.py current.stats --compare baseline.stats --fail-on-regression 15
```

### Available Tools

#### 1. `profile_site.py` - Profile Any Site
```bash
# Profile examples/showcase
python tests/performance/profile_site.py examples/showcase

# Compare parallel vs sequential
python tests/performance/profile_site.py examples/showcase --compare

# Profile with specific worker count
python tests/performance/profile_site.py examples/showcase --parallel --max-workers 4
```

#### 2. `flamegraph.py` - Visual Profiling ⭐ NEW
```bash
# Interactive HTML (opens browser automatically)
python tests/performance/flamegraph.py profile.stats

# Static SVG
python tests/performance/flamegraph.py profile.stats --tool flameprof --output flame.svg

# Call graph
python tests/performance/flamegraph.py profile.stats --tool gprof2dot --output graph.png

# List available tools
python tests/performance/flamegraph.py --list-tools
```

**Requirements:**
```bash
# For interactive flame graphs
pip install snakeviz

# For static SVG flame graphs
pip install flameprof

# For call graphs
pip install gprof2dot
brew install graphviz  # or apt-get install graphviz
```

#### 3. `analyze_profile.py` - Advanced Analysis ⭐ ENHANCED
```bash
# Basic analysis
python tests/performance/analyze_profile.py profile.stats

# Show top 50 functions
python tests/performance/analyze_profile.py profile.stats --top 50

# Compare with baseline (detect regressions)
python tests/performance/analyze_profile.py current.stats --compare baseline.stats

# Fail if >10% regression (for CI)
python tests/performance/analyze_profile.py current.stats --compare baseline.stats --fail-on-regression 10

# Generate flame graph after analysis
python tests/performance/analyze_profile.py profile.stats --flamegraph
```

#### 4. `profile_utils.py` - Programmatic Profiling ⭐ NEW
```python
from profile_utils import ProfileContext, profile_function

# Context manager
with ProfileContext(enabled=True, name="my_operation") as ctx:
    # Your code here
    expensive_operation()

profile_path = ctx.save(output_dir, filename="operation.stats")

# Function decorator
result, profile_path = profile_function(
    my_function,
    arg1, arg2,
    profile=True,
    profile_name="function_test"
)
```

### Profiling Workflow

#### 1. Establish Baseline
```bash
# Profile your current build
python tests/performance/profile_site.py examples/showcase

# Save as baseline
cp .bengal/profiles/build_profile.stats .bengal/profiles/baseline.stats
```

#### 2. Make Changes
```bash
# Edit your code...
git commit -m "Optimize rendering"
```

#### 3. Compare Performance
```bash
# Profile again
python tests/performance/profile_site.py examples/showcase

# Compare and detect regressions
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats \
    --compare .bengal/profiles/baseline.stats \
    --fail-on-regression 10
```

#### 4. Visualize Bottlenecks
```bash
# Generate flame graph to find hot spots
python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats
```

### CI Integration

```yaml
# .github/workflows/performance.yml
- name: Profile build
  run: |
    python tests/performance/profile_site.py examples/showcase

- name: Compare with baseline
  run: |
    python tests/performance/analyze_profile.py \
      .bengal/profiles/build_profile.stats \
      --compare .bengal/profiles/baseline.stats \
      --fail-on-regression 15
```

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
