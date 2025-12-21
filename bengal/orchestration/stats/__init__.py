"""
Build statistics collection and display.

Provides:
- BuildStats: Container for build metrics and timings
- BuildWarning: Warning/error data structure
- Display functions for various output formats
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
