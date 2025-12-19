"""
File watching using Rust-based watchfiles.

Provides fast, async file watching with:
- 10-50x faster change detection than Python alternatives
- Built-in debouncing and batching
- Native async iterator support
- Low memory footprint
- Event type propagation for smart rebuild decisions

Event Types:
    Watchers yield tuples of (changed_paths, event_types) where event_types
    is a set of strings indicating what kind of changes occurred:
    - "created": File was created (triggers full rebuild in BuildTrigger)
    - "modified": File was modified (allows incremental rebuild)
    - "deleted": File was deleted (triggers full rebuild in BuildTrigger)

    This enables BuildTrigger to make smart decisions about whether to
    perform a full rebuild (structural changes) or incremental rebuild
    (content-only changes).

Related:
    - bengal/server/ignore_filter.py: Provides filtering for watched paths
    - bengal/server/watcher_runner.py: Runs watcher and triggers builds
    - bengal/server/build_trigger.py: Uses event types for rebuild decisions
    - bengal/server/dev_server.py: Integrates file watching
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Protocol

import watchfiles

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class FileWatcher(Protocol):
    """
    Protocol for file watchers.

    File watchers yield tuples of (changed_paths, event_types) asynchronously.
    Implementations must handle filtering internally.

    Event types follow watchfiles conventions:
        - "created": File was created
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
    File watcher using Rust-based watchfiles.

    Features:
        - 10-50x faster change detection on large codebases
        - Built-in debouncing and batching
        - Native async iterator support
        - Low memory footprint
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
            - Change.added -> "created"
            - Change.modified -> "modified"
            - Change.deleted -> "deleted"
        """
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


def create_watcher(
    paths: list[Path],
    ignore_filter: Callable[[Path], bool],
) -> FileWatcher:
    """
    Create a file watcher for the given paths.

    Args:
        paths: Directories to watch
        ignore_filter: Function returning True if path should be ignored

    Returns:
        Configured FileWatcher instance

    Example:
        >>> filter = IgnoreFilter(glob_patterns=["*.pyc"])
        >>> watcher = create_watcher([Path(".")], filter)
    """
    logger.debug("file_watcher_backend", backend="watchfiles")
    return WatchfilesWatcher(paths, ignore_filter)
