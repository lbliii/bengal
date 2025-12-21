"""
Backward compatibility shim - import from bengal.errors instead.

This module re-exports from bengal.errors.exceptions for backward compatibility.
New code should import directly from bengal.errors.
"""

from bengal.errors.exceptions import (
    BengalCacheError,
    BengalConfigError,
    BengalContentError,
    BengalDiscoveryError,
    BengalError,
    BengalRenderingError,
)

__all__ = [
    "BengalError",
    "BengalConfigError",
    "BengalContentError",
    "BengalRenderingError",
    "BengalDiscoveryError",
    "BengalCacheError",
]
