"""
Asset and render sequencing after snapshot.

Dry-run short-circuit lives in `runner.py` so this module starts at
`pre_assets`, matching the former inline hook order.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from . import rendering

if TYPE_CHECKING:
    from .session import BuildSession


def run_asset_and_render_phases(session: BuildSession) -> None:
    """Run asset processing and page rendering groups (phases 13–16)."""
    orchestrator = session.orchestrator
    cli = session.cli
    early_ctx = session.early_ctx
    pages_to_build = session.pages_to_build

    # === ASSETS PHASE GROUP (dashboard-integrated) ===
    session.run_plugin_phase("pre_assets")
    session.notify_phase_start("assets")
    assets_start = time.time()

    # Phase 13: Process Assets
    session.assets_to_process = rendering.phase_assets(
        orchestrator,
        cli,
        session.incremental,
        not session.force_sequential,
        session.assets_to_process,
        collector=session.output_collector,
    )

    assets_duration_ms = (time.time() - assets_start) * 1000
    orchestrator.stats.record_phase_timing("Assets", assets_duration_ms)
    session.notify_phase_complete(
        "assets",
        assets_duration_ms,
        f"{len(session.assets_to_process) if session.assets_to_process else 0} assets processed",
    )
    session.run_plugin_phase("post_assets")

    # === RENDERING PHASE GROUP (dashboard-integrated) ===
    # Canonical hook name is `pre_render`; `pre_rendering` is emitted as a
    # back-compat alias for plugins registered against the older spelling.
    # Same alias pairing applies to post_render/post_rendering below.
    session.run_plugin_phase("pre_render")
    session.run_plugin_phase("pre_rendering")
    session.notify_phase_start("rendering")
    rendering_start = time.time()

    progress_manager = session.progress_manager
    if progress_manager:
        total_pages = len(pages_to_build) if pages_to_build else 0
        # IMPORTANT: start() must come BEFORE add_phase() to enable Rich Live display
        progress_manager.start()
        progress_manager.add_phase("rendering", "Rendering", total=total_pages)
        progress_manager.start_phase("rendering")

    early_ctx.output_collector = session.output_collector
    early_ctx.artifact_collector = session.artifact_collector
    try:
        ctx = rendering.phase_render(
            orchestrator,
            cli,
            session.incremental,
            session.force_sequential,
            session.quiet,
            session.verbose,
            session.memory_optimized,
            pages_to_build,
            session.profile,
            progress_manager,
            session.reporter,
            profile_templates=session.profile_templates,
            early_context=early_ctx,
            changed_sources=session.changed_sources,
            collector=session.output_collector,
        )
    finally:
        if progress_manager:
            rendering_elapsed_ms = (time.time() - rendering_start) * 1000
            progress_manager.complete_phase("rendering", elapsed_ms=rendering_elapsed_ms)
            progress_manager.stop()

    session.ctx = ctx

    # Phase 15: Update Site Pages (replace cached pages with rendered pages)
    rendering.phase_update_site_pages(orchestrator, session.incremental, pages_to_build, cli=cli)

    # Phase 16: Track Asset Dependencies
    rendering.phase_track_assets(orchestrator, pages_to_build, cli=cli, build_context=ctx)

    if hasattr(orchestrator, "_provenance_filter") and pages_to_build:
        from bengal.orchestration.build.provenance_filter import record_all_page_builds

        record_all_page_builds(orchestrator, pages_to_build, parallel=not session.force_sequential)

    rendering_duration_ms = (time.time() - rendering_start) * 1000
    orchestrator.stats.record_phase_timing("Rendering", rendering_duration_ms)
    session.notify_phase_complete(
        "rendering",
        rendering_duration_ms,
        f"{len(pages_to_build) if pages_to_build else 0} pages rendered",
    )
    session.run_plugin_phase("post_render")  # canonical
    session.run_plugin_phase("post_rendering")  # back-compat alias of post_render
