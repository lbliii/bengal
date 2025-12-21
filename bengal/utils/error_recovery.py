"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.recovery for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.recovery import (
    error_recovery_context,
    recover_file_processing,
    with_error_recovery,
)

__all__ = [
    "with_error_recovery",
    "error_recovery_context",
    "recover_file_processing",
]
