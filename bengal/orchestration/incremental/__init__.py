"""
Incremental build system for Bengal SSG.

This package provides incremental build orchestration:
- IncrementalOrchestrator: Main orchestrator for incremental builds
- EffectBasedDetector: Unified change detector (RFC: Snapshot-Enabled v2)
- CacheManager: Cache initialization and persistence
- cleanup_deleted_files: Deleted file cleanup

Usage:
    from bengal.orchestration.incremental import IncrementalOrchestrator

    orchestrator = IncrementalOrchestrator(site)
    cache, tracker = orchestrator.initialize(enabled=True)
    pages, assets, summary = orchestrator.find_work_early()

Related Modules:
- bengal.effects: Effect system for dependency tracking
- bengal.services: Pure functions for theme/query/data operations

"""

from __future__ import annotations

from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.incremental.effect_detector import (
    EffectBasedDetector,
    create_detector_from_build,
)
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator

__all__ = [
    "CacheManager",
    "EffectBasedDetector",
    "IncrementalOrchestrator",
    "cleanup_deleted_files",
    "create_detector_from_build",
]
