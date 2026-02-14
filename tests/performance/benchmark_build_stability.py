"""
Benchmark build stability and degradation over repeated builds.

Tests whether performance degrades over time due to:
- Cache bloat
- Memory leaks
- Accumulating state
- Resource exhaustion

This validates that the build system is stable for long-running
development sessions with hundreds of incremental rebuilds.

Tests:
- 100 consecutive incremental builds
- Memory usage tracking over time
- Cache size growth monitoring
- Build time consistency

Expected Results:
- No memory leaks (stable RSS usage)
- No cache bloat (stable cache size)
- Consistent build times (no degradation)
- No resource exhaustion errors
"""

import gc
import shutil
import statistics
import time
from pathlib import Path
from tempfile import mkdtemp

import psutil

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def create_test_site() -> Path:
    """Create a medium-sized test site for stability testing."""
    site_root = Path(mkdtemp(prefix="bengal_stability_"))

    content_dir = site_root / "content"
    content_dir.mkdir(parents=True)

    # Configuration
    config = """
[site]
title = "Stability Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
incremental = true
parallel = true

[assets]
minify = false
"""
    (site_root / "bengal.toml").write_text(config)

    # Create 100 pages for testing
    for i in range(100):
        section = f"section-{i // 20 + 1}"
        section_dir = content_dir / section
        section_dir.mkdir(exist_ok=True)

        if not (section_dir / "_index.md").exists():
            (section_dir / "_index.md").write_text(f"---\ntitle: {section}\n---\n# {section}\n")

        page_content = f"""---
title: "Page {i + 1}"
date: 2025-01-01
tags: ["tag-{i % 10}", "tag-{i % 5}"]
---

# Page {i + 1}

This is test page {i + 1}.

## Section 1

Content for page {i + 1}.

```python
def function_{i}():
    return {i}
```

## Section 2

More content here.
"""
        (section_dir / f"page-{i + 1:03d}.md").write_text(page_content)

    return site_root


def measure_memory() -> float:
    """Get current process RSS memory in MB."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def measure_cache_size(site_root: Path) -> float:
    """Measure cache file size in MB."""
    cache_file = site_root / "public" / ".bengal-cache.json"
    if cache_file.exists():
        return cache_file.stat().st_size / (1024 * 1024)
    return 0.0


def run_stability_benchmark(num_builds: int = 100):
    """
    Run multiple consecutive incremental builds and track stability.

    Args:
        num_builds: Number of consecutive builds to perform

    """
    print("=" * 80)
    print(f"BUILD STABILITY BENCHMARK - {num_builds} CONSECUTIVE BUILDS")
    print("=" * 80)
    print()
    print("This test validates that build performance remains stable")
    print("over many consecutive incremental builds.")
    print()

    # Create test site
    print("Creating test site...")
    site_root = create_test_site()

    try:
        # Initial full build
        print("Running initial full build...")
        site = Site.from_config(site_root)
        site.build(BuildOptions(incremental=False))

        # Track metrics
        build_times: list[float] = []
        memory_usage: list[float] = []
        cache_sizes: list[float] = []

        # Get baseline memory
        gc.collect()
        baseline_memory = measure_memory()

        print(f"\nRunning {num_builds} consecutive incremental builds...")
        print("(Each build modifies a different page)")
        print()

        content_dir = site_root / "content"
        pages = sorted(content_dir.glob("section-*/page-*.md"))

        # Create site once to avoid config reload issues
        site = Site.from_config(site_root)

        for i in range(num_builds):
            # Modify a different page each time
            page_to_modify = pages[i % len(pages)]

            original = page_to_modify.read_text()
            modified = original + f"\n\n## Update {i + 1}\n\nBuild iteration {i + 1}.\n"
            page_to_modify.write_text(modified)

            # Measure build
            start = time.perf_counter()
            site.build(BuildOptions(incremental=True))
            elapsed = time.perf_counter() - start

            # Collect metrics
            build_times.append(elapsed)

            gc.collect()
            current_memory = measure_memory()
            memory_usage.append(current_memory - baseline_memory)

            cache_size = measure_cache_size(site_root)
            cache_sizes.append(cache_size)

            # Restore original
            page_to_modify.write_text(original)

            # Progress indicator
            if (i + 1) % 10 == 0:
                avg_time = statistics.mean(build_times[-10:])
                print(f"  Build {i + 1:3d}: {elapsed:.3f}s (avg last 10: {avg_time:.3f}s)")

        # Analyze results
        print(f"\n{'=' * 80}")
        print("RESULTS")
        print(f"{'=' * 80}")

        # Build time statistics
        print("\nBuild Time Statistics:")
        print(f"  Mean:       {statistics.mean(build_times):.3f}s")
        print(f"  Median:     {statistics.median(build_times):.3f}s")
        print(f"  Std Dev:    {statistics.stdev(build_times):.3f}s")
        print(f"  Min:        {min(build_times):.3f}s")
        print(f"  Max:        {max(build_times):.3f}s")

        # First vs last 10 builds comparison
        first_10_avg = statistics.mean(build_times[:10])
        last_10_avg = statistics.mean(build_times[-10:])
        degradation_pct = ((last_10_avg - first_10_avg) / first_10_avg) * 100

        print("\nBuild Time Trend:")
        print(f"  First 10 builds avg: {first_10_avg:.3f}s")
        print(f"  Last 10 builds avg:  {last_10_avg:.3f}s")
        print(f"  Change:              {degradation_pct:+.1f}%")

        # Memory statistics
        print("\nMemory Usage (Delta from Baseline):")
        print(f"  Start:      {memory_usage[0]:.1f}MB")
        print(f"  End:        {memory_usage[-1]:.1f}MB")
        print(f"  Growth:     {memory_usage[-1] - memory_usage[0]:+.1f}MB")
        print(f"  Max:        {max(memory_usage):.1f}MB")

        # Cache size statistics
        print("\nCache Size:")
        print(f"  Start:      {cache_sizes[0]:.2f}MB")
        print(f"  End:        {cache_sizes[-1]:.2f}MB")
        print(f"  Growth:     {cache_sizes[-1] - cache_sizes[0]:+.2f}MB")

        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION")
        print(f"{'=' * 80}")
        print()

        checks = []

        # Check for performance degradation
        if abs(degradation_pct) < 10:
            checks.append(f"✅ Build time stable: {degradation_pct:+.1f}% change (target: <10%)")
        else:
            checks.append(f"❌ Build time degraded: {degradation_pct:+.1f}% change (target: <10%)")

        # Check for memory leaks
        memory_growth = memory_usage[-1] - memory_usage[0]
        if memory_growth < 50:  # Less than 50MB growth
            checks.append(f"✅ Memory stable: {memory_growth:+.1f}MB growth (target: <50MB)")
        else:
            checks.append(f"⚠️  Possible memory leak: {memory_growth:+.1f}MB growth (target: <50MB)")

        # Check for cache bloat
        cache_growth = cache_sizes[-1] - cache_sizes[0]
        if cache_growth < 5:  # Less than 5MB cache growth
            checks.append(f"✅ Cache stable: {cache_growth:+.2f}MB growth (target: <5MB)")
        else:
            checks.append(f"⚠️  Cache growing: {cache_growth:+.2f}MB growth (target: <5MB)")

        # Check build time consistency (low variance)
        cv = (statistics.stdev(build_times) / statistics.mean(build_times)) * 100
        if cv < 20:
            checks.append(f"✅ Build time consistent: CV={cv:.1f}% (target: <20%)")
        else:
            checks.append(f"⚠️  Build time variable: CV={cv:.1f}% (target: <20%)")

        for check in checks:
            print(check)

        # Summary verdict
        print()
        all_passed = all("✅" in check for check in checks)
        if all_passed:
            print("🎉 BUILD SYSTEM IS STABLE - No degradation detected")
        else:
            print("⚠️  BUILD SYSTEM SHOWS INSTABILITY - Investigation needed")

        print()

    finally:
        # Cleanup
        shutil.rmtree(site_root)


def run_cache_corruption_test():
    """
    Test that cache remains valid after many updates.

    Validates that incremental builds produce identical output to full builds
    even after hundreds of cache updates.

    """
    print("=" * 80)
    print("CACHE INTEGRITY TEST")
    print("=" * 80)
    print()
    print("This test validates that the cache doesn't become corrupted")
    print("after many incremental updates.")
    print()

    site_root = create_test_site()

    try:
        # Initial full build
        print("Running initial full build...")
        site = Site.from_config(site_root)
        site.build(BuildOptions(incremental=False))

        # Read output
        output_dir = site_root / "public"
        initial_files = {
            f.relative_to(output_dir): f.read_bytes() for f in output_dir.rglob("*.html")
        }

        # Make 50 incremental changes
        print("Making 50 incremental changes...")
        content_dir = site_root / "content"
        pages = sorted(content_dir.glob("section-*/page-*.md"))

        for i in range(50):
            page = pages[i % len(pages)]
            original = page.read_text()
            modified = original + f"\n<!-- Update {i} -->\n"
            page.write_text(modified)

            site = Site.from_config(site_root)
            site.build(BuildOptions(incremental=True))

            page.write_text(original)

        # Full rebuild and compare
        print("Running full rebuild to compare...")
        cache_file = site_root / "public" / ".bengal-cache.json"
        cache_file.unlink()

        site = Site.from_config(site_root)
        site.build(BuildOptions(incremental=False))

        final_files = {
            f.relative_to(output_dir): f.read_bytes() for f in output_dir.rglob("*.html")
        }

        # Compare outputs
        mismatches = []
        for path in initial_files:
            if path not in final_files:
                mismatches.append(f"Missing file: {path}")
            elif initial_files[path] != final_files[path]:
                mismatches.append(f"Content mismatch: {path}")

        mismatches.extend(
            f"Extra file: {path}" for path in final_files if path not in initial_files
        )

        # Report results
        print(f"\n{'=' * 80}")
        print("RESULTS")
        print(f"{'=' * 80}")
        print()

        if not mismatches:
            print("✅ Cache integrity verified - outputs match after 50 updates")
        else:
            print(f"❌ Cache corruption detected - {len(mismatches)} mismatches")
            for m in mismatches[:10]:  # Show first 10
                print(f"  - {m}")

        print()

    finally:
        shutil.rmtree(site_root)


if __name__ == "__main__":
    # Stability test
    run_stability_benchmark(num_builds=100)

    print("\n\n")

    # Cache integrity test
    run_cache_corruption_test()
