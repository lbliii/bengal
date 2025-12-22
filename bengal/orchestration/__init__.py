"""
Build orchestration module for Bengal SSG.

This module provides specialized orchestrators that handle different phases
of the build process. The orchestrator pattern separates build coordination
from data management, keeping the Site class focused on data representation
while orchestrators handle operations.

Architecture:
    Core models in bengal/core/ are passive data structures with no I/O.
    Orchestrators in this package handle all build operations, logging, and
    side effects. This separation enables testability and maintainability.

Orchestrators:
    BuildOrchestrator
        Main build coordinator that sequences all phases
    ContentOrchestrator
        Content and asset discovery, page/section setup
    TaxonomyOrchestrator
        Taxonomy collection (tags, categories) and dynamic page generation
    MenuOrchestrator
        Navigation menu building with caching and i18n support
    RenderOrchestrator
        Page rendering with parallel and sequential modes
    AssetOrchestrator
        Asset processing: copying, minification, optimization, fingerprinting
    PostprocessOrchestrator
        Post-build tasks: sitemap, RSS feeds, output formats
    IncrementalOrchestrator
        Change detection and caching for incremental builds

Performance:
    Orchestrators support parallel processing via ThreadPoolExecutor.
    Parallel thresholds (typically 5+ items) avoid thread overhead for
    small workloads. Free-threaded Python (3.13t+) is auto-detected for
    true parallelism without GIL contention.

Example:
    >>> from bengal.orchestration import BuildOrchestrator
    >>> orchestrator = BuildOrchestrator(site)
    >>> stats = orchestrator.build(parallel=True, incremental=True)

See Also:
    bengal.core: Passive data models (Page, Site, Section, Asset)
    bengal.cache: Build caching infrastructure
    bengal.rendering: Template and content rendering
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.orchestration.asset import AssetOrchestrator
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.content import ContentOrchestrator
    from bengal.orchestration.incremental import IncrementalOrchestrator
    from bengal.orchestration.menu import MenuOrchestrator
    from bengal.orchestration.postprocess import PostprocessOrchestrator
    from bengal.orchestration.render import RenderOrchestrator
    from bengal.orchestration.taxonomy import TaxonomyOrchestrator

__all__ = [
    "AssetOrchestrator",
    "BuildOrchestrator",
    "ContentOrchestrator",
    "IncrementalOrchestrator",
    "MenuOrchestrator",
    "PostprocessOrchestrator",
    "RenderOrchestrator",
    "TaxonomyOrchestrator",
]


def __getattr__(name: str) -> Any:
    """
    Lazily resolve orchestration re-exports.

    This keeps `import bengal.orchestration` lightweight and avoids import
    cycles between orchestration packages.
    """
    if name == "AssetOrchestrator":
        from bengal.orchestration.asset import AssetOrchestrator

        return AssetOrchestrator
    if name == "BuildOrchestrator":
        from bengal.orchestration.build import BuildOrchestrator

        return BuildOrchestrator
    if name == "ContentOrchestrator":
        from bengal.orchestration.content import ContentOrchestrator

        return ContentOrchestrator
    if name == "IncrementalOrchestrator":
        from bengal.orchestration.incremental import IncrementalOrchestrator

        return IncrementalOrchestrator
    if name == "MenuOrchestrator":
        from bengal.orchestration.menu import MenuOrchestrator

        return MenuOrchestrator
    if name == "PostprocessOrchestrator":
        from bengal.orchestration.postprocess import PostprocessOrchestrator

        return PostprocessOrchestrator
    if name == "RenderOrchestrator":
        from bengal.orchestration.render import RenderOrchestrator

        return RenderOrchestrator
    if name == "TaxonomyOrchestrator":
        from bengal.orchestration.taxonomy import TaxonomyOrchestrator

        return TaxonomyOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])
