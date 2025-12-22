"""
Health check report formatting and data structures.

This module provides the core data structures for health check results and
multiple output formats for different contexts (console, JSON, CI integration).

Data Models:
    CheckStatus: Severity enum (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)
    CheckResult: Individual check result with status, message, recommendations
    ValidatorStats: Observability metrics for validator execution
    ValidatorReport: Results from a single validator
    HealthReport: Aggregate report from all validators

Output Formats:
    - Console: Rich text with colors, progressive disclosure for readability
    - JSON: Machine-readable for CI integration and automation
    - Quality scoring: 0-100 score with ratings (Excellent/Good/Fair/Needs Improvement)

Architecture:
    Reports are immutable data containers with computed properties. Formatting
    logic is kept in methods rather than separate functions to enable easy
    serialization and manipulation.

Related:
    - bengal.health.health_check: Orchestrator that produces HealthReport
    - bengal.health.base: Validators that produce CheckResult objects
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from bengal.output.icons import get_icon_set
from bengal.utils.rich_console import should_use_emoji


class CheckStatus(Enum):
    """
    Severity level for a health check result.

    Severity levels are ordered from most to least critical. The build system
    uses these levels to determine exit codes and output formatting:

    Severity Levels:
        ERROR: Blocks builds in strict mode, must fix before shipping
        WARNING: Does not block but should fix, indicates potential problems
        SUGGESTION: Quality improvements, collapsed by default in output
        INFO: Contextual information, hidden unless verbose mode enabled
        SUCCESS: Check passed, typically not shown unless verbose

    Usage:
        Validators return CheckResult with appropriate status. Use factory
        methods like CheckResult.error() or CheckResult.warning() for clarity.
    """

    SUCCESS = "success"
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """
    Result of a single health check.

    CheckResult is the standard output from validators. Use factory methods
    (success, info, suggestion, warning, error) for cleaner construction.

    Attributes:
        status: Severity level (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)
        message: Human-readable description of what was checked/found
        recommendation: Optional fix suggestion (shown for warnings/errors)
        details: Optional list of specific items (e.g., file paths, line numbers)
        validator: Name of validator that produced this result
        metadata: Optional dict for validator-specific data (cacheable, machine-readable)

    Example:
        >>> result = CheckResult.error(
        ...     "Missing required frontmatter field",
        ...     recommendation="Add 'title' to frontmatter",
        ...     details=["content/post.md:1"],
        ... )
    """

    status: CheckStatus
    message: str
    recommendation: str | None = None
    details: list[str] | None = None
    validator: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def success(cls, message: str, validator: str = "") -> CheckResult:
        """Create a success result."""
        return cls(CheckStatus.SUCCESS, message, validator=validator)

    @classmethod
    def info(
        cls,
        message: str,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create an info result."""
        return cls(
            CheckStatus.INFO,
            message,
            recommendation,
            details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def suggestion(
        cls,
        message: str,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create a suggestion result (quality improvement, not a problem)."""
        return cls(
            CheckStatus.SUGGESTION,
            message,
            recommendation,
            details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def warning(
        cls,
        message: str,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create a warning result."""
        return cls(
            CheckStatus.WARNING,
            message,
            recommendation,
            details,
            validator=validator,
            metadata=metadata,
        )

    @classmethod
    def error(
        cls,
        message: str,
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create an error result."""
        return cls(
            CheckStatus.ERROR,
            message,
            recommendation,
            details,
            validator=validator,
            metadata=metadata,
        )

    def is_problem(self) -> bool:
        """Check if this is a warning or error (vs success/info/suggestion)."""
        return self.status in (CheckStatus.WARNING, CheckStatus.ERROR)

    def is_actionable(self) -> bool:
        """Check if this requires action (error, warning, or suggestion)."""
        return self.status in (CheckStatus.ERROR, CheckStatus.WARNING, CheckStatus.SUGGESTION)

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize CheckResult to JSON-serializable dict for caching.

        Returns:
            Dictionary with all fields as JSON-serializable types
        """
        return {
            "status": self.status.value,  # Enum to string
            "message": self.message,
            "recommendation": self.recommendation,
            "details": self.details,
            "validator": self.validator,
            "metadata": self.metadata,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> CheckResult:
        """
        Deserialize CheckResult from cached dict.

        Args:
            data: Dictionary from cache

        Returns:
            CheckResult instance
        """
        return cls(
            status=CheckStatus(data["status"]),  # String to enum
            message=data["message"],
            recommendation=data.get("recommendation"),
            details=data.get("details"),
            validator=data.get("validator", ""),
            metadata=data.get("metadata"),
        )


@dataclass
class ValidatorStats:
    """
    Observability metrics for a validator run.

    Validators can optionally populate stats to provide visibility into
    execution performance, cache effectiveness, and skip reasons. Stats
    are displayed in verbose mode and logged for debugging.

    Follows the ComponentStats pattern from bengal.utils.observability but
    uses page-specific naming appropriate for validator contexts.

    Attributes:
        pages_total: Total pages available in site
        pages_processed: Number of pages actually validated
        pages_skipped: Dict mapping skip reason to count
        cache_hits: Count of results retrieved from cache
        cache_misses: Count of results computed fresh
        sub_timings: Dict mapping operation name to duration in ms
        metrics: Custom metrics dict (validator-specific)

    Example:
        >>> stats = ValidatorStats(
        ...     pages_total=100,
        ...     pages_processed=95,
        ...     pages_skipped={"draft": 5},
        ...     cache_hits=80,
        ...     cache_misses=15,
        ... )
        >>> print(stats.format_summary())

    See Also:
        bengal.utils.observability.ComponentStats for the generic pattern
    """

    pages_total: int = 0
    pages_processed: int = 0
    pages_skipped: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    sub_timings: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, int | float | str] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        """Skip rate as percentage (0-100)."""
        if self.pages_total == 0:
            return 0.0
        skipped = sum(self.pages_skipped.values())
        return skipped / self.pages_total * 100

    @property
    def total_skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.pages_skipped.values())

    def format_summary(self) -> str:
        """Format stats for debug output."""
        parts = [f"processed={self.pages_processed}/{self.pages_total}"]

        if self.pages_skipped:
            skip_str = ", ".join(f"{k}={v}" for k, v in self.pages_skipped.items())
            parts.append(f"skipped=[{skip_str}]")

        if self.cache_hits or self.cache_misses:
            total = self.cache_hits + self.cache_misses
            parts.append(f"cache={self.cache_hits}/{total} ({self.cache_hit_rate:.0f}%)")

        if self.sub_timings:
            timing_str = ", ".join(f"{k}={v:.0f}ms" for k, v in self.sub_timings.items())
            parts.append(f"timings=[{timing_str}]")

        if self.metrics:
            metrics_str = ", ".join(f"{k}={v}" for k, v in self.metrics.items())
            parts.append(f"metrics=[{metrics_str}]")

        return " | ".join(parts)

    def to_log_context(self) -> dict[str, int | float | str]:
        """
        Convert to flat dict for structured logging.

        Returns:
            Flat dictionary suitable for structured logging kwargs.
        """
        ctx: dict[str, int | float | str] = {
            "pages_total": self.pages_total,
            "pages_processed": self.pages_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "skip_rate": self.skip_rate,
        }

        # Flatten sub-timings
        for timing_key, timing_val in self.sub_timings.items():
            ctx[f"timing_{timing_key}_ms"] = timing_val

        # Flatten skip reasons
        for skip_key, skip_val in self.pages_skipped.items():
            ctx[f"skipped_{skip_key}"] = skip_val

        # Flatten metrics
        for metric_key, metric_val in self.metrics.items():
            ctx[f"metric_{metric_key}"] = metric_val  # type: ignore[assignment]

        return ctx


@dataclass
class ValidatorReport:
    """
    Report from a single validator's execution.

    Aggregates all CheckResult objects from one validator along with timing
    and optional observability stats. Used by HealthReport to build the
    complete validation picture.

    Attributes:
        validator_name: Human-readable name of the validator
        results: All CheckResult objects produced by this validator
        duration_ms: Wall-clock time for validator execution
        stats: Optional ValidatorStats for observability
    """

    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    stats: ValidatorStats | None = None

    @property
    def passed_count(self) -> int:
        """Count of successful checks."""
        return sum(1 for r in self.results if r.status == CheckStatus.SUCCESS)

    @property
    def info_count(self) -> int:
        """Count of info messages."""
        return sum(1 for r in self.results if r.status == CheckStatus.INFO)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for r in self.results if r.status == CheckStatus.WARNING)

    @property
    def suggestion_count(self) -> int:
        """Count of suggestions (quality improvements)."""
        return sum(1 for r in self.results if r.status == CheckStatus.SUGGESTION)

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for r in self.results if r.status == CheckStatus.ERROR)

    @property
    def has_problems(self) -> bool:
        """Check if this validator found any warnings or errors."""
        return self.warning_count > 0 or self.error_count > 0

    @property
    def status_emoji(self) -> str:
        """Get icon representing overall status."""
        icons = get_icon_set(should_use_emoji())
        if self.error_count > 0:
            return icons.error
        elif self.warning_count > 0:
            return icons.warning
        elif self.suggestion_count > 0:
            return icons.tip
        elif self.info_count > 0:
            return icons.info
        else:
            return icons.success


@dataclass
class HealthReport:
    """
    Complete health check report aggregating all validator results.

    HealthReport is the top-level output from HealthCheck.run(). It provides
    multiple output formats (console, JSON) and computed properties for
    quality assessment.

    Attributes:
        validator_reports: List of ValidatorReport from each validator
        timestamp: When the health check was executed
        build_stats: Optional build statistics dict from the build process

    Output Formats:
        format_console(): Rich text with progressive disclosure
        format_json(): Machine-readable dict for CI/automation

    Quality Metrics:
        build_quality_score(): 0-100 penalty-based score
        quality_rating(): "Excellent"/"Good"/"Fair"/"Needs Improvement"
    """

    validator_reports: list[ValidatorReport] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    build_stats: dict[str, Any] | None = None

    @property
    def total_passed(self) -> int:
        """Total successful checks across all validators."""
        return sum(r.passed_count for r in self.validator_reports)

    @property
    def total_info(self) -> int:
        """Total info messages across all validators."""
        return sum(r.info_count for r in self.validator_reports)

    @property
    def total_warnings(self) -> int:
        """Total warnings across all validators."""
        return sum(r.warning_count for r in self.validator_reports)

    @property
    def total_suggestions(self) -> int:
        """Total suggestions (quality improvements) across all validators."""
        return sum(r.suggestion_count for r in self.validator_reports)

    @property
    def total_errors(self) -> int:
        """Total errors across all validators."""
        return sum(r.error_count for r in self.validator_reports)

    @property
    def total_checks(self) -> int:
        """Total number of checks run."""
        return (
            self.total_passed
            + self.total_info
            + self.total_suggestions
            + self.total_warnings
            + self.total_errors
        )

    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return self.total_errors > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return self.total_warnings > 0

    def has_problems(self) -> bool:
        """Check if any errors or warnings were found."""
        return self.has_errors() or self.has_warnings()

    def build_quality_score(self) -> int:
        """
        Calculate build quality score (0-100).

        Uses a penalty-based system where:
        - Base score is 100 (no problems = perfect)
        - Errors subtract significantly (blockers)
        - Warnings subtract moderately (should fix)
        - Diminishing returns prevent extreme scores for many small issues

        This ensures same problems always give the same score, regardless
        of how many checks ran.

        Returns:
            Score from 0-100 (100 = perfect)
        """
        if self.total_checks == 0:
            return 100

        # No problems = 100%
        if self.total_errors == 0 and self.total_warnings == 0:
            return 100

        # Penalty system with diminishing returns
        # Errors: 20 points each, but diminish after 2 (avoids 0% for many issues)
        # Formula: min(70, errors * 20 - max(0, errors - 2) * 5)
        # This gives: 1 error=20, 2 errors=40, 3 errors=55, 4 errors=70 (cap)
        error_penalty = min(70, self.total_errors * 20 - max(0, self.total_errors - 2) * 5)

        # Warnings: 5 points each, capped at 25
        warning_penalty = min(25, self.total_warnings * 5)

        score = 100 - error_penalty - warning_penalty
        return max(0, score)

    def quality_rating(self) -> str:
        """
        Get quality rating based on score.

        Thresholds aligned with penalty-based scoring:
        - Excellent (90+): No errors, 0-2 warnings
        - Good (75-89): 1 error or 3-5 warnings
        - Fair (50-74): 2-3 errors or many warnings
        - Needs Improvement (<50): 4+ errors
        """
        score = self.build_quality_score()

        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        else:
            return "Needs Improvement"

    def format_console(
        self, mode: str = "auto", verbose: bool = False, show_suggestions: bool = False
    ) -> str:
        """
        Format report for console output.

        Args:
            mode: Display mode - "auto", "quiet", "normal", "verbose"
                  auto = quiet if no problems, normal if warnings/errors
            verbose: Legacy parameter, sets mode to "verbose"
            show_suggestions: Whether to show suggestions (quality improvements)

        Returns:
            Formatted string ready to print
        """
        # Handle legacy verbose parameter
        if verbose:
            mode = "verbose"

        # Auto-detect mode based on results
        if mode == "auto":
            mode = "quiet" if not self.has_problems() else "normal"

        if mode == "quiet":
            return self._format_quiet(show_suggestions=show_suggestions)
        elif mode == "verbose":
            return self._format_verbose(show_suggestions=show_suggestions)
        else:  # normal
            return self._format_normal(show_suggestions=show_suggestions)

    def _format_quiet(self, show_suggestions: bool = False) -> str:
        """
        Minimal output - perfect builds get one line, problems shown clearly.

        Args:
            show_suggestions: Whether to show suggestions (ignored in quiet mode)
        """
        lines = []

        # Perfect build - just success message
        if not self.has_problems():
            score = self.build_quality_score()
            icons = get_icon_set(should_use_emoji())
            return f"{icons.success} Build complete. All health checks passed (quality: {score}%)\n"

        # Has problems - show them
        lines.append("")

        icons = get_icon_set(should_use_emoji())

        # Group by validator, only show problems
        for vr in self.validator_reports:
            if not vr.has_problems:
                continue

            # Show validator name with problem count
            problem_count = vr.warning_count + vr.error_count
            status_icon = icons.error if vr.error_count > 0 else icons.warning
            lines.append(f"{status_icon} {vr.validator_name} ({problem_count} issue(s)):")

            # Show problem messages
            for result in vr.results:
                if result.is_problem():
                    lines.append(f"   • {result.message}")

                    # Show recommendation
                    if result.recommendation:
                        lines.append(f"     {icons.tip} {result.recommendation}")

                    # Show first 3 details
                    if result.details:
                        for detail in result.details[:3]:
                            lines.append(f"        - {detail}")
                        if len(result.details) > 3:
                            remaining = len(result.details) - 3
                            lines.append(f"        ... and {remaining} more")

            lines.append("")  # Blank line between validators

        # Summary
        score = self.build_quality_score()
        rating = self.quality_rating()
        summary_parts = []

        if self.total_errors > 0:
            summary_parts.append(f"{self.total_errors} error(s)")
        if self.total_warnings > 0:
            summary_parts.append(f"{self.total_warnings} warning(s)")

        lines.append(f"Build Quality: {score}% ({rating}) · {', '.join(summary_parts)}")
        lines.append("")

        return "\n".join(lines)

    def _format_normal(self, show_suggestions: bool = False) -> str:
        """
        Balanced output with progressive disclosure - problems first, then successes.
        Reduces cognitive load by prioritizing actionable information.

        Args:
            show_suggestions: Whether to show suggestions (collapsed by default)
        """
        icons = get_icon_set(should_use_emoji())
        lines = []

        # No header - flows from phase line "✓ Health check Xms"
        lines.append("")

        # Separate validators by priority: problems first, then suggestions, then passed
        # Skip validators that only have INFO messages (writers don't need that noise)
        validators_with_problems = []
        validators_with_suggestions = []
        validators_passed = []

        for vr in self.validator_reports:
            # Skip INFO-only validators
            if (
                vr.info_count > 0
                and vr.error_count == 0
                and vr.warning_count == 0
                and vr.suggestion_count == 0
            ):
                continue

            if vr.has_problems:
                validators_with_problems.append(vr)
            elif vr.suggestion_count > 0:
                validators_with_suggestions.append(vr)
            else:
                validators_passed.append(vr)

        # Sort problems by severity: errors first, then warnings
        validators_with_problems.sort(key=lambda v: (v.error_count == 0, v.warning_count == 0))

        # Show problems first (most important - what needs attention)
        if validators_with_problems:
            lines.append("[bold]Issues:[/bold]")
            lines.append("")

            for i, vr in enumerate(validators_with_problems):
                is_last_problem = i == len(validators_with_problems) - 1

                # Clean header: - ValidatorName (count)
                if vr.error_count > 0:
                    count_str = f"[error]{vr.error_count} error(s)[/error]"
                elif vr.warning_count > 0:
                    count_str = f"[warning]{vr.warning_count} warning(s)[/warning]"
                else:
                    count_str = f"[info]{vr.info_count} info[/info]"

                lines.append(f"  {vr.status_emoji} [bold]{vr.validator_name}[/bold] ({count_str})")

                # Show problem details - location first, then context
                problem_results = [r for r in vr.results if r.is_problem()]
                for j, result in enumerate(problem_results):
                    # Brief message describing the issue type
                    lines.append(f"    • {result.message}")

                    # Show recommendation if available
                    if result.recommendation:
                        lines.append(f"      {icons.tip} {result.recommendation}")

                    # Details show location + context (the important part)
                    if result.details:
                        for detail in result.details[:3]:
                            # Details are already formatted with location:line
                            lines.append(f"      {detail}")
                        if len(result.details) > 3:
                            lines.append(f"      ... and {len(result.details) - 3} more")

                    # Add spacing between issues (not after the last one)
                    if j < len(problem_results) - 1:
                        lines.append("")

                if not is_last_problem:
                    lines.append("")  # Blank line between validators

        # Show suggestions (collapsed by default, only if show_suggestions=True)
        if validators_with_suggestions and show_suggestions:
            if validators_with_problems:
                lines.append("")
            lines.append("[bold]Suggestions:[/bold]")
            lines.append("")

            for i, vr in enumerate(validators_with_suggestions):
                is_last_suggestion = i == len(validators_with_suggestions) - 1

                lines.append(
                    f"  {icons.tip} [bold]{vr.validator_name}[/bold] ([info]{vr.suggestion_count} suggestion(s)[/info])"
                )

                for result in vr.results:
                    if result.status == CheckStatus.SUGGESTION:
                        lines.append(f"    • {result.message}")

                if not is_last_suggestion:
                    lines.append("")
        elif validators_with_suggestions:
            # Collapsed: just show count
            if validators_with_problems:
                lines.append("")
            lines.append(
                f"[info]{icons.tip} {self.total_suggestions} quality suggestion(s) available (use --suggestions to view)[/info]"
            )

        # Show passed validators in a collapsed summary (reduce noise)
        if validators_passed:
            if validators_with_problems or (validators_with_suggestions and show_suggestions):
                lines.append("")
            lines.append(
                f"[success]{icons.success} {len(validators_passed)} validator(s) passed[/success]"
            )
            # List them in a compact format if few, otherwise just count
            if len(validators_passed) <= 5:
                passed_names = ", ".join([vr.validator_name for vr in validators_passed])
                lines.append(f"   {passed_names}")

        # Summary (compact single line)
        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append("")
        lines.append(
            f"Health: {self.total_errors} error(s), {self.total_warnings} warning(s) | Quality: {score}% ({rating})"
        )

        # Indent all lines since this is a sub-item of the Health check phase
        return "\n".join(f"  {line}" if line.strip() else "" for line in lines)

    def _format_verbose(self, show_suggestions: bool = True) -> str:
        """
        Full audit trail with progressive disclosure - problems first, then all details.

        Args:
            show_suggestions: Whether to show suggestions (default True in verbose mode)
        """
        icons = get_icon_set(should_use_emoji())
        lines = []

        # No header - flows from phase line "✓ Health check Xms"
        lines.append("")

        # Separate validators by priority: problems first, then suggestions, then passed
        validators_with_problems = []
        validators_with_suggestions = []
        validators_passed = []

        for vr in self.validator_reports:
            if vr.has_problems:
                validators_with_problems.append(vr)
            elif vr.suggestion_count > 0:
                validators_with_suggestions.append(vr)
            else:
                validators_passed.append(vr)

        # Sort problems by severity: errors first, then warnings
        validators_with_problems.sort(key=lambda v: (v.error_count == 0, v.warning_count == 0))

        # Show problems first (most important - what needs attention)
        if validators_with_problems:
            lines.append("[bold]Issues:[/bold]")
            lines.append("")

            for i, vr in enumerate(validators_with_problems):
                is_last_problem = i == len(validators_with_problems) - 1

                # Clean header
                if vr.error_count > 0:
                    count_str = f"[error]{vr.error_count} error(s)[/error]"
                elif vr.warning_count > 0:
                    count_str = f"[warning]{vr.warning_count} warning(s)[/warning]"
                else:
                    count_str = f"[info]{vr.info_count} info[/info]"

                lines.append(f"  {vr.status_emoji} [bold]{vr.validator_name}[/bold] ({count_str})")

                # Show ALL results in verbose mode (including successes for context)
                problem_results = [r for r in vr.results if r.is_problem()]
                other_results = [r for r in vr.results if not r.is_problem()]

                for j, result in enumerate(problem_results):
                    # Problems get full detail - location first
                    lines.append(f"    • {result.message}")
                    if result.details:
                        for detail in result.details[:5]:
                            lines.append(f"      {detail}")
                        if len(result.details) > 5:
                            lines.append(f"      ... and {len(result.details) - 5} more")

                    # Add spacing between issues
                    if j < len(problem_results) - 1:
                        lines.append("")

                # Show successes briefly (grouped at end)
                for result in other_results:
                    lines.append(f"    {icons.success} {result.message}")

                if not is_last_problem:
                    lines.append("")

        # Show passed validators (collapsed in verbose too, but expandable)
        if validators_passed:
            if validators_with_problems:
                lines.append("")
            lines.append(
                f"[success]{icons.success} {len(validators_passed)} validator(s) passed[/success]"
            )

            # In verbose mode, show brief summary of passed checks within each validator
            for vr in validators_passed:
                lines.append(f"   {icons.success} {vr.validator_name}")

        # Summary (compact single line)
        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append("")
        lines.append(
            f"Health: {self.total_errors} error(s), {self.total_warnings} warning(s) | Quality: {score}% ({rating})"
        )

        # Indent all lines since this is a sub-item of the Health check phase
        return "\n".join(f"  {line}" if line.strip() else "" for line in lines)

    def format_json(self) -> dict[str, Any]:
        """
        Format report as JSON-serializable dictionary.

        Returns:
            Dictionary suitable for json.dumps()
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.total_passed,
                "info": self.total_info,
                "warnings": self.total_warnings,
                "errors": self.total_errors,
                "quality_score": self.build_quality_score(),
                "quality_rating": self.quality_rating(),
            },
            "validators": [
                {
                    "name": vr.validator_name,
                    "duration_ms": vr.duration_ms,
                    "summary": {
                        "passed": vr.passed_count,
                        "info": vr.info_count,
                        "warnings": vr.warning_count,
                        "errors": vr.error_count,
                    },
                    "results": [
                        {
                            "status": r.status.value,
                            "message": r.message,
                            "recommendation": r.recommendation,
                            "details": r.details,
                            "metadata": r.metadata,
                        }
                        for r in vr.results
                    ],
                }
                for vr in self.validator_reports
            ],
            "build_stats": self.build_stats,
        }
