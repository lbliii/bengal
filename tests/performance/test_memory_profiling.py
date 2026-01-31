"""
Memory profiling tests for Bengal SSG - CORRECTED VERSION.

This version properly measures memory by:
1. Separating fixture setup from actual build measurement
2. Tracking both Python heap and process RSS
3. Using snapshot comparison to identify allocators
4. Testing for actual memory leaks, not GC noise

Key differences from old implementation:
- Site generation happens OUTSIDE memory profiling
- Clean GC baseline before measurement
- Both tracemalloc (Python heap) and psutil (RSS) tracking
- Snapshot comparison to identify top allocators
"""

import gc
import statistics
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.utils.observability.logger import (
    LogLevel,
    configure_logging,
    reset_loggers,
)

from .memory_test_helpers import MemoryProfiler, profile_memory


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

        # Handle sections=0 case (site with only index page)
        if sections == 0:
            return site_root

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
                pages_per_section, page_count - 1 - (section_idx * pages_per_section)
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
    reset_loggers()
    gc.collect()
    yield
    reset_loggers()
    gc.collect()


@pytest.mark.slow
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
            stats = site.build(BuildOptions(force_sequential=True))

        delta = prof.get_delta()

        # Assertions on ACTUAL build memory
        assert stats.regular_pages >= 100, (
            f"Should have at least 100 regular pages, got {stats.regular_pages}"
        )

        # Use generous threshold initially until we establish real baseline
        assert delta.rss_delta_mb < 500, (
            f"Build used {delta.rss_delta_mb:.1f}MB RSS (expected <500MB)"
        )

        print(f"\nPer-page memory: {delta.rss_delta_mb / 100:.2f}MB RSS")

    def test_500_page_site_memory(self, site_generator):
        """Test memory usage for a 500-page site."""
        site_root = site_generator(page_count=500, sections=5)
        configure_logging(level=LogLevel.WARNING)

        with profile_memory("500-page build", verbose=True) as prof:
            site = Site.from_config(site_root)
            stats = site.build(BuildOptions(force_sequential=True))

        delta = prof.get_delta()

        assert stats.regular_pages >= 500, (
            f"Should have at least 500 regular pages, got {stats.regular_pages}"
        )
        assert delta.rss_delta_mb < 1000, (
            f"Build used {delta.rss_delta_mb:.1f}MB RSS (expected <1000MB)"
        )

        print(f"\nPer-page memory: {delta.rss_delta_mb / 500:.3f}MB RSS")

    def test_1k_page_site_memory(self, site_generator):
        """Test memory usage for a 1K-page site."""
        site_root = site_generator(page_count=1000, sections=10)
        configure_logging(level=LogLevel.WARNING)

        with profile_memory("1K-page build", verbose=True) as prof:
            site = Site.from_config(site_root)
            stats = site.build(BuildOptions(force_sequential=True))

        delta = prof.get_delta()

        assert stats.total_pages >= 1000, (
            f"Should have at least 1000 total pages, got {stats.total_pages}"
        )
        assert delta.rss_delta_mb < 1500, (
            f"Build used {delta.rss_delta_mb:.1f}MB RSS (expected <1500MB)"
        )

        print(f"\nPer-page memory: {delta.rss_delta_mb / 1000:.3f}MB RSS")

    def test_memory_scaling(self, site_generator):
        """Test how memory scales with page count."""
        page_counts = [50, 100, 200, 400]
        results = []

        print("\n" + "=" * 60)
        print("Memory Scaling Analysis")
        print("=" * 60)

        for count in page_counts:
            # Generate site
            site_root = site_generator(page_count=count, sections=5)
            configure_logging(level=LogLevel.WARNING)

            # Measure build memory
            profiler = MemoryProfiler(track_allocations=False)
            with profiler:
                site = Site.from_config(site_root)
                site.build(BuildOptions(force_sequential=True))

            delta = profiler.get_delta()
            results.append(
                {
                    "pages": count,
                    "rss_mb": delta.rss_delta_mb,
                    "python_heap_mb": delta.python_heap_delta_mb,
                    "per_page_mb": delta.rss_delta_mb / count,
                }
            )

            print(
                f"  {count:4d} pages: {delta.rss_delta_mb:6.1f}MB RSS, "
                f"{delta.python_heap_delta_mb:6.1f}MB heap, "
                f"{delta.rss_delta_mb / count:.3f}MB/page"
            )

            # Clean up between runs
            reset_loggers()
            gc.collect()

        # Analyze scaling
        print("\nScaling Summary:")
        print(f"{'Pages':<10} {'RSS (MB)':<12} {'Heap (MB)':<12} {'Per Page (MB)':<15}")
        print("-" * 60)

        for r in results:
            print(
                f"{r['pages']:<10} {r['rss_mb']:<12.1f} "
                f"{r['python_heap_mb']:<12.1f} {r['per_page_mb']:<15.3f}"
            )

        # Check scaling characteristics
        # Memory should be roughly linear: pages * constant + fixed_overhead
        # Smaller builds will have higher per-page cost due to fixed overhead
        # Larger builds amortize that overhead better

        per_page_costs = [r["per_page_mb"] for r in results]

        # Skip first build for per-page analysis (it has setup overhead)
        # Use builds 2-4 to analyze marginal per-page cost
        if len(per_page_costs) > 1:
            marginal_costs = per_page_costs[1:]
            avg_per_page = statistics.mean(marginal_costs)
            stddev = statistics.stdev(marginal_costs) if len(marginal_costs) > 1 else 0
        else:
            avg_per_page = statistics.mean(per_page_costs)
            stddev = 0

        print(f"\nMarginal per-page (excl. first build): {avg_per_page:.3f}MB ± {stddev:.3f}MB")

        # Check that memory doesn't grow quadratically
        # Total memory should be roughly: base + (pages * per_page)
        # If quadratic, larger builds would have much higher per-page cost
        if len(results) >= 3:
            # Compare 100-page vs 400-page: should be ~4x total memory, not 16x
            total_100 = results[1]["rss_mb"]  # 100 pages
            total_400 = results[3]["rss_mb"]  # 400 pages
            growth_ratio = total_400 / total_100 if total_100 > 0 else 0

            print(f"\nMemory growth 100→400 pages: {growth_ratio:.2f}x (expected: ~4x for linear)")

            # Allow some overhead, but should be closer to 4x than 16x
            assert growth_ratio < 8, (
                f"Memory scaling appears quadratic: {growth_ratio:.2f}x growth "
                f"for 4x page increase (expected ~4x for linear)"
            )

        # Per-page cost should decrease or stabilize as pages increase (not grow)
        # This confirms we're not leaking or having quadratic behavior
        assert per_page_costs[-1] <= per_page_costs[1], (
            f"Per-page cost increased with scale: {per_page_costs[1]:.3f} → {per_page_costs[-1]:.3f}MB/page"
        )

    def test_memory_leak_detection(self, site_generator):
        """Test for memory leaks with multiple builds."""
        site_root = site_generator(page_count=50, sections=3)
        configure_logging(level=LogLevel.WARNING)

        print("\n" + "=" * 60)
        print("Memory Leak Detection (10 builds)")
        print("=" * 60)

        # Build 10 times and track memory
        rss_samples = []

        for i in range(10):
            # Clean up thoroughly
            reset_loggers()
            gc.collect()

            # Measure build
            profiler = MemoryProfiler(track_allocations=False)
            with profiler:
                site = Site.from_config(site_root)
                site.build(BuildOptions(force_sequential=True))

            delta = profiler.get_delta()
            rss_samples.append(delta.rss_delta_mb)

            print(f"  Build {i + 1:2d}: {delta.rss_delta_mb:6.1f}MB RSS")

        # Statistical analysis
        # Skip first build (has setup overhead), compare builds 2-4 vs 8-10
        warmup = rss_samples[1:4]  # Builds 2-4
        final = rss_samples[-3:]  # Builds 8-10

        avg_warmup = statistics.mean(warmup)
        avg_final = statistics.mean(final)
        growth = avg_final - avg_warmup

        print(f"\n  Builds 2-4:  {avg_warmup:.1f}MB average")
        print(f"  Builds 8-10: {avg_final:.1f}MB average")
        print(f"  Growth:      {growth:+.1f}MB")

        # Memory leak detection strategy:
        # - Negative growth is GOOD (memory decreasing = no leak)
        # - Small positive growth is acceptable (noise)
        # - Only fail on significant POSITIVE growth (actual leak)
        # RSS measurements are noisy due to OS memory management, so use generous threshold

        # Use median of all builds (excluding first) as baseline
        median_usage = statistics.median(rss_samples[1:])
        # Allow up to 50% growth OR 5MB, whichever is larger
        threshold = max(abs(median_usage) * 0.5, 5.0)

        # Use pytest.approx for cleaner comparison (only check for POSITIVE growth)
        # Allow memory to stay same or decrease, but flag significant increases
        if growth > threshold:
            print(
                f"  ✗ Memory leak detected: {growth:+.1f}MB growth (threshold: {threshold:.1f}MB)"
            )
            # Use pytest.approx for the assertion
            assert avg_final == pytest.approx(avg_warmup, abs=threshold), (
                f"Memory leak detected: {growth:+.1f}MB growth exceeds threshold ({threshold:.1f}MB)"
            )
        elif growth < 0:
            print(f"  ✓ No leak - memory decreased by {abs(growth):.1f}MB")
        else:
            print(f"  ✓ No leak - growth {growth:+.1f}MB within threshold ({threshold:.1f}MB)")

    def test_build_with_detailed_allocators(self, site_generator):
        """Test build with detailed allocator tracking."""
        site_root = site_generator(page_count=100, sections=5)
        configure_logging(level=LogLevel.WARNING)

        print("\n" + "=" * 60)
        print("Detailed Memory Allocation Analysis")
        print("=" * 60)

        # Profile with detailed tracking
        profiler = MemoryProfiler(track_allocations=True)
        with profiler:
            site = Site.from_config(site_root)
            stats = site.build(BuildOptions(force_sequential=True))

        delta = profiler.get_delta(top_n=20)

        print("\nBuild Statistics:")
        print(f"  Regular pages: {stats.regular_pages}")
        print(f"  Total pages:   {stats.total_pages}")

        print("\nMemory Usage:")
        print(
            f"  Python heap:   Δ{delta.python_heap_delta_mb:+.1f}MB "
            f"(peak: {delta.python_heap_peak_mb:.1f}MB)"
        )
        print(f"  Process RSS:   Δ{delta.rss_delta_mb:+.1f}MB")
        print(f"  Per page:      {delta.rss_delta_mb / stats.regular_pages:.3f}MB RSS")

        if delta.top_allocators:
            print("\nTop 20 Memory Allocators:")
            for i, alloc in enumerate(delta.top_allocators, 1):
                print(f"  {i:2d}. {alloc}")

        assert stats.regular_pages >= 100
        # Check Python heap (more reliable than RSS which can be negative due to GC/OS)
        assert delta.python_heap_delta_mb > 0, (
            f"Should use some memory (Python heap: {delta.python_heap_delta_mb:.1f}MB)"
        )


@pytest.mark.slow
class TestMemoryEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_empty_site_memory(self, site_generator):
        """Test memory usage for minimal site (just index)."""
        site_root = site_generator(page_count=1, sections=0)
        configure_logging(level=LogLevel.WARNING)

        with profile_memory("Empty site build", verbose=False) as prof:
            site = Site.from_config(site_root)
            site.build(BuildOptions(force_sequential=True))

        delta = prof.get_delta()

        print(f"\nMinimal site: {delta}")

        # Even empty site should use some memory for framework
        # Check Python heap (more reliable than RSS)
        assert delta.python_heap_delta_mb > 0, (
            f"Should use some memory (Python heap: {delta.python_heap_delta_mb:.1f}MB)"
        )
        # RSS can be 0 or even negative, but if positive, should be reasonable
        if delta.rss_delta_mb > 0:
            assert delta.rss_delta_mb < 100, (
                f"Empty site used {delta.rss_delta_mb:.1f}MB RSS (expected <100MB)"
            )

    def test_config_load_memory(self, site_generator):
        """Test memory usage of just loading config (no build)."""
        site_root = site_generator(page_count=100, sections=5)
        configure_logging(level=LogLevel.WARNING)

        with profile_memory("Config load only", verbose=False) as prof:
            Site.from_config(site_root)
            # Don't build, just load config

        delta = prof.get_delta()

        print(f"\nConfig load only: {delta}")

        # Loading config should be very light
        assert delta.rss_delta_mb < 50, (
            f"Config load used {delta.rss_delta_mb:.1f}MB (expected <50MB)"
        )
