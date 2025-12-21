"""
Enums for CLI output system.
"""

from __future__ import annotations

from enum import Enum


class MessageLevel(Enum):
    """Message importance levels."""

    DEBUG = 0  # Only in --verbose
    INFO = 1  # Normal operations
    SUCCESS = 2  # Successful operations
    WARNING = 3  # Non-critical issues
    ERROR = 4  # Errors
    CRITICAL = 5  # Fatal errors


class OutputStyle(Enum):
    """Visual styles for messages."""

    PLAIN = "plain"
    HEADER = "header"
    PHASE = "phase"
    DETAIL = "detail"
    METRIC = "metric"
    PATH = "path"
    SUMMARY = "summary"
