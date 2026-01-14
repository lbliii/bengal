#!/usr/bin/env python
"""
Profile a Bengal site build to find actual bottlenecks.

Usage:
    python profile_site.py /path/to/site [--parallel] [--max-workers N]
"""

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path
from pstats import SortKey


def profile_build(site_path, parallel=True, max_workers=None):
    """Profile a site build and print detailed statistics."""

    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions
    from bengal.utils.observability.logger import LogLevel, configure_logging
    from bengal.utils.paths.paths import BengalPaths

    # Quiet logging for cleaner output
    configure_logging(level=LogLevel.WARNING, track_memory=False)

    # Load site
    print(f"\n{'=' * 60}")
    print("Profiling Bengal Build")
    print(f"{'=' * 60}")
    print(f"Site: {site_path}")
    print(f"Parallel: {parallel}")
    if max_workers:
        print(f"Max Workers: {max_workers}")
    print(f"{'=' * 60}\n")

    site = Site.from_config(Path(site_path).resolve())

    # Override max_workers if specified
    if max_workers:
        site.config["max_workers"] = max_workers

    # Profile the build
    profiler = cProfile.Profile()
    profiler.enable()

    start_time = time.time()
    stats = site.build(BuildOptions(force_sequential=not parallel, quiet=True))
    end_time = time.time()

    profiler.disable()

    # Print build stats
    build_time = end_time - start_time
    print(f"\n{'=' * 60}")
    print("Build Complete")
    print(f"{'=' * 60}")
    print(f"Total pages: {stats.total_pages}")
    print(f"Build time: {build_time:.2f}s")
    print(f"Pages/sec: {stats.total_pages / build_time:.1f}")
    print(f"{'=' * 60}\n")

    # Analyze profiling data
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    print("=" * 60)
    print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 60)
    ps.sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(30)
    print(s.getvalue())

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY INTERNAL TIME")
    print("=" * 60)
    ps.sort_stats(SortKey.TIME)
    ps.print_stats(30)
    print(s.getvalue())

    # Save full profile for detailed analysis using organized directory structure
    site_path_obj = Path(site_path).resolve()
    profile_file = BengalPaths.get_profile_path(site_path_obj, filename="build_profile.stats")
    profiler.dump_stats(profile_file)
    print(f"\n✓ Full profile saved to: {profile_file}")
    print(f"  Analyze with: python -m pstats {profile_file}")
    print(f"  Or use: python tests/performance/analyze_profile.py {profile_file}")

    return build_time, stats.total_pages


def compare_parallel_vs_sequential(site_path):
    """Compare parallel vs sequential builds."""
    print("\n" + "=" * 60)
    print("PARALLEL VS SEQUENTIAL COMPARISON")
    print("=" * 60 + "\n")

    # Sequential build
    print("Running SEQUENTIAL build...")
    seq_time, pages = profile_build(site_path, parallel=False)

    # Parallel build with different worker counts
    for workers in [2, 4, 8]:
        print(f"\nRunning PARALLEL build (max_workers={workers})...")
        par_time, _ = profile_build(site_path, parallel=True, max_workers=workers)

        speedup = seq_time / par_time
        print(f"\n→ Speedup: {speedup:.2f}x ({'faster' if speedup > 1 else 'slower'})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python profile_site.py /path/to/site [--parallel] [--compare]")
        print(
            "       python profile_site.py /path/to/site --compare  (compare parallel vs sequential)"
        )
        sys.exit(1)

    site_path = sys.argv[1]

    if "--compare" in sys.argv:
        compare_parallel_vs_sequential(site_path)
    else:
        parallel = "--parallel" in sys.argv or "--no-parallel" not in sys.argv
        profile_build(site_path, parallel=parallel)
