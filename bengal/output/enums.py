"""
Enums for CLI output system.

Defines message importance levels and visual styling options used
throughout the Bengal CLI output system. These enums provide
consistent categorization for filtering and styling output messages.

Related:
    - bengal/output/core.py: CLIOutput uses these enums for message handling
    - bengal/utils/rich_console.py: Rich theme maps OutputStyle to visual styles
"""

from __future__ import annotations

from enum import Enum


class MessageLevel(Enum):
    """
    Message importance levels for CLI output filtering.

    Messages are filtered based on their level and the current verbosity
    settings (quiet mode, verbose mode). Higher numeric values indicate
    more important messages that are less likely to be suppressed.

    Filtering Rules:
        - In quiet mode: Only WARNING and above are shown
        - In normal mode: INFO and above are shown
        - In verbose mode: All levels including DEBUG are shown

    Attributes:
        DEBUG: Detailed diagnostic information (only with --verbose)
        INFO: Normal operational messages
        SUCCESS: Successful completion indicators
        WARNING: Non-critical issues that don't stop execution
        ERROR: Errors that don't halt the build
        CRITICAL: Fatal errors that stop execution
    """

    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class OutputStyle(Enum):
    """
    Visual styling categories for CLI output.

    Each style maps to a specific visual treatment in the Rich theme
    (colors, bold, dim, etc.) and provides semantic meaning for
    different types of output content.

    Attributes:
        PLAIN: Unstyled default text
        HEADER: Main section headers with emphasis
        PHASE: Build phase status lines
        DETAIL: Indented detail/sub-item text
        METRIC: Label-value metric displays
        PATH: File or directory path displays
        SUMMARY: Final summary/results text
    """

    PLAIN = "plain"
    HEADER = "header"
    PHASE = "phase"
    DETAIL = "detail"
    METRIC = "metric"
    PATH = "path"
    SUMMARY = "summary"
