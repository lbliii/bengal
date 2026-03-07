#!/usr/bin/env python3
"""Profile Bengal's rendering pipeline to identify performance bottlenecks.

Runs a full build in-process with cProfile to capture where time is spent.
Use with --profile-templates for Bengal's built-in template profiler
(slowest templates/template functions).

Run with:
    # CPU profile (cProfile) - saves to .benchmarks/cpu_profile.prof
    uv run python benchmarks/profile_render.py --profile

    # Profile + template profiling (shows slow templates/functions)
    uv run python benchmarks/profile_render.py --profile --profile-templates

    # Use a specific site
    uv run python benchmarks/profile_render.py --profile --site /path/to/site

    # View saved profile
    python -m pstats benchmarks/.benchmarks/cpu_profile.prof
    # Then: sort cumtime, stats 30
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def create_test_site(num_pages: int = 100) -> Path:
    """Create minimal test site for profiling."""
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "content" / "posts").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-01-15
tags: [tag{i % 5}]
---

# Post {i}

Lorem ipsum dolor sit amet. Consectetur adipiscing elit.
"""
        (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(content)

    (temp_dir / "content" / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")
    (temp_dir / "bengal.toml").write_text("""
title = "Profile Benchmark"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
""")
    return temp_dir


def run_build(site_dir: Path, profile_templates: bool = False) -> dict:
    """Run full build and return timing breakdown."""
    site = Site.from_config(site_dir)
    if site.output_dir.exists():
        shutil.rmtree(site.output_dir)
    if (site_dir / ".bengal").exists():
        shutil.rmtree(site_dir / ".bengal")

    start = time.perf_counter()
    build_stats = site.build(
        BuildOptions(
            force_sequential=False,
            incremental=False,
            verbose=False,
            profile_templates=profile_templates,
        )
    )
    total = time.perf_counter() - start

    return {
        "total_s": total,
        "discovery_ms": build_stats.discovery_time_ms,
        "taxonomy_ms": build_stats.taxonomy_time_ms,
        "rendering_ms": build_stats.rendering_time_ms,
        "assets_ms": build_stats.assets_time_ms,
        "postprocess_ms": build_stats.postprocess_time_ms,
        "pages": len(site.pages),
    }


def print_phase_breakdown(stats: dict) -> None:
    """Print phase timing breakdown."""
    total_ms = stats["total_s"] * 1000
    print("\n" + "=" * 60)
    print("PHASE BREAKDOWN")
    print("=" * 60)
    print(
        f"  Discovery:     {stats['discovery_ms']:>8.1f}ms  ({stats['discovery_ms'] / total_ms * 100:>5.1f}%)"
    )
    print(
        f"  Taxonomy:      {stats['taxonomy_ms']:>8.1f}ms  ({stats['taxonomy_ms'] / total_ms * 100:>5.1f}%)"
    )
    print(
        f"  Rendering:   {stats['rendering_ms']:>8.1f}ms  ({stats['rendering_ms'] / total_ms * 100:>5.1f}%)"
    )
    print(
        f"  Assets:        {stats['assets_ms']:>8.1f}ms  ({stats['assets_ms'] / total_ms * 100:>5.1f}%)"
    )
    print(
        f"  Postprocess:   {stats['postprocess_ms']:>8.1f}ms  ({stats['postprocess_ms'] / total_ms * 100:>5.1f}%)"
    )
    print(f"  TOTAL:         {total_ms:>8.1f}ms")
    print(f"\n  Throughput: {stats['pages'] / stats['total_s']:.1f} pages/sec")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile Bengal rendering")
    parser.add_argument(
        "--site",
        type=Path,
        default=None,
        help="Site directory (default: create temp 100-page site)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with cProfile, save to .benchmarks/cpu_profile.prof",
    )
    parser.add_argument(
        "--profile-templates",
        action="store_true",
        help="Enable Bengal template profiler (shows slow templates/functions)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=100,
        help="Pages for temp site (default: 100)",
    )

    args = parser.parse_args()

    if args.site:
        site_dir = args.site
        if not site_dir.exists():
            print(f"❌ Site not found: {site_dir}")
            return 1
        cleanup = False
    else:
        site_dir = create_test_site(args.pages)
        cleanup = True

    def _run() -> None:
        stats = run_build(site_dir, profile_templates=args.profile_templates)
        print_phase_breakdown(stats)

    try:
        if args.profile:
            import cProfile

            prof_dir = Path(__file__).parent / ".benchmarks"
            prof_dir.mkdir(parents=True, exist_ok=True)
            prof_file = prof_dir / "cpu_profile.prof"

            cProfile.runctx(
                "_run()",
                globals={"site_dir": site_dir, "args": args, "_run": _run},
                locals={},
                filename=str(prof_file),
            )

            print(f"\nProfile saved to {prof_file}")
            print("View with: python -m pstats", prof_file)
            print("  Then: sort cumtime, stats 30")
        else:
            _run()
    finally:
        if cleanup:
            shutil.rmtree(site_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
