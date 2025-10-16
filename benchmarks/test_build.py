import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCENARIOS = ["small_site", "large_site"]


@pytest.mark.benchmark
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
    Expected speedup vs full build: 15-50x (or reveals if incremental is broken)
    """
    page_path = temporary_scenario / "content" / "page50.md"
    original_content = page_path.read_text()

    def build_after_page_change():
        # Modify the page with a unique marker to force rebuild detection
        page_path.write_text(original_content + f"\n\nModified at {time.time_ns()}")
        subprocess.run(
            ["bengal", "build"],
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
            ["bengal", "build"],
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
            ["bengal", "build"],
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
            ["bengal", "build"],
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
            ["bengal", "build"],
            cwd=temporary_scenario,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Restore
        page_path.write_text(original_content)

    # Run benchmark
    benchmark(benchmark_with_memory_tracking)
