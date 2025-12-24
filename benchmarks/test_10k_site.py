"""Performance benchmarks for large sites (10k+ pages).

Tests:
- Content discovery performance for 10k pages
- Memory usage during discovery
- Build time scaling

Phase 2 of RFC: User Scenario Coverage - Extended Validation

Run with:
    pytest benchmarks/test_10k_site.py -v --benchmark
    pytest benchmarks/test_10k_site.py -v  # Without benchmark plugin

Note: These tests are marked @pytest.mark.slow and should be run in nightly CI.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


def generate_large_site(
    root: Path,
    sections: int = 100,
    pages_per_section: int = 100,
) -> None:
    """Generate a large site for benchmarking.

    Creates a site with sections * pages_per_section total pages.
    Default: 100 sections × 100 pages = 10,000 pages.

    Args:
        root: Root directory for the site
        sections: Number of content sections
        pages_per_section: Pages per section
    """
    content_dir = root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create root index
    (content_dir / "_index.md").write_text(
        "---\ntitle: Large Site Benchmark\n---\n\nBenchmark home page.\n"
    )

    for s in range(sections):
        section_dir = content_dir / f"section-{s:03d}"
        section_dir.mkdir(exist_ok=True)

        # Section index
        (section_dir / "_index.md").write_text(
            f"---\ntitle: Section {s}\n---\n\nSection {s} index.\n"
        )

        # Pages in section
        for p in range(pages_per_section):
            day = (p % 28) + 1
            month = ((p // 28) % 12) + 1
            (section_dir / f"page-{p:03d}.md").write_text(
                f"---\n"
                f"title: Page {s}-{p}\n"
                f"date: 2025-{month:02d}-{day:02d}\n"
                f"tags:\n"
                f"  - section-{s}\n"
                f"  - page-{p % 10}\n"
                f"---\n\n"
                f"Content for page {s}-{p}.\n\n"
                f"This is a benchmark page to test performance at scale.\n"
            )


def create_site_config(root: Path) -> None:
    """Create minimal bengal.toml for benchmark site."""
    config = """[site]
title = "Benchmark Site"
baseurl = "/"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"
"""
    (root / "bengal.toml").write_text(config)


@pytest.mark.slow
@pytest.mark.benchmark
def test_10k_site_discovery_performance(tmp_path: Path) -> None:
    """Benchmark content discovery for 10k pages.

    Performance gate: Discovery should complete in <30s.
    Typical time on M1 Pro: ~8-15s for 10k pages.
    """
    from bengal.core.site import Site

    # Generate 10k page site (100 sections × 100 pages)
    generate_large_site(tmp_path, sections=100, pages_per_section=100)
    create_site_config(tmp_path)

    # Measure discovery time
    site = Site.from_config(tmp_path)

    start = time.perf_counter()
    site.discover_content()
    duration = time.perf_counter() - start

    # Verify page count (10k pages + 100 section indexes + 1 root index)
    expected_count = 10000 + 100 + 1
    actual_count = len(site.pages)

    print("\n📊 10k Site Discovery Benchmark:")
    print(f"   Pages discovered: {actual_count:,}")
    print(f"   Time: {duration:.2f}s")
    print(f"   Rate: {actual_count / duration:.0f} pages/sec")

    # Assertions
    assert actual_count == expected_count, f"Expected {expected_count} pages, found {actual_count}"

    # Performance gate: <30s
    assert duration < 30.0, f"Discovery took {duration:.2f}s, expected <30s"


@pytest.mark.slow
@pytest.mark.benchmark
def test_10k_site_memory_usage(tmp_path: Path) -> None:
    """Verify memory stays reasonable for 10k pages.

    Performance gate: Peak memory <2GB.
    Typical usage on M1 Pro: ~500MB-1GB for 10k pages.
    """
    from bengal.core.site import Site

    # Generate 10k page site
    generate_large_site(tmp_path, sections=100, pages_per_section=100)
    create_site_config(tmp_path)

    # Start memory tracking
    tracemalloc.start()

    site = Site.from_config(tmp_path)
    site.discover_content()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to readable units
    current_mb = current / (1024 * 1024)
    peak_mb = peak / (1024 * 1024)
    peak_gb = peak / (1024 * 1024 * 1024)

    print("\n📊 10k Site Memory Benchmark:")
    print(f"   Pages: {len(site.pages):,}")
    print(f"   Current memory: {current_mb:.1f} MB")
    print(f"   Peak memory: {peak_mb:.1f} MB ({peak_gb:.2f} GB)")
    print(f"   Per-page overhead: {peak / len(site.pages):.0f} bytes/page")

    # Gate: Peak memory <2GB
    max_bytes = 2 * 1024 * 1024 * 1024  # 2GB
    assert peak < max_bytes, f"Peak memory {peak_gb:.2f}GB exceeds 2GB limit"


@pytest.mark.slow
@pytest.mark.benchmark
def test_1k_site_discovery_performance(tmp_path: Path) -> None:
    """Benchmark content discovery for 1k pages (faster variant).

    This is a faster test suitable for regular CI runs.
    Performance gate: Discovery should complete in <5s.
    """
    from bengal.core.site import Site

    # Generate 1k page site (10 sections × 100 pages)
    generate_large_site(tmp_path, sections=10, pages_per_section=100)
    create_site_config(tmp_path)

    # Measure discovery time
    site = Site.from_config(tmp_path)

    start = time.perf_counter()
    site.discover_content()
    duration = time.perf_counter() - start

    # Verify page count (1k pages + 10 section indexes + 1 root index)
    expected_count = 1000 + 10 + 1
    actual_count = len(site.pages)

    print("\n📊 1k Site Discovery Benchmark:")
    print(f"   Pages discovered: {actual_count:,}")
    print(f"   Time: {duration:.2f}s")
    print(f"   Rate: {actual_count / duration:.0f} pages/sec")

    # Assertions
    assert actual_count == expected_count, f"Expected {expected_count} pages, found {actual_count}"

    # Performance gate: <5s
    assert duration < 5.0, f"Discovery took {duration:.2f}s, expected <5s"


@pytest.mark.slow
@pytest.mark.benchmark
def test_discovery_scaling(tmp_path: Path) -> None:
    """Test that discovery time scales roughly linearly with page count.

    Generates sites of increasing sizes and verifies scaling behavior.
    """
    from bengal.core.site import Site

    sizes = [100, 500, 1000]
    timings: list[tuple[int, float]] = []

    for size in sizes:
        # Clean up previous site
        site_dir = tmp_path / f"site-{size}"
        site_dir.mkdir(exist_ok=True)

        sections = max(1, size // 100)
        pages_per_section = size // sections

        generate_large_site(site_dir, sections=sections, pages_per_section=pages_per_section)
        create_site_config(site_dir)

        site = Site.from_config(site_dir)

        start = time.perf_counter()
        site.discover_content()
        duration = time.perf_counter() - start

        timings.append((len(site.pages), duration))

    print("\n📊 Discovery Scaling:")
    for pages, duration in timings:
        rate = pages / duration
        print(f"   {pages:,} pages: {duration:.2f}s ({rate:.0f} pages/sec)")

    # Verify roughly linear scaling (10x pages shouldn't be 100x slower)
    if len(timings) >= 2:
        first_rate = timings[0][0] / timings[0][1]
        last_rate = timings[-1][0] / timings[-1][1]

        # Rate should be within 5x (allowing for startup overhead)
        assert last_rate > first_rate / 5, (
            f"Scaling appears non-linear: first rate={first_rate:.0f}, last rate={last_rate:.0f}"
        )


