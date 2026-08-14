"""
Build pipeline runner.

Sequences existing hardcoded phases for `BuildOrchestrator.build()`.
This module does not add phases; plugin hook timing around the current
groups must stay identical to the former inline coordinator body.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .finalize_flow import run_finalization_phases
from .mid_flow import run_pre_output_phases
from .output_flow import run_asset_and_render_phases
from .session import prepare_build_session

if TYPE_CHECKING:
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build.inputs import BuildInput
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.stats import BuildStats


def run_build(
    orchestrator: BuildOrchestrator,
    options: BuildOptions | BuildInput,
) -> BuildStats:
    """
    Execute the full build pipeline.

    `build_complete` fires exactly once: on the happy path inside the body,
    and from `finally` when a mid-build phase raises (issue #437).
    """
    session = prepare_build_session(orchestrator, options)

    try:
        early_stats = run_pre_output_phases(session)
        if early_stats is not None:
            return early_stats

        if session.dry_run:
            session.cli.info("  Dry-run mode: skipping rendering and output phases")
            orchestrator.stats.build_time_ms = (time.time() - session.build_start) * 1000
            orchestrator.stats.dry_run = True
            orchestrator.site.set_build_state(None)
            session.fire_build_complete()
            return orchestrator.stats

        run_asset_and_render_phases(session)
        run_finalization_phases(session)
        return orchestrator.stats
    finally:
        # build_complete is a teardown contract: fire it whether the build
        # body returned normally or raised, then let any in-flight exception
        # continue to propagate to the caller (issue #437). BengalCacheError
        # from the cache-save phase still surfaces after the hook runs.
        session.fire_build_complete()
