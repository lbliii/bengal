# Memory Profiling - Corrected Implementation Plan

## Overview

This document provides a concrete, actionable plan for implementing proper memory profiling in Bengal SSG, addressing all the issues identified in the critical analysis.

---

## Design Principles

1. **Separation of Concerns**: Test fixture setup vs. actual build memory
2. **Dual Tracking**: Both Python heap (tracemalloc) AND process memory (psutil)
3. **Snapshot Comparison**: Identify WHAT is using memory, not just HOW MUCH
4. **Phase Isolation**: Reset measurements at phase boundaries
5. **Statistical Rigor**: Multiple runs, confidence intervals, outlier detection

---

## Dependencies

Add to `requirements.txt`:
```
psutil>=5.9.0  # Process memory tracking
```

---

## Implementation Structure

```
tests/performance/
├── test_memory_profiling.py          # NEW: Corrected implementation
├── memory_profiling_old.py           # Rename current (broken) version
└── fixtures/
    └── memory_test_helpers.py        # Shared utilities
```

---

## Core Components

### 1. Memory Measurement Context Manager

**File**: `tests/performance/fixtures/memory_test_helpers.py`

```python
"""Helper utilities for accurate memory profiling."""

import tracemalloc
import psutil
import gc
from dataclasses import dataclass
from typing import Optional, List
from contextlib import contextmanager


@dataclass
class MemorySnapshot:
    """Snapshot of memory state at a point in time."""
    
    # Python heap (tracemalloc)
    python_current_bytes: int
    python_peak_bytes: int
    
    # Process memory (psutil)
    rss_bytes: int  # Resident Set Size
    vms_bytes: int  # Virtual Memory Size
    
    # Tracemalloc snapshot for detailed analysis
    tracemalloc_snapshot: Optional[tracemalloc.Snapshot] = None
    
    @property
    def python_current_mb(self) -> float:
        return self.python_current_bytes / 1024 / 1024
    
    @property
    def python_peak_mb(self) -> float:
        return self.python_peak_bytes / 1024 / 1024
    
    @property
    def rss_mb(self) -> float:
        return self.rss_bytes / 1024 / 1024
    
    @property
    def vms_mb(self) -> float:
        return self.vms_bytes / 1024 / 1024


@dataclass
class MemoryDelta:
    """Memory change between two snapshots."""
    
    python_heap_delta_mb: float
    python_heap_peak_mb: float
    rss_delta_mb: float
    vms_delta_mb: float
    
    # Top allocators (filename, line, size)
    top_allocators: List[str]
    
    def __str__(self) -> str:
        return (
            f"Python Heap: Δ{self.python_heap_delta_mb:+.1f}MB "
            f"(peak: {self.python_heap_peak_mb:.1f}MB) | "
            f"RSS: Δ{self.rss_delta_mb:+.1f}MB"
        )


class MemoryProfiler:
    """Context manager for accurate memory profiling."""
    
    def __init__(self, track_allocations: bool = True):
        """
        Initialize memory profiler.
        
        Args:
            track_allocations: If True, capture detailed allocation info
                             (has ~2x performance overhead)
        """
        self.track_allocations = track_allocations
        self.process = psutil.Process()
        self.before: Optional[MemorySnapshot] = None
        self.after: Optional[MemorySnapshot] = None
        
    def __enter__(self):
        """Start profiling."""
        # Force GC to get clean baseline
        gc.collect()
        gc.collect()  # Run twice to catch circular refs
        gc.collect()  # Third time for good measure
        
        # Start tracemalloc
        tracemalloc.start()
        
        # Take initial snapshot
        self.before = self._take_snapshot()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling."""
        # Take final snapshot
        self.after = self._take_snapshot()
        
        # Stop tracemalloc
        tracemalloc.stop()
        
        return False  # Don't suppress exceptions
    
    def _take_snapshot(self) -> MemorySnapshot:
        """Capture current memory state."""
        # Get Python heap info
        current, peak = tracemalloc.get_traced_memory()
        
        # Get process memory info
        mem_info = self.process.memory_info()
        
        # Capture detailed snapshot if requested
        snapshot = None
        if self.track_allocations:
            snapshot = tracemalloc.take_snapshot()
        
        return MemorySnapshot(
            python_current_bytes=current,
            python_peak_bytes=peak,
            rss_bytes=mem_info.rss,
            vms_bytes=mem_info.vms,
            tracemalloc_snapshot=snapshot
        )
    
    def get_delta(self, top_n: int = 10) -> MemoryDelta:
        """
        Calculate memory delta between before and after.
        
        Args:
            top_n: Number of top allocators to include
            
        Returns:
            MemoryDelta object with detailed breakdown
        """
        if not self.before or not self.after:
            raise RuntimeError("Must use as context manager")
        
        # Calculate deltas
        python_delta_bytes = (
            self.after.python_current_bytes - self.before.python_current_bytes
        )
        python_peak_bytes = (
            self.after.python_peak_bytes - self.before.python_peak_bytes
        )
        rss_delta_bytes = self.after.rss_bytes - self.before.rss_bytes
        vms_delta_bytes = self.after.vms_bytes - self.before.vms_bytes
        
        # Get top allocators
        top_allocators = []
        if self.track_allocations and self.before.tracemalloc_snapshot:
            top_stats = self.after.tracemalloc_snapshot.compare_to(
                self.before.tracemalloc_snapshot,
                'lineno'
            )
            
            for stat in top_stats[:top_n]:
                size_mb = stat.size_diff / 1024 / 1024
                top_allocators.append(
                    f"{stat.traceback.format()[0].strip()} | "
                    f"{size_mb:+.2f}MB ({stat.count_diff:+d} blocks)"
                )
        
        return MemoryDelta(
            python_heap_delta_mb=python_delta_bytes / 1024 / 1024,
            python_heap_peak_mb=python_peak_bytes / 1024 / 1024,
            rss_delta_mb=rss_delta_bytes / 1024 / 1024,
            vms_delta_mb=vms_delta_bytes / 1024 / 1024,
            top_allocators=top_allocators
        )


@contextmanager
def profile_memory(name: str = "Operation", verbose: bool = True):
    """
    Convenience context manager for profiling memory.
    
    Example:
        with profile_memory("Building site", verbose=True) as prof:
            site.build()
        
        delta = prof.get_delta()
        assert delta.rss_delta_mb < 500
    """
    profiler = MemoryProfiler(track_allocations=verbose)
    
    with profiler:
        yield profiler
    
    if verbose:
        delta = profiler.get_delta()
        print(f"\n{name}:")
        print(f"  {delta}")
        if delta.top_allocators:
            print(f"  Top allocators:")
            for alloc in delta.top_allocators:
                print(f"    {alloc}")
```

---

### 2. Corrected Test Suite

**File**: `tests/performance/test_memory_profiling.py`

```python
"""
Memory profiling tests for Bengal SSG - CORRECTED VERSION.

This version properly measures memory by:
1. Separating fixture setup from actual build measurement
2. Tracking both Python heap and process RSS
3. Using snapshot comparison to identify allocators
4. Testing for actual memory leaks, not GC noise
"""

import pytest
from pathlib import Path
import gc
import statistics

from bengal.core.site import Site
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers, _loggers

from fixtures.memory_test_helpers import MemoryProfiler, profile_memory


@pytest.fixture
def site_generator(tmp_path):
    """
    Factory fixture for generating test sites.
    
    NOTE: Memory used by this fixture is NOT included in build measurements.
    """
    
    def _generate_site(page_count: int, sections: int = 5) -> Path:
        """Generate a test site with specified number of pages."""
        site_root = tmp_path / f"site_{page_count}pages"
        site_root.mkdir(exist_ok=True)
        
        # Create config
        config_file = site_root / "bengal.toml"
        config_file.write_text(f"""
[site]
title = "Test Site {page_count} Pages"
baseurl = "https://example.com"

[build]
parallel = false
""")
        
        # Create content directory
        content_dir = site_root / "content"
        content_dir.mkdir(exist_ok=True)
        
        # Create index
        (content_dir / "index.md").write_text("""---
title: Home
---
# Welcome

This is a test site for memory profiling.
""")
        
        # Calculate pages per section
        pages_per_section = (page_count - 1) // sections
        
        # Create sections with pages
        for section_idx in range(sections):
            section_name = f"section{section_idx:03d}"
            section_dir = content_dir / section_name
            section_dir.mkdir(exist_ok=True)
            
            # Section index
            (section_dir / "_index.md").write_text(f"""---
title: Section {section_idx}
---
# Section {section_idx}

This is section {section_idx}.
""")
            
            # Pages in section
            pages_in_this_section = min(
                pages_per_section,
                page_count - 1 - (section_idx * pages_per_section)
            )
            
            for page_idx in range(pages_in_this_section):
                page_file = section_dir / f"page{page_idx:04d}.md"
                page_file.write_text(f"""---
title: Page {section_idx}-{page_idx}
date: 2025-01-{(page_idx % 28) + 1:02d}
tags: [tag{page_idx % 10}, tag{page_idx % 20}]
---
# Page {section_idx}-{page_idx}

This is test page {page_idx} in section {section_idx}.

## Content

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

### Code Example

```python
def hello_world():
    print("Hello from page {section_idx}-{page_idx}")
    return 42
```

### List

- Item 1
- Item 2
- Item 3

[Link to home](/)
""")
        
        return site_root
    
    return _generate_site


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up before and after each test."""
    _loggers.clear()
    gc.collect()
    yield
    close_all_loggers()
    _loggers.clear()
    gc.collect()


class TestMemoryProfiling:
    """Memory profiling tests with correct measurement methodology."""
    
    def test_100_page_site_memory(self, site_generator):
        """Test memory usage for a 100-page site."""
        # Generate site OUTSIDE of profiling
        site_root = site_generator(page_count=100, sections=5)
        configure_logging(level=LogLevel.WARNING)
        
        # Profile ONLY the build
        with profile_memory("100-page build", verbose=True) as prof:
            site = Site.from_config(site_root)
            stats = site.build(parallel=False)
        
        delta = prof.get_delta()
        
        # Assertions on ACTUAL build memory
        assert stats.regular_pages >= 100
        assert delta.rss_delta_mb < 300, \
            f"Build used {delta.rss_delta_mb:.1f}MB RSS (expected <300MB)"
        
        print(f"\nPer-page memory: {delta.rss_delta_mb/100:.2f}MB RSS")
    
    def test_1k_page_site_memory(self, site_generator):
        """Test memory usage for a 1K-page site."""
        site_root = site_generator(page_count=1000, sections=10)
        configure_logging(level=LogLevel.WARNING)
        
        with profile_memory("1K-page build", verbose=True) as prof:
            site = Site.from_config(site_root)
            stats = site.build(parallel=False)
        
        delta = prof.get_delta()
        
        assert stats.total_pages >= 1000
        assert delta.rss_delta_mb < 800, \
            f"Build used {delta.rss_delta_mb:.1f}MB RSS (expected <800MB)"
        
        print(f"\nPer-page memory: {delta.rss_delta_mb/1000:.3f}MB RSS")
    
    def test_memory_scaling(self, site_generator):
        """Test how memory scales with page count."""
        page_counts = [50, 100, 200, 400]
        results = []
        
        for count in page_counts:
            # Generate site
            site_root = site_generator(page_count=count, sections=5)
            configure_logging(level=LogLevel.WARNING)
            
            # Measure build memory
            profiler = MemoryProfiler(track_allocations=False)
            with profiler:
                site = Site.from_config(site_root)
                site.build(parallel=False)
            
            delta = profiler.get_delta()
            results.append({
                'pages': count,
                'rss_mb': delta.rss_delta_mb,
                'per_page_mb': delta.rss_delta_mb / count
            })
            
            # Clean up between runs
            close_all_loggers()
            _loggers.clear()
            gc.collect()
        
        # Analyze scaling
        print("\nMemory Scaling Analysis:")
        print(f"{'Pages':<10} {'RSS (MB)':<12} {'Per Page (MB)':<15}")
        print("-" * 40)
        
        for r in results:
            print(f"{r['pages']:<10} {r['rss_mb']:<12.1f} {r['per_page_mb']:<15.3f}")
        
        # Check scaling characteristics
        # Memory should be roughly linear: pages * constant
        # Allow for overhead, but shouldn't be quadratic
        
        per_page_costs = [r['per_page_mb'] for r in results]
        avg_per_page = statistics.mean(per_page_costs)
        stddev = statistics.stdev(per_page_costs) if len(per_page_costs) > 1 else 0
        
        print(f"\nAverage per-page: {avg_per_page:.3f}MB ± {stddev:.3f}MB")
        
        # Per-page cost should be relatively stable (< 2x variation)
        max_cost = max(per_page_costs)
        min_cost = min(per_page_costs)
        assert max_cost / min_cost < 2.0, \
            f"Memory scaling is non-linear: {min_cost:.3f} to {max_cost:.3f} MB/page"
    
    def test_memory_leak_detection(self, site_generator):
        """Test for memory leaks with multiple builds."""
        site_root = site_generator(page_count=50, sections=3)
        configure_logging(level=LogLevel.WARNING)
        
        # Build 10 times and track memory
        rss_samples = []
        
        for i in range(10):
            # Clean up thoroughly
            close_all_loggers()
            _loggers.clear()
            gc.collect()
            
            # Measure build
            profiler = MemoryProfiler(track_allocations=False)
            with profiler:
                site = Site.from_config(site_root)
                site.build(parallel=False)
            
            delta = profiler.get_delta()
            rss_samples.append(delta.rss_delta_mb)
            
            print(f"  Build {i+1:2d}: {delta.rss_delta_mb:6.1f}MB RSS")
        
        # Statistical analysis
        first_three = rss_samples[:3]
        last_three = rss_samples[-3:]
        
        avg_first = statistics.mean(first_three)
        avg_last = statistics.mean(last_three)
        growth = avg_last - avg_first
        
        print(f"\n  First 3 builds:  {avg_first:.1f}MB average")
        print(f"  Last 3 builds:   {avg_last:.1f}MB average")
        print(f"  Growth:          {growth:+.1f}MB")
        
        # Check for leak: last 3 should not be significantly higher than first 3
        # Allow 10% variation for noise
        threshold = avg_first * 0.10
        assert abs(growth) < threshold, \
            f"Memory leak detected: {growth:+.1f}MB growth (threshold: {threshold:.1f}MB)"
        
        print(f"  ✓ No memory leak detected")
    
    def test_phase_memory_breakdown(self, site_generator):
        """Test memory usage breakdown by build phase."""
        site_root = site_generator(page_count=200, sections=5)
        configure_logging(level=LogLevel.INFO, track_memory=True)
        
        # We'll need to instrument the build to get per-phase breakdowns
        # For now, just verify we CAN track memory per phase
        
        with profile_memory("200-page build with phase tracking") as prof:
            site = Site.from_config(site_root)
            site.build(parallel=False)
        
        delta = prof.get_delta()
        
        # Get logger events to see phase memory
        from bengal.utils.logger import get_logger
        logger = get_logger("bengal.orchestration.build")
        events = logger.get_events()
        
        # This will still show GLOBAL peaks (our logger is still broken)
        # But at least we're measuring the TOTAL correctly now
        print(f"\nTotal build memory: {delta}")
        
        # TODO: Fix logger phase memory tracking (separate issue)
        assert delta.rss_delta_mb > 0, "Should use some memory"
```

---

### 3. Migration Plan

#### Phase 1: Add Dependencies and Helpers
1. Add `psutil` to `requirements.txt`
2. Create `tests/performance/fixtures/memory_test_helpers.py`
3. Add tests for the helper utilities

#### Phase 2: Create New Tests
1. Create `tests/performance/test_memory_profiling.py` (corrected version)
2. Run tests and establish real baselines
3. Document actual memory characteristics

#### Phase 3: Fix Logger Phase Tracking
1. Update `bengal/utils/logger.py` to track per-phase peaks correctly
2. Use snapshot comparison instead of global peak
3. Add tests for phase memory tracking

#### Phase 4: Deprecate Old Tests
1. Rename `test_memory_profiling.py` → `test_memory_profiling_old.py`
2. Add deprecation warning
3. Update documentation

#### Phase 5: Add CLI Integration
1. Add `--profile-memory` flag to `bengal build`
2. Generate memory report
3. Save report to `build/memory-profile.json`

---

## Expected Results

With correct implementation, we should see:

### 100-Page Site
- **RSS**: ~100-200MB (actual process memory)
- **Python Heap**: ~50-100MB (tracked allocations)
- **Per-page**: ~1-2MB RSS

### 1K-Page Site
- **RSS**: ~500-800MB
- **Python Heap**: ~300-500MB
- **Per-page**: ~0.5-0.8MB RSS

### 10K-Page Site
- **RSS**: ~3-5GB
- **Python Heap**: ~2-3GB
- **Per-page**: ~0.3-0.5MB RSS

These are ESTIMATES - we don't actually know yet because our current measurements are wrong!

---

## Success Criteria

✅ Memory measurements are reproducible (±10% variance)
✅ We can identify top memory allocators
✅ We can detect memory leaks reliably
✅ RSS and Python heap are tracked separately
✅ Per-phase memory is accurate
✅ Tests don't have false positives
✅ Documentation reflects reality

---

## Next Actions

1. **Review this plan** - Is the approach sound?
2. **Implement helpers** - Start with `memory_test_helpers.py`
3. **Write one corrected test** - Prove the approach works
4. **Establish baselines** - Run on real hardware
5. **Fix logger phase tracking** - Separate task
6. **Migrate remaining tests** - Systematically update

---

## Notes

- Current tests can stay as smoke tests (just change assertions)
- Need to add this to documentation
- Should track memory metrics in CI/CD
- Consider memory profiling mode in CLI for users


