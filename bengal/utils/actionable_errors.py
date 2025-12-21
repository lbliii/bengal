"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.suggestions for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.suggestions import (
    enhance_error_context,
    format_suggestion,
    get_attribute_error_suggestion,
    get_suggestion,
)

__all__ = [
    "get_suggestion",
    "format_suggestion",
    "enhance_error_context",
    "get_attribute_error_suggestion",
]
