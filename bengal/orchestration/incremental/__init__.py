"""
Incremental build orchestration for Bengal SSG.

.. deprecated:: 0.2.0
    Incremental orchestration has been superseded by provenance-based
    filtering. Use ``bengal.build.provenance.ProvenanceFilter`` instead.

This package handles cache management, change detection, and determining what
needs rebuilding during incremental builds. Uses file hashes, dependency graphs,
and taxonomy indexes to identify changed content and minimize rebuild work.

Key Components:
- IncrementalOrchestrator: Main orchestrator coordinating all incremental logic
- CacheManager: Cache initialization and persistence
- RebuildFilter: Pages/assets filtering for rebuilds
- CascadeTracker: Cascade dependency tracking
- BlockChangeDetector: Block-level template change detection
- RebuildDecisionEngine: Smart rebuild decisions based on block changes
- cleanup: Deleted file cleanup

Architecture:
The package refactors the monolithic `IncrementalOrchestrator` into focused
components following the single responsibility principle.

New Architecture (v0.2+):
Build orchestrator now uses provenance-based filtering by default::

    from bengal.build.provenance import ProvenanceFilter, ProvenanceCache
    cache = ProvenanceCache(site.root_path / ".bengal" / "provenance")
    filter = ProvenanceFilter(site, cache)
    result = filter.filter(pages, assets, incremental=True)

Legacy Components (deprecated):
- phase_incremental_filter - Replaced by phase_incremental_filter_provenance

Related Modules:
- bengal.build.pipeline: Change detection pipeline
- bengal.build.provenance: Provenance-based caching (recommended)
- bengal.cache.build_cache: Legacy build cache persistence

"""

from __future__ import annotations

from bengal.orchestration.incremental.block_detector import (
    BlockChangeDetector,
    BlockChangeSet,
)
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator
from bengal.orchestration.incremental.rebuild_decision import (
    RebuildDecision,
    RebuildDecisionEngine,
)
from bengal.orchestration.incremental.rebuild_filter import RebuildFilter

__all__ = [
    "IncrementalOrchestrator",
    "CacheManager",
    "RebuildFilter",
    "CascadeTracker",
    "BlockChangeDetector",
    "BlockChangeSet",
    "RebuildDecision",
    "RebuildDecisionEngine",
    "cleanup_deleted_files",
]
