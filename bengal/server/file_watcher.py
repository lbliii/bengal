"""
Modern file watching with watchfiles and watchdog fallback.

Provides an abstraction over file watching backends with:
- WatchfilesWatcher: Rust-based, 10-50x faster on large codebases
- WatchdogWatcher: Python-based fallback, always available
- Automatic backend selection with env var override
- Event type propagation for smart rebuild decisions

Event Types:
    Watchers yield tuples of (changed_paths, event_types) where event_types
    is a set of strings indicating what kind of changes occurred:
    - "created": File was created (triggers full rebuild in BuildTrigger)
    - "modified": File was modified (allows incremental rebuild)
    - "deleted": File was deleted (triggers full rebuild in BuildTrigger)
    - "moved": File was moved (watchdog only, triggers full rebuild)

    This enables BuildTrigger to make smart decisions about whether to
    perform a full rebuild (structural changes) or incremental rebuild
    (content-only changes).

Related:
    - bengal/server/ignore_filter.py: Provides filtering for watched paths
    - bengal/server/watcher_runner.py: Runs watcher and triggers builds
    - bengal/server/build_trigger.py: Uses event types for rebuild decisions
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

    File watchers yield tuples of (changed_paths, event_types) asynchronously.
    Implementations must handle filtering internally.

    Event types follow watchfiles conventions:
        - "added": File was created
        - "modified": File was modified
        - "deleted": File was deleted
    """

    async def watch(self) -> AsyncIterator[tuple[set[Path], set[str]]]:
        """
        Yield tuples of (changed_paths, event_types).

        Each yield produces a set of paths that changed since the last yield,
        along with the types of changes that occurred.

        Yields:
            Tuple of (set of changed Path objects, set of event type strings)
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

    async def watch(self) -> AsyncIterator[tuple[set[Path], set[str]]]:
        """
        Yield tuples of (changed_paths, event_types) using watchfiles.

        Uses watchfiles.awatch for native async file watching.
        The watch_filter callback excludes paths matching the ignore filter.

        Maps watchfiles.Change to event type strings:
            - Change.added -> "added" (maps to "created" for BuildTrigger)
            - Change.modified -> "modified"
            - Change.deleted -> "deleted"
        """
        import watchfiles

        # Map watchfiles.Change enum to event type strings
        change_type_map = {
            watchfiles.Change.added: "created",
            watchfiles.Change.modified: "modified",
            watchfiles.Change.deleted: "deleted",
        }

        # Create filter for watchfiles (returns True to INCLUDE)
        def watch_filter(change_type: watchfiles.Change, path: str) -> bool:
            return not self.ignore_filter(Path(path))

        async for changes in watchfiles.awatch(
            *self.paths,
            watch_filter=watch_filter,
        ):
            paths = {Path(path) for (_, path) in changes}
            event_types = {change_type_map.get(change, "modified") for (change, _) in changes}
            yield (paths, event_types)


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
        self._event_types: set[str] = set()
        self._event = asyncio.Event()

    async def watch(self) -> AsyncIterator[tuple[set[Path], set[str]]]:
        """
        Yield tuples of (changed_paths, event_types) using watchdog.

        Runs watchdog Observer in background thread and bridges events
        to the async context using asyncio.Event.

        Maps watchdog event types to strings:
            - created -> "created"
            - modified -> "modified"
            - deleted -> "deleted"
            - moved -> "moved"
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
                event_types = self._event_types.copy()
                self._changes.clear()
                self._event_types.clear()
                self._event.clear()

                if changes:
                    yield (changes, event_types)
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
                    # Map watchdog event_type to our standard types
                    event_type = getattr(event, "event_type", "modified")
                    watcher._event_types.add(event_type)
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
