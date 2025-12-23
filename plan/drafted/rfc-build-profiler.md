# RFC: Build Profiler ("Why Is This Slow?")

**Status**: Draft  
**Created**: 2025-12-08  
**Revised**: 2025-01-XX  
**Author**: AI Assistant  
**Confidence**: 85% 🟢
**Priority**: P2 (Medium)  

---

## Executive Summary

Enhance Bengal's existing performance infrastructure with per-page and per-shortcode timing, rich terminal output, and baseline comparison capabilities. This builds on existing phase timing (`BuildStats`), historical tracking (`PerformanceCollector`), and template profiling (`TemplateProfiler`) to provide actionable insights into build performance.

---

## Problem Statement

### Current State

Bengal already provides substantial performance visibility:

**✅ Existing Capabilities**:
- **Phase timing**: `BuildStats` tracks `discovery_time_ms`, `taxonomy_time_ms`, `rendering_time_ms`, `assets_time_ms`, `postprocess_time_ms` (see `bengal/orchestration/stats/models.py:69-74`)
- **Historical tracking**: `PerformanceCollector` saves metrics to `.bengal/metrics/history.jsonl` (see `bengal/utils/performance_collector.py`)
- **Trend analysis**: `PerformanceReport` compares builds and detects regressions (see `bengal/utils/performance_report.py`)
- **Template profiling**: `TemplateProfiler` tracks template render times and function calls (see `bengal/rendering/template_profiler.py`)
- **Python profiling**: `--perf-profile` flag for cProfile integration (see `bengal/cli/commands/build.py:76-78`)

**❌ Missing Capabilities**:
- **Per-page timing**: Cannot identify which individual pages are slow
- **Shortcode timing**: No visibility into which shortcodes are expensive
- **Rich output**: Phase timing exists but lacks visual formatting and recommendations
- **Baseline comparison**: Historical tracking exists but no explicit baseline save/compare workflow
- **Actionable recommendations**: No automated suggestions based on profile data

### Pain Points

1. **Slow page mystery**: Phase timing shows "rendering took 10s" but which page(s) caused it?
2. **Shortcode culprits**: That `diagram` shortcode might be expensive, but no data to confirm
3. **Baseline workflow**: Want to compare current build to a known-good baseline, not just previous build
4. **Output clarity**: Phase timing exists in `BuildStats` but needs rich formatting for quick insights
5. **Recommendations**: Users need actionable suggestions, not just raw data

### User Impact

While Bengal has good performance infrastructure, users still struggle to answer "which page/shortcode is slow?" and "is this build slower than my baseline?" The missing pieces prevent efficient performance optimization workflows.

---

## Goals & Non-Goals

**Goals**:
- ✅ **Per-page timing**: Track parse + render time for each individual page
- ✅ **Shortcode timing**: Track performance of each shortcode type (calls, total time, avg time)
- ✅ **Rich terminal output**: Visual formatting with bars, colors, and clear hierarchy
- ✅ **Baseline comparison**: Save/load baseline profiles and compare current build
- ✅ **Actionable recommendations**: Automated suggestions based on profile data

**Non-Goals**:
- ❌ Phase-by-phase timing (already exists in `BuildStats`)
- ❌ Historical trend tracking (already exists in `PerformanceReport`)
- ❌ Template profiling (already exists in `TemplateProfiler`)
- ❌ Line-level Python profiling (use `--perf-profile` with cProfile)
- ❌ Memory profiling (already tracked in `PerformanceCollector`)
- ❌ Real-time monitoring (batch analysis only)

---

## Architecture Impact

**Affected Subsystems**:
- **Orchestration** (`bengal/orchestration/`): Add per-page timing instrumentation
- **Rendering** (`bengal/rendering/`): Add shortcode timing instrumentation
- **CLI** (`bengal/cli/`): Add `--timing-profile` flag (note: `--profile` already used for build profiles)
- **Stats** (`bengal/orchestration/stats/`): Extend `BuildStats` with per-page/shortcode data

**Integration Points**:
- **Build on existing**: `PerformanceCollector` for storage, `BuildStats` for phase timing
- **Extend existing**: Add per-page/shortcode fields to `BuildStats`
- **New components**: Reporter for rich output, analyzer for recommendations

**New Components**:
- `bengal/profiling/page_timing.py` - Per-page timing collector
- `bengal/profiling/shortcode_timing.py` - Shortcode timing collector
- `bengal/profiling/reporter.py` - Rich terminal output formatter
- `bengal/profiling/analyzer.py` - Recommendations engine
- `bengal/profiling/baseline.py` - Baseline save/load/compare

---

## Proposed CLI Interface

**Note**: `--profile` is already used for build profiles (`dev`, `writer`, `theme-dev`). Use `--timing-profile` for performance profiling.

### Basic Profiling

```bash
# Run build with timing profile
bengal build --timing-profile

# Output:
#
# ⏱️  Build Profile (2.34s total)
#
# Phase Breakdown:
# ├─ Discovery       0.12s  (5%)   ████
# ├─ Parsing         0.78s  (33%)  ████████████████
# ├─ Taxonomies      0.15s  (6%)   ██████
# ├─ Rendering       1.20s  (51%)  █████████████████████████
# └─ Assets          0.09s  (4%)   ███
#
# 🐢 Slowest Pages:
# 1. api/reference.md          0.45s (parse: 0.12s, render: 0.33s)
# 2. changelog.md              0.23s (parse: 0.08s, render: 0.15s)
# 3. docs/advanced/plugins.md  0.18s (parse: 0.05s, render: 0.13s)
#
# 🔧 Recommendations:
# • api/reference.md: Consider splitting (4,521 lines, 0.45s build time)
# • Shortcode 'diagram' took 0.6s total across 12 uses (50ms avg)
```

### Detailed Profiling

```bash
# Full breakdown including shortcodes
bengal build --timing-profile --verbose

# Output includes:
#
# Shortcode Performance:
# ├─ diagram        12 calls   0.60s total   50ms avg
# ├─ code-tabs       8 calls   0.12s total   15ms avg
# ├─ admonition     45 calls   0.05s total    1ms avg
# └─ include         3 calls   0.02s total    7ms avg
#
# Note: Template performance available via --profile-templates
```

### Baseline Comparison

```bash
# Save current build as baseline
bengal build --timing-profile --save-baseline

# Compare against baseline
bengal build --timing-profile --compare-baseline

# Output:
#
# ⏱️  Build Comparison (vs baseline)
#
#                    Baseline    Current     Change
# Total              2.10s       2.34s       +11% ⚠️
# ├─ Discovery       0.11s       0.12s       +9%
# ├─ Parsing         0.72s       0.78s       +8%
# ├─ Taxonomies      0.14s       0.15s       +7%
# ├─ Rendering       1.05s       1.20s       +14% ⚠️
# └─ Assets          0.08s       0.09s       +12%
#
# 📈 New slow pages since baseline:
# • docs/new-feature.md (not in baseline)
# • api/reference.md: +0.15s (was 0.30s, now 0.45s)
```

### Integration with Existing Commands

```bash
# Historical tracking (already exists)
bengal perf show --last 10

# Template profiling (already exists)
bengal build --profile-templates

# Python profiling (already exists)
bengal build --perf-profile
```

---

## Detailed Design

### Extend BuildStats

```python
# bengal/orchestration/stats/models.py
@dataclass
class BuildStats:
    # ... existing fields ...

    # New: Per-page timing (only populated when --timing-profile enabled)
    page_timings: dict[str, PageTiming] = field(default_factory=dict)

    # New: Shortcode timing (only populated when --timing-profile enabled)
    shortcode_timings: dict[str, ShortcodeTiming] = field(default_factory=dict)

@dataclass
class PageTiming:
    """Timing data for a single page."""
    path: str
    parse_time_ms: float = 0
    render_time_ms: float = 0

    @property
    def total_time_ms(self) -> float:
        return self.parse_time_ms + self.render_time_ms

@dataclass
class ShortcodeTiming:
    """Timing data for a shortcode type."""
    name: str
    call_count: int = 0
    total_time_ms: float = 0

    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / self.call_count if self.call_count > 0 else 0
```

### Per-Page Timing Collector

```python
# bengal/profiling/page_timing.py
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

class PageTimingCollector:
    """Collect per-page timing data."""

    def __init__(self, stats: BuildStats):
        self.stats = stats
        self._active_pages: dict[str, float] = {}  # page_path -> start_time

    @contextmanager
    def measure_parse(self, page_path: str):
        """Measure page parsing time."""
        start = perf_counter()
        try:
            yield
        finally:
            duration_ms = (perf_counter() - start) * 1000
            if page_path not in self.stats.page_timings:
                from bengal.orchestration.stats.models import PageTiming
                self.stats.page_timings[page_path] = PageTiming(path=page_path)
            self.stats.page_timings[page_path].parse_time_ms = duration_ms

    @contextmanager
    def measure_render(self, page_path: str):
        """Measure page rendering time."""
        start = perf_counter()
        try:
            yield
        finally:
            duration_ms = (perf_counter() - start) * 1000
            if page_path not in self.stats.page_timings:
                from bengal.orchestration.stats.models import PageTiming
                self.stats.page_timings[page_path] = PageTiming(path=page_path)
            self.stats.page_timings[page_path].render_time_ms = duration_ms
```

### Shortcode Timing Collector

```python
# bengal/profiling/shortcode_timing.py
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

class ShortcodeTimingCollector:
    """Collect shortcode timing data."""

    def __init__(self, stats: BuildStats):
        self.stats = stats

    @contextmanager
    def measure(self, shortcode_name: str):
        """Measure shortcode execution time."""
        start = perf_counter()
        try:
            yield
        finally:
            duration_ms = (perf_counter() - start) * 1000
            if shortcode_name not in self.stats.shortcode_timings:
                from bengal.orchestration.stats.models import ShortcodeTiming
                self.stats.shortcode_timings[shortcode_name] = ShortcodeTiming(name=shortcode_name)

            timing = self.stats.shortcode_timings[shortcode_name]
            timing.call_count += 1
            timing.total_time_ms += duration_ms
```

### Instrumentation Points

```python
# bengal/orchestration/build/__init__.py
class BuildOrchestrator:
    def build(self, ..., timing_profile: bool = False, ...) -> BuildStats:
        # ... existing code ...

        # Initialize timing collectors if enabled
        page_collector = None
        shortcode_collector = None
        if timing_profile:
            from bengal.profiling.page_timing import PageTimingCollector
            from bengal.profiling.shortcode_timing import ShortcodeTimingCollector
            page_collector = PageTimingCollector(self.stats)
            shortcode_collector = ShortcodeTimingCollector(self.stats)

        # ... existing phase code ...

        # Parsing phase (add per-page timing)
        for page in pages:
            if page_collector:
                with page_collector.measure_parse(str(page.source_path)):
                    self.parse_page(page)
            else:
                self.parse_page(page)

        # Rendering phase (add per-page timing)
        for page in pages:
            if page_collector:
                with page_collector.measure_render(str(page.source_path)):
                    self.render_page(page)
            else:
                self.render_page(page)

        # ... rest of build ...

# bengal/rendering/shortcodes.py (or wherever shortcodes are processed)
class ShortcodeProcessor:
    def __init__(self, shortcode_collector: ShortcodeTimingCollector | None = None):
        self.shortcode_collector = shortcode_collector

    def process(self, name: str, content: str, **kwargs) -> str:
        if self.shortcode_collector:
            with self.shortcode_collector.measure(name):
                return self._do_process(name, content, **kwargs)
        return self._do_process(name, content, **kwargs)
```

### Profile Analyzer

```python
# bengal/profiling/analyzer.py
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats, PageTiming, ShortcodeTiming

@dataclass
class Recommendation:
    """A performance recommendation."""
    severity: str  # "warning", "info"
    target: str
    message: str
    suggestion: str

class ProfileAnalyzer:
    """Analyze BuildStats and generate recommendations."""

    def __init__(self, stats: BuildStats):
        self.stats = stats

    def get_slowest_pages(self, n: int = 5) -> list[tuple[str, float]]:
        """Get slowest pages by total time."""
        pages = [
            (path, timing.total_time_ms / 1000)  # Convert to seconds
            for path, timing in self.stats.page_timings.items()
        ]
        return sorted(pages, key=lambda x: -x[1])[:n]

    def get_shortcode_stats(self) -> list[ShortcodeTiming]:
        """Get shortcode statistics sorted by total time."""
        return sorted(
            self.stats.shortcode_timings.values(),
            key=lambda x: -x.total_time_ms
        )

    def generate_recommendations(self) -> list[Recommendation]:
        """Generate actionable recommendations."""
        recs = []

        # Check for slow pages
        slow_pages = self.get_slowest_pages(3)
        for page_path, duration_s in slow_pages:
            if duration_s > 0.5:  # >500ms
                timing = self.stats.page_timings[page_path]
                recs.append(Recommendation(
                    severity="warning",
                    target=page_path,
                    message=f"Page takes {duration_s:.2f}s to build",
                    suggestion=f"Consider splitting (parse: {timing.parse_time_ms:.0f}ms, render: {timing.render_time_ms:.0f}ms)",
                ))

        # Check for expensive shortcodes
        for sc in self.get_shortcode_stats():
            if sc.avg_time_ms > 100:  # >100ms average
                recs.append(Recommendation(
                    severity="info",
                    target=f"shortcode:{sc.name}",
                    message=f"Shortcode '{sc.name}' averages {sc.avg_time_ms:.0f}ms per call",
                    suggestion=f"Consider caching or optimizing ({sc.call_count} calls, {sc.total_time_ms:.0f}ms total)",
                ))

        # Check phase balance (use existing BuildStats phase timing)
        total_time_ms = self.stats.build_time_ms
        if total_time_ms > 0:
            render_pct = (self.stats.rendering_time_ms / total_time_ms) * 100
            if render_pct > 70:
                recs.append(Recommendation(
                    severity="info",
                    target="rendering",
                    message=f"Rendering takes {render_pct:.0f}% of build time",
                    suggestion="Check template complexity or enable caching",
                ))

        return recs
```

### Baseline Storage

```python
# bengal/profiling/baseline.py
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

class BaselineManager:
    """Manage baseline profiles for comparison."""

    def __init__(self, cache_dir: Path):
        self.baseline_path = cache_dir / "profiles" / "baseline.json"
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, stats: BuildStats) -> None:
        """Save current stats as baseline."""
        # Extract relevant fields for baseline
        baseline_data = {
            "build_time_ms": stats.build_time_ms,
            "discovery_time_ms": stats.discovery_time_ms,
            "taxonomy_time_ms": stats.taxonomy_time_ms,
            "rendering_time_ms": stats.rendering_time_ms,
            "assets_time_ms": stats.assets_time_ms,
            "postprocess_time_ms": stats.postprocess_time_ms,
            "page_timings": {
                path: {
                    "parse_time_ms": timing.parse_time_ms,
                    "render_time_ms": timing.render_time_ms,
                }
                for path, timing in stats.page_timings.items()
            },
            "shortcode_timings": {
                name: {
                    "call_count": timing.call_count,
                    "total_time_ms": timing.total_time_ms,
                }
                for name, timing in stats.shortcode_timings.items()
            },
        }
        self.baseline_path.write_text(json.dumps(baseline_data, indent=2))

    def load(self) -> dict | None:
        """Load baseline data."""
        if self.baseline_path.exists():
            return json.loads(self.baseline_path.read_text())
        return None
```

### Reporter

```python
# bengal/profiling/reporter.py
from rich.console import Console
from rich.table import Table
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

class ProfileReporter:
    """Format and display profile results using Rich."""

    def __init__(self, stats: BuildStats, baseline: dict | None = None):
        self.stats = stats
        self.baseline = baseline
        self.analyzer = ProfileAnalyzer(stats)
        self.console = Console()

    def print_summary(self, verbose: bool = False):
        """Print profile summary."""
        total_s = self.stats.build_time_ms / 1000
        self.console.print(f"\n⏱️  [bold]Build Profile[/bold] ({total_s:.2f}s total)\n")

        # Phase breakdown (using existing BuildStats fields)
        self.console.print("[bold]Phase Breakdown:[/bold]")
        phases = [
            ("Discovery", self.stats.discovery_time_ms),
            ("Parsing", self.stats.taxonomy_time_ms),  # Note: parsing time may need separate tracking
            ("Taxonomies", self.stats.taxonomy_time_ms),
            ("Rendering", self.stats.rendering_time_ms),
            ("Assets", self.stats.assets_time_ms),
            ("Postprocess", self.stats.postprocess_time_ms),
        ]

        for name, time_ms in phases:
            if time_ms > 0:
                time_s = time_ms / 1000
                pct = (time_ms / self.stats.build_time_ms * 100) if self.stats.build_time_ms > 0 else 0
                bar = "█" * int(pct / 2)

                delta = ""
                if self.baseline:
                    baseline_time_ms = self.baseline.get(f"{name.lower()}_time_ms", 0)
                    if baseline_time_ms > 0:
                        change = ((time_ms - baseline_time_ms) / baseline_time_ms) * 100
                        if abs(change) > 10:
                            color = "red" if change > 0 else "green"
                            delta = f" [{color}]{change:+.0f}%[/]"

                self.console.print(
                    f"├─ {name:<12} {time_s:.2f}s  ({pct:.0f}%)  {bar}{delta}"
                )

        # Slowest pages
        if self.stats.page_timings:
            self.console.print("\n[bold]🐢 Slowest Pages:[/bold]")
            slowest = self.analyzer.get_slowest_pages(5)
            for i, (page_path, duration_s) in enumerate(slowest, 1):
                timing = self.stats.page_timings[page_path]
                self.console.print(
                    f"{i}. {page_path:<40} {duration_s:.2f}s "
                    f"(parse: {timing.parse_time_ms:.0f}ms, render: {timing.render_time_ms:.0f}ms)"
                )

        # Shortcode performance (if verbose)
        if verbose and self.stats.shortcode_timings:
            self.console.print("\n[bold]Shortcode Performance:[/bold]")
            for sc in self.analyzer.get_shortcode_stats()[:10]:  # Top 10
                self.console.print(
                    f"├─ {sc.name:<20} {sc.call_count:>4} calls  "
                    f"{sc.total_time_ms:>6.0f}ms total  {sc.avg_time_ms:>5.0f}ms avg"
                )

        # Recommendations
        recs = self.analyzer.generate_recommendations()
        if recs:
            self.console.print("\n[bold]🔧 Recommendations:[/bold]")
            for rec in recs:
                icon = "⚠️" if rec.severity == "warning" else "ℹ️"
                self.console.print(f"{icon} {rec.target}: {rec.suggestion}")
```

---

## Configuration

```toml
# bengal.toml
[profiling]
# Enable timing profile by default (can override with --timing-profile flag)
enabled = false

# Warning thresholds
slow_page_threshold_ms = 500      # milliseconds
slow_shortcode_threshold_ms = 100 # milliseconds

# Baseline management
baseline_auto_save = false  # Auto-save after each build
```

**Note**: Historical tracking is already configured via `PerformanceCollector` and stored in `.bengal/metrics/`.

---

## Implementation Plan

### Phase 1: Data Collection (1 week)
- [ ] Extend `BuildStats` with `page_timings` and `shortcode_timings` fields
- [ ] Implement `PageTimingCollector` with parse/render instrumentation
- [ ] Implement `ShortcodeTimingCollector` with shortcode instrumentation
- [ ] Add instrumentation points in build orchestrator and shortcode processor
- [ ] CLI `--timing-profile` flag (note: `--profile` already used)

### Phase 2: Analysis & Reporting (1 week)
- [ ] Implement `ProfileAnalyzer` for recommendations
- [ ] Implement `ProfileReporter` with Rich output formatting
- [ ] Integrate with existing `BuildStats` phase timing
- [ ] Test with various site sizes

### Phase 3: Baseline Comparison (3 days)
- [ ] Implement `BaselineManager` for save/load
- [ ] Add `--save-baseline` and `--compare-baseline` flags
- [ ] Delta calculation and display
- [ ] Integration with reporter

### Phase 4: Polish & Integration (2 days)
- [ ] Configuration options in `bengal.toml`
- [ ] Documentation updates
- [ ] Performance overhead testing (<1% when disabled)
- [ ] Integration tests

---

## Success Criteria

- [ ] `bengal build --timing-profile` shows phase breakdown with visual bars
- [ ] Per-page timing identifies slowest pages with >90% accuracy
- [ ] Shortcode timing tracks all shortcode calls correctly
- [ ] Baseline comparison shows meaningful deltas
- [ ] Recommendations are actionable and accurate
- [ ] <1% overhead when `--timing-profile` disabled
- [ ] Integrates cleanly with existing `PerformanceCollector` and `BuildStats`

---

## References

### Existing Bengal Infrastructure
- `bengal/orchestration/stats/models.py` - `BuildStats` with phase timing
- `bengal/utils/performance_collector.py` - Historical metrics collection
- `bengal/utils/performance_report.py` - Trend analysis and comparison
- `bengal/rendering/template_profiler.py` - Template-level profiling
- `bengal/cli/commands/build.py` - `--perf-profile` and `--profile-templates` flags

### External References
- [Python cProfile](https://docs.python.org/3/library/profile.html)
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [webpack-bundle-analyzer](https://github.com/webpack-contrib/webpack-bundle-analyzer)
- [Gatsby Build Profiling](https://www.gatsbyjs.com/docs/profiling-site-performance-with-react-profiler/)

## Notes

- This RFC builds on existing performance infrastructure rather than creating parallel systems
- Phase timing already exists; this adds per-page and per-shortcode granularity
- Historical tracking exists; this adds explicit baseline comparison workflow
- Template profiling exists separately; this focuses on build-level performance
- CLI naming: `--timing-profile` avoids conflict with existing `--profile` flag
