#!/usr/bin/env python3
"""Profile Bengal build phases across page counts to identify super-linear scaling.

Creates temporary sites at 256, 512, and 1024 pages, instruments per-phase timing
via BuildOptions callbacks, and runs cProfile on the 1024-page build.

Run with:
    cd /path/to/bengal && uv run python benchmarks/profile_phases.py

Output:
    - Per-phase timing table at 256, 512, 1024 pages
    - Scaling ratio analysis (identifies super-linear phases)
    - Top 30 functions by cumulative time (cProfile, 1024 pages)
    - Post-processing breakdown
"""

from __future__ import annotations

import cProfile
import io
import pstats
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

PHASE_GROUPS = {
    "Discovery": [
        "fonts",
        "template_validation",
        "discovery",
        "cache_metadata",
        "config_check",
        "incremental_filter",
    ],
    "Content": [
        "sections",
        "taxonomies",
        "taxonomy_index",
        "menus",
        "related_posts",
        "query_indexes",
        "update_pages_list",
        "variant_filter",
        "url_collision",
    ],
    "Parsing": ["parse_content", "snapshot"],
    "Rendering": ["assets", "render", "update_site_pages", "track_assets"],
    "Finalization": ["postprocess", "cache_save", "collect_stats", "finalize"],
    "Health": ["health_check"],
}


@dataclass
class PhaseTimer:
    """Collects per-phase durations from build callbacks."""

    phases: dict[str, float] = field(default_factory=dict)
    _starts: dict[str, float] = field(default_factory=dict)

    def on_start(self, name: str) -> None:
        self._starts[name] = time.perf_counter()

    def on_complete(self, name: str, duration_ms: float, _details: str) -> None:
        self.phases[name] = duration_ms

    def group_totals(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        claimed: set[str] = set()
        for group, keys in PHASE_GROUPS.items():
            total = 0.0
            for k in keys:
                for phase_name, ms in self.phases.items():
                    norm = phase_name.lower().replace(" ", "_").replace("-", "_")
                    if norm == k or k in norm:
                        total += ms
                        claimed.add(phase_name)
                        break
            totals[group] = total

        unclaimed = sum(ms for name, ms in self.phases.items() if name not in claimed)
        if unclaimed > 0.5:
            totals["Other"] = unclaimed
        return totals


def create_site(num_pages: int) -> Path:
    """Create a temporary site directory with the given number of pages."""
    tmp = Path(tempfile.mkdtemp(prefix=f"bengal_profile_{num_pages}_"))
    content = tmp / "content" / "posts"
    content.mkdir(parents=True)
    (tmp / "public").mkdir()

    for i in range(num_pages):
        tag_a = f"tag-{i % 10}"
        tag_b = f"category-{i % 7}"
        page = f"""---
title: "Post {i}: Benchmark Article"
date: 2025-06-{(i % 28) + 1:02d}
tags: [{tag_a}, {tag_b}]
categories: [blog]
description: "Benchmark post number {i} for profiling."
---

# Post {i}

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident,
sunt in culpa qui officia deserunt mollit anim id est laborum.

Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam varius,
turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis
sollicitudin mauris. Integer in mauris eu nibh euismod gravida.
"""
        (content / f"post-{i}.md").write_text(page)

    (tmp / "content" / "_index.md").write_text("---\ntitle: Home\n---\n\n# Benchmark Site\n")
    (tmp / "content" / "posts" / "_index.md").write_text("---\ntitle: Posts\n---\n")

    (tmp / "bengal.toml").write_text("""\
title = "Phase Profile Benchmark"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false

[features]
sitemap = true
rss = true
json_index = true
""")
    return tmp


def run_timed_build(site_dir: Path) -> tuple[dict[str, float], dict[str, float], float]:
    """Run a build with phase callbacks, return (raw phases, group totals, wall time)."""
    site = Site.from_config(site_dir)

    for d in [site.output_dir, site_dir / ".bengal"]:
        if d.exists():
            shutil.rmtree(d)

    timer = PhaseTimer()
    opts = BuildOptions(
        force_sequential=True,
        incremental=False,
        verbose=False,
        quiet=True,
        on_phase_start=timer.on_start,
        on_phase_complete=timer.on_complete,
    )

    wall_start = time.perf_counter()
    site.build(options=opts)
    wall_s = time.perf_counter() - wall_start

    return timer.phases, timer.group_totals(), wall_s


def run_profiled_build(
    site_dir: Path,
) -> tuple[pstats.Stats, dict[str, float], dict[str, float], float]:
    """Run the 1024-page build under cProfile."""
    site = Site.from_config(site_dir)

    for d in [site.output_dir, site_dir / ".bengal"]:
        if d.exists():
            shutil.rmtree(d)

    timer = PhaseTimer()
    opts = BuildOptions(
        force_sequential=True,
        incremental=False,
        verbose=False,
        quiet=True,
        on_phase_start=timer.on_start,
        on_phase_complete=timer.on_complete,
    )

    prof = cProfile.Profile()
    wall_start = time.perf_counter()
    prof.enable()
    site.build(options=opts)
    prof.disable()
    wall_s = time.perf_counter() - wall_start

    stats = pstats.Stats(prof)
    return stats, timer.phases, timer.group_totals(), wall_s


def print_separator(char: str = "=", width: int = 90) -> None:
    print(char * width)


def print_scaling_table(
    results: dict[int, tuple[dict[str, float], dict[str, float], float]],
) -> None:
    """Print per-phase timing across page counts with scaling ratios."""
    sizes = sorted(results.keys())
    groups = [*list(PHASE_GROUPS.keys()), "Other"]

    print_separator()
    print("PER-PHASE TIMING (ms) — SCALING ANALYSIS")
    print_separator()

    header = f"{'Phase':<16}"
    for s in sizes:
        header += f"  {s:>6} pages"
    if len(sizes) >= 2:
        header += f"  {'ratio':>8}"
        header += f"  {'scaling':>10}"
    print(header)
    print_separator("-")

    for group in groups:
        vals = [results[s][1].get(group, 0.0) for s in sizes]
        if all(v < 0.5 for v in vals):
            continue

        row = f"{group:<16}"
        for v in vals:
            row += f"  {v:>10.1f}"

        if len(sizes) >= 2 and vals[-2] > 1.0:
            ratio = vals[-1] / vals[-2]
            row += f"  {ratio:>7.2f}x"
            if ratio > 2.2:
                row += f"  {'SUPER-LIN':>10}"
            elif ratio > 1.8:
                row += f"  {'~linear':>10}"
            else:
                row += f"  {'sub-lin':>10}"
        print(row)

    print_separator("-")
    wall_vals = [results[s][2] * 1000 for s in sizes]
    row = f"{'WALL TOTAL':<16}"
    for v in wall_vals:
        row += f"  {v:>10.1f}"
    if len(sizes) >= 2 and wall_vals[-2] > 1.0:
        ratio = wall_vals[-1] / wall_vals[-2]
        row += f"  {ratio:>7.2f}x"
    print(row)

    print()
    for s in sizes:
        wall = results[s][2]
        print(f"  {s} pages: {wall:.2f}s  ({s / wall:.0f} pages/sec)")
    print()


def print_raw_phases(phases: dict[str, float]) -> None:
    """Print individual phase timings for the largest build."""
    print_separator()
    print("INDIVIDUAL PHASE TIMINGS (1024 pages)")
    print_separator()
    for name, ms in sorted(phases.items(), key=lambda kv: -kv[1]):
        pct = ms / sum(phases.values()) * 100 if sum(phases.values()) > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {name:<30} {ms:>8.1f}ms  ({pct:>5.1f}%)  {bar}")
    print()


def print_cprofile_top(stats: pstats.Stats, n: int = 30) -> None:
    """Print top N functions by cumulative time."""
    print_separator()
    print(f"TOP {n} FUNCTIONS BY CUMULATIVE TIME (cProfile, 1024 pages)")
    print_separator()
    buf = io.StringIO()
    stats.stream = buf
    stats.sort_stats("cumulative")
    stats.print_stats(n)
    print(buf.getvalue())


def print_postprocess_breakdown(phases: dict[str, float]) -> None:
    """Highlight post-processing / output generation phases."""
    print_separator()
    print("POST-PROCESSING / OUTPUT GENERATION BREAKDOWN")
    print_separator()
    postprocess_keys = ["postprocess", "cache_save", "collect_stats", "finalize"]
    total_build = sum(phases.values())
    postprocess_total = 0.0
    for name, ms in sorted(phases.items(), key=lambda kv: -kv[1]):
        norm = name.lower().replace(" ", "_").replace("-", "_")
        if any(k in norm for k in postprocess_keys):
            print(f"  {name:<30} {ms:>8.1f}ms")
            postprocess_total += ms

    print(f"  {'─' * 50}")
    pct = postprocess_total / total_build * 100 if total_build > 0 else 0
    print(f"  {'Finalization total':<30} {postprocess_total:>8.1f}ms  ({pct:.1f}% of build)")
    print()


def main() -> int:
    page_counts = [256, 512, 1024]
    results: dict[int, tuple[dict[str, float], dict[str, float], float]] = {}
    site_dirs: dict[int, Path] = {}

    print("Bengal Build Phase Profiler")
    print_separator()
    print()

    try:
        for n in page_counts:
            print(f"Creating {n}-page site...", end=" ", flush=True)
            site_dirs[n] = create_site(n)
            print(f"done ({site_dirs[n]})")

        for n in page_counts[:-1]:
            print(f"\nBuilding {n} pages (sequential, full)...")
            phases, groups, wall = run_timed_build(site_dirs[n])
            results[n] = (phases, groups, wall)
            print(f"  -> {wall:.2f}s  ({n / wall:.0f} pages/sec)")

        n = page_counts[-1]
        print(f"\nBuilding {n} pages (sequential, full, cProfile)...")
        cprof_stats, phases_1024, groups_1024, wall_1024 = run_profiled_build(site_dirs[n])
        results[n] = (phases_1024, groups_1024, wall_1024)
        print(f"  -> {wall_1024:.2f}s  ({n / wall_1024:.0f} pages/sec)")

        # Save cProfile output
        prof_dir = Path(__file__).parent / ".benchmarks"
        prof_dir.mkdir(parents=True, exist_ok=True)
        prof_file = prof_dir / "phase_profile_1024.prof"
        cprof_stats.dump_stats(str(prof_file))
        print(f"\ncProfile data saved to {prof_file}")

        print()
        print_scaling_table(results)
        print_raw_phases(phases_1024)
        print_postprocess_breakdown(phases_1024)
        print_cprofile_top(cprof_stats, n=30)

    finally:
        for d in site_dirs.values():
            shutil.rmtree(d, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
