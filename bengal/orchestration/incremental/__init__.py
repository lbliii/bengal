"""
Incremental build orchestration for Bengal SSG.

This package handles cache management, change detection, and determining what
needs rebuilding during incremental builds. Uses file hashes, dependency graphs,
and taxonomy indexes to identify changed content and minimize rebuild work.

Key Components:
    - IncrementalOrchestrator: Main orchestrator coordinating all incremental logic
    - ChangeDetector: Unified change detection for incremental builds
    - CacheManager: Cache initialization and persistence
    - RebuildFilter: Pages/assets filtering for rebuilds
    - CascadeTracker: Cascade dependency tracking
    - cleanup: Deleted file cleanup

Architecture:
    The package refactors the monolithic `IncrementalOrchestrator` into focused
    components following the single responsibility principle:

    1. CacheManager - Handles cache initialization, loading, and saving
    2. ChangeDetector - Unified change detection with phase parameter (early/full)
    3. RebuildFilter - Filters pages and assets for rebuilding
    4. CascadeTracker - Tracks cascade metadata dependencies
    5. cleanup - Handles cleanup of deleted files

    The IncrementalOrchestrator coordinates these components but delegates
    the actual work to each specialized module.

Related Modules:
    - bengal.cache.build_cache: Build cache persistence
    - bengal.cache.dependency_tracker: Dependency graph construction

See Also:
    - plan/ready/plan-architecture-refactoring.md: Sprint 4 design
"""

from __future__ import annotations

from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
from bengal.orchestration.incremental.change_detector import ChangeDetector
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator
from bengal.orchestration.incremental.rebuild_filter import RebuildFilter

__all__ = [
    "IncrementalOrchestrator",
    "ChangeDetector",
    "CacheManager",
    "RebuildFilter",
    "CascadeTracker",
    "cleanup_deleted_files",
]
