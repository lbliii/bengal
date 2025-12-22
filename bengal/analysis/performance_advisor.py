"""
Performance analysis and intelligent suggestions for Bengal builds.

Analyzes build statistics to identify bottlenecks and generate actionable
recommendations for improving build speed, resource usage, and developer
experience. The advisor provides letter grades, priority-ranked suggestions,
and specific configuration examples.

Analysis Areas:
    - Parallel Processing: Detect opportunities for multi-core rendering
    - Incremental Builds: Identify potential for cache-based optimization
    - Rendering Performance: Find template bottlenecks and slow pages
    - Asset Optimization: Detect slow image/CSS processing
    - Memory Usage: Flag high memory consumption patterns
    - Template Complexity: Identify overly complex template logic

Grading System:
    - A (90-100): Excellent performance, well-optimized
    - B (75-89): Good performance, minor optimizations possible
    - C (60-74): Fair performance, improvements recommended
    - D (45-59): Poor performance, needs improvement
    - F (0-44): Critical performance issues

Classes:
    SuggestionType: Category of performance suggestion
    SuggestionPriority: Priority level (HIGH, MEDIUM, LOW)
    PerformanceSuggestion: A single recommendation with impact estimate
    PerformanceGrade: Overall build performance assessment
    PerformanceAdvisor: Main analyzer that generates suggestions

Example:
    >>> from bengal.analysis.performance_advisor import analyze_build
    >>> advisor = analyze_build(stats)
    >>> grade = advisor.get_grade()
    >>> print(f"Performance Grade: {grade.grade} ({grade.score}/100)")
    >>> for suggestion in advisor.get_top_suggestions(3):
    ...     print(f"{suggestion.title}: {suggestion.impact}")

See Also:
    - bengal/orchestration/stats.py: BuildStats data source
    - bengal/cli/build.py: CLI integration
"""

from __future__ import annotations

import multiprocessing
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats


class SuggestionType(Enum):
    """Types of performance suggestions."""

    PARALLEL = "parallel"
    CACHING = "caching"
    ASSETS = "assets"
    TEMPLATES = "templates"
    MEMORY = "memory"
    OPTIMIZATION = "optimization"


class SuggestionPriority(Enum):
    """Priority levels for suggestions."""

    HIGH = "high"  # >20% potential improvement
    MEDIUM = "medium"  # 5-20% potential improvement
    LOW = "low"  # <5% potential improvement


@dataclass
class PerformanceSuggestion:
    """
    A single performance improvement suggestion.

    Represents an actionable recommendation to improve build performance,
    with estimated impact and configuration examples.

    Attributes:
        type: Category of suggestion (BUILD, CONTENT, CONFIG, etc.)
        priority: Priority level (HIGH, MEDIUM, LOW)
        title: Short title of the suggestion
        description: Detailed explanation of the issue
        impact: Estimated performance impact (e.g., "Could save ~2.5s")
        action: What the user should do to implement this suggestion
        config_example: Optional example configuration change
    """

    type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    impact: str  # e.g., "Could save ~2.5s" or "Would improve by 30%"
    action: str  # What the user should do
    config_example: str | None = None  # Example config change

    def __str__(self) -> str:
        """Format suggestion for display."""
        priority_emoji = {
            SuggestionPriority.HIGH: "🔥",
            SuggestionPriority.MEDIUM: "💡",
            SuggestionPriority.LOW: "ℹ️",
        }

        emoji = priority_emoji.get(self.priority, "ℹ️")
        return f"{emoji} {self.title}"


@dataclass
class PerformanceGrade:
    """
    Overall performance assessment for a build.

    Provides a letter grade (A-F) and category assessment based on
    build performance metrics and best practices compliance.

    Attributes:
        grade: Letter grade (A, B, C, D, or F)
        score: Numeric score (0-100)
        category: Performance category ("Excellent", "Good", "Fair", "Poor", "Critical")
        summary: One-line summary of performance assessment
    """

    grade: str  # A, B, C, D, F
    score: int  # 0-100
    category: str  # "Excellent", "Good", "Fair", "Poor", "Critical"
    summary: str  # One-line summary

    @classmethod
    def calculate(cls, stats: BuildStats) -> PerformanceGrade:
        """
        Calculate performance grade based on build statistics.

        Scoring factors:
        - Build speed (pages/second)
        - Time distribution (balanced vs bottlenecked)
        - Cache effectiveness (if incremental)
        - Resource usage
        """
        score = 100

        # Factor 1: Throughput (50 points)
        if stats.build_time_ms > 0 and stats.total_pages > 0:
            pages_per_second = (stats.total_pages / stats.build_time_ms) * 1000

            if pages_per_second >= 100:
                throughput_score = 50
            elif pages_per_second >= 50:
                throughput_score = 40
            elif pages_per_second >= 20:
                throughput_score = 30
            elif pages_per_second >= 10:
                throughput_score = 20
            else:
                throughput_score = 10

            score = throughput_score

        # Factor 2: Time distribution (30 points)
        # Penalize if one phase takes >60% of time (bottleneck)
        total_phase_time = (
            stats.discovery_time_ms
            + stats.taxonomy_time_ms
            + stats.rendering_time_ms
            + stats.assets_time_ms
            + stats.postprocess_time_ms
        )

        if total_phase_time > 0:
            max_phase_pct = max(
                stats.discovery_time_ms / total_phase_time,
                stats.taxonomy_time_ms / total_phase_time,
                stats.rendering_time_ms / total_phase_time,
                stats.assets_time_ms / total_phase_time,
                stats.postprocess_time_ms / total_phase_time,
            )

            if max_phase_pct < 0.5:
                balance_score = 30  # Well balanced
            elif max_phase_pct < 0.6:
                balance_score = 20  # Slight bottleneck
            elif max_phase_pct < 0.7:
                balance_score = 10  # Clear bottleneck
            else:
                balance_score = 0  # Severe bottleneck

            score += balance_score

        # Factor 3: Build mode (20 points)
        if stats.parallel:
            score += 15  # Using parallelism
        if stats.incremental:
            score += 5  # Using caching

        # Convert score to grade
        if score >= 90:
            grade = "A"
            category = "Excellent"
            summary = "Build performance is excellent! 🚀"
        elif score >= 75:
            grade = "B"
            category = "Good"
            summary = "Build performance is good, but could be optimized"
        elif score >= 60:
            grade = "C"
            category = "Fair"
            summary = "Build performance is acceptable, improvements recommended"
        elif score >= 45:
            grade = "D"
            category = "Poor"
            summary = "Build performance needs improvement"
        else:
            grade = "F"
            category = "Critical"
            summary = "Build performance is critically slow"

        return cls(grade=grade, score=score, category=category, summary=summary)


class PerformanceAdvisor:
    """
    Analyzes build performance and provides intelligent suggestions.

    Uses build statistics to identify bottlenecks and recommend
    optimizations tailored to the specific project.
    """

    def __init__(self, stats: BuildStats, environment: dict[str, Any] | None = None):
        """
        Initialize performance advisor.

        Args:
            stats: Build statistics to analyze
            environment: Environment info from rich_console.detect_environment()
        """
        self.stats = stats
        self.environment = environment or {}
        self.suggestions: list[PerformanceSuggestion] = []

    def analyze(self) -> list[PerformanceSuggestion]:
        """
        Analyze build and generate suggestions.

        Returns:
            List of suggestions, ordered by priority
        """
        self.suggestions = []

        # Skip analysis if build was skipped
        if self.stats.skipped:
            return []

        # Run analysis checks
        self._check_parallel_opportunity()
        self._check_incremental_opportunity()
        self._check_rendering_bottleneck()
        self._check_asset_optimization()
        self._check_memory_usage()
        self._check_template_complexity()

        # Sort by priority (high -> medium -> low)
        priority_order = {
            SuggestionPriority.HIGH: 0,
            SuggestionPriority.MEDIUM: 1,
            SuggestionPriority.LOW: 2,
        }
        self.suggestions.sort(key=lambda s: priority_order[s.priority])

        return self.suggestions

    def _check_parallel_opportunity(self) -> None:
        """Check if parallel builds would help."""
        # Already using parallel?
        if self.stats.parallel:
            # Check if we're using optimal workers
            cpu_cores = self.environment.get("cpu_cores", multiprocessing.cpu_count())

            # For large page counts, suggest adjusting max_workers
            if self.stats.total_pages > 500 and cpu_cores > 4:
                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.PARALLEL,
                        priority=SuggestionPriority.LOW,
                        title="Fine-tune parallel workers",
                        description=f"You have {cpu_cores} CPU cores and {self.stats.total_pages} pages",
                        impact="Could improve by 10-20% with optimal settings",
                        action=f"Try setting max_workers to {min(cpu_cores, 8)} in config",
                        config_example=f"max_workers: {min(cpu_cores, 8)}",
                    )
                )
            return

        # Not using parallel - would it help?
        if self.stats.total_pages >= 20:
            # Estimate time savings
            estimated_speedup = min(3.0, multiprocessing.cpu_count() / 2)
            time_saved = self.stats.rendering_time_ms * (1 - 1 / estimated_speedup) / 1000

            if time_saved > 1.0:  # >1s savings
                priority = SuggestionPriority.HIGH if time_saved > 5 else SuggestionPriority.MEDIUM

                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.PARALLEL,
                        priority=priority,
                        title="Enable parallel rendering",
                        description=f"Your {self.stats.total_pages} pages are rendered sequentially",
                        impact=f"Could save ~{time_saved:.1f}s ({estimated_speedup:.1f}x speedup)",
                        action="Run: bengal build --parallel",
                        config_example="parallel: true  # in config.yml",
                    )
                )

    def _check_incremental_opportunity(self) -> None:
        """Check if incremental builds would help."""
        if self.stats.incremental:
            # Already using incremental - check cache effectiveness
            # This would require cache stats (Phase 2 feature)
            return

        # Not using incremental - would it help?
        if self.stats.total_pages >= 10:
            # For development, incremental can save significant time
            typical_change_pct = 0.05  # Assume 5% of pages change typically
            estimated_pages_saved = int(self.stats.total_pages * (1 - typical_change_pct))
            time_per_page = self.stats.rendering_time_ms / max(self.stats.total_pages, 1)
            time_saved = (estimated_pages_saved * time_per_page) / 1000

            if time_saved > 2.0:  # >2s potential savings
                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.CACHING,
                        priority=SuggestionPriority.MEDIUM,
                        title="Try incremental builds",
                        description=f"Rebuilding all {self.stats.total_pages} pages each time",
                        impact=f"Could skip ~{estimated_pages_saved} unchanged pages in dev",
                        action="Run: bengal build --incremental",
                        config_example="# Automatically enabled in 'bengal serve'",
                    )
                )

    def _check_rendering_bottleneck(self) -> None:
        """Check if rendering is a bottleneck."""
        total_phase_time = (
            self.stats.discovery_time_ms
            + self.stats.taxonomy_time_ms
            + self.stats.rendering_time_ms
            + self.stats.assets_time_ms
            + self.stats.postprocess_time_ms
        )

        if total_phase_time == 0:
            return

        # Is rendering >60% of build time?
        rendering_pct = self.stats.rendering_time_ms / total_phase_time

        if rendering_pct > 0.6 and self.stats.rendering_time_ms > 1000:
            # Rendering is a bottleneck
            time_per_page = self.stats.rendering_time_ms / max(self.stats.total_pages, 1)

            if time_per_page > 50:  # >50ms per page is slow
                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.TEMPLATES,
                        priority=SuggestionPriority.HIGH,
                        title="Optimize template rendering",
                        description=f"Templates take {time_per_page:.0f}ms per page (slow)",
                        impact="Could improve build time by 30-50%",
                        action="Check for expensive filters, loops, or includes in templates",
                        config_example="# Consider simplifying complex template logic",
                    )
                )

    def _check_asset_optimization(self) -> None:
        """Check asset processing performance."""
        if self.stats.assets_time_ms == 0:
            return

        # Is asset processing slow relative to page count?
        if self.stats.assets_time_ms > 2000 and self.stats.total_assets > 20:
            time_per_asset = self.stats.assets_time_ms / max(self.stats.total_assets, 1)

            if time_per_asset > 100:  # >100ms per asset
                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.ASSETS,
                        priority=SuggestionPriority.MEDIUM,
                        title="Optimize asset processing",
                        description=f"Assets take {time_per_asset:.0f}ms each to process",
                        impact="Could save 2-5s with optimization",
                        action="Check for large images or unoptimized CSS bundles",
                        config_example="# Consider image optimization or lazy loading",
                    )
                )

    def _check_memory_usage(self) -> None:
        """Check memory usage and suggest optimizations."""
        if self.stats.memory_peak_mb == 0:
            return  # No memory data

        # Is memory usage high?
        if self.stats.memory_peak_mb > 1000:  # >1GB
            self.suggestions.append(
                PerformanceSuggestion(
                    type=SuggestionType.MEMORY,
                    priority=SuggestionPriority.MEDIUM,
                    title="High memory usage detected",
                    description=f"Peak memory: {self.stats.memory_peak_mb:.0f}MB",
                    impact="Could reduce memory footprint by 30-50%",
                    action="Consider using --memory-optimized flag for large sites",
                    config_example="memory_optimized: true  # For 5K+ pages",
                )
            )

    def _check_template_complexity(self) -> None:
        """Check for template complexity issues."""
        # Check if we have directive statistics
        if self.stats.total_directives > 0:
            # High directive usage might indicate complex templates
            directives_per_page = self.stats.total_directives / max(self.stats.total_pages, 1)

            if directives_per_page > 20:  # >20 directives per page average
                self.suggestions.append(
                    PerformanceSuggestion(
                        type=SuggestionType.TEMPLATES,
                        priority=SuggestionPriority.LOW,
                        title="Template complexity is high",
                        description=f"Average {directives_per_page:.0f} directives per page",
                        impact="Simplified templates render faster",
                        action="Review templates for unnecessary complexity",
                        config_example="# Consider extracting reusable components",
                    )
                )

    def get_grade(self) -> PerformanceGrade:
        """
        Get overall performance grade.

        Returns:
            PerformanceGrade with score and category
        """
        return PerformanceGrade.calculate(self.stats)

    def get_bottleneck(self) -> str | None:
        """
        Identify the primary bottleneck phase.

        Returns:
            Name of slowest phase, or None if well-balanced
        """
        phases = {
            "Discovery": self.stats.discovery_time_ms,
            "Taxonomies": self.stats.taxonomy_time_ms,
            "Rendering": self.stats.rendering_time_ms,
            "Assets": self.stats.assets_time_ms,
            "Postprocess": self.stats.postprocess_time_ms,
        }

        total = sum(phases.values())
        if total == 0:
            return None

        # Find slowest phase
        slowest = max(phases.items(), key=lambda x: x[1])

        # Only consider it a bottleneck if >50% of time
        if slowest[1] / total > 0.5:
            return slowest[0]

        return None

    def get_top_suggestions(self, limit: int = 3) -> list[PerformanceSuggestion]:
        """
        Get top N suggestions.

        Args:
            limit: Maximum number of suggestions to return

        Returns:
            Up to `limit` highest-priority suggestions
        """
        if not self.suggestions:
            self.analyze()

        return self.suggestions[:limit]

    def format_summary(self) -> str:
        """
        Format a text summary of analysis.

        Returns:
            Multi-line string with analysis summary
        """
        grade = self.get_grade()
        bottleneck = self.get_bottleneck()
        top_suggestions = self.get_top_suggestions(3)

        lines = []
        lines.append(f"Performance Grade: {grade.grade} ({grade.score}/100)")
        lines.append(f"Category: {grade.category}")

        if bottleneck:
            lines.append(f"Bottleneck: {bottleneck}")

        if top_suggestions:
            lines.append("\nTop Suggestions:")
            for i, suggestion in enumerate(top_suggestions, 1):
                lines.append(f"  {i}. {suggestion.title}")
                lines.append(f"     {suggestion.impact}")

        return "\n".join(lines)


# Convenience function for quick analysis
def analyze_build(
    stats: BuildStats, environment: dict[str, Any] | None = None
) -> PerformanceAdvisor:
    """
    Quick analysis of build statistics.

    Args:
        stats: Build statistics
        environment: Optional environment info

    Returns:
        PerformanceAdvisor with analysis complete
    """
    advisor = PerformanceAdvisor(stats, environment)
    advisor.analyze()
    return advisor
