# Continuous Performance Tracking - Implementation Plan

## Current State Analysis

### ✅ What We Have

**1. Memory Profiling Tests**
- Location: `tests/performance/test_memory_profiling.py`
- Provides: One-time measurements during test runs
- Data: RSS, Python heap, top allocators
- **Gap**: Only runs on-demand, not continuous

**2. Logger with Memory Tracking**
- Location: `bengal/utils/logger.py`
- Has: `track_memory` flag, `memory_mb`, `peak_memory_mb` fields
- Tracks: Per-phase memory deltas
- **Gap**: Data is ephemeral (printed, not persisted)

**3. Build Stats**
- Location: `bengal/utils/build_stats.py`
- Has: Page counts, timing, file counts
- **Gap**: No memory metrics, no historical tracking

**4. Documentation**
- Location: `ARCHITECTURE.md`, `README.md`
- Has: Static performance claims (100 pages = 35MB)
- **Gap**: Not automatically updated

### ❌ What We Don't Have

1. **No Metrics Persistence**: Memory/timing data disappears after build
2. **No Historical Tracking**: Can't see performance trends over time
3. **No CI Integration**: Performance not tracked across commits
4. **No Regression Detection**: Can't automatically detect slowdowns/leaks
5. **No Observability Dashboard**: Can't visualize performance
6. **Disconnected Systems**: Tests, logger, and stats don't talk to each other

---

## The Vision: Unified Performance Tracking

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Build Process                             │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐   │
│  │  Discovery │ ───▶ │  Rendering │ ───▶ │Postprocess │   │
│  └────────────┘      └────────────┘      └────────────┘   │
│         │                   │                    │          │
│         └───────────────────┴────────────────────┘          │
│                             │                                │
│                    ┌────────▼────────┐                      │
│                    │ Performance     │                      │
│                    │ Metrics         │                      │
│                    │ Collector       │                      │
│                    └────────┬────────┘                      │
└─────────────────────────────┼───────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Metrics Storage  │
                    │  (JSON/SQLite)    │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐      ┌─────▼──────┐    ┌──────▼─────┐
    │   CLI     │      │    CI      │    │  Dashboard │
    │  Report   │      │  Tracking  │    │  (Future)  │
    └───────────┘      └────────────┘    └────────────┘
```

---

## Implementation Phases

### Phase 1: Unified Metrics Collection (Week 1)

#### 1.1 Create PerformanceCollector Class

**File**: `bengal/utils/performance_collector.py`

```python
"""
Unified performance metrics collection.

Collects metrics from builds and persists them for analysis.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import psutil
import tracemalloc


@dataclass
class PhaseMetrics:
    """Metrics for a single build phase."""
    name: str
    duration_ms: float
    memory_delta_mb: float
    memory_peak_mb: float
    items_processed: int = 0


@dataclass
class BuildMetrics:
    """Complete metrics for a build."""
    # Metadata
    timestamp: str
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    
    # Build info
    page_count: int = 0
    total_pages: int = 0
    asset_count: int = 0
    
    # Overall timing
    total_duration_ms: float = 0
    
    # Overall memory
    memory_rss_mb: float = 0
    memory_heap_mb: float = 0
    memory_peak_mb: float = 0
    
    # Per-phase breakdown
    phases: List[PhaseMetrics] = field(default_factory=list)
    
    # Top allocators
    top_allocators: List[Dict[str, any]] = field(default_factory=list)
    
    # System info
    python_version: str = ""
    platform: str = ""
    cpu_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def summary_line(self) -> str:
        """One-line summary for logs."""
        return (
            f"{self.page_count} pages | "
            f"{self.total_duration_ms/1000:.2f}s | "
            f"{self.memory_rss_mb:.1f}MB RSS | "
            f"{self.memory_heap_mb:.1f}MB heap"
        )


class PerformanceCollector:
    """
    Collects and persists performance metrics.
    
    Usage:
        collector = PerformanceCollector()
        collector.start_build()
        
        with collector.phase("discovery"):
            # ... do work ...
            collector.record_items(100)
        
        metrics = collector.end_build(build_stats)
        collector.save(metrics)
    """
    
    def __init__(self, metrics_dir: Path = None):
        self.metrics_dir = metrics_dir or Path(".bengal-metrics")
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.start_time = None
        self.start_memory = None
        self.phases = []
        self.current_phase = None
        
        self.process = psutil.Process()
    
    def start_build(self):
        """Start collecting metrics for a build."""
        self.start_time = time.time()
        
        # Start memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self.start_memory = tracemalloc.get_traced_memory()[0]
        self.start_rss = self.process.memory_info().rss
    
    @contextmanager
    def phase(self, name: str):
        """Context manager for tracking a phase."""
        phase_start = time.time()
        phase_memory_start = tracemalloc.get_traced_memory()[0]
        
        self.current_phase = {'name': name, 'items': 0}
        
        try:
            yield self
        finally:
            duration_ms = (time.time() - phase_start) * 1000
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            memory_delta = (current_mem - phase_memory_start) / 1024 / 1024
            memory_peak = peak_mem / 1024 / 1024
            
            phase_metrics = PhaseMetrics(
                name=name,
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta,
                memory_peak_mb=memory_peak,
                items_processed=self.current_phase['items']
            )
            self.phases.append(phase_metrics)
            self.current_phase = None
    
    def record_items(self, count: int):
        """Record number of items processed in current phase."""
        if self.current_phase:
            self.current_phase['items'] += count
    
    def end_build(self, build_stats=None) -> BuildMetrics:
        """End collection and generate metrics."""
        total_duration = (time.time() - self.start_time) * 1000
        
        # Memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        memory_heap = (current_mem - self.start_memory) / 1024 / 1024
        memory_peak = peak_mem / 1024 / 1024
        
        current_rss = self.process.memory_info().rss
        memory_rss = (current_rss - self.start_rss) / 1024 / 1024
        
        # Top allocators
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        top_allocators = [
            {
                'file': str(stat.traceback),
                'size_mb': stat.size / 1024 / 1024,
                'count': stat.count
            }
            for stat in top_stats[:10]
        ]
        
        # Git info
        git_commit, git_branch = self._get_git_info()
        
        # Build metrics
        metrics = BuildMetrics(
            timestamp=datetime.utcnow().isoformat(),
            git_commit=git_commit,
            git_branch=git_branch,
            page_count=build_stats.regular_pages if build_stats else 0,
            total_pages=build_stats.total_pages if build_stats else 0,
            asset_count=len(build_stats.assets) if build_stats else 0,
            total_duration_ms=total_duration,
            memory_rss_mb=memory_rss,
            memory_heap_mb=memory_heap,
            memory_peak_mb=memory_peak,
            phases=self.phases,
            top_allocators=top_allocators,
            python_version=sys.version.split()[0],
            platform=sys.platform,
            cpu_count=os.cpu_count() or 0
        )
        
        return metrics
    
    def save(self, metrics: BuildMetrics):
        """Save metrics to disk."""
        # Save individual build
        filename = f"build_{metrics.timestamp.replace(':', '-')}.json"
        filepath = self.metrics_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        # Append to history
        history_file = self.metrics_dir / "history.jsonl"
        with open(history_file, 'a') as f:
            f.write(json.dumps(metrics.to_dict()) + '\n')
    
    def _get_git_info(self) -> tuple:
        """Get current git commit and branch."""
        try:
            import subprocess
            commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            return commit[:8], branch
        except:
            return None, None
```

#### 1.2 Integrate with BuildOrchestrator

**File**: `bengal/orchestration/build.py`

```python
# Add at top
from bengal.utils.performance_collector import PerformanceCollector

class BuildOrchestrator:
    def build(self, parallel=True, incremental=False):
        # Initialize collector
        collector = PerformanceCollector()
        collector.start_build()
        
        # Wrap existing phases
        with collector.phase("discovery"):
            pages, sections = discover_content(...)
            collector.record_items(len(pages))
        
        with collector.phase("rendering"):
            render_pages(...)
            collector.record_items(len(pages))
        
        # ... etc for all phases ...
        
        # At end
        metrics = collector.end_build(stats)
        collector.save(metrics)
        
        # Optionally print summary
        if verbose:
            print(f"\n📊 Performance: {metrics.summary_line()}")
        
        return stats
```

---

### Phase 2: CLI Integration (Week 1)

#### 2.1 Add Performance Report Command

**File**: `bengal/cli.py`

```python
@cli.command()
@click.option('--last', '-n', default=10, help='Show last N builds')
@click.option('--format', type=click.Choice(['table', 'json', 'chart']), default='table')
def perf(last, format):
    """Show performance metrics and trends."""
    from bengal.utils.performance_report import PerformanceReport
    
    report = PerformanceReport()
    report.show(last=last, format=format)
```

#### 2.2 Create Performance Report

**File**: `bengal/utils/performance_report.py`

```python
class PerformanceReport:
    """Generate performance reports from collected metrics."""
    
    def show(self, last=10, format='table'):
        """Show performance summary."""
        metrics = self._load_recent(last)
        
        if format == 'table':
            self._print_table(metrics)
        elif format == 'json':
            print(json.dumps([m.to_dict() for m in metrics], indent=2))
        elif format == 'chart':
            self._print_chart(metrics)
    
    def _print_table(self, metrics):
        """Print as ASCII table."""
        print("\n📊 Performance History\n")
        print(f"{'Date':<20} {'Pages':<8} {'Time':<10} {'RSS':<12} {'Heap':<12}")
        print("─" * 70)
        
        for m in metrics:
            date = m.timestamp[:19].replace('T', ' ')
            print(
                f"{date:<20} "
                f"{m.page_count:<8} "
                f"{m.total_duration_ms/1000:>8.2f}s "
                f"{m.memory_rss_mb:>10.1f}MB "
                f"{m.memory_heap_mb:>10.1f}MB"
            )
        
        # Show trends
        if len(metrics) >= 2:
            first, last = metrics[0], metrics[-1]
            
            time_change = (last.total_duration_ms - first.total_duration_ms) / first.total_duration_ms * 100
            mem_change = (last.memory_rss_mb - first.memory_rss_mb) / first.memory_rss_mb * 100
            
            print(f"\n📈 Trends ({len(metrics)} builds)")
            print(f"  Time: {time_change:+.1f}%")
            print(f"  Memory: {mem_change:+.1f}%")
```

---

### Phase 3: CI Integration (Week 2)

#### 3.1 GitHub Actions Workflow

**File**: `.github/workflows/performance.yml`

```yaml
name: Performance Tracking

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  track-performance:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Run performance tests
        run: |
          pytest tests/performance/test_memory_profiling.py -v --json-report --json-report-file=perf-report.json
      
      - name: Extract metrics
        run: |
          python scripts/extract_perf_metrics.py perf-report.json > metrics.json
      
      - name: Upload metrics
        uses: actions/upload-artifact@v3
        with:
          name: performance-metrics
          path: metrics.json
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const metrics = JSON.parse(fs.readFileSync('metrics.json', 'utf8'));
            
            const body = `## 📊 Performance Impact
            
            | Metric | Before | After | Change |
            |--------|--------|-------|--------|
            | 100 pages (RSS) | ${metrics.baseline.rss_mb}MB | ${metrics.current.rss_mb}MB | ${metrics.change.rss_pct}% |
            | Build time | ${metrics.baseline.time_s}s | ${metrics.current.time_s}s | ${metrics.change.time_pct}% |
            
            ${metrics.change.rss_pct > 10 ? '⚠️ **Significant memory increase detected**' : '✅ Memory usage within acceptable range'}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

---

### Phase 4: Regression Detection (Week 2)

#### 4.1 Automated Threshold Checking

**File**: `bengal/utils/performance_validator.py`

```python
class PerformanceValidator:
    """Validate performance metrics against thresholds."""
    
    THRESHOLDS = {
        'memory_rss_per_page_mb': 0.5,  # Max 0.5MB RSS per page
        'time_per_page_ms': 50,          # Max 50ms per page
        'memory_growth_pct': 10,         # Max 10% memory growth
        'time_growth_pct': 20,           # Max 20% time growth
    }
    
    def validate(self, current: BuildMetrics, baseline: BuildMetrics = None):
        """Validate metrics against thresholds."""
        issues = []
        
        # Per-page memory
        memory_per_page = current.memory_rss_mb / current.page_count
        if memory_per_page > self.THRESHOLDS['memory_rss_per_page_mb']:
            issues.append(f"Memory per page ({memory_per_page:.2f}MB) exceeds threshold")
        
        # Per-page time
        time_per_page = current.total_duration_ms / current.page_count
        if time_per_page > self.THRESHOLDS['time_per_page_ms']:
            issues.append(f"Time per page ({time_per_page:.1f}ms) exceeds threshold")
        
        # Growth (if baseline provided)
        if baseline:
            mem_growth = (current.memory_rss_mb - baseline.memory_rss_mb) / baseline.memory_rss_mb * 100
            if mem_growth > self.THRESHOLDS['memory_growth_pct']:
                issues.append(f"Memory regression: +{mem_growth:.1f}%")
            
            time_growth = (current.total_duration_ms - baseline.total_duration_ms) / baseline.total_duration_ms * 100
            if time_growth > self.THRESHOLDS['time_growth_pct']:
                issues.append(f"Time regression: +{time_growth:.1f}%")
        
        return issues
```

---

## Summary: Complete Tracking System

### Data Flow

```
1. Build runs → PerformanceCollector gathers metrics
2. Metrics saved to .bengal-metrics/history.jsonl
3. CLI: `bengal perf` shows trends
4. CI: Automatic tracking on every commit
5. PR: Performance impact comment
6. Alerts: Regression detection
```

### Commands

```bash
# Show recent performance
bengal perf

# Show last 20 builds
bengal perf --last 20

# JSON output
bengal perf --format json

# Chart view
bengal perf --format chart

# Compare two builds
bengal perf compare HEAD~5 HEAD
```

### Files Created

```
.bengal-metrics/
├── history.jsonl          # All builds (append-only)
├── build_2025-10-05.json  # Individual builds
└── summary.json           # Latest summary

scripts/
└── extract_perf_metrics.py  # CI helper

.github/workflows/
└── performance.yml        # CI tracking
```

---

## Implementation Timeline

| Week | Tasks | Outcome |
|------|-------|---------|
| **1** | PerformanceCollector, CLI integration | Can track builds locally |
| **2** | CI integration, regression detection | Automated tracking |
| **3** | Dashboard (optional), visualization | Historical analysis |

---

## Next Steps

1. **Implement Phase 1** (PerformanceCollector)
2. **Test locally** (`bengal build` should save metrics)
3. **Add CLI command** (`bengal perf`)
4. **Set up CI** (GitHub Actions)
5. **Monitor** (Watch for regressions)

This creates a **complete observability pipeline** from build → metrics → analysis → alerting.

