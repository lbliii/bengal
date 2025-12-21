"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.handlers for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.handlers import (
    ContextAwareHelp,
    get_context_aware_help,
)

__all__ = [
    "ContextAwareHelp",
    "get_context_aware_help",
]
