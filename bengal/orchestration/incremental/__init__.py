"""
Incremental build system for Bengal SSG.

This package provides incremental build orchestration:
- IncrementalOrchestrator: Cache and tracer setup for incremental builds
- EffectBasedDetector: Constructed by initialize(); not the live invalidator
- CacheManager: Cache initialization and persistence
- cleanup_deleted_files: Deleted file cleanup

The live invalidator is ``phase_incremental_filter_provenance`` in
``bengal.orchestration.build.provenance_filter``, called from
``bengal.orchestration.build.mid_flow``. Production builds do not call
``find_work_early()``.

Usage:
    from bengal.orchestration.incremental import IncrementalOrchestrator

    orchestrator = IncrementalOrchestrator(site)
    cache = orchestrator.initialize(enabled=True)

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
