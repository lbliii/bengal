#!/usr/bin/env python3
"""
Worker Scaling Analysis Benchmark

Tests parallelism efficiency across worker counts to identify:
1. Optimal worker count for different workloads
2. Per-worker overhead (initialization, cache contention)
3. Diminishing returns threshold
4. Lock contention indicators

This benchmark answers the question: "Why might 2 workers be faster than 4?"

Usage:
    python tests/performance/benchmark_worker_scaling.py
    python tests/performance/benchmark_worker_scaling.py --quick  # Fewer iterations
    python tests/performance/benchmark_worker_scaling.py --workers 1,2,4,8

Results are saved to: tests/performance/benchmark_results/worker_scaling/
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure bengal is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class WorkerResult:
    """Results for a single worker count test."""

    worker_count: int
    times: list[float] = field(default_factory=list)
    pages_rendered: int = 0
    init_overhead_ms: float = 0.0

    @property
    def mean_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0.0

    @property
    def std_dev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def pages_per_sec(self) -> float:
        return self.pages_rendered / self.mean_time if self.mean_time > 0 else 0.0

    @property
    def efficiency(self) -> float:
        """Efficiency ratio: actual speedup vs theoretical (1 worker baseline)."""
        # Will be calculated after all results are collected
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_count": self.worker_count,
            "times": self.times,
            "mean_time": self.mean_time,
            "std_dev": self.std_dev,
            "pages_rendered": self.pages_rendered,
            "pages_per_sec": self.pages_per_sec,
            "init_overhead_ms": self.init_overhead_ms,
        }


@dataclass
class WorkloadResult:
    """Results for a workload type across all worker counts."""

    workload_name: str
    workload_description: str
    worker_results: dict[int, WorkerResult] = field(default_factory=dict)
    optimal_workers: int = 0
    peak_throughput: float = 0.0

    def calculate_efficiency(self) -> None:
        """Calculate efficiency ratios relative to 1 worker."""
        if 1 not in self.worker_results:
            return

        baseline = self.worker_results[1].mean_time
        for workers, result in self.worker_results.items():
            if result.mean_time > 0:
                actual_speedup = baseline / result.mean_time
                theoretical_speedup = workers
                # Store efficiency as actual/theoretical (1.0 = perfect scaling)
                result._efficiency = actual_speedup / theoretical_speedup
            else:
                result._efficiency = 0.0

        # Find optimal
        best = max(self.worker_results.items(), key=lambda x: x[1].pages_per_sec, default=(0, None))
        if best[1]:
            self.optimal_workers = best[0]
            self.peak_throughput = best[1].pages_per_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_name": self.workload_name,
            "workload_description": self.workload_description,
            "worker_results": {k: v.to_dict() for k, v in self.worker_results.items()},
            "optimal_workers": self.optimal_workers,
            "peak_throughput": self.peak_throughput,
        }


# =============================================================================
# Test Site Generators
# =============================================================================


def create_code_heavy_site(temp_dir: Path, num_pages: int = 50) -> Path:
    """Create a site with many code blocks (syntax highlighting heavy)."""
    content_dir = temp_dir / "content"
    content_dir.mkdir(parents=True)

    # Languages to cycle through
    languages = ["python", "javascript", "typescript", "rust", "go", "bash", "yaml", "json"]

    for i in range(num_pages):
        lang = languages[i % len(languages)]

        # Generate code samples
        code_blocks = []
        for j in range(5):  # 5 code blocks per page
            if lang == "python":
                code = f'''```python
def function_{j}(x: int, y: int) -> int:
    """Calculate something for iteration {j}."""
    result = x + y * {j}
    for i in range({j + 1}):
        result += i ** 2
    return result

class Handler_{j}:
    def __init__(self):
        self.value = {j}

    def process(self, data: list[str]) -> dict:
        return {{"count": len(data), "id": {j}}}
```'''
            elif lang == "javascript":
                code = f"""```javascript
const handler_{j} = async (req, res) => {{
    const data = await fetch('/api/data/{j}');
    const result = data.json();
    return {{ success: true, id: {j} }};
}};

class Component_{j} extends React.Component {{
    render() {{
        return <div>Item {j}</div>;
    }}
}}
```"""
            elif lang == "rust":
                code = f"""```rust
fn process_{j}(input: &str) -> Result<i32, Error> {{
    let value = input.parse::<i32>()?;
    Ok(value * {j})
}}

struct Handler_{j} {{
    id: u32,
    data: Vec<String>,
}}

impl Handler_{j} {{
    fn new() -> Self {{
        Self {{ id: {j}, data: Vec::new() }}
    }}
}}
```"""
            else:
                code = f"""```{lang}
# Code block {j} for {lang}
# This is sample content for benchmarking
# Multiple lines to simulate real code
value_{j} = "test"
```"""
            code_blocks.append(code)

        content = f"""---
title: Code Heavy Page {i}
date: 2025-01-{(i % 28) + 1:02d}
tags: [benchmark, {lang}]
---

# Code Heavy Page {i}

This page tests syntax highlighting performance with multiple code blocks.

{"".join(code_blocks)}

## Summary

This page contains 5 code blocks in {lang}.
"""
        (content_dir / f"page-{i:03d}.md").write_text(content)

    # Create minimal config
    (temp_dir / "bengal.toml").write_text("""
[site]
title = "Worker Scaling Benchmark - Code Heavy"
baseurl = ""

[build]
parallel = true
validate_links = false
validate_build = false
""")

    return temp_dir


def create_content_light_site(temp_dir: Path, num_pages: int = 50) -> Path:
    """Create a site with simple markdown (minimal processing)."""
    content_dir = temp_dir / "content"
    content_dir.mkdir(parents=True)

    for i in range(num_pages):
        content = f"""---
title: Light Page {i}
date: 2025-01-{(i % 28) + 1:02d}
---

# Light Page {i}

This is a simple page with minimal markdown processing.

Some **bold** and *italic* text. A [link](/page-{(i + 1) % num_pages:03d}/).

- Item 1
- Item 2
- Item 3

That's all.
"""
        (content_dir / f"page-{i:03d}.md").write_text(content)

    (temp_dir / "bengal.toml").write_text("""
[site]
title = "Worker Scaling Benchmark - Light"
baseurl = ""

[build]
parallel = true
validate_links = false
validate_build = false
""")

    return temp_dir


def create_mixed_site(temp_dir: Path, num_pages: int = 50) -> Path:
    """Create a realistic mixed workload site."""
    content_dir = temp_dir / "content"
    (content_dir / "docs").mkdir(parents=True)
    (content_dir / "blog").mkdir(parents=True)

    # 60% docs (code heavy), 40% blog (lighter)
    docs_count = int(num_pages * 0.6)
    blog_count = num_pages - docs_count

    for i in range(docs_count):
        code = f'''```python
def api_endpoint_{i}(request):
    """Handle request for endpoint {i}."""
    data = request.json()
    result = process_data(data)
    return Response(result)
```'''
        content = f"""---
title: API Reference {i}
section: docs
---

# API Endpoint {i}

This endpoint handles requests for resource {i}.

## Usage

{code}

## Parameters

| Name | Type | Description |
|------|------|-------------|
| id | int | Resource ID |
| name | str | Resource name |

## Returns

JSON response with the processed data.
"""
        (content_dir / "docs" / f"api-{i:03d}.md").write_text(content)

    for i in range(blog_count):
        content = f"""---
title: Blog Post {i}
date: 2025-01-{(i % 28) + 1:02d}
tags: [news, updates]
---

# Blog Post {i}

Today we're announcing some exciting updates.

## What's New

We've made several improvements to the platform.

> This is a blockquote with some insight.

Thanks for reading!
"""
        (content_dir / "blog" / f"post-{i:03d}.md").write_text(content)

    (temp_dir / "bengal.toml").write_text("""
[site]
title = "Worker Scaling Benchmark - Mixed"
baseurl = ""

[build]
parallel = true
validate_links = false
validate_build = false
""")

    return temp_dir


# =============================================================================
# Benchmark Runner
# =============================================================================


def run_build_with_workers(site_dir: Path, max_workers: int) -> tuple[float, int, float]:
    """
    Run a build with specific worker count.

    Returns:
        Tuple of (build_time_seconds, pages_rendered, init_overhead_ms)
    """
    # Import here to get fresh state
    from bengal.core.site import Site
    from bengal.orchestration.render import clear_thread_local_pipelines

    # Clear any cached state
    clear_thread_local_pipelines()
    gc.collect()

    # Set worker count via environment (config override)
    os.environ["BENGAL_MAX_WORKERS"] = str(max_workers)

    try:
        # Time the build
        start = time.perf_counter()

        site = Site.from_config(site_dir)
        site.config["max_workers"] = max_workers

        # Run discovery
        site.discover_content()
        site.discover_assets()

        # Run build (the part we care about)
        from bengal.orchestration import BuildOrchestrator

        orchestrator = BuildOrchestrator(site)
        orchestrator.build(quiet=True)

        elapsed = time.perf_counter() - start
        pages = len(site.pages)

        # Rough init overhead estimate (would need profiling for accuracy)
        init_overhead = 0.0  # Placeholder

        return elapsed, pages, init_overhead

    finally:
        os.environ.pop("BENGAL_MAX_WORKERS", None)


def benchmark_workload(
    workload_name: str,
    workload_desc: str,
    site_generator: callable,
    worker_counts: list[int],
    num_pages: int = 50,
    iterations: int = 3,
) -> WorkloadResult:
    """Run benchmark for a specific workload type."""
    result = WorkloadResult(workload_name=workload_name, workload_description=workload_desc)

    for workers in worker_counts:
        print(f"    Testing {workers} worker(s)...", end=" ", flush=True)
        worker_result = WorkerResult(worker_count=workers)

        for i in range(iterations):
            # Create fresh temp site for each run
            temp_dir = Path(tempfile.mkdtemp())
            try:
                site_dir = site_generator(temp_dir, num_pages)
                build_time, pages, init_overhead = run_build_with_workers(site_dir, workers)

                worker_result.times.append(build_time)
                worker_result.pages_rendered = pages
                worker_result.init_overhead_ms = init_overhead

                print(f"[{i + 1}]", end=" ", flush=True)

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        print(f"→ {worker_result.mean_time:.2f}s ({worker_result.pages_per_sec:.0f} pages/sec)")
        result.worker_results[workers] = worker_result

    result.calculate_efficiency()
    return result


# =============================================================================
# Results Output
# =============================================================================


def print_results(results: list[WorkloadResult]) -> None:
    """Print formatted benchmark results."""
    print("\n" + "=" * 90)
    print("WORKER SCALING ANALYSIS RESULTS")
    print("=" * 90)

    for workload in results:
        print(f"\n{'─' * 90}")
        print(f"WORKLOAD: {workload.workload_name}")
        print(f"Description: {workload.workload_description}")
        print(f"{'─' * 90}")

        # Header
        print(
            f"{'Workers':>8} │ {'Time (s)':>10} │ {'Std Dev':>8} │ "
            f"{'Pages/sec':>10} │ {'vs 1 worker':>12} │ {'Efficiency':>10}"
        )
        print("─" * 90)

        baseline_time = workload.worker_results.get(1, WorkerResult(1)).mean_time

        for workers in sorted(workload.worker_results.keys()):
            r = workload.worker_results[workers]
            speedup = baseline_time / r.mean_time if r.mean_time > 0 else 0
            efficiency = speedup / workers if workers > 0 else 0

            # Efficiency indicator
            if efficiency >= 0.8:
                eff_indicator = "🟢"
            elif efficiency >= 0.5:
                eff_indicator = "🟡"
            else:
                eff_indicator = "🔴"

            print(
                f"{workers:>8} │ {r.mean_time:>10.3f} │ {r.std_dev:>8.3f} │ "
                f"{r.pages_per_sec:>10.1f} │ {speedup:>11.2f}x │ "
                f"{efficiency:>8.0%} {eff_indicator}"
            )

        print()
        print(f"  ⭐ Optimal: {workload.optimal_workers} workers")
        print(f"  📈 Peak throughput: {workload.peak_throughput:.1f} pages/sec")

        # Insights
        if workload.optimal_workers < max(workload.worker_results.keys()):
            print(
                f"  ⚠️  Diminishing returns after {workload.optimal_workers} workers "
                "(possible contention)"
            )


def save_results(results: list[WorkloadResult], output_dir: Path) -> Path:
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "python_version": sys.version,
        "workloads": [w.to_dict() for w in results],
        "summary": {
            "optimal_workers_by_workload": {w.workload_name: w.optimal_workers for w in results},
            "peak_throughput_by_workload": {w.workload_name: w.peak_throughput for w in results},
        },
    }

    output_file.write_text(json.dumps(data, indent=2))

    # Also save as latest.json
    (output_dir / "latest.json").write_text(json.dumps(data, indent=2))

    return output_file


def print_summary(results: list[WorkloadResult]) -> None:
    """Print executive summary."""
    print("\n" + "=" * 90)
    print("EXECUTIVE SUMMARY")
    print("=" * 90)

    # Find consensus optimal
    optimal_counts = [w.optimal_workers for w in results]
    from collections import Counter

    most_common = Counter(optimal_counts).most_common(1)[0]

    print(f"\n  Recommended default worker count: {most_common[0]}")
    print(f"  (Optimal for {most_common[1]}/{len(results)} workload types)")

    print("\n  Workload-specific recommendations:")
    for w in results:
        print(f"    • {w.workload_name}: {w.optimal_workers} workers")

    # Check for contention indicators
    contention_detected = False
    for w in results:
        sorted_workers = sorted(w.worker_results.keys())
        if len(sorted_workers) >= 3:
            # Check if more workers = worse performance
            for i in range(len(sorted_workers) - 1):
                w1, w2 = sorted_workers[i], sorted_workers[i + 1]
                if w.worker_results[w2].mean_time > w.worker_results[w1].mean_time * 1.05:
                    if not contention_detected:
                        print("\n  ⚠️  Contention indicators detected:")
                        contention_detected = True
                    print(f"    • {w.workload_name}: {w2} workers slower than {w1} workers")

    if not contention_detected:
        print("\n  ✅ No obvious contention detected (performance scales with workers)")

    print()


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Worker scaling analysis benchmark")
    parser.add_argument(
        "--quick", action="store_true", help="Run fewer iterations (faster but less accurate)"
    )
    parser.add_argument(
        "--workers",
        type=str,
        default="1,2,4,6,8",
        help="Comma-separated worker counts to test (default: 1,2,4,6,8)",
    )
    parser.add_argument("--pages", type=int, default=50, help="Pages per test site (default: 50)")
    parser.add_argument(
        "--iterations", type=int, default=3, help="Iterations per worker count (default: 3)"
    )
    parser.add_argument(
        "--workload",
        type=str,
        choices=["code_heavy", "content_light", "mixed", "all"],
        default="all",
        help="Workload type to test (default: all)",
    )
    args = parser.parse_args()

    worker_counts = [int(w.strip()) for w in args.workers.split(",")]
    iterations = 2 if args.quick else args.iterations
    num_pages = 30 if args.quick else args.pages

    print("=" * 90)
    print("BENGAL SSG - WORKER SCALING ANALYSIS")
    print("=" * 90)
    print()
    print(f"  Worker counts: {worker_counts}")
    print(f"  Pages per site: {num_pages}")
    print(f"  Iterations: {iterations}")
    print(f"  Workload: {args.workload}")
    print()

    workloads = {
        "code_heavy": (
            "Code Heavy",
            "Pages with 5+ code blocks each (syntax highlighting stress test)",
            create_code_heavy_site,
        ),
        "content_light": (
            "Content Light",
            "Simple markdown pages (minimal processing)",
            create_content_light_site,
        ),
        "mixed": (
            "Mixed Realistic",
            "60% docs with code, 40% blog posts (typical documentation site)",
            create_mixed_site,
        ),
    }

    selected = list(workloads.keys()) if args.workload == "all" else [args.workload]

    results = []
    for workload_key in selected:
        name, desc, generator = workloads[workload_key]
        print(f"\n{'─' * 90}")
        print(f"BENCHMARKING: {name}")
        print(f"{'─' * 90}")

        result = benchmark_workload(
            workload_name=name,
            workload_desc=desc,
            site_generator=generator,
            worker_counts=worker_counts,
            num_pages=num_pages,
            iterations=iterations,
        )
        results.append(result)

    # Print and save results
    print_results(results)
    print_summary(results)

    # Save to file
    output_dir = Path(__file__).parent / "benchmark_results" / "worker_scaling"
    output_file = save_results(results, output_dir)
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
