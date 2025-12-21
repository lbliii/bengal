"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.reporter for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.reporter import (
    format_error_report,
    format_error_summary,
)

__all__ = [
    "format_error_report",
    "format_error_summary",
]
