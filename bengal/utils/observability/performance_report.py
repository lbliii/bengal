"""
Performance metrics reporting and analysis.

Reads collected metrics from `.bengal/metrics/` and provides analysis,
visualization, and trend detection for build performance tracking.

Key Features:
- Load historical build metrics from JSONL files
- Analyze trends (time, memory, throughput)
- Compare specific builds side-by-side
- Generate ASCII tables and JSON output
- Detect performance regressions

Usage:
    >>> from bengal.utils.observability.performance_report import PerformanceReport
    >>>
    >>> report = PerformanceReport()
    >>> report.show(last=10, format='table')
    >>>
    >>> # Compare two builds
    >>> report.compare(build1_idx=0, build2_idx=1)

Related Modules:
- bengal/utils/performance_collector.py: Collects metrics
- bengal/cli/commands/perf.py: CLI for `bengal perf` command
- bengal/utils/paths.py: Metrics directory paths

See Also:
- .bengal/metrics/history.jsonl: Build history (JSON lines)
- .bengal/metrics/latest.json: Most recent build metrics

"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BuildMetric:
    """
    Represents a single build's performance metrics.

    Immutable record of timing, memory, and configuration data
    captured during a build. Used for historical analysis and
    trend detection.

    Attributes:
        timestamp: ISO 8601 timestamp when build completed.
        total_pages: Number of pages processed.
        build_time_ms: Total build duration in milliseconds.
        memory_rss_mb: Resident Set Size memory growth in MB.
        memory_heap_mb: Python heap memory growth in MB (tracemalloc).
        memory_peak_mb: Peak memory usage during build in MB.
        parallel: Whether parallel rendering was enabled.
        incremental: Whether this was an incremental build.
        skipped: Whether build was skipped (no changes detected).
        discovery_time_ms: Content discovery phase duration.
        taxonomy_time_ms: Taxonomy building phase duration.
        rendering_time_ms: Template rendering phase duration.
        assets_time_ms: Asset processing phase duration.
        postprocess_time_ms: Post-processing phase duration.

    Example:
            >>> metric = BuildMetric.from_dict({"total_pages": 100, "build_time_ms": 2500})
            >>> metric.build_time_s
        2.5
            >>> metric.pages_per_second
        40.0

    """

    timestamp: str
    total_pages: int
    build_time_ms: float
    memory_rss_mb: float
    memory_heap_mb: float
    memory_peak_mb: float
    parallel: bool
    incremental: bool
    skipped: bool

    # Optional fields (0 if not recorded)
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0

    @property
    def build_time_s(self) -> float:
        """Build time in seconds (convenience property)."""
        return self.build_time_ms / 1000

    @property
    def rendering_time_s(self) -> float:
        """Rendering time in seconds (convenience property)."""
        return self.rendering_time_ms / 1000

    @property
    def pages_per_second(self) -> float:
        """Rendering throughput in pages per second."""
        time_s = self.rendering_time_s if self.rendering_time_s > 0 else self.build_time_s
        if time_s > 0:
            return self.total_pages / time_s
        return 0

    @property
    def memory_per_page_mb(self) -> float:
        """Average memory usage per page in MB."""
        if self.total_pages > 0:
            return self.memory_rss_mb / self.total_pages
        return 0

    @property
    def as_datetime(self) -> datetime:
        """Parse timestamp string to datetime object."""
        return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildMetric:
        """
        Create a BuildMetric from a dictionary (e.g., from JSON).

        Args:
            data: Dictionary with metric fields. Missing fields use defaults.

        Returns:
            BuildMetric instance populated from the dictionary.
        """
        return cls(
            timestamp=data.get("timestamp", ""),
            total_pages=data.get("total_pages", 0),
            build_time_ms=data.get("build_time_ms", 0),
            memory_rss_mb=data.get("memory_rss_mb", 0),
            memory_heap_mb=data.get("memory_heap_mb", 0),
            memory_peak_mb=data.get("memory_peak_mb", 0),
            parallel=data.get("parallel", False),
            incremental=data.get("incremental", False),
            skipped=data.get("skipped", False),
            discovery_time_ms=data.get("discovery_time_ms", 0),
            taxonomy_time_ms=data.get("taxonomy_time_ms", 0),
            rendering_time_ms=data.get("rendering_time_ms", 0),
            assets_time_ms=data.get("assets_time_ms", 0),
            postprocess_time_ms=data.get("postprocess_time_ms", 0),
        )


class PerformanceReport:
    """
    Generates performance reports from collected build metrics.

    Loads metrics from `.bengal/metrics/history.jsonl`, analyzes trends,
    and outputs reports in various formats. Used by the `bengal perf`
    CLI command for performance monitoring.

    Attributes:
        metrics_dir: Directory containing metrics files.

    Example:
            >>> report = PerformanceReport()
            >>>
            >>> # Show last 10 builds as ASCII table
            >>> report.show(last=10, format='table')
            >>>
            >>> # Get JSON output for automation
            >>> report.show(last=5, format='json')
            >>>
            >>> # Compare latest build to previous
            >>> report.compare(build1_idx=0, build2_idx=1)

    """

    def __init__(self, metrics_dir: Path | None = None):
        """
        Initialize the performance report generator.

        Args:
            metrics_dir: Directory containing metrics files. Defaults to
                `.bengal/metrics` in the current directory.
        """
        self.metrics_dir = metrics_dir or Path(".bengal/metrics")

    def load_metrics(self, last: int | None = None) -> list[BuildMetric]:
        """
        Load metrics from the history file.

        Reads the JSONL history file and parses each line into a BuildMetric.
        Malformed lines are silently skipped.

        Args:
            last: Number of recent builds to return. If None, returns all builds.

        Returns:
            List of BuildMetric objects ordered most-recent-first.
            Returns empty list if history file doesn't exist.

        Example:
            >>> report = PerformanceReport()
            >>> metrics = report.load_metrics(last=5)
            >>> len(metrics)
            5
            >>> metrics[0].as_datetime > metrics[1].as_datetime  # Most recent first
            True
        """
        history_file = self.metrics_dir / "history.jsonl"

        if not history_file.exists():
            return []

        metrics = []
        with open(history_file, encoding="utf-8") as f:
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

    def show(self, last: int = 10, format: str = "table") -> None:
        """
        Display a performance report.

        Outputs build metrics in the specified format. Includes trend analysis
        when enough data points are available.

        Args:
            last: Number of recent builds to include (default: 10).
            format: Output format - 'table' (ASCII table), 'json' (machine-readable),
                or 'summary' (brief overview of latest build).
        """
        metrics = self.load_metrics(last=last)
        from bengal.output import get_cli_output

        cli = get_cli_output()

        if not metrics:
            cli.render_write(
                "validation_report.kida",
                title="Performance",
                issues=[
                    {
                        "level": "info",
                        "message": "No performance metrics found",
                        "detail": f"Metrics will be collected in: {self.metrics_dir}/",
                    }
                ],
                summary=None,
            )
            return

        if format == "table":
            self._print_table(metrics, cli=cli)
        elif format == "json":
            self._print_json(metrics, cli=cli)
        elif format == "summary":
            self._print_summary(metrics, cli=cli)
        else:
            cli.error(f"Unknown format: {format}")

    def _print_table(self, metrics: list[BuildMetric], *, cli: Any) -> None:
        """
        Print metrics as an ASCII table.

        Displays a formatted table with columns for date, page count,
        build time, memory usage, and build type.

        Args:
            metrics: List of BuildMetric objects to display.
        """
        cli.render_write(
            "kv_detail.kida",
            title="Performance History",
            items=[{"label": "Builds shown", "value": str(len(metrics))}],
        )
        rows: list[list[str]] = []
        for m in metrics:
            date = m.as_datetime.strftime("%Y-%m-%d %H:%M")
            if m.skipped:
                build_type = "skipped"
            elif m.incremental:
                build_type = "incremental"
            elif m.parallel:
                build_type = "parallel"
            else:
                build_type = "sequential"

            rows.append(
                [
                    date,
                    str(m.total_pages),
                    f"{m.build_time_s:.2f}s",
                    f"{m.memory_rss_mb:.1f}MB",
                    build_type,
                ]
            )
        cli.render_write(
            "item_list.kida",
            mode="table",
            headers=["Date", "Pages", "Time", "Memory", "Type"],
            table_data=rows,
        )

        # Show trends if enough data
        if len(metrics) >= 2:
            self._print_trends(metrics, cli=cli)

    def _print_trends(self, metrics: list[BuildMetric], *, cli: Any) -> None:
        """
        Print trend analysis comparing oldest and newest builds.

        Calculates percentage changes in build time and memory usage,
        and displays average metrics across all builds. Includes warnings
        for significant performance changes.

        Args:
            metrics: List of BuildMetric objects (must have at least 2).
        """
        # Filter out skipped builds for trend analysis
        valid_metrics = [m for m in metrics if not m.skipped]

        if len(valid_metrics) < 2:
            return

        first = valid_metrics[-1]  # Oldest
        last = valid_metrics[0]  # Newest

        # Calculate changes
        time_change = (
            ((last.build_time_ms - first.build_time_ms) / first.build_time_ms * 100)
            if first.build_time_ms > 0
            else 0
        )
        mem_change = (
            ((last.memory_rss_mb - first.memory_rss_mb) / first.memory_rss_mb * 100)
            if first.memory_rss_mb > 0
            else 0
        )

        # Average metrics
        avg_time = sum(m.build_time_ms for m in valid_metrics) / len(valid_metrics) / 1000
        avg_memory = sum(m.memory_rss_mb for m in valid_metrics) / len(valid_metrics)
        avg_throughput = sum(m.pages_per_second for m in valid_metrics) / len(valid_metrics)

        cli.render_write(
            "kv_detail.kida",
            title=f"Trends (last {len(valid_metrics)} builds)",
            items=[
                {"label": "Time", "value": f"{time_change:+.1f}%"},
                {"label": "Memory", "value": f"{mem_change:+.1f}%"},
                {"label": "Average build time", "value": f"{avg_time:.2f}s"},
                {"label": "Average memory", "value": f"{avg_memory:.1f}MB"},
                {"label": "Average throughput", "value": f"{avg_throughput:.1f} pages/s"},
            ],
        )

        # Warnings
        if abs(time_change) > 20:
            cli.warning(f"Significant time change: {time_change:+.1f}%")
        if abs(mem_change) > 15:
            cli.warning(f"Significant memory change: {mem_change:+.1f}%")

    def _print_json(self, metrics: list[BuildMetric], *, cli: Any) -> None:
        """
        Print metrics as a JSON array.

        Outputs machine-readable JSON suitable for automation, dashboards,
        or further analysis.

        Args:
            metrics: List of BuildMetric objects to serialize.
        """
        data = [
            {
                "timestamp": m.timestamp,
                "pages": m.total_pages,
                "build_time_s": m.build_time_s,
                "memory_rss_mb": m.memory_rss_mb,
                "memory_heap_mb": m.memory_heap_mb,
                "throughput": m.pages_per_second,
                "incremental": m.incremental,
                "parallel": m.parallel,
            }
            for m in metrics
        ]
        cli.render_write("json_output.kida", data=json.dumps(data, indent=2))

    def _print_summary(self, metrics: list[BuildMetric], *, cli: Any) -> None:
        """
        Print a summary of the latest build with comparison to average.

        Shows detailed information about the most recent build including
        phase breakdown, and compares performance to historical average.

        Args:
            metrics: List of BuildMetric objects (uses first element as latest).
        """
        if not metrics:
            return

        latest = metrics[0]

        cli.render_write(
            "kv_detail.kida",
            title="Latest Build",
            items=[
                {"label": "Date", "value": latest.as_datetime.strftime("%Y-%m-%d %H:%M:%S")},
                {"label": "Pages", "value": str(latest.total_pages)},
                {"label": "Time", "value": f"{latest.build_time_s:.2f}s"},
                {"label": "Memory", "value": f"{latest.memory_rss_mb:.1f}MB RSS"},
                {"label": "Throughput", "value": f"{latest.pages_per_second:.1f} pages/s"},
                {
                    "label": "Type",
                    "value": f"{'incremental' if latest.incremental else 'full'} / {'parallel' if latest.parallel else 'sequential'}",
                },
            ],
        )

        if len(metrics) > 1:
            # Compare to average
            valid_metrics = [m for m in metrics if not m.skipped]
            if len(valid_metrics) > 1:
                avg_time = sum(m.build_time_s for m in valid_metrics) / len(valid_metrics)
                avg_memory = sum(m.memory_rss_mb for m in valid_metrics) / len(valid_metrics)

                time_diff = latest.build_time_s - avg_time
                mem_diff = latest.memory_rss_mb - avg_memory

                cli.render_write(
                    "kv_detail.kida",
                    title=f"vs. Average ({len(valid_metrics)} builds)",
                    items=[
                        {
                            "label": "Time",
                            "value": f"{time_diff:+.2f}s ({(time_diff / avg_time * 100):+.1f}%)",
                        },
                        {
                            "label": "Memory",
                            "value": f"{mem_diff:+.1f}MB ({(mem_diff / avg_memory * 100):+.1f}%)",
                        },
                    ],
                )

        # Phase breakdown if available
        if latest.rendering_time_ms > 0:
            cli.render_write(
                "kv_detail.kida",
                title="Phase Breakdown",
                items=[
                    {"label": "Discovery", "value": f"{latest.discovery_time_ms:.0f}ms"},
                    {"label": "Taxonomies", "value": f"{latest.taxonomy_time_ms:.0f}ms"},
                    {"label": "Rendering", "value": f"{latest.rendering_time_ms:.0f}ms"},
                    {"label": "Assets", "value": f"{latest.assets_time_ms:.0f}ms"},
                    {"label": "Postproc", "value": f"{latest.postprocess_time_ms:.0f}ms"},
                ],
            )

    def compare(self, build1_idx: int = 0, build2_idx: int = 1) -> None:
        """
        Compare two builds side-by-side.

        Displays a detailed comparison of two builds showing differences
        in page count, build time, memory usage, and throughput.

        Args:
            build1_idx: Index of first build in history (0 = latest).
            build2_idx: Index of second build in history.

        Example:
            >>> report = PerformanceReport()
            >>> report.compare(0, 1)  # Compare latest to previous
            >>> report.compare(0, 9)  # Compare latest to 10 builds ago
        """
        metrics = self.load_metrics()
        from bengal.output import get_cli_output

        cli = get_cli_output()

        if len(metrics) < 2:
            cli.warning("Need at least 2 builds to compare.")
            return

        if build1_idx >= len(metrics) or build2_idx >= len(metrics):
            cli.error(f"Invalid build indices. Only {len(metrics)} builds available.")
            return

        b1 = metrics[build1_idx]
        b2 = metrics[build2_idx]

        cli.render_write(
            "kv_detail.kida",
            title="Build Comparison",
            items=[
                {"label": "Build 1", "value": b1.as_datetime.strftime("%Y-%m-%d %H:%M")},
                {"label": "Build 2", "value": b2.as_datetime.strftime("%Y-%m-%d %H:%M")},
            ],
        )
        rows = [
            self._compare_metric("Pages", b1.total_pages, b2.total_pages),
            self._compare_metric(
                "Build time",
                f"{b1.build_time_s:.2f}s",
                f"{b2.build_time_s:.2f}s",
                b1.build_time_s,
                b2.build_time_s,
            ),
            self._compare_metric(
                "Memory (RSS)",
                f"{b1.memory_rss_mb:.1f}MB",
                f"{b2.memory_rss_mb:.1f}MB",
                b1.memory_rss_mb,
                b2.memory_rss_mb,
            ),
            self._compare_metric(
                "Memory (heap)",
                f"{b1.memory_heap_mb:.1f}MB",
                f"{b2.memory_heap_mb:.1f}MB",
                b1.memory_heap_mb,
                b2.memory_heap_mb,
            ),
            self._compare_metric(
                "Throughput",
                f"{b1.pages_per_second:.1f}/s",
                f"{b2.pages_per_second:.1f}/s",
                b1.pages_per_second,
                b2.pages_per_second,
            ),
        ]
        cli.render_write(
            "item_list.kida",
            mode="table",
            headers=["Metric", "Build 1", "Build 2", "Change"],
            table_data=rows,
        )

    def _compare_metric(
        self, name: str, val1: Any, val2: Any, num1: float | None = None, num2: float | None = None
    ) -> list[str]:
        """
        Print a single row in the comparison table.

        Args:
            name: Metric name for the row label.
            val1: Display value for build 1.
            val2: Display value for build 2.
            num1: Numeric value for build 1 (for percentage calculation).
            num2: Numeric value for build 2 (for percentage calculation).
        """
        if num1 is not None and num2 is not None and num1 > 0:
            change_pct = ((num2 - num1) / num1) * 100
            change_str = f"{change_pct:+.1f}%"
        else:
            change_str = "-"

        return [name, str(val1), str(val2), change_str]
