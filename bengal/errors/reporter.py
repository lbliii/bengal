"""
Error reporting utilities for formatting comprehensive error reports.

This module provides functions for formatting error summaries and detailed
error reports from ``BuildStats`` for display in the CLI and build output.

Functions
=========

**format_error_report()**
Format a comprehensive multi-line error report from BuildStats.
Groups errors by category, shows file paths and suggestions in
verbose mode.

**format_error_summary()**
Format a brief one-line summary suitable for build completion
messages (e.g., "Build completed with 2 errors, 3 warnings").

Output Format
=============

Reports include:

- Error and warning counts per category
- ❌ markers for errors, ⚠️ markers for warnings
- File paths and line numbers (in verbose mode)
- Actionable suggestions (in verbose mode)

Usage
=====

Format a full error report::

from bengal.errors import format_error_report

    report = format_error_report(stats, verbose=True)
print(report)

Format a brief summary::

from bengal.errors import format_error_summary

    summary = format_error_summary(stats)
print(summary)  # "✓ Build completed successfully" or "⚠ Build completed with 2 errors"

See Also
========

- ``bengal/orchestration/stats/`` - BuildStats implementation
- ``bengal/cli/commands/build.py`` - CLI usage

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.output.icons import get_icon_set
from bengal.utils.observability.rich_console import should_use_emoji

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats


def format_error_report(stats: BuildStats, verbose: bool = False) -> str:
    """
    Format comprehensive error report from BuildStats.

    Args:
        stats: BuildStats instance with collected errors
        verbose: If True, include detailed file paths and suggestions

    Returns:
        Formatted error report string

    Example:
            >>> from bengal.errors import format_error_report
            >>> report = format_error_report(stats, verbose=True)
            >>> print(report)

    """
    summary = stats.get_error_summary()

    icons = get_icon_set(should_use_emoji())

    # If no errors or warnings, return success message
    if summary["total_errors"] == 0 and summary["total_warnings"] == 0:
        return f"{icons.success} No errors or warnings"

    lines: list[str] = []
    lines.append(f"Errors: {summary['total_errors']}, Warnings: {summary['total_warnings']}")

    # Report by category
    for category_name, category in stats.errors_by_category.items():
        if not category.errors and not category.warnings:
            continue

        lines.append(f"\n{category_name.upper()}:")

        # Report errors
        for error in category.errors:
            error_msg = _get_error_message(error)
            lines.append(f"  ❌ {error_msg}")

            if verbose:
                if hasattr(error, "file_path") and error.file_path:
                    lines.append(f"     File: {error.file_path}")
                if hasattr(error, "line_number") and error.line_number:
                    lines.append(f"     Line: {error.line_number}")
                if hasattr(error, "suggestion") and error.suggestion:
                    lines.append(f"     Tip: {error.suggestion}")

        # Report warnings
        for warning in category.warnings:
            lines.append(f"  ⚠️  {warning}")

    # Also report template_errors for backward compatibility
    if stats.template_errors:
        if "rendering" not in stats.errors_by_category:
            lines.append("\nRENDERING:")
        for error in stats.template_errors:
            error_msg = _get_error_message(error)
            lines.append(f"  ❌ {error_msg}")
            if verbose:
                if hasattr(error, "template_context"):
                    ctx = error.template_context
                    if ctx.template_path:
                        lines.append(f"     Template: {ctx.template_path}")
                    if ctx.line_number:
                        lines.append(f"     Line: {ctx.line_number}")
                if hasattr(error, "suggestion") and error.suggestion:
                    lines.append(f"     Tip: {error.suggestion}")

    # Report general warnings
    if stats.warnings and (
        "general" not in stats.errors_by_category
        or not stats.errors_by_category["general"].warnings
    ):
        if "general" not in stats.errors_by_category:
            lines.append("\nGENERAL:")
        for warning in stats.warnings:
            lines.append(f"  ⚠️  {warning.file_path}: {warning.message}")

    return "\n".join(lines)


def _get_error_message(error: Any) -> str:
    """
    Extract error message from an error object.

    Handles both BengalError instances (which have a ``message`` attribute)
    and standard exceptions (which use ``str()``).

    Special handling for Kida TemplateRuntimeError which may have empty messages
    but include location info in the formatted output.

    Args:
        error: Error object to extract message from.

    Returns:
        Human-readable error message string.

    """
    msg = ""
    if hasattr(error, "message"):
        msg = str(error.message)
    else:
        msg = str(error)

    # Handle Kida's empty-message TemplateRuntimeError format
    # Format: "Runtime Error: \n  Location: template.html:37\n  ..."
    # When message is empty, we get "Runtime Error: " followed by location
    if msg.startswith("Runtime Error:") and "\n" in msg:
        lines = msg.split("\n")
        first_line = lines[0].strip()
        # If first line is just "Runtime Error:" with nothing after the colon
        # extract location from subsequent lines for a better message
        if first_line == "Runtime Error:":
            # Try to get location and source line for context
            location = ""
            source_line = ""
            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith("Location:"):
                    location = stripped[9:].strip()  # Remove "Location:" prefix
                elif stripped.startswith("Expression:"):
                    source_line = stripped[11:].strip()  # Remove "Expression:" prefix

            # Construct a more informative message
            if location:
                msg = f"Runtime Error in {location}"
                if source_line and source_line != "<see stack trace>":
                    msg += f": {source_line}"
            else:
                msg = "Runtime Error (no details available)"

    return msg


def format_error_summary(stats: BuildStats) -> str:
    """
    Format brief error summary (one line).

    Args:
        stats: BuildStats instance

    Returns:
        Brief summary string

    """
    icons = get_icon_set(should_use_emoji())
    summary = stats.get_error_summary()
    if summary["total_errors"] == 0 and summary["total_warnings"] == 0:
        return f"{icons.success} Build completed successfully"

    parts = []
    if summary["total_errors"] > 0:
        parts.append(
            f"{summary['total_errors']} error{'s' if summary['total_errors'] != 1 else ''}"
        )
    if summary["total_warnings"] > 0:
        parts.append(
            f"{summary['total_warnings']} warning{'s' if summary['total_warnings'] != 1 else ''}"
        )

    return f"{icons.warning} Build completed with {', '.join(parts)}"
