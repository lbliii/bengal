"""
Virtual page orchestration for the autodoc documentation system.

This package transforms extracted DocElement trees into virtual Page and
Section objects that integrate with Bengal's standard rendering pipeline.

Key Components:
    - VirtualAutodocOrchestrator: Main coordinator that runs extractors and
      builds virtual pages. Entry point for autodoc integration.
    - AutodocRunResult: Summary of a generation run including counts of
      pages, sections, and any extraction errors.
    - PageContext: Lightweight page-like object for template rendering that
      provides the same interface as Bengal's Page model.

Architecture:
    The orchestrator follows Bengal's standard orchestrator pattern:
    1. Load configuration and determine which extractors to run
    2. Execute enabled extractors to produce DocElement trees
    3. Transform elements into virtual Page/Section objects
    4. Return results for integration into the main Site

Virtual Pages:
    Unlike regular content pages, autodoc pages have no source files.
    They are generated on-demand during build and rendered directly
    via theme templates (e.g., `autodoc/python/module.html`).

Example:
    >>> from bengal.autodoc.orchestration import VirtualAutodocOrchestrator
    >>> orchestrator = VirtualAutodocOrchestrator(site, config)
    >>> result = orchestrator.run()
    >>> print(f"Generated {result.page_count} pages")

Related:
    - bengal/autodoc/extractors/: Source extractors
    - bengal/themes/default/templates/autodoc/: Default templates
    - bengal/orchestration/build_orchestrator.py: Build integration
"""

from __future__ import annotations

from bengal.autodoc.orchestration.orchestrator import VirtualAutodocOrchestrator
from bengal.autodoc.orchestration.result import AutodocRunResult, PageContext

__all__ = [
    "VirtualAutodocOrchestrator",
    "AutodocRunResult",
    "PageContext",
]
