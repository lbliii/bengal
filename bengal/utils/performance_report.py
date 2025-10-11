"""
Performance metrics reporting and analysis.

Reads collected metrics from .bengal-metrics/ and provides analysis,
visualization, and trend detection.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BuildMetric:
    """Single build metric record."""
    timestamp: str
    total_pages: int
    build_time_ms: float
    memory_rss_mb: float
    memory_heap_mb: float
    memory_peak_mb: float
    parallel: bool
    incremental: bool
    skipped: bool

    # Optional fields
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0

    @property
    def build_time_s(self) -> float:
        """Build time in seconds."""
        return self.build_time_ms / 1000

    @property
    def pages_per_second(self) -> float:
        """Throughput in pages/second."""
        if self.build_time_s > 0:
            return self.total_pages / self.build_time_s
        return 0

    @property
    def memory_per_page_mb(self) -> float:
        """Memory per page in MB."""
        if self.total_pages > 0:
            return self.memory_rss_mb / self.total_pages
        return 0

    @property
    def datetime(self) -> datetime:
        """Parse timestamp to datetime."""
        return datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BuildMetric':
        """Create from dictionary."""
        return cls(
            timestamp=data.get('timestamp', ''),
            total_pages=data.get('total_pages', 0),
            build_time_ms=data.get('build_time_ms', 0),
            memory_rss_mb=data.get('memory_rss_mb', 0),
            memory_heap_mb=data.get('memory_heap_mb', 0),
            memory_peak_mb=data.get('memory_peak_mb', 0),
            parallel=data.get('parallel', False),
            incremental=data.get('incremental', False),
            skipped=data.get('skipped', False),
            discovery_time_ms=data.get('discovery_time_ms', 0),
            taxonomy_time_ms=data.get('taxonomy_time_ms', 0),
            rendering_time_ms=data.get('rendering_time_ms', 0),
            assets_time_ms=data.get('assets_time_ms', 0),
            postprocess_time_ms=data.get('postprocess_time_ms', 0),
        )


class PerformanceReport:
    """
    Generates performance reports from collected metrics.

    Usage:
        report = PerformanceReport()
        report.show(last=10, format='table')
    """

    def __init__(self, metrics_dir: Path | None = None):
        """
        Initialize report generator.

        Args:
            metrics_dir: Directory containing metrics (default: .bengal-metrics)
        """
        self.metrics_dir = metrics_dir or Path(".bengal-metrics")

    def load_metrics(self, last: int | None = None) -> list[BuildMetric]:
        """
        Load metrics from history file.

        Args:
            last: Number of recent builds to load (None = all)

        Returns:
            List of BuildMetric objects, most recent first
        """
        history_file = self.metrics_dir / "history.jsonl"

        if not history_file.exists():
            return []

        metrics = []
        with open(history_file, encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    metrics.append(BuildMetric.from_dict(data))
                except json.JSONDecodeError:
                    continue  # Skip malformed lines

        # Most recent first
        metrics.reverse()

        if last:
            metrics = metrics[:last]

        return metrics

    def show(self, last: int = 10, format: str = 'table'):
        """
        Show performance report.

        Args:
            last: Number of recent builds to show
            format: Output format ('table', 'json', 'summary')
        """
        metrics = self.load_metrics(last=last)

        if not metrics:
            print("No performance metrics found.")
            print(f"Metrics will be collected in: {self.metrics_dir}/")
            return

        if format == 'table':
            self._print_table(metrics)
        elif format == 'json':
            self._print_json(metrics)
        elif format == 'summary':
            self._print_summary(metrics)
        else:
            print(f"Unknown format: {format}")

    def _print_table(self, metrics: list[BuildMetric]):
        """Print as ASCII table."""
        print("\n📊 Performance History")
        print(f"   Showing {len(metrics)} most recent builds\n")

        # Header
        print(f"{'Date':<20} {'Pages':<8} {'Time':<10} {'Memory':<12} {'Type':<12}")
        print("─" * 75)

        # Rows
        for m in metrics:
            date = m.datetime.strftime('%Y-%m-%d %H:%M')

            # Build type
            if m.skipped:
                build_type = "skipped"
            elif m.incremental:
                build_type = "incremental"
            elif m.parallel:
                build_type = "parallel"
            else:
                build_type = "sequential"

            print(
                f"{date:<20} "
                f"{m.total_pages:<8} "
                f"{m.build_time_s:>8.2f}s "
                f"{m.memory_rss_mb:>10.1f}MB "
                f"{build_type:<12}"
            )

        # Show trends if enough data
        if len(metrics) >= 2:
            self._print_trends(metrics)

    def _print_trends(self, metrics: list[BuildMetric]):
        """Print trend analysis."""
        # Filter out skipped builds for trend analysis
        valid_metrics = [m for m in metrics if not m.skipped]

        if len(valid_metrics) < 2:
            return

        first = valid_metrics[-1]  # Oldest
        last = valid_metrics[0]    # Newest

        # Calculate changes
        time_change = ((last.build_time_ms - first.build_time_ms) / first.build_time_ms * 100) if first.build_time_ms > 0 else 0
        mem_change = ((last.memory_rss_mb - first.memory_rss_mb) / first.memory_rss_mb * 100) if first.memory_rss_mb > 0 else 0

        # Average metrics
        avg_time = sum(m.build_time_ms for m in valid_metrics) / len(valid_metrics) / 1000
        avg_memory = sum(m.memory_rss_mb for m in valid_metrics) / len(valid_metrics)
        avg_throughput = sum(m.pages_per_second for m in valid_metrics) / len(valid_metrics)

        print(f"\n📈 Trends (last {len(valid_metrics)} builds)")
        print(f"   Time:       {time_change:+.1f}%")
        print(f"   Memory:     {mem_change:+.1f}%")

        print("\n📊 Averages")
        print(f"   Build time: {avg_time:.2f}s")
        print(f"   Memory:     {avg_memory:.1f}MB")
        print(f"   Throughput: {avg_throughput:.1f} pages/s")

        # Warnings
        if abs(time_change) > 20:
            print(f"\n⚠️  Significant time change: {time_change:+.1f}%")
        if abs(mem_change) > 15:
            print(f"⚠️  Significant memory change: {mem_change:+.1f}%")

    def _print_json(self, metrics: list[BuildMetric]):
        """Print as JSON array."""
        data = [
            {
                'timestamp': m.timestamp,
                'pages': m.total_pages,
                'build_time_s': m.build_time_s,
                'memory_rss_mb': m.memory_rss_mb,
                'memory_heap_mb': m.memory_heap_mb,
                'throughput': m.pages_per_second,
                'incremental': m.incremental,
                'parallel': m.parallel,
            }
            for m in metrics
        ]
        print(json.dumps(data, indent=2))

    def _print_summary(self, metrics: list[BuildMetric]):
        """Print summary statistics."""
        if not metrics:
            return

        latest = metrics[0]

        print("\n📊 Latest Build")
        print(f"   Date:       {latest.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Pages:      {latest.total_pages}")
        print(f"   Time:       {latest.build_time_s:.2f}s")
        print(f"   Memory:     {latest.memory_rss_mb:.1f}MB RSS")
        print(f"   Throughput: {latest.pages_per_second:.1f} pages/s")
        print(f"   Type:       {'incremental' if latest.incremental else 'full'} / {'parallel' if latest.parallel else 'sequential'}")

        if len(metrics) > 1:
            # Compare to average
            valid_metrics = [m for m in metrics if not m.skipped]
            if len(valid_metrics) > 1:
                avg_time = sum(m.build_time_s for m in valid_metrics) / len(valid_metrics)
                avg_memory = sum(m.memory_rss_mb for m in valid_metrics) / len(valid_metrics)

                time_diff = latest.build_time_s - avg_time
                mem_diff = latest.memory_rss_mb - avg_memory

                print(f"\n📈 vs. Average ({len(valid_metrics)} builds)")
                print(f"   Time:       {time_diff:+.2f}s ({(time_diff/avg_time*100):+.1f}%)")
                print(f"   Memory:     {mem_diff:+.1f}MB ({(mem_diff/avg_memory*100):+.1f}%)")

        # Phase breakdown if available
        if latest.rendering_time_ms > 0:
            print("\n⏱️  Phase Breakdown")
            print(f"   Discovery:  {latest.discovery_time_ms:>6.0f}ms")
            print(f"   Taxonomies: {latest.taxonomy_time_ms:>6.0f}ms")
            print(f"   Rendering:  {latest.rendering_time_ms:>6.0f}ms")
            print(f"   Assets:     {latest.assets_time_ms:>6.0f}ms")
            print(f"   Postproc:   {latest.postprocess_time_ms:>6.0f}ms")

    def compare(self, build1_idx: int = 0, build2_idx: int = 1):
        """
        Compare two builds.

        Args:
            build1_idx: Index of first build (0 = latest)
            build2_idx: Index of second build
        """
        metrics = self.load_metrics()

        if len(metrics) < 2:
            print("Need at least 2 builds to compare.")
            return

        if build1_idx >= len(metrics) or build2_idx >= len(metrics):
            print(f"Invalid build indices. Only {len(metrics)} builds available.")
            return

        b1 = metrics[build1_idx]
        b2 = metrics[build2_idx]

        print("\n📊 Build Comparison")
        print(f"\n   Build 1: {b1.datetime.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Build 2: {b2.datetime.strftime('%Y-%m-%d %H:%M')}")

        print(f"\n{'Metric':<20} {'Build 1':>12} {'Build 2':>12} {'Change':>12}")
        print("─" * 60)

        self._compare_metric("Pages", b1.total_pages, b2.total_pages)
        self._compare_metric("Build time", f"{b1.build_time_s:.2f}s", f"{b2.build_time_s:.2f}s",
                           b1.build_time_s, b2.build_time_s)
        self._compare_metric("Memory (RSS)", f"{b1.memory_rss_mb:.1f}MB", f"{b2.memory_rss_mb:.1f}MB",
                           b1.memory_rss_mb, b2.memory_rss_mb)
        self._compare_metric("Memory (heap)", f"{b1.memory_heap_mb:.1f}MB", f"{b2.memory_heap_mb:.1f}MB",
                           b1.memory_heap_mb, b2.memory_heap_mb)
        self._compare_metric("Throughput", f"{b1.pages_per_second:.1f}/s", f"{b2.pages_per_second:.1f}/s",
                           b1.pages_per_second, b2.pages_per_second)

    def _compare_metric(self, name: str, val1, val2, num1=None, num2=None):
        """Print comparison row."""
        if num1 is not None and num2 is not None and num1 > 0:
            change_pct = ((num2 - num1) / num1) * 100
            change_str = f"{change_pct:+.1f}%"
        else:
            change_str = "-"

        print(f"{name:<20} {val1!s:>12} {val2!s:>12} {change_str:>12}")

