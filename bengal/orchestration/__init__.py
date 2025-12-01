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
    from bengal.orchestration import BuildOrchestrator

    orchestrator = BuildOrchestrator(site)
    stats = orchestrator.build(parallel=True, incremental=True)
"""

from __future__ import annotations

from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.incremental import IncrementalOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.taxonomy import TaxonomyOrchestrator

# Import BuildOrchestrator using relative import to avoid circular import
# (build/__init__.py imports from other orchestration modules)
from .build import BuildOrchestrator

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
