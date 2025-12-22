"""
Build statistics collection and display.

This package provides data models for tracking build metrics and functions
for displaying build results in various formats.

Data Models:
    BuildStats
        Container for all build metrics: timings, counts, warnings, errors,
        and build configuration. Created at build start and populated
        throughout the build phases.
    BuildWarning
        Data structure for warnings and errors with category, message,
        file path, and severity information.

Display Functions:
    display_build_stats
        Full build statistics with timing breakdown and performance summary.
    display_simple_build_stats
        Minimal output for writer persona or quiet mode.
    display_warnings
        Formatted warning and error display with categorization.
    display_template_errors
        Specialized display for template validation errors.

Helper Functions:
    format_time
        Formats milliseconds into human-readable strings (e.g., '1.2s').
    show_building_indicator
        Displays build-in-progress indicator.
    show_clean_success
        Displays clean command success message.
    show_error
        Displays formatted error messages.
    show_welcome
        Displays Bengal welcome banner.

Package Structure:
    models.py: BuildStats and BuildWarning dataclasses
    display.py: Main display functions
    warnings.py: Warning display formatting
    helpers.py: Utility display functions

See Also:
    bengal.orchestration.summary: Rich dashboard display
    bengal.analysis.performance_advisor: Performance analysis and grading
"""

from __future__ import annotations

from bengal.orchestration.stats.display import (
    display_build_stats,
    display_simple_build_stats,
)
from bengal.orchestration.stats.helpers import (
    display_template_errors,
    format_time,
    show_building_indicator,
    show_clean_success,
    show_error,
    show_welcome,
)
from bengal.orchestration.stats.models import BuildStats, BuildWarning
from bengal.orchestration.stats.warnings import display_warnings

__all__ = [
    # Models
    "BuildStats",
    "BuildWarning",
    # Display
    "display_build_stats",
    "display_simple_build_stats",
    "display_warnings",
    "display_template_errors",
    # Helpers
    "format_time",
    "show_building_indicator",
    "show_clean_success",
    "show_error",
    "show_welcome",
]
