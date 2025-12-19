"""
Development server for Bengal SSG.

Provides a local HTTP server with file watching and automatic rebuilds
for a smooth development experience.

Components:
- DevServer: Main development server with HTTP serving and file watching
- WatcherRunner: Async-to-sync bridge for FileWatcher with debouncing
- BuildTrigger: Build execution handler with pre/post hooks
- BuildExecutor: Process-isolated build execution for resilience
- FileWatcher: Rust-based file watching (watchfiles)
- IgnoreFilter: Configurable file ignore patterns (glob + regex)
- LiveReloadMixin: Server-Sent Events (SSE) for browser hot reload
- RequestHandler: Custom HTTP request handler with beautiful logging
- ResourceManager: Graceful cleanup of server resources on shutdown
- PIDManager: Process tracking and stale process recovery

Features:
- Automatic incremental rebuilds on file changes
- Event type detection (created/modified/deleted) for smart rebuild decisions
- Beautiful, minimal request logging
- Custom 404 error pages
- Graceful shutdown handling (Ctrl+C, SIGTERM)
- Stale process detection and cleanup
- Automatic port fallback if port is in use
- Optional browser auto-open
- Pre/post build hooks for custom workflows
- Process-isolated builds for crash resilience
- Configurable ignore patterns (exclude_patterns, exclude_regex)
- Fast file watching via watchfiles (Rust-based, 10-50x faster)
- Default ignore patterns for common cache/build directories (.bengal, .git, etc.)

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

The server watches for changes in:
- content/ - Markdown content files
- assets/ - CSS, JS, images
- templates/ - Jinja2 templates
- data/ - YAML/JSON data files
- themes/ - Theme files
- bengal.toml - Configuration file
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Lazy export of DevServer to avoid importing heavy dependencies
# when users are not running the dev server.

if TYPE_CHECKING:
    # For type checkers only; does not execute at runtime
    from bengal.server.build_executor import BuildExecutor as BuildExecutor
    from bengal.server.build_executor import BuildRequest as BuildRequest
    from bengal.server.build_executor import BuildResult as BuildResult
    from bengal.server.build_trigger import BuildTrigger as BuildTrigger
    from bengal.server.dev_server import DevServer as DevServer
    from bengal.server.file_watcher import FileWatcher as FileWatcher
    from bengal.server.ignore_filter import IgnoreFilter as IgnoreFilter
    from bengal.server.watcher_runner import WatcherRunner as WatcherRunner

__all__ = [
    "DevServer",
    "WatcherRunner",
    "BuildTrigger",
    "BuildExecutor",
    "BuildRequest",
    "BuildResult",
    "FileWatcher",
    "IgnoreFilter",
]


def __getattr__(name: str) -> Any:
    """
    Lazy import pattern for server components.

    Args:
        name: The attribute name being accessed

    Returns:
        The requested attribute

    Raises:
        AttributeError: If the attribute is not found
    """
    if name == "DevServer":
        from bengal.server.dev_server import DevServer

        return DevServer
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
