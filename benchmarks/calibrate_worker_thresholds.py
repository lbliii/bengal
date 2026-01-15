"""
Benchmark suite to calibrate worker auto-tune thresholds.

Measures break-even points and optimal worker counts for each module.
Run with: python -m benchmarks.calibrate_worker_thresholds

Outputs JSON with recommended thresholds per module.

Usage:
    # Run all calibrations
    python -m benchmarks.calibrate_worker_thresholds

    # Run specific calibration
    python -m benchmarks.calibrate_worker_thresholds --module render

    # Quick mode (fewer iterations)
    python -m benchmarks.calibrate_worker_thresholds --quick

See Also:
    - RFC: rfc-unified-worker-autotune.md for design rationale
    - bengal/utils/workers.py for the auto-tune implementation
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


@dataclass
class CalibrationResult:
    """Result of calibrating a module's worker settings.

    Attributes:
        module: Name of the module being calibrated
        workload_type: Type of workload (cpu_bound, io_bound, mixed)
        break_even_threshold: Tasks where parallel beats sequential
        optimal_workers_small: Best workers for small workloads (<50 tasks)
        optimal_workers_large: Best workers for large workloads (>100 tasks)
        max_useful_workers: Beyond this, performance degrades
        speedup_at_optimal: Speedup vs sequential at optimal
        contention_point: Worker count where adding more hurts
        measurements: Raw timing data
    """

    module: str
    workload_type: str
    break_even_threshold: int
    optimal_workers_small: int
    optimal_workers_large: int
    max_useful_workers: int
    speedup_at_optimal: float
    contention_point: int
    measurements: dict = field(default_factory=dict)


def measure_parallel_execution(
    tasks: list[T],
    processor: Callable[[T], None],
    worker_counts: list[int],
    iterations: int = 3,
) -> dict[int, float]:
    """
    Measure execution time for different worker counts.

    Args:
        tasks: List of work items
        processor: Function to process each task
        worker_counts: Worker counts to test (e.g., [1, 2, 4, 6, 8])
        iterations: Number of iterations per worker count

    Returns:
        Dict mapping worker count to median execution time
    """
    results: dict[int, list[float]] = {w: [] for w in worker_counts}

    for workers in worker_counts:
        for _ in range(iterations):
            start = time.perf_counter()

            if workers == 1:
                # Sequential baseline
                for task in tasks:
                    processor(task)
            else:
                # Parallel execution
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    list(executor.map(processor, tasks))

            elapsed = time.perf_counter() - start
            results[workers].append(elapsed)

    # Return median times
    return {w: statistics.median(times) for w, times in results.items()}


def find_break_even_threshold(
    task_generator: Callable[[int], list[T]],
    processor: Callable[[T], None],
    task_counts: list[int] | None = None,
    workers: int = 2,
    iterations: int = 5,
) -> int:
    """
    Find minimum task count where parallelization beats sequential.

    Args:
        task_generator: Function to generate N tasks
        processor: Function to process each task
        task_counts: Task counts to test
        workers: Worker count for parallel test
        iterations: Iterations for timing accuracy

    Returns:
        Minimum task count where parallel is faster
    """
    if task_counts is None:
        task_counts = [2, 5, 10, 20, 50]

    for count in task_counts:
        tasks = task_generator(count)
        times = measure_parallel_execution(tasks, processor, [1, workers], iterations=iterations)

        if times[workers] < times[1]:
            return count

    return task_counts[-1]  # Parallel never faster at tested sizes


def find_optimal_workers(
    tasks: list[T],
    processor: Callable[[T], None],
    worker_counts: list[int] | None = None,
    iterations: int = 3,
) -> tuple[int, float]:
    """
    Find optimal worker count for given tasks.

    Args:
        tasks: List of work items
        processor: Function to process each task
        worker_counts: Worker counts to test
        iterations: Iterations for timing accuracy

    Returns:
        Tuple of (optimal_workers, speedup_vs_sequential)
    """
    if worker_counts is None:
        cpu_count = os.cpu_count() or 4
        worker_counts = [1, 2, 4, 6, 8, min(10, cpu_count), min(12, cpu_count)]

    times = measure_parallel_execution(tasks, processor, worker_counts, iterations)

    # Find minimum time
    best_workers = min(times, key=times.get)  # type: ignore
    best_time = times[best_workers]
    sequential_time = times.get(1, best_time)

    speedup = sequential_time / best_time if best_time > 0 else 1.0

    return best_workers, speedup


def find_contention_point(
    tasks: list[T],
    processor: Callable[[T], None],
    worker_counts: list[int] | None = None,
    iterations: int = 3,
) -> int:
    """
    Find worker count where adding more hurts performance.

    Args:
        tasks: List of work items
        processor: Function to process each task
        worker_counts: Worker counts to test
        iterations: Iterations for timing accuracy

    Returns:
        Worker count at contention point
    """
    if worker_counts is None:
        cpu_count = os.cpu_count() or 4
        worker_counts = sorted([1, 2, 4, 6, 8, 10, 12, min(16, cpu_count * 2)])

    times = measure_parallel_execution(tasks, processor, worker_counts, iterations)

    # Find where performance starts degrading
    prev_time = float("inf")
    for workers in sorted(worker_counts):
        curr_time = times[workers]
        if curr_time > prev_time * 1.1:  # 10% degradation threshold
            return workers - 1 if workers > 1 else workers
        prev_time = curr_time

    return worker_counts[-1]


# =============================================================================
# Synthetic Task Generators (for baseline calibration)
# =============================================================================


def _generate_cpu_tasks(count: int, complexity: int = 1000) -> list[int]:
    """Generate CPU-bound tasks (compute Fibonacci)."""
    return [complexity] * count


def _process_cpu_task(n: int) -> int:
    """CPU-bound task: compute sum of range."""
    return sum(i * i for i in range(n))


def _generate_io_tasks(count: int, size: int = 1000) -> list[bytes]:
    """Generate I/O-bound tasks (data to process)."""
    return [b"x" * size for _ in range(count)]


def _process_io_task(data: bytes) -> int:
    """I/O-simulated task: hash data."""
    import hashlib

    return len(hashlib.sha256(data).digest())


def _generate_mixed_tasks(count: int) -> list[tuple[int, bytes]]:
    """Generate mixed CPU + I/O tasks."""
    return [(500, b"x" * 500) for _ in range(count)]


def _process_mixed_task(task: tuple[int, bytes]) -> int:
    """Mixed task: CPU compute + data hash."""
    n, data = task
    cpu_result = sum(i for i in range(n))
    import hashlib

    io_result = len(hashlib.sha256(data).digest())
    return cpu_result + io_result


# =============================================================================
# Module-Specific Calibrators
# =============================================================================


def calibrate_synthetic_cpu() -> CalibrationResult:
    """Calibrate CPU-bound synthetic workload."""
    print("  Calibrating synthetic CPU-bound workload...")

    # Find break-even threshold
    break_even = find_break_even_threshold(
        lambda n: _generate_cpu_tasks(n, complexity=2000),
        _process_cpu_task,
    )

    # Optimal workers for small workload
    small_tasks = _generate_cpu_tasks(30, complexity=2000)
    opt_small, _ = find_optimal_workers(small_tasks, _process_cpu_task)

    # Optimal workers for large workload
    large_tasks = _generate_cpu_tasks(200, complexity=2000)
    opt_large, speedup = find_optimal_workers(large_tasks, _process_cpu_task)

    # Find contention point
    contention = find_contention_point(large_tasks, _process_cpu_task)

    return CalibrationResult(
        module="synthetic_cpu",
        workload_type="cpu_bound",
        break_even_threshold=break_even,
        optimal_workers_small=opt_small,
        optimal_workers_large=opt_large,
        max_useful_workers=contention,
        speedup_at_optimal=speedup,
        contention_point=contention,
    )


def calibrate_synthetic_io() -> CalibrationResult:
    """Calibrate I/O-bound synthetic workload."""
    print("  Calibrating synthetic I/O-bound workload...")

    # Find break-even threshold
    break_even = find_break_even_threshold(
        lambda n: _generate_io_tasks(n, size=10000),
        _process_io_task,
    )

    # Optimal workers for small workload
    small_tasks = _generate_io_tasks(30, size=10000)
    opt_small, _ = find_optimal_workers(small_tasks, _process_io_task)

    # Optimal workers for large workload
    large_tasks = _generate_io_tasks(200, size=10000)
    opt_large, speedup = find_optimal_workers(large_tasks, _process_io_task)

    # Find contention point
    contention = find_contention_point(large_tasks, _process_io_task)

    return CalibrationResult(
        module="synthetic_io",
        workload_type="io_bound",
        break_even_threshold=break_even,
        optimal_workers_small=opt_small,
        optimal_workers_large=opt_large,
        max_useful_workers=contention,
        speedup_at_optimal=speedup,
        contention_point=contention,
    )


def calibrate_synthetic_mixed() -> CalibrationResult:
    """Calibrate mixed synthetic workload."""
    print("  Calibrating synthetic mixed workload...")

    # Find break-even threshold
    break_even = find_break_even_threshold(
        _generate_mixed_tasks,
        _process_mixed_task,
    )

    # Optimal workers for small workload
    small_tasks = _generate_mixed_tasks(30)
    opt_small, _ = find_optimal_workers(small_tasks, _process_mixed_task)

    # Optimal workers for large workload
    large_tasks = _generate_mixed_tasks(200)
    opt_large, speedup = find_optimal_workers(large_tasks, _process_mixed_task)

    # Find contention point
    contention = find_contention_point(large_tasks, _process_mixed_task)

    return CalibrationResult(
        module="synthetic_mixed",
        workload_type="mixed",
        break_even_threshold=break_even,
        optimal_workers_small=opt_small,
        optimal_workers_large=opt_large,
        max_useful_workers=contention,
        speedup_at_optimal=speedup,
        contention_point=contention,
    )


def calibrate_patitas_parse() -> CalibrationResult | None:
    """Calibrate patitas Markdown parsing."""
    print("  Calibrating patitas parsing...")

    try:
        from bengal.parsing.backends.patitas import parse
    except ImportError:
        print("    Skipped: patitas not available")
        return None

    # Generate markdown documents of varying complexity
    def generate_docs(count: int) -> list[str]:
        base = """# Heading

This is a paragraph with **bold** and *italic* text.

```python
def example():
    return "code block"
```

- List item 1
- List item 2
- List item 3

> A blockquote with some content.

"""
        return [base * 3 for _ in range(count)]  # ~1KB per doc

    def process_doc(doc: str) -> str:
        return parse(doc)

    # Find break-even threshold
    break_even = find_break_even_threshold(generate_docs, process_doc)

    # Optimal workers
    small_docs = generate_docs(30)
    opt_small, _ = find_optimal_workers(small_docs, process_doc)

    large_docs = generate_docs(200)
    opt_large, speedup = find_optimal_workers(large_docs, process_doc)

    contention = find_contention_point(large_docs, process_doc)

    return CalibrationResult(
        module="patitas_parse",
        workload_type="cpu_bound",
        break_even_threshold=break_even,
        optimal_workers_small=opt_small,
        optimal_workers_large=opt_large,
        max_useful_workers=contention,
        speedup_at_optimal=speedup,
        contention_point=contention,
    )


# =============================================================================
# Main Entry Point
# =============================================================================


def run_all_calibrations(quick: bool = False) -> list[CalibrationResult]:
    """Run all calibration benchmarks."""
    print("\n=== Worker Auto-Tune Calibration ===\n")
    print(f"CPU cores detected: {os.cpu_count()}")
    print(f"Mode: {'quick' if quick else 'full'}\n")

    calibrators = [
        calibrate_synthetic_cpu,
        calibrate_synthetic_io,
        calibrate_synthetic_mixed,
        calibrate_patitas_parse,
    ]

    results = []
    for calibrator in calibrators:
        try:
            result = calibrator()
            if result:
                results.append(result)
        except Exception as e:
            print(f"  Error in {calibrator.__name__}: {e}")

    return results


def save_results(results: list[CalibrationResult], output_path: Path) -> None:
    """Save calibration results to JSON."""
    output = {r.module: asdict(r) for r in results}
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to: {output_path}")


def print_summary(results: list[CalibrationResult]) -> None:
    """Print calibration summary."""
    print("\n=== Calibration Summary ===\n")

    for r in results:
        print(f"{r.module} ({r.workload_type}):")
        print(f"  Break-even threshold: {r.break_even_threshold} tasks")
        print(
            f"  Optimal workers: {r.optimal_workers_small} (small) / "
            f"{r.optimal_workers_large} (large)"
        )
        print(f"  Contention point: {r.contention_point} workers")
        print(f"  Max speedup: {r.speedup_at_optimal:.2f}x")
        print()

    # Recommendations
    print("=== Recommendations for _PROFILES ===\n")
    for r in results:
        print(f"# {r.module}")
        print(
            f"# parallel_threshold={r.break_even_threshold}, "
            f"min_workers=2, max_workers={r.optimal_workers_large}, "
            f"cpu_fraction=0.5"
        )
        print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Calibrate worker auto-tune thresholds")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick calibration with fewer iterations",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/calibration_results.json"),
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--module",
        type=str,
        help="Run only specific module calibration",
    )

    args = parser.parse_args()

    results = run_all_calibrations(quick=args.quick)

    if results:
        save_results(results, args.output)
        print_summary(results)
    else:
        print("No calibration results generated.")


if __name__ == "__main__":
    main()
