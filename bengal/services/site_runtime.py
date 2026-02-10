"""
Runtime service helpers for Site operations.

These helpers keep heavy runtime wiring (server/orchestration/rendering/cache)
out of core model modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.protocols import SiteLike


def create_query_index_registry(site: SiteLike, indexes_dir: Path) -> Any:
    """Create query index registry lazily."""
    from bengal.cache.query_index_registry import QueryIndexRegistry

    return QueryIndexRegistry(site, indexes_dir)


def build_site(site: Any, options: Any) -> Any:
    """Build a site through orchestration."""
    from bengal.orchestration import BuildOrchestrator

    orchestrator = BuildOrchestrator(site)
    return orchestrator.build(options)


def start_dev_server(
    site: Any,
    *,
    host: str,
    port: int,
    watch: bool,
    auto_port: bool,
    open_browser: bool,
    version_scope: str | None,
    target_outputs: frozenset[str],
) -> None:
    """Start dev server for a site."""
    from bengal.server.dev_server import DevServer
    from bengal.server.wiring import get_reload_controller

    server = DevServer(
        site,
        host=host,
        port=port,
        watch=watch,
        auto_port=auto_port,
        open_browser=open_browser,
        version_scope=version_scope,
        target_outputs=target_outputs,
        reload_controller=get_reload_controller(),
    )
    server.start()


def reset_rendering_runtime_state() -> None:
    """Clear runtime rendering thread-local state."""
    from bengal.rendering.assets import reset_asset_manifest
    from bengal.rendering.pipeline.thread_local import get_created_dirs

    get_created_dirs().clear()
    reset_asset_manifest()
