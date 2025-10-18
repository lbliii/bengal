# Benchmark Suite Enhancements Plan

## Context

The initial benchmarking suite (PR: "Add Robust Benchmarking Suite") has been merged and provides a solid foundation. However, it has critical gaps that prevent us from:
1. Validating incremental build fixes (currently performing full rebuilds)
2. Identifying scale degradation causes (memory pressure vs algorithmic)
3. Tracking performance regressions over time
4. Profiling to find bottlenecks

This plan addresses those gaps systematically.

---

## Phase 1: Critical Infrastructure (Days 1-3) 🔴

### 1.1 Incremental Build Benchmarking

**Why**: Your `BENCHMARK_RESULTS_ANALYSIS.md` identified that incremental builds are broken (1.1x speedup instead of 15-50x). We need to benchmark this to validate fixes.

**Implementation**:
```python
# benchmarks/test_build.py - add new test

@pytest.mark.benchmark
def test_incremental_build_single_page(benchmark, tmp_path):
    """
    Benchmark incremental build with single page change.
    Tests the core incremental optimization.
    """
    scenario_path = Path(__file__).parent / "scenarios" / "large_site"

    # Copy scenario to tmp location
    import shutil
    test_site = tmp_path / "test_site"
    shutil.copytree(scenario_path, test_site)

    # Full build first
    subprocess.run(["bengal", "build"], cwd=test_site, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Now modify one page
    page = test_site / "content" / "page50.md"
    original_content = page.read_text()

    def build_after_change():
        page.write_text(original_content + "\n\nModified at " + str(time.time()))
        subprocess.run(["bengal", "build"], cwd=test_site, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    benchmark(build_after_change)
    page.write_text(original_content)  # restore
```

**Metrics Tracked**:
- Single page change (typical developer workflow)
- Multi-page batch change
- Asset change only
- Config change detection

**Success Criteria**:
- Incremental single-page builds show >5x speedup vs full build
- Config change triggers full rebuild (validate detection works)
- Results show improvement after fixes

---

### 1.2 Memory Profiling

**Why**: Performance degrades from 141 pps (1K pages) → 29 pps (10K pages). Could be memory pressure, GC thrashing, or algorithmic issues.

**Implementation**:
```python
# benchmarks/memory_profiler.py - new module

import tracemalloc
from pathlib import Path
import subprocess
import json

class MemoryProfiler:
    def __init__(self, scenario_path):
        self.scenario_path = scenario_path

    def profile_build(self):
        """Profile memory usage during build."""
        tracemalloc.start()

        subprocess.run(
            ["bengal", "build"],
            cwd=self.scenario_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
        }

# Integration with pytest-benchmark
@pytest.mark.benchmark
def test_build_memory_usage(scenario, tmp_path):
    """Track memory during build."""
    profiler = MemoryProfiler(scenario_path)
    stats = profiler.profile_build()

    # pytest-benchmark can track extra info
    with open(tmp_path / "memory.json", "w") as f:
        json.dump(stats, f)
```

**Metrics Tracked**:
- Peak memory per scenario size
- Memory growth curve (1K → 5K → 10K)
- Identify if memory is the bottleneck

**Success Criteria**:
- Clear memory data for each scenario
- Can identify if scale degradation is memory-related
- Establish baselines for regression detection

---

### 1.3 Regression Detection & Historical Tracking

**Why**: Without historical data, we can't tell if changes improved or degraded performance.

**Implementation**:
```bash
# benchmarks/pytest.ini - enable comparison

[pytest]
addopts = --benchmark-only
          --benchmark-warmup=on
          --benchmark-save-data
          --benchmark-compare=0001
          --benchmark-compare-fail=mean:10%

# Store results for regression detection
markers =
    benchmark: mark a test as a benchmark
    regression: mark tests that track regressions
```

**Setup**:
```bash
# First run - save baseline
pytest benchmarks/ --benchmark-save=baseline

# Subsequent runs - compare to baseline
pytest benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:10%
```

**Metrics Tracked**:
- Historical build times per scenario
- Regression alerts if performance drops >10%
- Comparison between runs

---

## Phase 2: Enhanced Scenarios (Days 4-5) 🟡

### 2.1 Dynamic Scenario Generator

**Why**: Manually creating 100-page scenario doesn't scale. Need 1K, 5K, 10K pages dynamically.

**Implementation**:
```python
# benchmarks/scenario_generator.py - new module

class ScenarioGenerator:
    def __init__(self, output_dir, page_count):
        self.output_dir = Path(output_dir)
        self.page_count = page_count

    def generate(self):
        """Generate scenario with given page count."""
        self.output_dir.mkdir(exist_ok=True)

        # Create content directory
        content_dir = self.output_dir / "content"
        content_dir.mkdir(exist_ok=True)

        # Create index
        (content_dir / "_index.md").write_text(
            "---\ntitle: Generated Benchmark Site\n---\n\n# Home"
        )

        # Generate pages
        for i in range(self.page_count):
            page_file = content_dir / f"page{i:05d}.md"
            page_file.write_text(
                f"---\ntitle: Page {i}\n---\n\n"
                f"# Page {i}\n\n"
                f"This is page {i} of the generated scenario."
            )

        # Create config
        (self.output_dir / "bengal.toml").write_text(
            "[site]\n"
            f'title = "Generated Site ({self.page_count} pages)"\n'
            "base_url = https://example.com\n\n"
            "[build]\n"
            "fast_mode = true\n"
            "output_dir = output"
        )

# Usage in tests
@pytest.fixture(params=[1000, 5000, 10000])
def dynamic_scenario(tmp_path, request):
    """Generate scenarios of different sizes."""
    generator = ScenarioGenerator(tmp_path / "scenario", request.param)
    generator.generate()
    return tmp_path / "scenario"

@pytest.mark.benchmark
def test_build_dynamic_scenarios(benchmark, dynamic_scenario):
    """Benchmark builds across different page counts."""
    # ... benchmark code
```

**Benefits**:
- Scale testing without disk space bloat
- Can test 10K pages, 50K pages, etc.
- Reproducible scenario generation

---

### 2.2 API Documentation Scenario

**Why**: Your strongest use case is Sphinx migration (API docs). Need a realistic scenario.

**Implementation**:
```python
# benchmarks/scenarios/api_docs/

# Generate a realistic API docs scenario with:
# - Module hierarchy (e.g., my_package.module.submodule)
# - Auto-generated API docs
# - Cross-references between pages
# - Code examples and syntax highlighting

# Similar to Sphinx autodoc output but with Bengal's AST-based approach
```

---

### 2.3 Nested Section Hierarchy Scenario

**Why**: Tests how performance scales with section depth and complexity.

**Implementation**:
```
# benchmarks/scenarios/nested_sections/

content/
  _index.md
  section1/
    _index.md
    subsection1/
      _index.md
      page1.md
      page2.md
    subsection2/
      _index.md
      page3.md
  section2/
    _index.md
    ...
```

---

## Phase 3: Profiling & Analysis Tools (Days 6-7) 🟢

### 3.1 CPU Profiling Integration

**Implementation**:
```python
# benchmarks/profilers.py

import cProfile
import pstats
from pathlib import Path

class CPUProfiler:
    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self.profiler = cProfile.Profile()

    def profile_subprocess(self, cmd, cwd):
        """Profile subprocess execution."""
        # Launch with profiling enabled
        subprocess.run(
            ["python", "-m", "cProfile", "-o", str(self.output_path / "profile.prof")]
            + cmd,
            cwd=cwd
        )

    def report(self):
        """Generate human-readable profile report."""
        stats = pstats.Stats(str(self.output_path / "profile.prof"))
        stats.sort_stats('cumulative')
        stats.print_stats(30)  # Top 30 functions
```

**Usage**:
```bash
# Run with CPU profiling
pytest benchmarks/ -v --profile
```

---

### 3.2 Flame Graph Generation

**Why**: Visual identification of bottlenecks is much faster than reading profiles.

**Implementation**:
```bash
# benchmarks/generate_flamegraph.sh

# 1. Run with py-spy
py-spy record -o profile.svg -- bengal site build

# 2. Generate interactive HTML
speedscope profile.svg
```

---

## Phase 4: Reporting & Dashboarding (Days 8-10) 🔵

### 4.1 Benchmark Report Generator

**Implementation**:
```python
# benchmarks/report_generator.py

import json
from pathlib import Path
from datetime import datetime

class BenchmarkReporter:
    def __init__(self, benchmark_dir):
        self.benchmark_dir = Path(benchmark_dir)

    def generate_html_report(self, output_file):
        """Generate interactive HTML benchmark report."""
        # Parse .benchmarks/ directory
        # Generate HTML with:
        # - Time series of performance
        # - Scenario comparisons
        # - Memory usage graphs
        # - Regression alerts
        pass

# Usage
reporter = BenchmarkReporter(".benchmarks")
reporter.generate_html_report("benchmark_report.html")
```

**Report Includes**:
- Performance history (1K/5K/10K pages)
- Regression detection (red/yellow/green)
- Memory usage trends
- Comparison to baseline
- Recommendations (if degradation detected)

---

### 4.2 GitHub Actions Integration

**Implementation**:
```yaml
# .github/workflows/benchmarks.yml

name: Benchmarks

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install -r benchmarks/requirements.txt

      - name: Run benchmarks
        run: pytest benchmarks/ --benchmark-compare=main

      - name: Generate report
        run: python benchmarks/report_generator.py

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-report
          path: benchmark_report.html

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            // Post benchmark results as PR comment
```

---

## Implementation Roadmap

### Week 1

| Day | Task | Priority | Effort |
|-----|------|----------|--------|
| Mon | 1.1: Incremental build benchmarks | 🔴 Critical | 4h |
| Tue | 1.2: Memory profiling | 🔴 Critical | 3h |
| Tue | 1.3: Regression detection | 🔴 Critical | 2h |
| Wed | 2.1: Dynamic scenario generator | 🟡 High | 3h |
| Thu | 2.2: API docs scenario | 🟡 High | 2h |
| Fri | 3.1: CPU profiling | 🟢 Medium | 2h |
| Fri | 3.2: Flame graphs | 🟢 Medium | 1h |

### Week 2

| Day | Task | Priority | Effort |
|-----|------|----------|--------|
| Mon | 4.1: Benchmark reporter | 🟢 Medium | 4h |
| Tue | 4.2: GitHub Actions CI | 🟢 Medium | 3h |
| Wed | Documentation & testing | 🟢 Medium | 3h |
| Thu-Fri | Buffer / contingency | - | - |

---

## Success Criteria

### Phase 1 ✅
- [ ] Incremental builds benchmark shows >5x speedup (or confirms bug)
- [ ] Memory tracking shows peak MB for each scenario
- [ ] Historical baseline established
- [ ] Regression detection working

### Phase 2 ✅
- [ ] Dynamic scenarios generate 1K/5K/10K pages
- [ ] API docs scenario runs without errors
- [ ] Benchmark suite covers diverse workloads

### Phase 3 ✅
- [ ] CPU profiles identify top 5 bottlenecks
- [ ] Flame graphs generate successfully
- [ ] Profiling integrated with CI

### Phase 4 ✅
- [ ] HTML reports generated and human-readable
- [ ] GitHub Actions benchmark workflow deployed
- [ ] PR comments show performance deltas

---

## Critical Outputs

After completing this plan:

1. **Incremental Build Validation**: Can measure if fixes work
2. **Performance Baselines**: Know what's normal, catch regressions
3. **Bottleneck Identification**: Flame graphs show where to optimize
4. **Regression Detection**: Automatic alerts if performance degrades
5. **CI Integration**: Benchmarks run on every push/PR

---

## Related Plans

- `plan/active/BENCHMARK_RESULTS_ANALYSIS.md` - The analysis that triggered this plan
- `plan/active/SCALE_DEGRADATION_ANALYSIS.md` - Performance degradation investigation

## Next Steps

1. Start Phase 1 immediately (incremental build benchmarking is critical)
2. Weekly syncs to assess progress and adjust priorities
3. Deploy to CI/CD by end of Phase 4
