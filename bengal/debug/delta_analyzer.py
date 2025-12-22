"""
Build delta analyzer for comparing builds and explaining changes.

Provides tools for comparing build snapshots to understand what changed
between builds, tracking build time trends, and identifying performance
regressions over time.

Key Features:
    - BuildSnapshot: Captures build state for comparison
    - BuildDelta: Computes differences between two snapshots
    - BuildHistory: Tracks builds over time for trend analysis
    - BuildDeltaAnalyzer: Debug tool combining all capabilities

Use Cases:
    - Compare current build to previous build
    - Track build performance trends over time
    - Identify when builds started slowing down
    - Understand what content was added/removed

Example:
    >>> from bengal.debug import BuildDeltaAnalyzer
    >>> analyzer = BuildDeltaAnalyzer(cache=cache)
    >>> delta = analyzer.compare_to_previous()
    >>> if delta:
    ...     print(delta.format_summary())
    +5 pages | +120ms (+8%) | ⚠️ config changed

Related Modules:
    - bengal.orchestration.stats: BuildStats from build runs
    - bengal.cache.build_cache: Cache with build state
    - bengal.debug.base: Debug tool infrastructure

See Also:
    - bengal/debug/incremental_debugger.py: Cache-specific debugging
    - bengal/cli/commands/debug.py: CLI integration
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.debug.base import DebugRegistry, DebugReport, DebugTool, Severity

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.stats import BuildStats


@dataclass
class BuildSnapshot:
    """
    Snapshot of a build state for comparison.

    Captures key metrics and file lists from a build for delta analysis.

    Attributes:
        timestamp: When the build occurred
        build_time_ms: Total build time
        page_count: Number of pages built
        asset_count: Number of assets processed
        pages: Set of page paths in this build
        output_files: Set of output file paths
        phase_times: Timing by phase (discovery, rendering, etc.)
        config_hash: Hash of configuration at build time
        metadata: Additional build metadata
    """

    timestamp: datetime
    build_time_ms: float = 0
    page_count: int = 0
    asset_count: int = 0
    pages: set[str] = field(default_factory=set)
    output_files: set[str] = field(default_factory=set)
    phase_times: dict[str, float] = field(default_factory=dict)
    config_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_build_stats(cls, stats: BuildStats, pages: set[str]) -> BuildSnapshot:
        """
        Create snapshot from BuildStats.

        Args:
            stats: BuildStats from a completed build
            pages: Set of page paths that were built

        Returns:
            BuildSnapshot capturing the build state
        """
        return cls(
            timestamp=datetime.now(),
            build_time_ms=stats.build_time_ms,
            page_count=stats.total_pages,
            asset_count=stats.total_assets,
            pages=pages,
            phase_times={
                "discovery": stats.discovery_time_ms,
                "taxonomy": stats.taxonomy_time_ms,
                "rendering": stats.rendering_time_ms,
                "assets": stats.assets_time_ms,
                "postprocess": stats.postprocess_time_ms,
            },
            metadata={
                "parallel": stats.parallel,
                "incremental": stats.incremental,
            },
        )

    @classmethod
    def from_cache(cls, cache: BuildCache) -> BuildSnapshot:
        """
        Create snapshot from BuildCache.

        Args:
            cache: BuildCache with build state

        Returns:
            BuildSnapshot capturing cached state
        """
        # Extract content pages from cache
        pages = {
            path for path in cache.file_fingerprints if path.endswith((".md", ".markdown", ".rst"))
        }

        # Parse last build timestamp
        timestamp = datetime.now()
        if cache.last_build:
            with contextlib.suppress(ValueError):
                timestamp = datetime.fromisoformat(cache.last_build)

        return cls(
            timestamp=timestamp,
            page_count=len(pages),
            pages=pages,
            config_hash=cache.config_hash,
            metadata={
                "cached_content": len(cache.parsed_content),
                "tracked_files": len(cache.file_fingerprints),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary suitable for json.dumps(). Sets are converted to lists.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "build_time_ms": self.build_time_ms,
            "page_count": self.page_count,
            "asset_count": self.asset_count,
            "pages": list(self.pages),
            "output_files": list(self.output_files),
            "phase_times": self.phase_times,
            "config_hash": self.config_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildSnapshot:
        """
        Create snapshot from dictionary.

        Args:
            data: Dictionary from to_dict() or JSON parsing.

        Returns:
            Reconstructed BuildSnapshot instance.
        """
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            build_time_ms=data.get("build_time_ms", 0),
            page_count=data.get("page_count", 0),
            asset_count=data.get("asset_count", 0),
            pages=set(data.get("pages", [])),
            output_files=set(data.get("output_files", [])),
            phase_times=data.get("phase_times", {}),
            config_hash=data.get("config_hash"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class BuildDelta:
    """
    Difference between two builds.

    Captures what changed between builds including added/removed pages,
    timing changes, and configuration differences.

    Attributes:
        before: The earlier build snapshot
        after: The later build snapshot
        added_pages: Pages in 'after' but not in 'before'
        removed_pages: Pages in 'before' but not in 'after'
        time_change_ms: Change in build time (positive = slower)
        time_change_pct: Percentage change in build time
        phase_changes: Changes in phase timings
        config_changed: Whether configuration hash changed
    """

    before: BuildSnapshot
    after: BuildSnapshot
    added_pages: set[str] = field(default_factory=set)
    removed_pages: set[str] = field(default_factory=set)
    time_change_ms: float = 0
    time_change_pct: float = 0
    phase_changes: dict[str, float] = field(default_factory=dict)
    config_changed: bool = False

    @classmethod
    def compute(cls, before: BuildSnapshot, after: BuildSnapshot) -> BuildDelta:
        """
        Compute delta between two builds.

        Args:
            before: Earlier build snapshot
            after: Later build snapshot

        Returns:
            BuildDelta with computed differences
        """
        delta = cls(before=before, after=after)

        # Page changes
        delta.added_pages = after.pages - before.pages
        delta.removed_pages = before.pages - after.pages

        # Time changes
        delta.time_change_ms = after.build_time_ms - before.build_time_ms
        if before.build_time_ms > 0:
            delta.time_change_pct = (delta.time_change_ms / before.build_time_ms) * 100

        # Phase changes
        for phase in set(before.phase_times.keys()) | set(after.phase_times.keys()):
            before_time = before.phase_times.get(phase, 0)
            after_time = after.phase_times.get(phase, 0)
            if before_time > 0 or after_time > 0:
                delta.phase_changes[phase] = after_time - before_time

        # Config change
        delta.config_changed = before.config_hash != after.config_hash

        return delta

    @property
    def page_change_count(self) -> int:
        """
        Total pages added or removed.

        Returns:
            Sum of added and removed page counts.
        """
        return len(self.added_pages) + len(self.removed_pages)

    @property
    def is_significant(self) -> bool:
        """
        Check if delta represents significant changes.

        A delta is significant if:
            - Any pages were added or removed
            - Build time changed by more than 10%
            - Configuration changed

        Returns:
            True if changes are significant enough to report.
        """
        return self.page_change_count > 0 or abs(self.time_change_pct) > 10 or self.config_changed

    def format_summary(self) -> str:
        """
        Format as brief one-line summary.

        Returns:
            String like "+5 pages | +120ms (+8%) 🐌 | ⚠️ config changed"
        """
        parts = []

        if self.added_pages:
            parts.append(f"+{len(self.added_pages)} pages")
        if self.removed_pages:
            parts.append(f"-{len(self.removed_pages)} pages")

        if self.time_change_ms != 0:
            sign = "+" if self.time_change_ms > 0 else ""
            if abs(self.time_change_ms) < 1000:
                parts.append(f"{sign}{self.time_change_ms:.0f}ms")
            else:
                parts.append(f"{sign}{self.time_change_ms / 1000:.2f}s")

            if abs(self.time_change_pct) >= 5:
                emoji = "🐌" if self.time_change_pct > 0 else "🚀"
                parts.append(f"({self.time_change_pct:+.0f}%) {emoji}")

        if self.config_changed:
            parts.append("⚠️ config changed")

        return " | ".join(parts) if parts else "No significant changes"

    def format_detailed(self) -> str:
        """
        Format with full details for verbose output.

        Includes timestamps, page changes (with samples), timing
        breakdown by phase, and configuration change warnings.

        Returns:
            Multi-line formatted string.
        """
        lines = ["📊 Build Delta Analysis", ""]

        # Overview
        lines.append(f"Before: {self.before.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"After:  {self.after.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Page changes
        if self.added_pages or self.removed_pages:
            lines.append("📄 Page Changes:")
            if self.added_pages:
                lines.append(f"   Added:   +{len(self.added_pages)}")
                for page in list(self.added_pages)[:5]:
                    lines.append(f"      • {page}")
                if len(self.added_pages) > 5:
                    lines.append(f"      ... and {len(self.added_pages) - 5} more")
            if self.removed_pages:
                lines.append(f"   Removed: -{len(self.removed_pages)}")
                for page in list(self.removed_pages)[:5]:
                    lines.append(f"      • {page}")
                if len(self.removed_pages) > 5:
                    lines.append(f"      ... and {len(self.removed_pages) - 5} more")
            lines.append("")

        # Timing changes
        if self.before.build_time_ms > 0 or self.after.build_time_ms > 0:
            lines.append("⏱️ Timing Changes:")
            lines.append(
                f"   Total: {self._format_time_change(self.time_change_ms, self.time_change_pct)}"
            )

            if self.phase_changes:
                for phase, change in sorted(self.phase_changes.items(), key=lambda x: -abs(x[1])):
                    if abs(change) > 10:  # Only show meaningful changes
                        before_time = self.before.phase_times.get(phase, 0)
                        pct = (change / before_time * 100) if before_time > 0 else 0
                        lines.append(f"   {phase.title()}: {self._format_time_change(change, pct)}")
            lines.append("")

        # Config changes
        if self.config_changed:
            lines.append("⚠️ Configuration Changed")
            lines.append("   Build may have different behavior due to config changes")
            lines.append("")

        return "\n".join(lines)

    def _format_time_change(self, ms: float, pct: float) -> str:
        """
        Format time change with emoji indicators.

        Args:
            ms: Time change in milliseconds.
            pct: Percentage change.

        Returns:
            Formatted string like "+150ms (+12%) 🐌" or "-50ms (-5%) 🚀"
        """
        sign = "+" if ms > 0 else ""

        time_str = f"{sign}{ms:.0f}ms" if abs(ms) < 1000 else f"{sign}{ms / 1000:.2f}s"

        if abs(pct) >= 5:
            emoji = "🐌" if pct > 0 else "🚀"
            return f"{time_str} ({pct:+.0f}%) {emoji}"
        return time_str


class BuildHistory:
    """
    Tracks build history for trend analysis.

    Stores snapshots of builds over time to enable trend analysis,
    baseline comparisons, and performance regression detection.
    History is persisted to disk and automatically pruned to
    max_snapshots.

    Attributes:
        storage_path: Path to JSON file storing history.
        max_snapshots: Maximum number of snapshots to retain.
        snapshots: List of BuildSnapshot in chronological order.

    Example:
        >>> history = BuildHistory(max_snapshots=100)
        >>> history.add(current_snapshot)
        >>> trend = history.compute_trend()
        >>> print(f"Avg build time: {trend['avg_build_time_ms']:.0f}ms")
    """

    def __init__(self, storage_path: Path | None = None, max_snapshots: int = 50):
        """
        Initialize build history.

        Args:
            storage_path: Path to store history JSON file.
                Defaults to .bengal/build_history.json.
            max_snapshots: Maximum snapshots to retain. Older snapshots
                are pruned when limit is exceeded.
        """
        self.storage_path = storage_path or Path(".bengal/build_history.json")
        self.max_snapshots = max_snapshots
        self.snapshots: list[BuildSnapshot] = []
        self._load()

    def _load(self) -> None:
        """Load history from disk if storage file exists."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.snapshots = [BuildSnapshot.from_dict(s) for s in data.get("snapshots", [])]
            except (json.JSONDecodeError, KeyError):
                self.snapshots = []

    def _save(self) -> None:
        """Save history to disk, creating parent directories if needed."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"snapshots": [s.to_dict() for s in self.snapshots]}
        self.storage_path.write_text(json.dumps(data, indent=2))

    def add(self, snapshot: BuildSnapshot) -> None:
        """
        Add a snapshot to history.

        Automatically prunes oldest snapshots if max_snapshots is exceeded.

        Args:
            snapshot: BuildSnapshot to add.
        """
        self.snapshots.append(snapshot)
        # Trim to max
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots :]
        self._save()

    def get_latest(self, n: int = 1) -> list[BuildSnapshot]:
        """
        Get the N most recent snapshots.

        Args:
            n: Number of snapshots to return.

        Returns:
            List of most recent snapshots (may be fewer than n if history is short).
        """
        return self.snapshots[-n:]

    def get_baseline(self) -> BuildSnapshot | None:
        """
        Get the baseline (first) snapshot in history.

        Returns:
            First recorded snapshot, or None if history is empty.
        """
        return self.snapshots[0] if self.snapshots else None

    def compute_trend(self) -> dict[str, Any]:
        """
        Compute trend statistics over history.

        Returns:
            Dictionary with keys:
                - build_count: Number of builds in history
                - avg_build_time_ms: Average build time
                - min_build_time_ms: Fastest build time
                - max_build_time_ms: Slowest build time
                - time_trend: Change in build time (first to last)
                - page_trend: Change in page count (first to last)

            Returns empty dict if fewer than 2 snapshots.
        """
        if len(self.snapshots) < 2:
            return {}

        times = [s.build_time_ms for s in self.snapshots]
        pages = [s.page_count for s in self.snapshots]

        return {
            "build_count": len(self.snapshots),
            "avg_build_time_ms": sum(times) / len(times),
            "min_build_time_ms": min(times),
            "max_build_time_ms": max(times),
            "time_trend": times[-1] - times[0] if len(times) > 1 else 0,
            "page_trend": pages[-1] - pages[0] if len(pages) > 1 else 0,
        }


@DebugRegistry.register
class BuildDeltaAnalyzer(DebugTool):
    """
    Debug tool for comparing builds and explaining changes.

    Helps understand what changed between builds, why build times
    changed, and track build evolution over time.

    Creation:
        Direct instantiation or via DebugRegistry:
            analyzer = BuildDeltaAnalyzer(site=site, cache=cache)

    Example:
        >>> analyzer = BuildDeltaAnalyzer(cache=cache)
        >>> # Compare current build to previous
        >>> delta = analyzer.compare_to_previous()
        >>> print(delta.format_detailed())
    """

    name = "delta"
    description = "Compare builds and explain changes"

    def __init__(
        self,
        site: Site | None = None,
        cache: BuildCache | None = None,
        root_path: Path | None = None,
        history: BuildHistory | None = None,
    ):
        """
        Initialize build delta analyzer.

        Args:
            site: Site instance for current state
            cache: BuildCache for cache inspection
            root_path: Root path of the project
            history: Optional BuildHistory for trend analysis
        """
        super().__init__(site=site, cache=cache, root_path=root_path)
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(self.root_path)
        self.history = history or BuildHistory(storage_path=paths.build_history)

    def analyze(self) -> DebugReport:
        """
        Analyze build deltas and trends.

        Returns:
            DebugReport with findings about build changes
        """
        report = self.create_report()
        report.summary = "Build comparison and trend analysis"

        # Get current state as snapshot
        current = self._get_current_snapshot()
        if not current:
            report.add_finding(
                title="No build data available",
                description="Cannot analyze builds without cache or site data",
                severity=Severity.INFO,
            )
            return report

        # Compare to previous if available
        previous_snapshots = self.history.get_latest(1)
        if previous_snapshots:
            previous = previous_snapshots[0]
            delta = BuildDelta.compute(previous, current)

            report.statistics["pages_added"] = len(delta.added_pages)
            report.statistics["pages_removed"] = len(delta.removed_pages)
            report.statistics["time_change_ms"] = delta.time_change_ms
            report.statistics["time_change_pct"] = f"{delta.time_change_pct:.1f}%"

            # Report significant changes
            if delta.added_pages:
                report.add_finding(
                    title=f"{len(delta.added_pages)} new pages since last build",
                    description="New content was added",
                    severity=Severity.INFO,
                    category="content",
                    metadata={"pages": list(delta.added_pages)[:10]},
                )

            if delta.removed_pages:
                report.add_finding(
                    title=f"{len(delta.removed_pages)} pages removed since last build",
                    description="Content was removed",
                    severity=Severity.INFO,
                    category="content",
                    metadata={"pages": list(delta.removed_pages)[:10]},
                )

            if delta.time_change_pct > 20:
                report.add_finding(
                    title=f"Build time increased by {delta.time_change_pct:.0f}%",
                    description=f"Build took {delta.time_change_ms:.0f}ms longer",
                    severity=Severity.WARNING,
                    category="performance",
                    suggestion="Check for new expensive content or template changes",
                )
            elif delta.time_change_pct < -20:
                report.add_finding(
                    title=f"Build time improved by {abs(delta.time_change_pct):.0f}%",
                    description=f"Build is {abs(delta.time_change_ms):.0f}ms faster",
                    severity=Severity.INFO,
                    category="performance",
                )

            if delta.config_changed:
                report.add_finding(
                    title="Configuration changed since last build",
                    description="Build behavior may differ due to config changes",
                    severity=Severity.WARNING,
                    category="config",
                )

        # Analyze trends
        trend = self.history.compute_trend()
        if trend:
            report.statistics["trend_builds"] = trend["build_count"]
            report.statistics["avg_build_time"] = f"{trend['avg_build_time_ms']:.0f}ms"

            # Long-term performance regression
            if trend.get("time_trend", 0) > 1000:  # >1s slower
                report.add_finding(
                    title="Build times trending slower over time",
                    description=f"Builds are ~{trend['time_trend'] / 1000:.1f}s slower than first recorded",
                    severity=Severity.WARNING,
                    category="trend",
                    suggestion="Consider auditing content and templates for performance",
                )

        # Add current snapshot to history
        self.history.add(current)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def compare_snapshots(self, before: BuildSnapshot, after: BuildSnapshot) -> BuildDelta:
        """
        Compare two specific snapshots.

        Args:
            before: Earlier snapshot
            after: Later snapshot

        Returns:
            BuildDelta with comparison results
        """
        return BuildDelta.compute(before, after)

    def compare_to_previous(self) -> BuildDelta | None:
        """
        Compare current state to most recent snapshot.

        Returns:
            BuildDelta or None if no history available
        """
        current = self._get_current_snapshot()
        if not current:
            return None

        previous_snapshots = self.history.get_latest(1)
        if not previous_snapshots:
            return None

        return BuildDelta.compute(previous_snapshots[0], current)

    def compare_to_baseline(self) -> BuildDelta | None:
        """
        Compare current state to baseline (first) snapshot.

        Returns:
            BuildDelta or None if no baseline available
        """
        current = self._get_current_snapshot()
        if not current:
            return None

        baseline = self.history.get_baseline()
        if not baseline:
            return None

        return BuildDelta.compute(baseline, current)

    def save_baseline(self) -> None:
        """
        Save current state as new baseline.

        Clears history and starts fresh with current build as baseline.
        Useful after major changes or optimizations.
        """
        current = self._get_current_snapshot()
        if current:
            self.history.snapshots = [current]
            self.history._save()

    def _get_current_snapshot(self) -> BuildSnapshot | None:
        """
        Get snapshot of current build state.

        Creates snapshot from cache if available.

        Returns:
            BuildSnapshot or None if no cache available.
        """
        if self.cache:
            return BuildSnapshot.from_cache(self.cache)
        return None

    def _generate_recommendations(self, report: DebugReport) -> list[str]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            report: Completed DebugReport with findings.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        for finding in report.findings:
            if finding.category == "performance" and finding.severity == Severity.WARNING:
                recommendations.append("Investigate build performance regression")
                break

        if report.statistics.get("pages_removed", 0) > 10:
            recommendations.append("Review removed content to ensure it was intentional")

        trend_builds = report.statistics.get("trend_builds", 0)
        if trend_builds < 5:
            recommendations.append(
                "Continue building to establish performance baseline (need 5+ builds)"
            )

        if not recommendations:
            recommendations.append("Build comparison looks healthy! ✅")

        return recommendations
