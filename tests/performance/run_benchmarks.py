#!/usr/bin/env python3
"""
Automated benchmark runner for Bengal SSG.

Runs performance benchmarks in sequence and generates a summary report.

Usage:
    # Quick validation (10-15 min)
    python run_benchmarks.py --quick

    # Full suite including scale tests (2-3 hours)
    python run_benchmarks.py --full

    # Specific benchmarks
    python run_benchmarks.py --benchmarks parallel,incremental,scale

    # Output to file
    python run_benchmarks.py --quick --output results.txt
"""

import argparse
import contextlib
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Benchmark definitions
BENCHMARKS = {
    "parallel": {
        "name": "Parallel Processing",
        "script": "benchmark_parallel.py",
        "duration_min": 2,
        "suite": "quick",
    },
    "incremental": {
        "name": "Incremental Builds (Small Scale)",
        "script": "benchmark_incremental.py",
        "duration_min": 5,
        "suite": "quick",
    },
    "full_build": {
        "name": "Full Build Performance",
        "script": "benchmark_full_build.py",
        "duration_min": 3,
        "suite": "quick",
    },
    "template_complexity": {
        "name": "Template Complexity Impact",
        "script": "benchmark_template_complexity.py",
        "duration_min": 5,
        "suite": "quick",
    },
    "scale": {
        "name": "Incremental Build Scaling (1K-10K pages)",
        "script": "benchmark_incremental_scale.py",
        "duration_min": 60,
        "suite": "full",
    },
    "stability": {
        "name": "Build Stability (100 builds)",
        "script": "benchmark_build_stability.py",
        "duration_min": 15,
        "suite": "full",
    },
    "realistic_scale": {
        "name": "Realistic Content at Scale",
        "script": "benchmark_realistic_scale.py",
        "duration_min": 10,
        "suite": "full",
    },
    "ssg_comparison": {
        "name": "SSG Comparison (vs Hugo, Eleventy, etc.)",
        "script": "benchmark_ssg_comparison.py",
        "duration_min": 45,
        "suite": "comparison",
    },
}


def run_benchmark(script_name: str, output_file=None) -> dict:
    """
    Run a single benchmark script.

    Args:
        script_name: Name of the benchmark script
        output_file: Optional file to write output to

    Returns:
        Dict with execution results

    """
    script_path = Path(__file__).parent / script_name

    print(f"Running {script_name}...")
    print("-" * 80)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        elapsed = time.time() - start_time

        # Print output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        # Write to file if requested
        if output_file:
            output_file.write(f"\n{'=' * 80}\n")
            output_file.write(f"{script_name}\n")
            output_file.write(f"{'=' * 80}\n\n")
            output_file.write(result.stdout)
            if result.stderr:
                output_file.write("\nSTDERR:\n")
                output_file.write(result.stderr)

        return {
            "script": script_name,
            "success": result.returncode == 0,
            "duration": elapsed,
            "returncode": result.returncode,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"ERROR: {e}")

        return {
            "script": script_name,
            "success": False,
            "duration": elapsed,
            "error": str(e),
        }


def run_benchmark_suite(benchmarks_to_run: list[str], output_path: str | None = None):
    """
    Run a suite of benchmarks and generate summary.

    Args:
        benchmarks_to_run: List of benchmark keys to run
        output_path: Optional file path to write results

    """
    # Use context manager for file handling
    with open(output_path, "w") if output_path else contextlib.nullcontext() as output_file:
        if output_file:
            output_file.write("Bengal SSG Performance Benchmarks\n")
            output_file.write(f"Generated: {datetime.now().isoformat()}\n")
            output_file.write(f"{'=' * 80}\n\n")
        print("=" * 80)
        print("BENGAL SSG - PERFORMANCE BENCHMARK SUITE")
        print("=" * 80)
        print()
        print(f"Running {len(benchmarks_to_run)} benchmarks")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Estimate duration
        total_minutes = sum(
            BENCHMARKS[key]["duration_min"] for key in benchmarks_to_run if key in BENCHMARKS
        )
        print(f"Estimated duration: {total_minutes} minutes")
        print()

        # Run each benchmark
        results = []
        start_time = time.time()

        for i, key in enumerate(benchmarks_to_run, 1):
            if key not in BENCHMARKS:
                print(f"WARNING: Unknown benchmark '{key}', skipping")
                continue

            bench = BENCHMARKS[key]
            print(f"\n[{i}/{len(benchmarks_to_run)}] {bench['name']}")
            print(f"Expected duration: ~{bench['duration_min']} minutes")
            print()

            result = run_benchmark(bench["script"], output_file)
            results.append({**result, "name": bench["name"]})

            print()
            print(f"✓ Completed in {result['duration']:.1f} seconds")
            print()

        total_duration = time.time() - start_time

        # Print summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUITE SUMMARY")
        print("=" * 80)
        print()
        print(f"{'Benchmark':<45} {'Duration':<12} {'Status':<10}")
        print("-" * 80)

        for r in results:
            status = "✅ PASS" if r["success"] else "❌ FAIL"
            duration_str = f"{r['duration']:.1f}s"
            print(f"{r['name']:<45} {duration_str:<12} {status:<10}")

        print()
        print(f"Total duration: {total_duration / 60:.1f} minutes")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Success/failure counts
        passed = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        print()
        if failed == 0:
            print(f"🎉 All {passed} benchmarks passed!")
        else:
            print(f"⚠️  {passed} passed, {failed} failed")

        print()

        if output_file:
            output_file.write(f"\n{'=' * 80}\n")
            output_file.write("SUMMARY\n")
            output_file.write(f"{'=' * 80}\n\n")
            output_file.write(f"Total duration: {total_duration / 60:.1f} minutes\n")
            output_file.write(f"Passed: {passed}, Failed: {failed}\n")
            print(f"Full results written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Bengal SSG performance benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation suite (10-15 min)",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full suite including scale tests (2-3 hours)",
    )

    parser.add_argument(
        "--benchmarks",
        type=str,
        help="Comma-separated list of specific benchmarks to run",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available benchmarks and exit",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Write results to file",
    )

    args = parser.parse_args()

    # List benchmarks
    if args.list:
        print("Available benchmarks:")
        print()
        for key, bench in BENCHMARKS.items():
            print(f"  {key:<20} - {bench['name']}")
            print(f"  {'':<20}   Duration: ~{bench['duration_min']} min, Suite: {bench['suite']}")
            print()
        return 0

    # Determine which benchmarks to run
    benchmarks_to_run = []

    if args.benchmarks:
        # Specific benchmarks
        benchmarks_to_run = [b.strip() for b in args.benchmarks.split(",")]
    elif args.quick:
        # Quick suite
        benchmarks_to_run = [key for key, bench in BENCHMARKS.items() if bench["suite"] == "quick"]
    elif args.full:
        # Full suite (quick + scale tests)
        benchmarks_to_run = [
            key for key, bench in BENCHMARKS.items() if bench["suite"] in ["quick", "full"]
        ]
    else:
        # Default: quick suite
        benchmarks_to_run = [key for key, bench in BENCHMARKS.items() if bench["suite"] == "quick"]

    if not benchmarks_to_run:
        print("ERROR: No benchmarks selected")
        parser.print_help()
        return 1

    # Run benchmarks
    run_benchmark_suite(benchmarks_to_run, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
