#!/usr/bin/env python3
"""
Benchmark different Bengal build modes for cold builds.

Compares:
1. Standard build (parallel)
2. Standard build (sequential / --no-parallel)
3. Pipeline build (--pipeline)
4. Fast mode (--fast)

Each run:
- Cleans cache completely (ensures cold build)
- Times the build
- Captures key metrics
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BuildResult:
    """Result of a single build run."""

    name: str
    command: str
    elapsed_seconds: float
    exit_code: int
    success: bool
    pages_rendered: int | None = None
    output_lines: list[str] = field(default_factory=list)
    error_output: str = ""

    def __str__(self) -> str:
        status = "✅" if self.success else "❌"
        pages = f" ({self.pages_rendered} pages)" if self.pages_rendered else ""
        return f"{status} {self.name}: {self.elapsed_seconds:.2f}s{pages}"


def clean_cache(site_dir: Path) -> None:
    """Clean cache and output directories for a cold build."""
    cache_dir = site_dir / ".bengal"
    output_dir = site_dir / "public"

    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)


def run_build(site_dir: Path, name: str, *args: str) -> BuildResult:
    """Run a build with given arguments and measure time."""
    cmd = ["bengal", "build", "--verbose", *args, "."]
    cmd_str = " ".join(cmd)

    print(f"\n🔨 {name}...")

    # Clean cache first
    clean_cache(site_dir)

    # Run build
    start_time = time.time()
    result = subprocess.run(
        cmd,
        cwd=site_dir,
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - start_time

    # Parse output for page count
    pages_rendered = None
    output_lines = result.stdout.splitlines()
    for line in output_lines:
        if "pages" in line.lower() and ("rendered" in line.lower() or "built" in line.lower()):
            import re

            match = re.search(r"(\d+)\s*pages", line, re.IGNORECASE)
            if match:
                pages_rendered = int(match.group(1))
                break
        if "total_pages" in line.lower():
            import re

            match = re.search(r"total_pages[=:]\s*(\d+)", line, re.IGNORECASE)
            if match:
                pages_rendered = int(match.group(1))
                break

    build_result = BuildResult(
        name=name,
        command=cmd_str,
        elapsed_seconds=elapsed,
        exit_code=result.returncode,
        success=result.returncode == 0,
        pages_rendered=pages_rendered,
        output_lines=output_lines[-20:],
        error_output=result.stderr[:500] if result.stderr else "",
    )

    status = "✅" if build_result.success else "❌"
    print(f"   {status} {elapsed:.2f}s")

    return build_result


def run_benchmarks(site_dir: Path, iterations: int = 1) -> list[BuildResult]:
    """Run all benchmark configurations."""
    results: list[BuildResult] = []

    configs = [
        ("Standard (parallel)", []),
        ("Standard (no-parallel)", ["--no-parallel"]),
        ("Pipeline (--pipeline)", ["--pipeline"]),
        ("Fast mode (--fast)", ["--fast"]),
    ]

    for iteration in range(iterations):
        if iterations > 1:
            print(f"\n{'─' * 40}")
            print(f"Iteration {iteration + 1}/{iterations}")
            print(f"{'─' * 40}")

        for name, args in configs:
            run_name = f"{name}" if iterations == 1 else f"{name} #{iteration + 1}"
            result = run_build(site_dir, run_name, *args)
            results.append(result)
            time.sleep(0.5)

    return results


def print_summary(results: list[BuildResult]) -> None:
    """Print a summary comparison of all builds."""
    print("\n")
    print("═" * 70)
    print("📊 BENCHMARK SUMMARY - Cold Build Comparison")
    print("═" * 70)

    # Group by base name (remove iteration suffix)
    from collections import defaultdict

    mode_results: dict[str, list[BuildResult]] = defaultdict(list)

    for result in results:
        base_name = result.name.split(" #")[0]  # Remove iteration suffix
        mode_results[base_name].append(result)

    # Calculate stats for each mode
    stats = []
    for mode, mode_runs in mode_results.items():
        successful = [r for r in mode_runs if r.success]
        if successful:
            times = [r.elapsed_seconds for r in successful]
            avg = sum(times) / len(times)
            min_t = min(times)
            max_t = max(times)
            pages = successful[0].pages_rendered or 0
            stats.append(
                {
                    "mode": mode,
                    "avg": avg,
                    "min": min_t,
                    "max": max_t,
                    "pages": pages,
                    "runs": len(successful),
                    "success": True,
                }
            )
        else:
            stats.append(
                {
                    "mode": mode,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "pages": 0,
                    "runs": 0,
                    "success": False,
                }
            )

    # Sort by avg time
    stats.sort(key=lambda x: (not x["success"], x["avg"]))
    baseline = stats[0]["avg"] if stats and stats[0]["avg"] > 0 else 1

    print(f"\n{'Build Mode':<30} {'Avg':>10} {'Min':>10} {'Max':>10} {'Speedup':>10}")
    print("─" * 70)

    for s in stats:
        if s["success"]:
            speedup = baseline / s["avg"] if s["avg"] > 0 else 0
            speedup_str = f"{speedup:.2f}x" if speedup > 0 else "—"
            if s["runs"] > 1:
                print(
                    f"  {s['mode']:<28} {s['avg']:>8.2f}s {s['min']:>8.2f}s {s['max']:>8.2f}s {speedup_str:>10}"
                )
            else:
                print(f"  {s['mode']:<28} {s['avg']:>8.2f}s {'—':>10} {'—':>10} {speedup_str:>10}")
        else:
            print(f"❌ {s['mode']:<28} {'FAILED':>10}")

    print("─" * 70)

    # Winner announcement
    winner = stats[0]
    if winner["success"]:
        print(f"\n🏆 FASTEST: {winner['mode']} at {winner['avg']:.2f}s ({winner['pages']} pages)")

        if len(stats) > 1:
            standard = next((s for s in stats if "Standard (parallel)" in s["mode"]), None)
            pipeline = next((s for s in stats if "Pipeline" in s["mode"]), None)

            if standard and pipeline and standard["success"] and pipeline["success"]:
                diff = standard["avg"] - pipeline["avg"]
                pct = (diff / standard["avg"]) * 100
                print(f"\n📈 Pipeline vs Standard: {diff:.2f}s faster ({pct:.1f}% improvement)")

    print("\n")
    print("📋 Build Mode Descriptions:")
    print("─" * 70)
    print("• Standard (parallel)   : Default orchestrator with ThreadPoolExecutor")
    print("• Standard (no-parallel): Sequential processing, single-threaded")
    print("• Pipeline (--pipeline) : Reactive dataflow with streaming transforms")
    print("• Fast mode (--fast)    : Quiet output + guaranteed parallel")
    print("─" * 70)
    print("\n🔍 Key Insight: The pipeline approach uses lazy stream evaluation")
    print("   with automatic caching at each transformation stage, reducing")
    print("   redundant computation compared to the orchestrator's batch approach.")
    print()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Bengal build modes")
    parser.add_argument(
        "--site",
        type=Path,
        default=Path.cwd() / "site",
        help="Path to site directory (defaults to ./site)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations per build mode",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    if not args.site.exists():
        print(f"❌ Site directory not found: {args.site}")
        return

    print("\n🐅 Bengal Cold Build Benchmark")
    print(f"📁 Site: {args.site}")
    print(f"🔄 Iterations: {args.iterations}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = run_benchmarks(args.site, args.iterations)

    print_summary(results)

    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "site": str(args.site),
            "iterations": args.iterations,
            "results": [
                {
                    "name": r.name,
                    "command": r.command,
                    "elapsed_seconds": r.elapsed_seconds,
                    "success": r.success,
                    "pages_rendered": r.pages_rendered,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(output_data, indent=2))
        print(f"📁 Results saved to: {args.output}")


if __name__ == "__main__":
    main()
