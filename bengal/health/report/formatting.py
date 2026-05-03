"""
Console formatting for health reports.

This module provides functions for formatting health reports for console
output with Rich integration and progressive disclosure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output.icons import get_icon_set
from bengal.utils.observability.terminal import should_use_emoji

from .models import CheckStatus

if TYPE_CHECKING:
    from .models import ValidatorReport


def _result_detail(result, detail_limit: int) -> str:
    """Build a compact detail string for Kida validation report rows."""
    parts: list[str] = []
    if result.recommendation:
        parts.append(result.recommendation)
    if result.details:
        shown = result.details[:detail_limit]
        parts.extend(shown)
        if len(result.details) > detail_limit:
            parts.append(f"... and {len(result.details) - detail_limit} more")
    return " | ".join(parts)


def validation_report_context(
    validator_reports: list[ValidatorReport],
    has_problems: bool,
    total_errors: int,
    total_warnings: int,
    total_suggestions: int,
    total_passed: int,
    quality_score: int,
    quality_rating: str,
    mode: str = "auto",
    verbose: bool = False,
    show_suggestions: bool = False,
) -> dict:
    """
    Build structured context for ``validation_report.kida``.

    This is the CLI-facing report boundary: health owns report semantics, while
    Milo/Kida owns terminal rendering.
    """
    if verbose:
        mode = "verbose"
    if mode == "auto":
        mode = "quiet" if not has_problems else "normal"

    issues: list[dict[str, str]] = []

    if mode == "quiet" and not has_problems:
        issues.append(
            {
                "level": "success",
                "message": f"All health checks passed (quality: {quality_score}%)",
                "detail": f"{total_passed} check(s)",
            }
        )
        return {
            "title": "Health Check",
            "issues": issues,
            "summary": {"errors": 0, "warnings": 0, "passed": 1},
        }

    if mode == "verbose":
        visible_statuses = {
            CheckStatus.ERROR,
            CheckStatus.WARNING,
            CheckStatus.SUGGESTION,
            CheckStatus.INFO,
            CheckStatus.SUCCESS,
        }
        detail_limit = 5
    else:
        visible_statuses = {CheckStatus.ERROR, CheckStatus.WARNING}
        if show_suggestions:
            visible_statuses.add(CheckStatus.SUGGESTION)
        detail_limit = 3

    for validator in _ordered_validator_reports(validator_reports):
        for result in validator.results:
            if result.status not in visible_statuses:
                continue
            if (
                result.status == CheckStatus.SUGGESTION
                and not show_suggestions
                and mode != "verbose"
            ):
                continue
            issues.append(
                {
                    "level": _template_level(result.status),
                    "message": f"{validator.validator_name}: {result.formatted_message}",
                    "detail": _result_detail(result, detail_limit),
                }
            )

    if not issues:
        if total_suggestions and not show_suggestions:
            issues.append(
                {
                    "level": "info",
                    "message": f"{total_suggestions} quality suggestion(s) available",
                    "detail": "Use --suggestions to view them.",
                }
            )
        else:
            issues.append(
                {
                    "level": "success",
                    "message": f"Health checks passed (quality: {quality_score}%)",
                    "detail": f"{total_passed} check(s)",
                }
            )
    elif total_suggestions and not show_suggestions and mode != "verbose":
        issues.append(
            {
                "level": "info",
                "message": f"{total_suggestions} quality suggestion(s) available",
                "detail": "Use --suggestions to view them.",
            }
        )

    issues.append(
        {
            "level": "info",
            "message": (
                f"Health: {total_errors} error(s), {total_warnings} warning(s) | "
                f"Quality: {quality_score}% ({quality_rating})"
            ),
            "detail": "",
        }
    )

    return {
        "title": "Health Check",
        "issues": issues,
        "summary": {
            "errors": total_errors,
            "warnings": total_warnings,
            "passed": 1 if total_errors == 0 and total_warnings == 0 else 0,
        },
    }


def _ordered_validator_reports(validator_reports: list[ValidatorReport]) -> list[ValidatorReport]:
    """Sort problem validators first while preserving non-problem ordering."""
    return sorted(
        validator_reports,
        key=lambda report: (
            report.error_count == 0,
            report.warning_count == 0,
            report.validator_name,
        ),
    )


def _template_level(status: CheckStatus) -> str:
    """Map health severities to validation_report.kida status levels."""
    if status == CheckStatus.ERROR:
        return "error"
    if status == CheckStatus.WARNING:
        return "warning"
    if status == CheckStatus.SUCCESS:
        return "success"
    return "info"


def format_quiet(
    validator_reports: list[ValidatorReport],
    has_problems: bool,
    total_errors: int,
    total_warnings: int,
    quality_score: int,
    quality_rating: str,
    show_suggestions: bool = False,
) -> str:
    """
    Minimal output - perfect builds get one line, problems shown clearly.

    Args:
        validator_reports: List of validator reports
        has_problems: Whether any warnings or errors were found
        total_errors: Total error count
        total_warnings: Total warning count
        quality_score: Quality score (0-100)
        quality_rating: Quality rating string
        show_suggestions: Whether to show suggestions (ignored in quiet mode)

    Returns:
        Formatted string for console output
    """
    lines = []

    # Perfect build - just success message
    if not has_problems:
        icons = get_icon_set(should_use_emoji())
        return f"{icons.success} Build complete. All health checks passed (quality: {quality_score}%)\n"

    # Has problems - show them
    lines.append("")

    icons = get_icon_set(should_use_emoji())

    # Group by validator, only show problems
    for vr in validator_reports:
        if not vr.has_problems:
            continue

        # Show validator name with problem count
        problem_count = vr.warning_count + vr.error_count
        status_icon = icons.error if vr.error_count > 0 else icons.warning
        lines.append(f"{status_icon} {vr.validator_name} ({problem_count} issue(s)):")

        # Show problem messages
        for result in vr.results:
            if result.is_problem():
                lines.append(f"   • {result.formatted_message}")

                # Show recommendation
                if result.recommendation:
                    lines.append(f"     {icons.tip} {result.recommendation}")

                # Show first 3 details
                if result.details:
                    lines.extend(f"        - {detail}" for detail in result.details[:3])
                    if len(result.details) > 3:
                        remaining = len(result.details) - 3
                        lines.append(f"        ... and {remaining} more")

        lines.append("")  # Blank line between validators

    # Summary
    summary_parts = []

    if total_errors > 0:
        summary_parts.append(f"{total_errors} error(s)")
    if total_warnings > 0:
        summary_parts.append(f"{total_warnings} warning(s)")

    lines.append(f"Build Quality: {quality_score}% ({quality_rating}) · {', '.join(summary_parts)}")
    lines.append("")

    return "\n".join(lines)


def format_normal(
    validator_reports: list[ValidatorReport],
    total_errors: int,
    total_warnings: int,
    total_suggestions: int,
    quality_score: int,
    quality_rating: str,
    show_suggestions: bool = False,
) -> str:
    """
    Balanced output with progressive disclosure - problems first, then successes.
    Reduces cognitive load by prioritizing actionable information.

    Args:
        validator_reports: List of validator reports
        total_errors: Total error count
        total_warnings: Total warning count
        total_suggestions: Total suggestion count
        quality_score: Quality score (0-100)
        quality_rating: Quality rating string
        show_suggestions: Whether to show suggestions (collapsed by default)

    Returns:
        Formatted string for console output
    """
    icons = get_icon_set(should_use_emoji())
    lines = []

    # No header - flows from phase line "✓ Health check Xms"
    lines.append("")

    # Separate validators by priority: problems first, then suggestions
    # Skip validators that only have INFO messages (writers don't need that noise)
    validators_with_problems = []
    validators_with_suggestions = []

    for vr in validator_reports:
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
                # Brief message describing the issue type (with code if available)
                lines.append(f"    • {result.formatted_message}")

                # Show recommendation if available
                if result.recommendation:
                    lines.append(f"      {icons.tip} {result.recommendation}")

                # Details show location + context (the important part)
                if result.details:
                    # Details are already formatted with location:line
                    lines.extend(f"      {detail}" for detail in result.details[:3])
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

            lines.extend(
                f"    • {result.formatted_message}"
                for result in vr.results
                if result.status == CheckStatus.SUGGESTION
            )

            if not is_last_suggestion:
                lines.append("")
    elif validators_with_suggestions:
        # Collapsed: just show count
        if validators_with_problems:
            lines.append("")
        lines.append(
            f"[info]{icons.tip} {total_suggestions} quality suggestion(s) available (use --suggestions to view)[/info]"
        )

    # Summary (compact single line)
    lines.append("")
    lines.append(
        f"Health: {total_errors} error(s), {total_warnings} warning(s) | Quality: {quality_score}% ({quality_rating})"
    )

    # Indent all lines since this is a sub-item of the Health check phase
    return "\n".join(f"  {line}" if line.strip() else "" for line in lines)


def format_verbose(
    validator_reports: list[ValidatorReport],
    total_errors: int,
    total_warnings: int,
    quality_score: int,
    quality_rating: str,
    show_suggestions: bool = True,
) -> str:
    """
    Full audit trail with progressive disclosure - problems first, then all details.

    Args:
        validator_reports: List of validator reports
        total_errors: Total error count
        total_warnings: Total warning count
        quality_score: Quality score (0-100)
        quality_rating: Quality rating string
        show_suggestions: Whether to show suggestions (default True in verbose mode)

    Returns:
        Formatted string for console output
    """
    icons = get_icon_set(should_use_emoji())
    lines = []

    # No header - flows from phase line "✓ Health check Xms"
    lines.append("")

    # Separate validators by priority: problems first, then suggestions
    validators_with_problems = []
    validators_with_suggestions = []

    for vr in validator_reports:
        if vr.has_problems:
            validators_with_problems.append(vr)
        elif vr.suggestion_count > 0:
            validators_with_suggestions.append(vr)

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
                # Problems get full detail - location first (with code if available)
                lines.append(f"    • {result.formatted_message}")
                if result.details:
                    lines.extend(f"      {detail}" for detail in result.details[:5])
                    if len(result.details) > 5:
                        lines.append(f"      ... and {len(result.details) - 5} more")

                # Add spacing between issues
                if j < len(problem_results) - 1:
                    lines.append("")

            # Show successes briefly (grouped at end)
            lines.extend(
                f"    {icons.success} {result.formatted_message}" for result in other_results
            )

            if not is_last_problem:
                lines.append("")

    # Summary (compact single line)
    lines.append("")
    lines.append(
        f"Health: {total_errors} error(s), {total_warnings} warning(s) | Quality: {quality_score}% ({quality_rating})"
    )

    # Indent all lines since this is a sub-item of the Health check phase
    return "\n".join(f"  {line}" if line.strip() else "" for line in lines)
