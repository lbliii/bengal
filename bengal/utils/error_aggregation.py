"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.aggregation for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.aggregation import (
    ErrorAggregator,
    extract_error_context,
)

__all__ = [
    "ErrorAggregator",
    "extract_error_context",
]
