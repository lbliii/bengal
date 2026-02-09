"""
Development server for Bengal SSG.

Powered by the Bengal ecosystem stack:
- **Pounce**: Free-threading-native ASGI server (HTTP/1.1, HTTP/2, compression)
- **Chirp**: SSE-first web framework (EventStream, StaticFiles middleware)

Provides a local development server with file watching, automatic rebuilds,
and browser live reload for a smooth development experience.

Components:
Core Server:
- DevServer: Main orchestrator with ASGI serving and file watching
- DevState: Shared state bridge between build pipeline and ASGI app
- ResourceManager: Graceful cleanup of resources on shutdown
- PIDManager: Process tracking and stale process recovery

ASGI App (bengal/server/asgi_app.py):
- create_dev_app: Chirp app factory with SSE, static files, middleware
- HtmlInjectionMiddleware: Injects live reload script into HTML responses
- BuildGateMiddleware: Returns rebuilding page during active builds

File Watching:
- FileWatcher: Rust-based file watching (watchfiles backend)
- WatcherRunner: Async-to-sync bridge with debouncing
- IgnoreFilter: Configurable ignore patterns (glob + regex)

Build System:
- BuildTrigger: Build orchestration with pre/post hooks
- BuildExecutor: Process-isolated build execution for crash resilience
- ReloadController: Smart reload decisions (CSS-only vs full)

Live Reload:
- SSE endpoint via Chirp EventStream at /__bengal_reload__
- notify_clients_reload: Trigger browser refresh
- send_reload_payload: Send structured reload events

Architecture:
The dev server coordinates several subsystems in a pipeline:

FileWatcher → WatcherRunner → BuildTrigger → BuildExecutor
                                   ↓
                          ReloadController → DevState → SSE → Browser

All resources are managed by ResourceManager for reliable cleanup.

Usage:
    ```python
    from bengal.server import DevServer
    from bengal.core import Site

    site = Site.from_config()
    server = DevServer(
        site,
        host="localhost",
        port=5173,
        watch=True,
        auto_port=True,
        open_browser=True
    )
    server.start()
    ```

Related:
- bengal/cli/serve.py: CLI command for starting dev server
- bengal/orchestration/build_orchestrator.py: Build logic

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Lazy export of DevServer to avoid importing heavy dependencies
# when users are not running the dev server.

if TYPE_CHECKING:
    from bengal.server.asgi_app import DevState as DevState
    from bengal.server.build_executor import BuildExecutor as BuildExecutor
    from bengal.server.build_executor import BuildRequest as BuildRequest
    from bengal.server.build_executor import BuildResult as BuildResult
    from bengal.server.build_trigger import BuildTrigger as BuildTrigger
    from bengal.server.dev_server import DevServer as DevServer
    from bengal.server.file_watcher import FileWatcher as FileWatcher
    from bengal.server.ignore_filter import IgnoreFilter as IgnoreFilter
    from bengal.server.watcher_runner import WatcherRunner as WatcherRunner

__all__ = [
    "BuildExecutor",
    "BuildRequest",
    "BuildResult",
    "BuildTrigger",
    "DevServer",
    "DevState",
    "FileWatcher",
    "IgnoreFilter",
    "WatcherRunner",
]


def __getattr__(name: str) -> Any:
    """Lazy import pattern for server components."""
    if name == "DevServer":
        from bengal.server.dev_server import DevServer

        return DevServer
    if name == "DevState":
        from bengal.server.asgi_app import DevState

        return DevState
    if name == "WatcherRunner":
        from bengal.server.watcher_runner import WatcherRunner

        return WatcherRunner
    if name == "BuildTrigger":
        from bengal.server.build_trigger import BuildTrigger

        return BuildTrigger
    if name in ("BuildExecutor", "BuildRequest", "BuildResult"):
        from bengal.server import build_executor

        return getattr(build_executor, name)
    if name == "FileWatcher":
        from bengal.server.file_watcher import FileWatcher

        return FileWatcher
    if name == "IgnoreFilter":
        from bengal.server.ignore_filter import IgnoreFilter

        return IgnoreFilter
    raise AttributeError(f"module 'bengal.server' has no attribute {name!r}")
