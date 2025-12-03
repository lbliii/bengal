#!/usr/bin/env python3
"""
Benchmark different Bengal build modes for cold builds.

Compares:
1. Standard build (parallel)
2. Standard build (sequential / --no-parallel)
3. Pipeline build (--pipeline)
4. Memory-optimized build (--memory-optimized)
5. Fast mode (--fast)

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
    
    print(f"   🧹 Cleaned cache and output")


def run_build(site_dir: Path, name: str, *args: str) -> BuildResult:
    """Run a build with given arguments and measure time."""
    cmd = ["bengal", "build", "--verbose", *args, "."]
    cmd_str = " ".join(cmd)
    
    print(f"\n{'='*60}")
    print(f"🔨 Running: {name}")
    print(f"   Command: {cmd_str}")
    print(f"{'='*60}")
    
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
            # Try to extract page count
            import re
            match = re.search(r'(\d+)\s*pages', line, re.IGNORECASE)
            if match:
                pages_rendered = int(match.group(1))
                break
        # Also check for summary stats
        if "total_pages" in line.lower():
            import re
            match = re.search(r'total_pages[=:]\s*(\d+)', line, re.IGNORECASE)
            if match:
                pages_rendered = int(match.group(1))
    
    build_result = BuildResult(
        name=name,
        command=cmd_str,
        elapsed_seconds=elapsed,
        exit_code=result.returncode,
        success=result.returncode == 0,
        pages_rendered=pages_rendered,
        output_lines=output_lines[-20:],  # Last 20 lines
        error_output=result.stderr[:500] if result.stderr else "",
    )
    
    # Print immediate result
    print(f"\n{build_result}")
    if result.stderr and result.returncode != 0:
        print(f"   stderr: {result.stderr[:200]}...")
    
    return build_result


def run_benchmarks(site_dir: Path, iterations: int = 1) -> list[BuildResult]:
    """Run all benchmark configurations."""
    results: list[BuildResult] = []
    
    configs = [
        ("Standard (parallel)", []),
        ("Standard (no-parallel)", ["--no-parallel"]),
        ("Pipeline (parallel)", ["--pipeline"]),
        ("Memory-optimized", ["--memory-optimized"]),
        ("Fast mode", ["--fast"]),
    ]
    
    for iteration in range(iterations):
        if iterations > 1:
            print(f"\n{'#'*60}")
            print(f"# ITERATION {iteration + 1}/{iterations}")
            print(f"{'#'*60}")
        
        for name, args in configs:
            run_name = f"{name}" if iterations == 1 else f"{name} (run {iteration + 1})"
            result = run_build(site_dir, run_name, *args)
            results.append(result)
            
            # Brief pause between builds
            time.sleep(1)
    
    return results


def print_summary(results: list[BuildResult]) -> None:
    """Print a summary comparison of all builds."""
    print("\n")
    print("="*70)
    print("📊 BENCHMARK SUMMARY - Cold Build Comparison")
    print("="*70)
    
    # Sort by elapsed time
    sorted_results = sorted(results, key=lambda r: r.elapsed_seconds)
    baseline = sorted_results[0].elapsed_seconds if sorted_results else 1
    
    print(f"\n{'Build Mode':<30} {'Time':>10} {'vs Best':>12} {'Pages':>10}")
    print("-"*70)
    
    for result in sorted_results:
        ratio = result.elapsed_seconds / baseline if baseline > 0 else 0
        pages_str = str(result.pages_rendered) if result.pages_rendered else "?"
        status = "✅" if result.success else "❌"
        ratio_str = f"{ratio:.2f}x" if ratio > 0 else "N/A"
        
        print(f"{status} {result.name:<28} {result.elapsed_seconds:>8.2f}s {ratio_str:>12} {pages_str:>10}")
    
    print("-"*70)
    
    # Calculate averages if multiple iterations
    if len(results) > 5:  # Multiple iterations
        print("\n📈 Average by Build Mode:")
        print("-"*70)
        
        from collections import defaultdict
        mode_times: dict[str, list[float]] = defaultdict(list)
        
        for result in results:
            # Extract base mode name (without iteration number)
            base_name = result.name.split(" (run")[0]
            mode_times[base_name].append(result.elapsed_seconds)
        
        averages = []
        for mode, times in mode_times.items():
            avg = sum(times) / len(times)
            averages.append((mode, avg, min(times), max(times)))
        
        averages.sort(key=lambda x: x[1])
        baseline_avg = averages[0][1] if averages else 1
        
        print(f"\n{'Build Mode':<30} {'Avg':>10} {'Min':>10} {'Max':>10} {'vs Best':>12}")
        print("-"*70)
        
        for mode, avg, min_t, max_t in averages:
            ratio = avg / baseline_avg if baseline_avg > 0 else 0
            ratio_str = f"{ratio:.2f}x"
            print(f"  {mode:<28} {avg:>8.2f}s {min_t:>8.2f}s {max_t:>8.2f}s {ratio_str:>12}")
    
    print("\n")
    
    # Architecture comparison explanation
    print("📋 Build Mode Descriptions:")
    print("-"*70)
    print("• Standard (parallel)   : Default orchestrator-based build with ThreadPoolExecutor")
    print("• Standard (no-parallel): Sequential processing, single-threaded")
    print("• Pipeline (parallel)   : Reactive dataflow pipeline with streaming transforms")
    print("• Memory-optimized      : Streaming build for memory efficiency (batched)")
    print("• Fast mode             : Quiet output + guaranteed parallel + max speed")
    print("-"*70)


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Bengal build modes")
    parser.add_argument(
        "--site",
        type=Path,
        default=Path("/Users/llane/Documents/github/python/bengal/site"),
        help="Path to site directory",
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
    
    # Save to JSON if requested
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

