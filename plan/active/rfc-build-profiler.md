# RFC: Build Profiler ("Why Is This Slow?")

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 90% 🟢

---

## Executive Summary

Add built-in build profiling to Bengal that answers "why is this slow?" with actionable insights. Show timing breakdowns by phase, identify expensive pages/shortcodes, and track performance over time.

---

## Problem Statement

### Current State

When builds are slow, Bengal provides minimal visibility:
- Total build time is logged
- No breakdown by phase
- No identification of expensive pages
- No historical tracking

**Evidence**:
- `bengal/orchestration/build_orchestrator.py`: Logs total time only
- No profiling infrastructure in codebase

### Pain Points

1. **Black box builds**: "It took 30s" but why?
2. **Slow page mystery**: One page takes 10x longer but which one?
3. **Regression blindness**: Build got slower but when?
4. **Shortcode culprits**: That `diagram` shortcode might be expensive
5. **No baseline**: Is 30s normal for this site?

### User Impact

Users can't optimize what they can't measure. Performance degrades gradually, and by the time it's noticeable, the cause is buried in history.

---

## Goals & Non-Goals

**Goals**:
- Phase-by-phase timing breakdown
- Per-page timing with outlier detection
- Shortcode/filter performance tracking
- Historical trend tracking
- Actionable recommendations

**Non-Goals**:
- Line-level Python profiling (use cProfile)
- Memory profiling (separate concern)
- Real-time monitoring (batch analysis)

---

## Architecture Impact

**Affected Subsystems**:
- **Orchestration** (`bengal/orchestration/`): Instrumentation points
- **Rendering** (`bengal/rendering/`): Template/shortcode timing
- **CLI** (`bengal/cli/`): Profile command and flags
- **Cache** (`bengal/cache/`): Profile data storage

**New Components**:
- `bengal/profiling/` - Profiling infrastructure
- `bengal/profiling/collector.py` - Data collection
- `bengal/profiling/analyzer.py` - Analysis and recommendations
- `bengal/profiling/reporter.py` - Output formatting

---

## Proposed CLI Interface

### Basic Profiling

```bash
# Run build with profiling
bengal build --profile

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
# 1. api/reference.md          0.45s (parsed + rendered)
# 2. changelog.md              0.23s
# 3. docs/advanced/plugins.md  0.18s
# 
# 🔧 Recommendations:
# • api/reference.md: Consider splitting (4,521 lines)
# • Shortcode 'diagram' took 0.6s total across 12 uses
```

### Detailed Profiling

```bash
# Full breakdown including shortcodes
bengal build --profile --verbose

# Output includes:
# 
# Shortcode Performance:
# ├─ diagram        12 calls   0.60s total   50ms avg
# ├─ code-tabs       8 calls   0.12s total   15ms avg
# ├─ admonition     45 calls   0.05s total    1ms avg
# └─ include         3 calls   0.02s total    7ms avg
# 
# Template Performance:
# ├─ doc.html       89 renders  0.89s total   10ms avg
# ├─ api.html       42 renders  0.35s total    8ms avg
# └─ home.html       1 render   0.02s total   20ms avg
```

### Profile Comparison

```bash
# Compare against baseline
bengal build --profile --compare

# Output:
# 
# ⏱️  Build Comparison
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

### Save Baseline

```bash
# Save current profile as baseline
bengal build --profile --save-baseline

# Baselines stored in .bengal/profiles/
```

### Profile History

```bash
# Show profile history
bengal profile history

# Output:
# 
# Build History (last 10)
# 
# Date                 Total    Pages   Δ
# 2024-12-08 14:30    2.34s    156     +0.24s ⚠️
# 2024-12-08 10:15    2.10s    154     +0.02s
# 2024-12-07 16:45    2.08s    154     -
# 2024-12-07 09:20    2.12s    153     +0.04s
# ...
```

---

## Detailed Design

### Profiler Context Manager

```python
# bengal/profiling/collector.py
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
import threading

@dataclass
class ProfileEvent:
    name: str
    phase: str
    start: float
    end: float
    metadata: dict = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        return self.end - self.start

@dataclass
class BuildProfile:
    events: list[ProfileEvent] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    page_count: int = 0
    
    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time
    
    def get_phase_duration(self, phase: str) -> float:
        return sum(e.duration for e in self.events if e.phase == phase)
    
    def get_slowest_pages(self, n: int = 5) -> list[tuple[str, float]]:
        page_times = {}
        for e in self.events:
            if e.phase in ("parse", "render") and "page" in e.metadata:
                page = e.metadata["page"]
                page_times[page] = page_times.get(page, 0) + e.duration
        return sorted(page_times.items(), key=lambda x: -x[1])[:n]


class ProfileCollector:
    """Thread-safe profile data collector."""
    
    _instance: 'ProfileCollector | None' = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.profile = BuildProfile()
        self._event_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'ProfileCollector':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @contextmanager
    def measure(self, name: str, phase: str, **metadata):
        """Context manager to measure a code block."""
        start = perf_counter()
        try:
            yield
        finally:
            end = perf_counter()
            event = ProfileEvent(
                name=name,
                phase=phase,
                start=start,
                end=end,
                metadata=metadata,
            )
            with self._event_lock:
                self.profile.events.append(event)
    
    def record(self, name: str, phase: str, duration: float, **metadata):
        """Record a pre-measured event."""
        event = ProfileEvent(
            name=name,
            phase=phase,
            start=0,
            end=duration,
            metadata=metadata,
        )
        with self._event_lock:
            self.profile.events.append(event)
```

### Instrumentation Points

```python
# bengal/orchestration/build_orchestrator.py
from bengal.profiling import ProfileCollector

class BuildOrchestrator:
    def build(self, profile: bool = False):
        collector = ProfileCollector.get_instance() if profile else None
        
        if collector:
            collector.profile.start_time = perf_counter()
        
        # Discovery phase
        with self._maybe_measure(collector, "discovery", "discovery"):
            pages = self.discover_content()
        
        # Parsing phase
        with self._maybe_measure(collector, "parsing", "parse"):
            for page in pages:
                with self._maybe_measure(collector, f"parse:{page.path}", "parse", page=page.path):
                    self.parse_page(page)
        
        # Taxonomy phase
        with self._maybe_measure(collector, "taxonomies", "taxonomy"):
            self.build_taxonomies()
        
        # Rendering phase
        with self._maybe_measure(collector, "rendering", "render"):
            for page in pages:
                with self._maybe_measure(collector, f"render:{page.path}", "render", page=page.path):
                    self.render_page(page)
        
        # Asset phase
        with self._maybe_measure(collector, "assets", "assets"):
            self.process_assets()
        
        if collector:
            collector.profile.end_time = perf_counter()
            collector.profile.page_count = len(pages)
        
        return collector.profile if collector else None
    
    @contextmanager
    def _maybe_measure(self, collector, name, phase, **metadata):
        if collector:
            with collector.measure(name, phase, **metadata):
                yield
        else:
            yield
```

### Shortcode Profiling

```python
# bengal/rendering/shortcodes.py
class ShortcodeProcessor:
    def __init__(self, collector: ProfileCollector | None = None):
        self.collector = collector
    
    def process(self, name: str, content: str, **kwargs) -> str:
        if self.collector:
            with self.collector.measure(f"shortcode:{name}", "shortcode", shortcode=name):
                return self._do_process(name, content, **kwargs)
        return self._do_process(name, content, **kwargs)
```

### Profile Analyzer

```python
# bengal/profiling/analyzer.py

class ProfileAnalyzer:
    """Analyze profile data and generate recommendations."""
    
    def __init__(self, profile: BuildProfile):
        self.profile = profile
    
    def get_phase_breakdown(self) -> dict[str, PhaseStats]:
        """Get timing breakdown by phase."""
        phases = {}
        for phase in ["discovery", "parse", "taxonomy", "render", "assets"]:
            duration = self.profile.get_phase_duration(phase)
            phases[phase] = PhaseStats(
                duration=duration,
                percentage=duration / self.profile.total_duration * 100,
            )
        return phases
    
    def get_shortcode_stats(self) -> list[ShortcodeStats]:
        """Get shortcode performance statistics."""
        shortcode_events = [e for e in self.profile.events if e.phase == "shortcode"]
        
        stats = {}
        for e in shortcode_events:
            name = e.metadata.get("shortcode", "unknown")
            if name not in stats:
                stats[name] = ShortcodeStats(name=name, calls=0, total_time=0)
            stats[name].calls += 1
            stats[name].total_time += e.duration
        
        for s in stats.values():
            s.avg_time = s.total_time / s.calls
        
        return sorted(stats.values(), key=lambda x: -x.total_time)
    
    def generate_recommendations(self) -> list[Recommendation]:
        """Generate actionable recommendations."""
        recs = []
        
        # Check for slow pages
        slow_pages = self.profile.get_slowest_pages(3)
        for page, duration in slow_pages:
            if duration > 0.5:  # >500ms
                recs.append(Recommendation(
                    severity="warning",
                    target=page,
                    message=f"Page takes {duration:.2f}s to build",
                    suggestion="Consider splitting into smaller pages",
                ))
        
        # Check for expensive shortcodes
        for sc in self.get_shortcode_stats():
            if sc.avg_time > 0.1:  # >100ms average
                recs.append(Recommendation(
                    severity="info",
                    target=f"shortcode:{sc.name}",
                    message=f"Shortcode '{sc.name}' averages {sc.avg_time*1000:.0f}ms per call",
                    suggestion="Consider caching or optimizing",
                ))
        
        # Check phase balance
        phases = self.get_phase_breakdown()
        if phases["render"].percentage > 70:
            recs.append(Recommendation(
                severity="info",
                target="rendering",
                message="Rendering takes >70% of build time",
                suggestion="Check template complexity or enable caching",
            ))
        
        return recs
```

### Profile Storage

```python
# bengal/profiling/storage.py
import json
from pathlib import Path
from datetime import datetime

class ProfileStorage:
    """Store and retrieve profile history."""
    
    def __init__(self, cache_dir: Path):
        self.profiles_dir = cache_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_path = self.profiles_dir / "baseline.json"
    
    def save(self, profile: BuildProfile) -> Path:
        """Save profile with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.profiles_dir / f"profile_{timestamp}.json"
        path.write_text(json.dumps(profile.to_dict()))
        return path
    
    def save_baseline(self, profile: BuildProfile):
        """Save profile as baseline for comparison."""
        self.baseline_path.write_text(json.dumps(profile.to_dict()))
    
    def load_baseline(self) -> BuildProfile | None:
        """Load baseline profile."""
        if self.baseline_path.exists():
            data = json.loads(self.baseline_path.read_text())
            return BuildProfile.from_dict(data)
        return None
    
    def get_history(self, limit: int = 10) -> list[BuildProfile]:
        """Get recent profile history."""
        profiles = []
        for path in sorted(self.profiles_dir.glob("profile_*.json"), reverse=True)[:limit]:
            data = json.loads(path.read_text())
            profiles.append(BuildProfile.from_dict(data))
        return profiles
```

### Reporter

```python
# bengal/profiling/reporter.py
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn

class ProfileReporter:
    """Format and display profile results."""
    
    def __init__(self, profile: BuildProfile, baseline: BuildProfile | None = None):
        self.profile = profile
        self.baseline = baseline
        self.analyzer = ProfileAnalyzer(profile)
        self.console = Console()
    
    def print_summary(self):
        """Print profile summary."""
        self.console.print(f"\n⏱️  [bold]Build Profile[/bold] ({self.profile.total_duration:.2f}s total)\n")
        
        # Phase breakdown
        self.console.print("[bold]Phase Breakdown:[/bold]")
        phases = self.analyzer.get_phase_breakdown()
        
        for name, stats in phases.items():
            bar = "█" * int(stats.percentage / 2)
            delta = ""
            if self.baseline:
                baseline_stats = ProfileAnalyzer(self.baseline).get_phase_breakdown().get(name)
                if baseline_stats:
                    change = (stats.duration - baseline_stats.duration) / baseline_stats.duration * 100
                    if abs(change) > 10:
                        delta = f" [{'red' if change > 0 else 'green'}]{change:+.0f}%[/]"
            
            self.console.print(
                f"├─ {name:<12} {stats.duration:.2f}s  ({stats.percentage:.0f}%)  {bar}{delta}"
            )
        
        # Slowest pages
        self.console.print("\n[bold]🐢 Slowest Pages:[/bold]")
        for i, (page, duration) in enumerate(self.profile.get_slowest_pages(5), 1):
            self.console.print(f"{i}. {page:<40} {duration:.2f}s")
        
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
# Auto-save profiles
auto_save = true

# Keep last N profiles
history_limit = 50

# Warning thresholds
slow_page_threshold = 0.5      # seconds
slow_shortcode_threshold = 0.1 # seconds

# Output format
format = "rich"  # or "json", "markdown"
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (1 week)
- [ ] ProfileCollector with context manager
- [ ] Basic instrumentation in build orchestrator
- [ ] CLI `--profile` flag

### Phase 2: Analysis (1 week)
- [ ] Phase breakdown
- [ ] Slowest pages detection
- [ ] Shortcode timing

### Phase 3: Comparison (1 week)
- [ ] Profile storage
- [ ] Baseline save/load
- [ ] Delta reporting

### Phase 4: Polish (1 week)
- [ ] Rich terminal output
- [ ] Recommendations engine
- [ ] History command

---

## Success Criteria

- [ ] `bengal build --profile` shows phase breakdown
- [ ] Slowest pages identified with >90% accuracy
- [ ] Profile comparison shows meaningful deltas
- [ ] Recommendations are actionable
- [ ] <1% overhead when profiling disabled

---

## References

- [Python cProfile](https://docs.python.org/3/library/profile.html)
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [webpack-bundle-analyzer](https://github.com/webpack-contrib/webpack-bundle-analyzer)
- [Gatsby Build Profiling](https://www.gatsbyjs.com/docs/profiling-site-performance-with-react-profiler/)


