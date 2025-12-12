"""
Autodoc orchestration package.

This package provides the virtual autodoc orchestration system that generates
API documentation as virtual Page and Section objects.

Public API:
    - VirtualAutodocOrchestrator: Main orchestrator for autodoc generation
    - AutodocRunResult: Summary of an autodoc generation run
"""

from __future__ import annotations

from bengal.autodoc.orchestration.result import AutodocRunResult, PageContext

__all__ = [
    "AutodocRunResult",
    "PageContext",
]

# Note: VirtualAutodocOrchestrator is imported from parent package to avoid
# circular imports during migration. Once migration is complete, it will be
# exported from here.
