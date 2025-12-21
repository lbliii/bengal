"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.context for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.context import (
    ErrorContext,
    enrich_error,
    get_context_from_exception,
)

__all__ = [
    "ErrorContext",
    "enrich_error",
    "get_context_from_exception",
]
