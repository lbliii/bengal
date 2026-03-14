"""
Snapshot creation phase for build orchestration.

Creates immutable site snapshot for lock-free parallel rendering.
Includes NavTreeCache setup, global context pre-warming, directive cache
configuration, and service instantiation (QueryService, DataService).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build_context import BuildContext


def phase_snapshot(
    orchestrator: BuildOrchestrator,
    cli: object,
    early_ctx: BuildContext,
    pages_to_build: list[Page],
    force_sequential: bool,
) -> None:
    """
    Create site snapshot, warm caches, instantiate services on early_ctx.

    Runs after parsing, before rendering. Creates immutable snapshot for
    lock-free parallel rendering. Mutates early_ctx in place.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output (for phase timing)
        early_ctx: Build context to populate (mutated in place)
        pages_to_build: Pages being built (for stats/logging)
        force_sequential: Unused, reserved for future parallel snapshot

    """
    from bengal.snapshots import create_site_snapshot
    from bengal.snapshots.persistence import SnapshotCache

    snapshot_start = time.time()
    with orchestrator.logger.phase("snapshot"):
        site_snapshot = create_site_snapshot(orchestrator.site)
        snapshot_duration_ms = (time.time() - snapshot_start) * 1000

        early_ctx.snapshot = site_snapshot
        if hasattr(orchestrator.stats, "snapshot_time_ms"):
            orchestrator.stats.snapshot_time_ms = snapshot_duration_ms

        # Install pre-computed NavTrees for lock-free lookups during rendering
        from bengal.core.nav_tree import NavTreeCache

        NavTreeCache.set_precomputed(dict(site_snapshot.nav_trees))

        # Eagerly create global context wrappers (eliminates _context_lock
        # contention during parallel rendering)
        from bengal.rendering.context import _get_global_contexts

        _get_global_contexts(orchestrator.site, build_context=early_ctx)

        # Configure directive cache before parallel rendering
        from bengal.cache.directive_cache import configure_for_site

        configure_for_site(orchestrator.site)

        # Save snapshot for incremental builds (RFC: rfc-bengal-snapshot-engine)
        cache_dir = orchestrator.site.root_path / ".bengal" / "cache" / "snapshots"
        snapshot_cache = SnapshotCache(cache_dir)
        snapshot_cache.save(site_snapshot)

        # Service instantiation (RFC: bengal-v2-architecture Phase 1)
        from bengal.services.query import QueryService

        early_ctx.query_service = QueryService.from_snapshot(site_snapshot)
        try:
            from bengal.services.data import DataService

            early_ctx.data_service = DataService.from_root(orchestrator.site.root_path)
        except Exception:
            pass  # data/ dir may not exist; service remains None
