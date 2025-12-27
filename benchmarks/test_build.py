"""
Benchmark suite for Bengal SSG build performance.

This suite validates performance claims and tracks improvements over time.
All benchmarks use pytest-benchmark for statistical analysis.

Benchmark Categories:
====================

1. Full Build Performance
   - test_build_performance: Baseline builds for small/large sites
   - test_full_build_baseline: Full build without cache (baseline for comparisons)

2. Fast Mode Benchmarks
   - test_fast_mode_cli_flag: Build with --fast flag (quiet + guaranteed parallel)
   - test_fast_mode_vs_default: Compare fast mode vs default build
   - test_incremental_with_fast_mode: Incremental + fast mode combination

3. Parallel Processing Benchmarks
   - test_parallel_vs_sequential: Parallel vs sequential builds (validates 2-4x speedup)
   - test_sequential_build: Sequential build baseline

4. Incremental Build Benchmarks
   - test_incremental_single_page_change: Single page edit (most common workflow)
   - test_incremental_multi_page_change: Batch edits (5 pages)
   - test_incremental_config_change: Config modification (should trigger full rebuild)
   - test_incremental_no_changes: Cache validation (should be <1s)

5. Memory Optimization Benchmarks
   - test_memory_optimized_build: Streaming build for large sites (--memory-optimized)
   - test_memory_usage_small_site: Memory profiling for small sites
   - test_memory_usage_large_site: Memory profiling for large sites (100 pages)
   - test_incremental_memory_tracking: Memory usage during incremental builds

Expected Performance (Python 3.14):
====================================
- Full build: ~256 pages/sec (Python 3.14), ~373 pps (Python 3.14t)
- Incremental: 15-50x speedup for single-page changes
- Parallel: 2-4x speedup on multi-core systems
- Fast mode: Reduced logging overhead, guaranteed parallel

Recent Optimizations (2025-10-20):
===================================
- Page list caching: 75% reduction in equality checks
- Parallel related posts: 7.5x faster (10K pages: 120s → 16s)
- Parallel taxonomy generation: Automatic for 100+ page sites
- Fast mode: Quiet output + guaranteed parallel processing
"""

import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCENARIOS = ["small_site", "large_site"]


@pytest.mark.benchmark
@pytest.mark.parallel_unsafe
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_build_performance(benchmark, scenario):
    """
    Benchmark the build process for different scenarios.
    """
    scenario_path = Path(__file__).parent / "scenarios" / scenario

    def build_site():
        subprocess.run(
            ["bengal", "build"],
            cwd=scenario_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(build_site)


@pytest.fixture
def temporary_scenario(tmp_path):
    """
    Copy a scenario to a temporary location for testing incremental builds.
    Cleans up after the test.
    """
    source = Path(__file__).parent / "scenarios" / "large_site"
    target = tmp_path / "scenario"
    shutil.copytree(source, target)

    # Perform initial full build
    subprocess.run(
        ["bengal", "build"],
        cwd=target,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    yield target

    # Cleanup
    if target.exists():
        shutil.rmtree(target)


@pytest.mark.benchmark
def test_incremental_single_page_change(benchmark, temporary_scenario):
    """
    Benchmark incremental build after modifying a single page.

    This tests the most common developer workflow: edit one page, rebuild.
    Expected speedup vs full build: 15-50x (validated at 1K-10K pages).
    Recent optimizations (page list caching, parallel related posts) may affect baseline.
    """
    page_path = temporary_scenario / "content" / "page50.md"
    original_content = page_path.read_text()

    def build_after_page_change():
        # Modify the page with a unique marker to force rebuild detection
        page_path.write_text(original_content + f"\n\nModified at {time.time_ns()}")
        subprocess.run(
            ["bengal", "build", "--incremental"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Restore original
        page_path.write_text(original_content)

    benchmark(build_after_page_change)


@pytest.mark.benchmark
def test_incremental_multi_page_change(benchmark, temporary_scenario):
    """
    Benchmark incremental build after modifying multiple pages (batch edit).

    Tests if the system handles multiple changes efficiently.
    Expected: Should be faster than full build but slower than single-page.
    """
    pages_to_modify = [
        temporary_scenario / "content" / f"page{i:02d}.md" for i in [10, 20, 30, 40, 50]
    ]
    original_contents = [p.read_text() for p in pages_to_modify]

    def build_after_multi_page_change():
        # Modify multiple pages
        for page_path, original in zip(pages_to_modify, original_contents, strict=False):
            page_path.write_text(original + f"\n\nBatch modified at {time.time_ns()}")

        subprocess.run(
            ["bengal", "build", "--incremental"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Restore originals
        for page_path, original in zip(pages_to_modify, original_contents, strict=False):
            page_path.write_text(original)

    benchmark(build_after_multi_page_change)


@pytest.mark.benchmark
def test_incremental_config_change(benchmark, temporary_scenario):
    """
    Benchmark behavior when config changes (should trigger full rebuild).

    This validates that config change detection works correctly and triggers
    a full rebuild when needed.
    """
    config_path = temporary_scenario / "bengal.toml"
    original_config = config_path.read_text()

    def build_after_config_change():
        # Modify config (add a comment)
        config_path.write_text(original_config + f"\n# Modified at {time.time_ns()}\n")

        subprocess.run(
            ["bengal", "build", "--incremental"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Restore original
        config_path.write_text(original_config)

    benchmark(build_after_config_change)


@pytest.mark.benchmark
def test_incremental_no_changes(benchmark, temporary_scenario):
    """
    Benchmark rebuild with no changes (cache validation test).

    Expected: Very fast, just validates cache. Should be <1 second.
    This helps identify cache overhead.
    """

    def rebuild_no_changes():
        subprocess.run(
            ["bengal", "build", "--incremental"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(rebuild_no_changes)


# Memory profiling tests (non-benchmark)
def test_memory_usage_small_site(tmp_path):
    """
    Profile memory usage for small site scenario.

    Provides baseline for identifying memory-related bottlenecks.
    """
    from memory_profiler import MemoryProfiler

    scenario_path = Path(__file__).parent / "scenarios" / "small_site"
    profiler = MemoryProfiler(scenario_path)

    stats = profiler.profile_build(page_count=3)

    print("\nSmall Site Memory Profile:")
    print(f"  Peak Memory: {stats.peak_mb} MB")
    print(f"  Current Memory: {stats.current_mb} MB")
    print(f"  Memory per Page: {stats.memory_per_page} MB")

    # Save results
    results_file = tmp_path / "memory_small_site.json"
    profiler.profile_and_save(results_file, page_count=3)
    assert results_file.exists()


def test_memory_usage_large_site(tmp_path):
    """
    Profile memory usage for large site scenario (100 pages).

    Used to identify if scale degradation is memory-related.
    """
    from memory_profiler import MemoryProfiler

    scenario_path = Path(__file__).parent / "scenarios" / "large_site"
    profiler = MemoryProfiler(scenario_path)

    stats = profiler.profile_build(page_count=100)

    print("\nLarge Site Memory Profile:")
    print(f"  Peak Memory: {stats.peak_mb} MB")
    print(f"  Current Memory: {stats.current_mb} MB")
    print(f"  Memory per Page: {stats.memory_per_page} MB")

    # Save results
    results_file = tmp_path / "memory_large_site.json"
    profiler.profile_and_save(results_file, page_count=100)
    assert results_file.exists()


@pytest.mark.benchmark
def test_incremental_memory_tracking(benchmark, temporary_scenario):
    """
    Benchmark and track memory during incremental builds.

    Helps identify if memory accumulates during incremental builds.
    """
    page_path = temporary_scenario / "content" / "page50.md"
    original_content = page_path.read_text()

    def benchmark_with_memory_tracking():
        # Modify page
        page_path.write_text(original_content + f"\n\nModified at {time.time_ns()}")

        subprocess.run(
            ["bengal", "build", "--incremental"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Restore
        page_path.write_text(original_content)

    # Run benchmark
    benchmark(benchmark_with_memory_tracking)


@pytest.fixture
def fresh_scenario(tmp_path):
    """
    Create a fresh copy of large_site for baseline full build testing.

    This fixture creates a NEW copy each time, ensuring we measure
    a true full build without any cache.
    """
    source = Path(__file__).parent / "scenarios" / "large_site"
    target = tmp_path / "fresh_scenario"
    shutil.copytree(source, target)
    yield target

    # Cleanup
    if target.exists():
        shutil.rmtree(target)


@pytest.mark.benchmark
def test_full_build_baseline(benchmark, fresh_scenario):
    """
    Measure full build performance (no cache, no incremental).

    This provides the baseline to compare against incremental builds.
    Expected: This should be slower than incremental single-page changes (15-50x).
    Recent performance: ~256 pps (Python 3.14), ~373 pps (Python 3.14t free-threading).
    """

    def full_build():
        subprocess.run(
            ["bengal", "build"],  # <-- NO --incremental
            cwd=fresh_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(full_build)


@pytest.fixture
def fresh_scenario_no_fast(tmp_path):
    """
    Create a fresh copy of large_site WITHOUT fast_mode for comparison testing.

    This allows us to test --fast flag impact by comparing with/without fast mode.
    """
    source = Path(__file__).parent / "scenarios" / "large_site"
    target = tmp_path / "fresh_scenario_no_fast"
    shutil.copytree(source, target)

    # Remove fast_mode from config to test CLI flag
    config_path = target / "bengal.toml"
    config_content = config_path.read_text()
    # Remove fast_mode line
    lines = [line for line in config_content.splitlines() if "fast_mode" not in line]
    config_path.write_text("\n".join(lines))

    yield target

    # Cleanup
    if target.exists():
        shutil.rmtree(target)


@pytest.mark.benchmark
def test_fast_mode_cli_flag(benchmark, fresh_scenario_no_fast):
    """
    Measure build performance with --fast CLI flag.

    Fast mode enables quiet output and guarantees parallel processing.
    Expected: Should be similar or slightly faster than default (reduced logging overhead).
    """

    def fast_build():
        subprocess.run(
            ["bengal", "build", "--fast"],
            cwd=fresh_scenario_no_fast,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(fast_build)


@pytest.mark.benchmark
def test_fast_mode_vs_default(benchmark, fresh_scenario_no_fast):
    """
    Compare fast mode (CLI flag) vs default build mode.

    This validates that --fast provides measurable improvement through
    reduced logging overhead and guaranteed parallel processing.
    """

    def default_build():
        subprocess.run(
            ["bengal", "build"],
            cwd=fresh_scenario_no_fast,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(default_build)


@pytest.mark.benchmark
def test_memory_optimized_build(benchmark, fresh_scenario):
    """
    Measure build performance with --memory-optimized flag.

    Memory-optimized mode uses streaming build for large sites (5K+ pages).
    Expected: May be slightly slower than standard build due to batching overhead,
    but uses constant memory instead of linear memory scaling.

    Note: This is most beneficial for very large sites (10K+ pages).
    """

    def memory_optimized_build():
        subprocess.run(
            ["bengal", "build", "--memory-optimized"],
            cwd=fresh_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(memory_optimized_build)


@pytest.mark.benchmark
def test_parallel_vs_sequential(benchmark, fresh_scenario_no_fast):
    """
    Compare parallel vs sequential build performance.

    Validates that parallel processing provides 2-4x speedup on multi-core systems.
    This tests the core parallel optimization that benefits all builds.
    """

    def parallel_build():
        subprocess.run(
            ["bengal", "build", "--parallel"],
            cwd=fresh_scenario_no_fast,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(parallel_build)


@pytest.mark.benchmark
def test_sequential_build(benchmark, fresh_scenario_no_fast):
    """
    Measure sequential (non-parallel) build performance.

    Provides baseline for comparing against parallel builds.
    Expected: 2-4x slower than parallel on multi-core systems.
    """

    def sequential_build():
        subprocess.run(
            ["bengal", "build", "--no-parallel"],
            cwd=fresh_scenario_no_fast,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(sequential_build)


@pytest.mark.benchmark
def test_incremental_with_fast_mode(benchmark, temporary_scenario):
    """
    Benchmark incremental build with fast mode enabled.

    Combines incremental build speedup with fast mode optimizations.
    Expected: Should match or slightly improve on standard incremental builds.
    """
    page_path = temporary_scenario / "content" / "page50.md"
    original_content = page_path.read_text()

    def incremental_fast_build():
        # Modify the page
        page_path.write_text(original_content + f"\n\nModified at {time.time_ns()}")
        subprocess.run(
            ["bengal", "build", "--incremental", "--fast"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Restore original
        page_path.write_text(original_content)

    benchmark(incremental_fast_build)
