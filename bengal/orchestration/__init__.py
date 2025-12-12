"""
Build orchestration module for Bengal SSG.

This module provides specialized orchestrators that handle different phases
of the build process. The orchestrator pattern separates build coordination
from data management, making the Site class simpler and more maintainable.

Orchestrators:
    - BuildOrchestrator: Main build coordinator
    - ContentOrchestrator: Content/asset discovery and setup
    - TaxonomyOrchestrator: Taxonomies and dynamic page generation
    - MenuOrchestrator: Navigation menu building
    - RenderOrchestrator: Page rendering (sequential and parallel)
    - AssetOrchestrator: Asset processing (minify, optimize, copy)
    - PostprocessOrchestrator: Sitemap, RSS, link validation
    - IncrementalOrchestrator: Incremental build logic

Usage:

```python
from bengal.orchestration import BuildOrchestrator

orchestrator = BuildOrchestrator(site)
stats = orchestrator.build(parallel=True, incremental=True)
```
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
