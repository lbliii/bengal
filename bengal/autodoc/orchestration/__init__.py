"""
Autodoc orchestration package.

This package provides the virtual autodoc orchestration system that generates
API documentation as virtual Page and Section objects.

Public API:
    - VirtualAutodocOrchestrator: Main orchestrator for autodoc generation
    - AutodocRunResult: Summary of an autodoc generation run
    - PageContext: Lightweight page-like context for template rendering
"""

from __future__ import annotations

from bengal.autodoc.orchestration.orchestrator import VirtualAutodocOrchestrator
from bengal.autodoc.orchestration.result import AutodocRunResult, PageContext

__all__ = [
    "VirtualAutodocOrchestrator",
    "AutodocRunResult",
    "PageContext",
]
