"""
Build warnings display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output import CLIOutput

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

    cli = CLIOutput()

    # Header
    warning_count = len(stats.warnings)
    cli.error_header(f"Build completed with warnings ({warning_count})")

    # Group by type
    type_names = {
        "jinja2": "Jinja2 Template Errors",
        "preprocessing": "Pre-processing Errors",
        "link": "Link Validation Warnings",
        "other": "Other Warnings",
    }

    grouped = stats.warnings_by_type

    for warning_type, type_warnings in grouped.items():
        type_name = type_names.get(warning_type, warning_type.title())

        if cli.use_rich:
            cli.console.print(f"   [header]{type_name} ({len(type_warnings)}):[/header]")
        else:
            cli.info(f"   {type_name} ({len(type_warnings)}):")

        for i, warning in enumerate(type_warnings):
            is_last = i == len(type_warnings) - 1
            prefix = "   └─ " if is_last else "   ├─ "

            # Show short path
            if cli.use_rich:
                cli.console.print(
                    f"   [info]{prefix}[/info][warning]{warning.short_path}[/warning]"
                )
            else:
                cli.info(f"{prefix}{warning.short_path}")

            # Show message indented
            msg_prefix = "      " if is_last else "   │  "
            if cli.use_rich:
                cli.console.print(
                    f"   [info]{msg_prefix}└─[/info] [error]{warning.message}[/error]"
                )
            else:
                cli.info(f"{msg_prefix}└─ {warning.message}")

        cli.blank()
