"""
Health check report formatting and data structures.

Provides structured reporting of health check results with multiple output formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CheckStatus(Enum):
    """Status of a health check.

    Severity levels (from most to least critical):
    - ERROR: Blocks builds, must fix
    - WARNING: Don't block, but should fix
    - SUGGESTION: Quality improvements (collapsed by default)
    - INFO: Contextual information (hidden unless verbose)
    - SUCCESS: Check passed
    """

    SUCCESS = "success"
    INFO = "info"
    SUGGESTION = "suggestion"  # Quality improvements, not problems
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """
    Result of a single health check.

    Attributes:
        status: Status level (success, info, warning, error)
        message: Human-readable description of the check result
        recommendation: Optional suggestion for how to fix/improve (shown for warnings/errors)
        details: Optional additional context (list of strings)
        validator: Name of validator that produced this result
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

    These stats help diagnose performance issues and validate
    that optimizations (like caching) are working correctly.

    Attributes:
        pages_total: Total pages in site
        pages_processed: Pages actually validated
        pages_skipped: Dict of skip reasons and counts
        cache_hits: Number of cache hits (if applicable)
        cache_misses: Number of cache misses (if applicable)
        sub_timings: Dict of sub-operation names to duration_ms
    """

    pages_total: int = 0
    pages_processed: int = 0
    pages_skipped: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    sub_timings: dict[str, float] = field(default_factory=dict)

    def format_summary(self) -> str:
        """Format stats for debug output."""
        parts = [f"processed={self.pages_processed}/{self.pages_total}"]

        if self.pages_skipped:
            skip_str = ", ".join(f"{k}={v}" for k, v in self.pages_skipped.items())
            parts.append(f"skipped=[{skip_str}]")

        if self.cache_hits or self.cache_misses:
            total = self.cache_hits + self.cache_misses
            rate = (self.cache_hits / total * 100) if total > 0 else 0
            parts.append(f"cache={self.cache_hits}/{total} ({rate:.0f}%)")

        if self.sub_timings:
            timing_str = ", ".join(f"{k}={v:.0f}ms" for k, v in self.sub_timings.items())
            parts.append(f"timings=[{timing_str}]")

        return " | ".join(parts)


@dataclass
class ValidatorReport:
    """
    Report for a single validator's checks.

    Attributes:
        validator_name: Name of the validator
        results: List of check results from this validator
        duration_ms: How long the validator took to run
        stats: Optional observability metrics
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
        """Get emoji representing overall status."""
        if self.error_count > 0:
            return "❌"
        elif self.warning_count > 0:
            return "⚠️"
        elif self.suggestion_count > 0:
            return "💡"
        elif self.info_count > 0:
            return "ℹ️"
        else:
            return "✅"


@dataclass
class HealthReport:
    """
    Complete health check report for a build.

    Attributes:
        validator_reports: Reports from each validator
        timestamp: When the health check was run
        build_stats: Optional build statistics
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

        Formula:
        - Each passed check: +1 point
        - Each info: +0.8 points
        - Each suggestion: +0.9 points (quality improvement, not a problem)
        - Each warning: +0.5 points
        - Each error: +0 points

        Returns:
            Score from 0-100 (100 = perfect)
        """
        if self.total_checks == 0:
            return 100

        points = (
            self.total_passed * 1.0
            + self.total_info * 0.8
            + self.total_suggestions * 0.9  # Suggestions are quality improvements
            + self.total_warnings * 0.5
            + self.total_errors * 0.0
        )

        return int((points / self.total_checks) * 100)

    def quality_rating(self) -> str:
        """Get quality rating based on score."""
        score = self.build_quality_score()

        if score >= 95:
            return "Excellent"
        elif score >= 85:
            return "Good"
        elif score >= 70:
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
            return f"✓ Build complete. All health checks passed (quality: {score}%)\n"

        # Has problems - show them
        lines.append("")

        # Group by validator, only show problems
        for vr in self.validator_reports:
            if not vr.has_problems:
                continue

            # Show validator name with problem count
            problem_count = vr.warning_count + vr.error_count
            emoji = "❌" if vr.error_count > 0 else "⚠️"
            lines.append(f"{emoji} {vr.validator_name} ({problem_count} issue(s)):")

            # Show problem messages
            for result in vr.results:
                if result.is_problem():
                    lines.append(f"   • {result.message}")

                    # Show recommendation
                    if result.recommendation:
                        lines.append(f"     💡 {result.recommendation}")

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
        lines = []

        lines.append("\n🏥 Health Check Summary")
        lines.append("━" * 60)
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
                        lines.append(f"      💡 {result.recommendation}")

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
                    f"  💡 [bold]{vr.validator_name}[/bold] ([info]{vr.suggestion_count} suggestion(s)[/info])"
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
                f"[info]💡 {self.total_suggestions} quality suggestion(s) available (use --suggestions to view)[/info]"
            )

        # Show passed checks in a collapsed summary (reduce noise)
        if validators_passed:
            if validators_with_problems or (validators_with_suggestions and show_suggestions):
                lines.append("")
            lines.append(f"[success]✓ {len(validators_passed)} check(s) passed[/success]")
            # List them in a compact format if few, otherwise just count
            if len(validators_passed) <= 5:
                passed_names = ", ".join([vr.validator_name for vr in validators_passed])
                lines.append(f"   {passed_names}")

        # Summary
        lines.append("")
        lines.append("━" * 60)
        lines.append(
            f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors"
        )

        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append(f"Build Quality: {score}% ({rating})")
        lines.append("")

        return "\n".join(lines)

    def _format_verbose(self, show_suggestions: bool = True) -> str:
        """
        Full audit trail with progressive disclosure - problems first, then all details.

        Args:
            show_suggestions: Whether to show suggestions (default True in verbose mode)
        """
        lines = []

        # Header
        lines.append("\n🏥 Health Check Report")
        lines.append("━" * 60)
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
                    lines.append(f"    ✓ {result.message}")

                if not is_last_problem:
                    lines.append("")

        # Show passed checks (collapsed in verbose too, but expandable)
        if validators_passed:
            if validators_with_problems:
                lines.append("")
            lines.append(f"[success]✓ {len(validators_passed)} check(s) passed[/success]")

            # In verbose mode, show brief summary of passed checks
            for vr in validators_passed:
                lines.append(f"   ✓ {vr.validator_name}: {vr.passed_count} check(s) passed")

        # Summary
        lines.append("")
        lines.append("━" * 60)
        lines.append(
            f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors"
        )

        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append(f"Build Quality: {score}% ({rating})")
        lines.append("")

        return "\n".join(lines)

        # Summary
        lines.append("")
        lines.append("━" * 60)
        lines.append(
            f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors"
        )

        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append(f"Build Quality: {score}% ({rating})")

        # Build stats if available
        if self.build_stats:
            build_time = self.build_stats.get("build_time_ms", 0) / 1000
            lines.append(f"Build Time: {build_time:.2f}s")

        lines.append("")

        return "\n".join(lines)

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
