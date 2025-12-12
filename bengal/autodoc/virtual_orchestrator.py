"""
Virtual page orchestrator for autodoc.

Generates API documentation as virtual Page and Section objects
that integrate directly into the build pipeline without intermediate
markdown files.

This is the new architecture that replaces markdown-based autodoc generation.

Note:
    This module is now a backward-compatibility shim. The actual implementation
    has been modularized into bengal/autodoc/orchestration/. All classes and
    functions are re-imported here for backward compatibility.
"""

from __future__ import annotations

# Backward compatibility: Re-export from orchestration package
from bengal.autodoc.orchestration import (
    AutodocRunResult,
    VirtualAutodocOrchestrator,
)

__all__ = [
    "VirtualAutodocOrchestrator",
    "AutodocRunResult",
]
