"""
HealthReport - Complete health check report.

This module provides the HealthReport class which aggregates all validator
results and provides multiple output formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .formatting import format_normal, format_quiet, format_verbose
from .models import ValidatorReport
from .scoring import calculate_quality_score, get_quality_rating
from .serialization import format_report_json


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
        return calculate_quality_score(self.total_errors, self.total_warnings, self.total_checks)

    def quality_rating(self) -> str:
        """
        Get quality rating based on score.

        Thresholds aligned with penalty-based scoring:
        - Excellent (90+): No errors, 0-2 warnings
        - Good (75-89): 1 error or 3-5 warnings
        - Fair (50-74): 2-3 errors or many warnings
        - Needs Improvement (<50): 4+ errors
        """
        return get_quality_rating(self.build_quality_score())

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

        quality_score = self.build_quality_score()
        quality_rating = self.quality_rating()

        if mode == "quiet":
            return format_quiet(
                self.validator_reports,
                self.has_problems(),
                self.total_errors,
                self.total_warnings,
                quality_score,
                quality_rating,
                show_suggestions=show_suggestions,
            )
        elif mode == "verbose":
            return format_verbose(
                self.validator_reports,
                self.total_errors,
                self.total_warnings,
                quality_score,
                quality_rating,
                show_suggestions=show_suggestions,
            )
        else:  # normal
            return format_normal(
                self.validator_reports,
                self.total_errors,
                self.total_warnings,
                self.total_suggestions,
                quality_score,
                quality_rating,
                show_suggestions=show_suggestions,
            )

    def format_json(self) -> dict[str, Any]:
        """
        Format report as JSON-serializable dictionary.

        Returns:
            Dictionary suitable for json.dumps()
        """
        return format_report_json(
            self.validator_reports,
            self.timestamp,
            self.build_stats,
            self.total_checks,
            self.total_passed,
            self.total_info,
            self.total_warnings,
            self.total_errors,
            self.build_quality_score(),
            self.quality_rating(),
        )
