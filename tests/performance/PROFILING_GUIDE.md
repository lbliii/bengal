# Profiling Guide

Complete guide to profiling Bengal SSG performance.

## Quick Start

```bash
# 1. Profile a build
python tests/performance/profile_site.py examples/showcase

# 2. View flame graph (visual, easiest)
python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats

# 3. Analyze details
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats
```

## Tools Overview

| Tool | Purpose | Output | Best For |
|------|---------|--------|----------|
| **flamegraph.py** | Visual profiling | Interactive HTML/SVG | Finding bottlenecks quickly |
| **analyze_profile.py** | Detailed analysis | Text report | Understanding specific functions |
| **profile_site.py** | Profile any site | .stats file + report | Real-world profiling |
| **profile_rendering.py** | Profile with test data | .stats file + report | Controlled benchmarks |
| **profile_utils.py** | Programmatic profiling | Python API | Custom profiling |

## Installation

```bash
# Core tools (included)
# No additional requirements for basic profiling

# Visual profiling (highly recommended)
pip install snakeviz

# Advanced visualization
pip install flameprof gprof2dot
brew install graphviz  # For call graphs
```

## Workflow

### Step 1: Profile Your Build

```bash
# Profile examples/showcase site
python tests/performance/profile_site.py examples/showcase
```

**Output:**
```
Profile saved to: .bengal/profiles/build_profile.stats
Analyze with:
  python -m pstats .bengal/profiles/build_profile.stats
  python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats
  python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats
```

### Step 2: Visualize with Flame Graph

```bash
# Opens browser with interactive flame graph
python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats
```

**What to look for:**
- **Wide bars** = functions taking lots of time
- **Tall stacks** = deep call chains
- **Color** = different modules (hover for details)

**Example findings:**
```
🔥 Wide bar: mistune.BlockParser.parse() - Markdown parsing is slow
🔥 Tall stack: 15 levels deep in template rendering - Too much nesting?
```

### Step 3: Detailed Analysis

```bash
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats --top 50
```

**Output includes:**
- Top functions by cumulative time
- Top functions by internal time
- Most called functions
- Bottleneck identification
- Automatic recommendations

**Example output:**
```
🔥 KEY BOTTLENECKS:
Function                      File                Time (s)  % of Total
mistune.parse                 mistune.py         2.345     (23.5%)
jinja2.Template.render        template.py        1.234     (12.3%)
...

💡 RECOMMENDATIONS:
• Markdown parsing is significant (2.35s) - consider content caching
• Template rendering is significant (1.23s) - check bytecode caching
```

### Step 4: Compare with Baseline

```bash
# First time: save baseline
cp .bengal/profiles/build_profile.stats .bengal/profiles/baseline.stats

# After changes: compare
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats \
    --compare .bengal/profiles/baseline.stats
```

**Output:**
```
⚠️  PERFORMANCE REGRESSIONS (slower):
Function                                Change      Current    Baseline
mistune.py::parse                      +15.3%     2.345s     2.034s
pipeline.py::process_page              +8.7%      1.234s     1.135s

✅ PERFORMANCE IMPROVEMENTS (faster):
Function                                Change      Current    Baseline
cache.py::is_changed                   -23.1%     0.123s     0.160s
```

### Step 5: Fail on Regressions (CI)

```bash
# Exit with error if any function regresses >10%
python tests/performance/analyze_profile.py current.stats \
    --compare baseline.stats \
    --fail-on-regression 10
```

## Advanced Usage

### Profile Specific Operations

```python
from profile_utils import ProfileContext

# Profile a specific code block
with ProfileContext(enabled=True, name="discovery") as ctx:
    site.discover_content()
    site.discover_assets()

profile_path = ctx.save(output_dir)
print(f"Profile saved: {profile_path}")
```

### Compare Parallel vs Sequential

```bash
# Profile both and compare
python tests/performance/profile_site.py examples/showcase --compare
```

**Output:**
```
SEQUENTIAL build: 5.23s (100 pages = 19.1 pages/sec)
PARALLEL build (2 workers): 3.45s → 1.52x speedup
PARALLEL build (4 workers): 2.12s → 2.47x speedup  
PARALLEL build (8 workers): 1.89s → 2.77x speedup
```

### Profile with Different Configurations

```bash
# Test different markdown parsers
python tests/performance/profile_site.py examples/showcase
# Edit bengal.toml, change markdown_engine
python tests/performance/profile_site.py examples/showcase
# Compare profiles
```

### Generate Multiple Visualizations

```bash
PROFILE=.bengal/profiles/build_profile.stats

# Interactive HTML
python tests/performance/flamegraph.py $PROFILE --tool snakeviz

# Static SVG (for docs/reports)
python tests/performance/flamegraph.py $PROFILE --tool flameprof --output flame.svg

# Call graph (shows function relationships)
python tests/performance/flamegraph.py $PROFILE --tool gprof2dot --output graph.png
```

## Common Patterns

### Find Slow Imports

```bash
# Profile with python -X importtime
python -X importtime -m bengal build 2> imports.log

# Analyze
cat imports.log | grep "cumulative"
```

### Profile Memory + CPU Together

```bash
# Run memory profiling test
python tests/performance/test_memory_profiling.py -v -s

# Then CPU profile
python tests/performance/profile_site.py examples/showcase

# Compare findings
```

### Track Performance Over Time

```bash
# Save dated profiles
DATE=$(date +%Y%m%d)
python tests/performance/profile_site.py examples/showcase
cp .bengal/profiles/build_profile.stats .bengal/profiles/build_${DATE}.stats

# Compare trends
python tests/performance/analyze_profile.py .bengal/profiles/build_${DATE}.stats \
    --compare .bengal/profiles/baseline.stats
```

## Interpreting Results

### Cumulative vs Total Time

**Cumulative Time:** Total time spent in function + all calls it makes
- Use to find "expensive call chains"
- Good for high-level bottlenecks

**Total Time (Internal):** Time spent in function itself (not calls)
- Use to find "expensive functions"
- Good for pinpointing exact bottleneck

### Example Interpretation

```
Function: site.build()
  Cumulative: 5.0s  (entire build)
  Total:      0.1s  (just the site.build logic)

→ build() itself is fast, but it calls expensive things

Function: mistune.parse()
  Cumulative: 2.5s
  Total:      2.3s

→ parse() itself is slow (92% is internal work)
→ THIS is the real bottleneck!
```

### Call Count Analysis

```
Function: slugify()
  Calls:  50,000
  Total:  1.2s
  Per call: 0.024ms

→ Called way too often! Cache the results.
```

### Flame Graph Colors

Different tools use different colors:
- **snakeviz**: Random colors, width = time
- **flameprof**: Red (hot) = most time
- **gprof2dot**: Color by module/package

## Troubleshooting

### "snakeviz not found"

```bash
pip install snakeviz
```

### "Can't generate call graph"

```bash
# macOS
brew install graphviz

# Linux
apt-get install graphviz

# Then
pip install gprof2dot
```

### Profile file too large

```bash
# Limit what's profiled
import cProfile
profiler = cProfile.Profile()
profiler.enable()
# ... only critical code ...
profiler.disable()
```

### Can't find bottleneck

1. Check flame graph first (visual is easier)
2. Sort by "tottime" not "cumulative"
3. Look for high call counts
4. Profile with smaller data set to isolate

## Best Practices

1. **Always save baseline** before making changes
2. **Profile real sites** (examples/showcase) not just tests
3. **Use flame graphs** for exploration, analysis for details
4. **Compare before/after** every optimization
5. **Profile in CI** to catch regressions early
6. **Focus on wide bars** in flame graphs (not tall stacks)
7. **Check call counts** for accidental O(n²) patterns

## Examples

### Find Rendering Bottleneck

```bash
# 1. Profile
python tests/performance/profile_site.py examples/showcase

# 2. Visual inspection
python tests/performance/flamegraph.py .bengal/profiles/build_profile.stats

# 3. Find rendering.* functions that are wide
# 4. Analyze those specifically
python tests/performance/analyze_profile.py .bengal/profiles/build_profile.stats | grep rendering

# 5. If needed, add line profiling to that function
```

### Validate Optimization

```bash
# Before
python tests/performance/profile_site.py examples/showcase
cp .bengal/profiles/build_profile.stats before.stats

# Make optimization
# ... edit code ...

# After
python tests/performance/profile_site.py examples/showcase
cp .bengal/profiles/build_profile.stats after.stats

# Compare
python tests/performance/analyze_profile.py after.stats --compare before.stats
```

### CI/CD Integration

```yaml
# .github/workflows/performance.yml
jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install snakeviz

      - name: Download baseline
        uses: actions/download-artifact@v3
        with:
          name: baseline-profile
          path: .bengal/profiles/

      - name: Profile build
        run: python tests/performance/profile_site.py examples/showcase

      - name: Compare with baseline
        run: |
          python tests/performance/analyze_profile.py \
            .bengal/profiles/build_profile.stats \
            --compare .bengal/profiles/baseline.stats \
            --fail-on-regression 15

      - name: Upload profile
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: current-profile
          path: .bengal/profiles/build_profile.stats
```

## See Also

- [README.md](README.md) - Performance benchmarks
- [RESULTS_GUIDE.md](RESULTS_GUIDE.md) - Benchmark result storage
- [test_memory_profiling.py](test_memory_profiling.py) - Memory profiling
