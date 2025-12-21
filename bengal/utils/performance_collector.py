"""
Performance metrics collection for Bengal SSG.

Collects and persists build performance metrics including timing and memory usage.
This is Phase 1 of the continuous performance tracking system.

Example:

```python
from bengal.utils.performance_collector import PerformanceCollector

collector = PerformanceCollector()
collector.start_build()

# ... run build ...

stats = collector.end_build(build_stats)
collector.save(stats)
```
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

logger = get_logger(__name__)

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class PerformanceCollector:
    """
    Collects and persists build performance metrics.

    Phase 1 implementation: Basic timing and memory collection.
    Future phases will add per-phase tracking, git info, and top allocators.

    Usage:
        collector = PerformanceCollector()
        collector.start_build()

        # ... execute build ...

        stats = collector.end_build(build_stats)
        collector.save(stats)
    """

    def __init__(self, metrics_dir: Path | None = None):
        """
        Initialize performance collector.

        Args:
            metrics_dir: Directory to store metrics (default: .bengal/metrics)
        """
        self.metrics_dir = metrics_dir or Path(".bengal/metrics")
        self.start_time: float | None = None
        self.start_memory: int | None = None
        self.start_rss: int | None = None

        # Initialize psutil if available
        if HAS_PSUTIL:
            self.process = psutil.Process()
        else:
            self.process = None

    def start_build(self) -> None:
        """Start collecting metrics for a build."""
        self.start_time = time.time()

        # Start memory tracking with tracemalloc
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        self.start_memory = tracemalloc.get_traced_memory()[0]

        # Get initial RSS if psutil available
        if self.process:
            self.start_rss = self.process.memory_info().rss

    def end_build(self, stats: BuildStats) -> BuildStats:
        """
        End collection and update stats with memory metrics.

        Args:
            stats: BuildStats object to update with memory information

        Returns:
            Updated BuildStats object
        """
        # Calculate Python heap memory
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        memory_heap_mb = (current_mem - (self.start_memory or 0)) / 1024 / 1024
        memory_peak_mb = peak_mem / 1024 / 1024

        # Calculate RSS memory if available
        memory_rss_mb = 0.0
        if self.process and self.start_rss:
            current_rss = self.process.memory_info().rss
            memory_rss_mb = (current_rss - self.start_rss) / 1024 / 1024

        # Update BuildStats with memory metrics
        stats.memory_rss_mb = memory_rss_mb
        stats.memory_heap_mb = memory_heap_mb
        stats.memory_peak_mb = memory_peak_mb

        return stats

    def save(self, stats: BuildStats) -> None:
        """
        Save metrics to disk for historical tracking.

        Args:
            stats: BuildStats object to persist
        """
        try:
            # Create metrics directory if it doesn't exist
            self.metrics_dir.mkdir(exist_ok=True)

            # Prepare metrics dictionary
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                **stats.to_dict(),
            }

            # Append to history file (JSONL format - one JSON object per line)
            history_file = self.metrics_dir / "history.jsonl"
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")

            # Also save as latest.json for easy access
            latest_file = self.metrics_dir / "latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)

        except Exception as e:
            # Fail gracefully - don't break the build if metrics can't be saved
            logger.warning(
                "performance_metrics_save_failed", error=str(e), error_type=type(e).__name__
            )

    def get_summary(self, stats: BuildStats) -> str:
        """
        Generate a one-line summary of build metrics.

        Args:
            stats: BuildStats object

        Returns:
            Formatted summary string
        """
        return (
            f"{stats.total_pages} pages | "
            f"{stats.build_time_ms / 1000:.2f}s | "
            f"{stats.memory_rss_mb:.1f}MB RSS"
        )


def format_memory(mb: float) -> str:
    """
    Format memory size for display.

    Args:
        mb: Memory in megabytes

    Returns:
        Formatted string (e.g., "125.3 MB" or "1.2 GB")
    """
    if mb < 1:
        return f"{mb * 1024:.1f} KB"
    elif mb < 1024:
        return f"{mb:.1f} MB"
    else:
        return f"{mb / 1024:.2f} GB"
