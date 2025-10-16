"""
Memory profiling utilities for benchmark analysis.

Tracks peak memory usage during builds to identify memory-related bottlenecks
and help understand scale degradation (141 pps @ 1K pages → 29 pps @ 10K pages).
"""

import json
import subprocess
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class MemoryStats:
    """Memory statistics from a single build run."""

    peak_mb: float
    """Peak memory usage in megabytes."""

    current_mb: float
    """Current memory usage when measurement ended."""

    page_count: int
    """Number of pages in the scenario."""

    memory_per_page: float
    """Average memory per page (peak_mb / page_count)."""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MemoryProfiler:
    """Profile memory usage during Bengal builds."""

    def __init__(self, scenario_path: Path):
        """
        Initialize profiler for a scenario.

        Args:
            scenario_path: Path to the scenario directory containing bengal.toml
        """
        self.scenario_path = Path(scenario_path)

    def profile_build(self, page_count: int | None = None) -> MemoryStats:
        """
        Profile memory usage during a build.

        Args:
            page_count: Number of pages in scenario (for per-page calculation).
                       If not provided, will try to count .md files.

        Returns:
            MemoryStats with peak memory and other statistics.
        """
        if page_count is None:
            # Count markdown files in content directory
            content_dir = self.scenario_path / "content"
            page_count = len(list(content_dir.glob("**/*.md")))

        tracemalloc.start()

        try:
            subprocess.run(
                ["bengal", "build"],
                cwd=self.scenario_path,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            current, peak = tracemalloc.get_traced_memory()

            # Convert bytes to megabytes
            current_mb = current / 1024 / 1024
            peak_mb = peak / 1024 / 1024

            return MemoryStats(
                peak_mb=round(peak_mb, 2),
                current_mb=round(current_mb, 2),
                page_count=page_count,
                memory_per_page=round(peak_mb / page_count, 4),
            )

        finally:
            tracemalloc.stop()

    def profile_and_save(self, output_file: Path, page_count: int | None = None) -> MemoryStats:
        """
        Profile build and save results to JSON file.

        Args:
            output_file: Path where JSON results will be saved.
            page_count: Number of pages in scenario.

        Returns:
            MemoryStats with the collected statistics.
        """
        stats = self.profile_build(page_count)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(stats.to_dict(), f, indent=2)

        return stats


def compare_memory_stats(stats_list: list[MemoryStats]) -> dict:
    """
    Compare memory statistics across multiple runs.

    Useful for identifying scale degradation patterns.

    Args:
        stats_list: List of MemoryStats from different scenario sizes.

    Returns:
        Dictionary with comparison analysis.
    """
    if not stats_list:
        return {}

    return {
        "runs": len(stats_list),
        "min_peak_mb": min(s.peak_mb for s in stats_list),
        "max_peak_mb": max(s.peak_mb for s in stats_list),
        "avg_peak_mb": round(sum(s.peak_mb for s in stats_list) / len(stats_list), 2),
        "min_per_page": min(s.memory_per_page for s in stats_list),
        "max_per_page": max(s.memory_per_page for s in stats_list),
        "avg_per_page": round(sum(s.memory_per_page for s in stats_list) / len(stats_list), 4),
        "details": [s.to_dict() for s in stats_list],
    }
