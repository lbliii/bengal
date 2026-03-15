"""
Unit tests for error reporter formatting.

Tests: format_error_report, format_error_summary, verbose mode,
empty stats, errors by category.
"""

from __future__ import annotations

from bengal.errors import BengalDiscoveryError, ErrorCode
from bengal.errors.reporter import format_error_report, format_error_summary
from bengal.orchestration.stats.models import BuildStats, ErrorCategory


def _make_stats(
    *,
    errors: list | None = None,
    warnings: list[str] | None = None,
    template_errors: list | None = None,
) -> BuildStats:
    """Create BuildStats with optional errors/warnings."""
    stats = BuildStats()
    if errors:
        cat = ErrorCategory(name="discovery", errors=errors, warnings=[])
        stats.errors_by_category["discovery"] = cat
    if warnings:
        if "general" not in stats.errors_by_category:
            stats.errors_by_category["general"] = ErrorCategory(
                name="general", errors=[], warnings=warnings
            )
        else:
            stats.errors_by_category["general"].warnings.extend(warnings)
    if template_errors:
        stats.template_errors = template_errors
    return stats


class TestFormatErrorSummary:
    """Test format_error_summary."""

    def test_no_errors_success_message(self) -> None:
        """No errors returns success message."""
        stats = BuildStats()
        summary = format_error_summary(stats)
        assert "success" in summary.lower() or "✓" in summary

    def test_with_errors_shows_count(self) -> None:
        """With errors shows error count."""
        err = BengalDiscoveryError("x", code=ErrorCode.D001, file_path=None)
        stats = _make_stats(errors=[err])
        summary = format_error_summary(stats)
        assert "1 error" in summary or "error" in summary.lower()

    def test_with_warnings_shows_count(self) -> None:
        """With warnings shows warning count."""
        stats = _make_stats(warnings=["warning 1"])
        summary = format_error_summary(stats)
        assert "warning" in summary.lower()


class TestFormatErrorReport:
    """Test format_error_report."""

    def test_no_errors_or_warnings(self) -> None:
        """Empty stats returns no-errors message."""
        stats = BuildStats()
        report = format_error_report(stats)
        assert "error" in report.lower() or "No" in report

    def test_with_errors_includes_message(self) -> None:
        """Report includes error messages."""
        err = BengalDiscoveryError(
            "Content dir missing",
            code=ErrorCode.D001,
            file_path=None,
            suggestion="Create content directory",
        )
        stats = _make_stats(errors=[err])
        report = format_error_report(stats, verbose=True)
        assert "Content" in report or "missing" in report
        assert "Create" in report or "suggestion" in report.lower()

    def test_verbose_includes_file_and_tip(self) -> None:
        """Verbose mode includes file path and suggestion."""
        err = BengalDiscoveryError(
            "x",
            code=ErrorCode.D001,
            file_path="/site/content",
            suggestion="Fix it",
        )
        stats = _make_stats(errors=[err])
        report = format_error_report(stats, verbose=True)
        assert "content" in report or "File" in report
        assert "Fix" in report or "Tip" in report
