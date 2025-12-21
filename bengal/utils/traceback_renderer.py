"""
Backward compatibility shim - import from bengal.errors.traceback instead.

This module re-exports from bengal.errors.traceback.renderer for backward compatibility.
New code should import directly from bengal.errors.traceback.
"""

from bengal.errors.traceback.renderer import (
    CompactTracebackRenderer,
    FullTracebackRenderer,
    MinimalTracebackRenderer,
    OffTracebackRenderer,
    TracebackRenderer,
)

__all__ = [
    "TracebackRenderer",
    "FullTracebackRenderer",
    "CompactTracebackRenderer",
    "MinimalTracebackRenderer",
    "OffTracebackRenderer",
]
