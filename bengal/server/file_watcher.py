"""
Modern file watching with watchfiles and watchdog fallback.

Provides an abstraction over file watching backends with:
- WatchfilesWatcher: Rust-based, 10-50x faster on large codebases
- WatchdogWatcher: Python-based fallback, always available
- Automatic backend selection with env var override

Related:
    - bengal/server/ignore_filter.py: Provides filtering for watched paths
    - bengal/server/build_handler.py: Handles file change events
    - bengal/server/dev_server.py: Integrates file watching

Configuration:
    Backend selection via BENGAL_WATCH_BACKEND env var:
    - "auto" (default): Use watchfiles if available, fall back to watchdog
    - "watchfiles": Force watchfiles (error if not installed)
    - "watchdog": Force watchdog (always available)
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Protocol

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class FileWatcher(Protocol):
    """
    Protocol for file watchers.

    File watchers yield sets of changed paths asynchronously.
    Implementations must handle filtering internally.
    """

    async def watch(self) -> AsyncIterator[set[Path]]:
        """
        Yield sets of changed paths.

        Each yield produces a set of paths that changed since the last yield.
        The watcher handles debouncing and batching internally.

        Yields:
            Set of changed Path objects
        """
        ...


class WatchfilesWatcher:
    """
    Primary watcher using Rust-based watchfiles.

    Features:
        - 10-50x faster change detection than watchdog on large codebases
        - Built-in debouncing and batching
        - Native async iterator support
        - Low memory footprint

    Requires:
        watchfiles>=0.20 (optional dependency)
    """

    def __init__(
        self,
        paths: list[Path],
        ignore_filter: Callable[[Path], bool],
    ) -> None:
        """
        Initialize watchfiles watcher.

        Args:
            paths: Directories to watch recursively
            ignore_filter: Function returning True if path should be ignored
        """
        self.paths = paths
        self.ignore_filter = ignore_filter

    async def watch(self) -> AsyncIterator[set[Path]]:
        """
        Yield sets of changed paths using watchfiles.

        Uses watchfiles.awatch for native async file watching.
        The watch_filter callback excludes paths matching the ignore filter.
        """
        import watchfiles

        # Create filter for watchfiles (returns True to INCLUDE)
        def watch_filter(change_type: watchfiles.Change, path: str) -> bool:
            return not self.ignore_filter(Path(path))

        async for changes in watchfiles.awatch(
            *self.paths,
            watch_filter=watch_filter,
        ):
            yield {Path(path) for (_, path) in changes}


class WatchdogWatcher:
    """
    Fallback watcher using Python-based watchdog.

    Features:
        - Always available (bundled with Bengal)
        - Compatible with all platforms
        - Manual debouncing via asyncio

    Note:
        Slower than watchfiles on large codebases (200ms vs 20ms latency).
        Use watchfiles for best performance.
    """

    def __init__(
        self,
        paths: list[Path],
        ignore_filter: Callable[[Path], bool],
        debounce_ms: int = 100,
    ) -> None:
        """
        Initialize watchdog watcher.

        Args:
            paths: Directories to watch recursively
            ignore_filter: Function returning True if path should be ignored
            debounce_ms: Milliseconds to wait before yielding changes
        """
        self.paths = paths
        self.ignore_filter = ignore_filter
        self.debounce_ms = debounce_ms
        self._changes: set[Path] = set()
        self._event = asyncio.Event()

    async def watch(self) -> AsyncIterator[set[Path]]:
        """
        Yield sets of changed paths using watchdog.

        Runs watchdog Observer in background thread and bridges events
        to the async context using asyncio.Event.
        """
        from watchdog.observers import Observer

        handler = self._create_handler()
        observer = Observer()

        for path in self.paths:
            observer.schedule(handler, str(path), recursive=True)

        observer.start()

        try:
            while True:
                await self._event.wait()
                await asyncio.sleep(self.debounce_ms / 1000)

                changes = self._changes.copy()
                self._changes.clear()
                self._event.clear()

                if changes:
                    yield changes
        finally:
            observer.stop()
            observer.join()

    def _create_handler(self) -> object:
        """
        Create watchdog event handler.

        Returns:
            FileSystemEventHandler that bridges to async context
        """
        from watchdog.events import FileSystemEventHandler

        watcher = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: object) -> None:
                # Skip directory events
                if getattr(event, "is_directory", False):
                    return

                path = Path(getattr(event, "src_path", ""))
                if not watcher.ignore_filter(path):
                    watcher._changes.add(path)
                    watcher._event.set()

        return Handler()


def create_watcher(
    paths: list[Path],
    ignore_filter: Callable[[Path], bool],
    backend: str = "auto",
) -> FileWatcher:
    """
    Create appropriate file watcher based on backend preference.

    Backend selection order:
    1. Environment variable BENGAL_WATCH_BACKEND
    2. Explicit backend parameter
    3. Auto-detection (prefer watchfiles if available)

    Args:
        paths: Directories to watch
        ignore_filter: Function returning True if path should be ignored
        backend: Backend preference ("auto", "watchfiles", or "watchdog")

    Returns:
        Configured FileWatcher instance

    Raises:
        ImportError: If watchfiles backend is explicitly requested but not installed

    Example:
        >>> filter = IgnoreFilter(glob_patterns=["*.pyc"])
        >>> watcher = create_watcher([Path(".")], filter, backend="auto")
    """
    # Environment variable takes precedence
    backend = os.environ.get("BENGAL_WATCH_BACKEND", backend).lower()

    if backend == "watchdog":
        logger.debug("file_watcher_backend", backend="watchdog", reason="explicit")
        return WatchdogWatcher(paths, ignore_filter)

    if backend in ("watchfiles", "auto"):
        try:
            import watchfiles  # noqa: F401

            logger.debug("file_watcher_backend", backend="watchfiles", reason="available")
            return WatchfilesWatcher(paths, ignore_filter)
        except ImportError as e:
            if backend == "watchfiles":
                raise ImportError(
                    "watchfiles not installed. Install with: pip install watchfiles"
                ) from e
            # Fall back to watchdog for "auto"
            logger.debug(
                "file_watcher_backend", backend="watchdog", reason="watchfiles_unavailable"
            )

    # Default fallback
    return WatchdogWatcher(paths, ignore_filter)


def is_watchfiles_available() -> bool:
    """
    Check if watchfiles package is available.

    Returns:
        True if watchfiles is installed and importable
    """
    try:
        import watchfiles  # noqa: F401

        return True
    except ImportError:
        return False
