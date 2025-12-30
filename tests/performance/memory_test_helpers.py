"""Helper utilities for accurate memory profiling."""

import gc
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass

import psutil


@dataclass
class MemorySnapshot:
    """Snapshot of memory state at a point in time."""

    # Python heap (tracemalloc)
    python_current_bytes: int
    python_peak_bytes: int

    # Process memory (psutil)
    rss_bytes: int  # Resident Set Size
    vms_bytes: int  # Virtual Memory Size

    # Tracemalloc snapshot for detailed analysis
    tracemalloc_snapshot: tracemalloc.Snapshot | None = None

    @property
    def python_current_mb(self) -> float:
        return self.python_current_bytes / 1024 / 1024

    @property
    def python_peak_mb(self) -> float:
        return self.python_peak_bytes / 1024 / 1024

    @property
    def rss_mb(self) -> float:
        return self.rss_bytes / 1024 / 1024

    @property
    def vms_mb(self) -> float:
        return self.vms_bytes / 1024 / 1024


@dataclass
class MemoryDelta:
    """Memory change between two snapshots."""

    python_heap_delta_mb: float
    python_heap_peak_mb: float
    rss_delta_mb: float
    vms_delta_mb: float

    # Top allocators (filename, line, size)
    top_allocators: list[str]

    def __str__(self) -> str:
        return (
            f"Python Heap: Δ{self.python_heap_delta_mb:+.1f}MB "
            f"(peak: {self.python_heap_peak_mb:.1f}MB) | "
            f"RSS: Δ{self.rss_delta_mb:+.1f}MB"
        )


class MemoryProfiler:
    """Context manager for accurate memory profiling."""

    def __init__(self, track_allocations: bool = True):
        """
        Initialize memory profiler.

        Args:
            track_allocations: If True, capture detailed allocation info
                             (has ~2x performance overhead)
        """
        self.track_allocations = track_allocations
        self.process = psutil.Process()
        self.before: MemorySnapshot | None = None
        self.after: MemorySnapshot | None = None

    def __enter__(self):
        """Start profiling."""
        # Force GC to get clean baseline
        gc.collect()
        gc.collect()  # Run twice to catch circular refs
        gc.collect()  # Third time for good measure

        # Start tracemalloc
        tracemalloc.start()

        # Take initial snapshot
        self.before = self._take_snapshot()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling."""
        # Take final snapshot
        self.after = self._take_snapshot()

        # Stop tracemalloc
        tracemalloc.stop()

        return False  # Don't suppress exceptions

    def _take_snapshot(self) -> MemorySnapshot:
        """Capture current memory state."""
        # Get Python heap info
        current, peak = tracemalloc.get_traced_memory()

        # Get process memory info
        mem_info = self.process.memory_info()

        # Capture detailed snapshot if requested
        snapshot = None
        if self.track_allocations:
            snapshot = tracemalloc.take_snapshot()

        return MemorySnapshot(
            python_current_bytes=current,
            python_peak_bytes=peak,
            rss_bytes=mem_info.rss,
            vms_bytes=mem_info.vms,
            tracemalloc_snapshot=snapshot,
        )

    def get_delta(self, top_n: int = 10) -> MemoryDelta:
        """
        Calculate memory delta between before and after.

        Args:
            top_n: Number of top allocators to include

        Returns:
            MemoryDelta object with detailed breakdown
        """
        if not self.before or not self.after:
            raise RuntimeError("Must use as context manager")

        # Calculate deltas
        python_delta_bytes = self.after.python_current_bytes - self.before.python_current_bytes
        python_peak_bytes = self.after.python_peak_bytes - self.before.python_peak_bytes
        rss_delta_bytes = self.after.rss_bytes - self.before.rss_bytes
        vms_delta_bytes = self.after.vms_bytes - self.before.vms_bytes

        # Get top allocators
        top_allocators = []
        if self.track_allocations and self.before.tracemalloc_snapshot:
            top_stats = self.after.tracemalloc_snapshot.compare_to(
                self.before.tracemalloc_snapshot, "lineno"
            )

            for stat in top_stats[:top_n]:
                size_mb = stat.size_diff / 1024 / 1024
                top_allocators.append(
                    f"{stat.traceback.format()[0].strip()} | "
                    f"{size_mb:+.2f}MB ({stat.count_diff:+d} blocks)"
                )

        return MemoryDelta(
            python_heap_delta_mb=python_delta_bytes / 1024 / 1024,
            python_heap_peak_mb=python_peak_bytes / 1024 / 1024,
            rss_delta_mb=rss_delta_bytes / 1024 / 1024,
            vms_delta_mb=vms_delta_bytes / 1024 / 1024,
            top_allocators=top_allocators,
        )


@contextmanager
def profile_memory(name: str = "Operation", verbose: bool = True):
    """
    Convenience context manager for profiling memory.

    Example:
        with profile_memory("Building site", verbose=True) as prof:
            site.build(BuildOptions())

        delta = prof.get_delta()
        assert delta.rss_delta_mb < 500
    """
    profiler = MemoryProfiler(track_allocations=verbose)

    with profiler:
        yield profiler

    if verbose:
        delta = profiler.get_delta()
        print(f"\n{name}:")
        print(f"  {delta}")
        if delta.top_allocators:
            print("  Top allocators:")
            for alloc in delta.top_allocators:
                print(f"    {alloc}")
