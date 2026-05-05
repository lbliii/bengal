"""
Build warnings display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output import get_cli_output

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats


def display_warnings(stats: BuildStats) -> None:
    """
    Display grouped warnings and errors.

    Args:
        stats: Build statistics with warnings

    """
    if not stats.warnings:
        return

    cli = get_cli_output()

    type_names = {
        "jinja2": "Jinja2 Template Errors",
        "kida": "Kida Template Errors",
        "template": "Template Syntax Errors",
        "preprocessing": "Pre-processing Errors",
        "link": "Link Validation Warnings",
        "other": "Other Warnings",
    }

    grouped = stats.warnings_by_type
    warning_groups = []
    for warning_type, type_warnings in grouped.items():
        type_name = type_names.get(warning_type, warning_type.title())
        warning_groups.append(
            {
                "type_name": type_name,
                "warnings": [
                    {"short_path": w.short_path, "message": w.message} for w in type_warnings
                ],
            }
        )

    cli.render_write(
        "build_summary.kida",
        skipped=False,
        has_errors=False,
        has_warnings=False,
        total_pages=0,
        warning_groups=warning_groups,
        warning_count=len(stats.warnings),
        error_lines=[],
    )
