"""
File watching using Rust-based watchfiles.

Provides fast, async file watching with:
- 10-50x faster change detection than Python alternatives
- Built-in debouncing and batching
- Native async iterator support
- Low memory footprint
- Event type propagation for smart rebuild decisions

Reliability:
- On macOS (darwin), native FSEvents can miss changes (atomic writes, sync).
  Polling mode (force_polling=True) is more reliable and works with
  symlinks, monorepos, and editable installs.
- WATCHFILES_FORCE_POLLING=1 enables polling from any platform.
- dev_server.watch.force_polling in config overrides platform default.

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

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import watchfiles

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    import asyncio
    from collections.abc import AsyncIterator, Callable

logger = get_logger(__name__)


def _should_use_polling(force_polling: bool | None) -> bool:
    """
    Determine if polling mode should be used for reliable change detection.

    Polling is more reliable than native OS events when:
    - macOS: FSEvents can miss atomic writes from vim, neovim, and similar editors
    - Symlinks / monorepos: Path resolution can differ between watcher and editor
    - Editable installs: Parent-dir layouts can confuse native watchers

    On macOS, polling is the default because FSEvents misses atomic swap writes
    that editors like vim/neovim use (write to temp file, then rename).
    Set WATCHFILES_FORCE_POLLING=0 to use native FSEvents instead.

    Args:
        force_polling: Explicit override from config (None = auto-detect)

    Returns:
        True if polling should be used
    """
    if force_polling is not None:
        logger.debug("file_watcher_mode", polling=force_polling, reason="explicit_config")
        return force_polling
    # Env var (watchfiles convention) — checked before platform defaults so users can override
    env_val = (os.environ.get("WATCHFILES_FORCE_POLLING", "") or "").strip().lower()
    if env_val:
        use_polling = env_val not in ("0", "false", "no", "disable", "disabled")
        logger.debug(
            "file_watcher_mode",
            polling=use_polling,
            reason="env_var_WATCHFILES_FORCE_POLLING",
        )
        return use_polling
    # macOS: known watchfiles reliability issues with atomic writes
    if sys.platform == "darwin":
        logger.debug(
            "file_watcher_mode",
            polling=True,
            reason="macos_default",
            hint="FSEvents misses atomic writes from vim/neovim; using polling. "
            "Set WATCHFILES_FORCE_POLLING=0 to use native events.",
        )
        return True
    return False


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
        - Graceful shutdown via stop_event

    """

    def __init__(
        self,
        paths: list[Path],
        ignore_filter: Callable[[Path], bool],
        stop_event: asyncio.Event | None = None,
        *,
        force_polling: bool | None = None,
    ) -> None:
        """
        Initialize watchfiles watcher.

        Args:
            paths: Directories to watch recursively (resolved to absolute)
            ignore_filter: Function returning True if path should be ignored
            stop_event: Optional asyncio.Event to signal graceful shutdown
            force_polling: Use polling instead of native events (None=auto for macOS)
        """
        self.paths = [p.resolve() for p in paths]
        self.ignore_filter = ignore_filter
        self.stop_event = stop_event
        self._force_polling = force_polling

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

        use_polling = _should_use_polling(self._force_polling)
        if use_polling:
            logger.debug(
                "file_watcher_using_polling",
                reason="reliability",
                paths_count=len(self.paths),
            )

        # Disable watchfiles' built-in debounce (default 1600ms) since
        # WatcherRunner already handles debouncing. This eliminates ~1.6s
        # of redundant delay between file detection and rebuild.
        async for changes in watchfiles.awatch(
            *self.paths,
            watch_filter=watch_filter,
            stop_event=self.stop_event,
            debounce=0,
            force_polling=use_polling,
            poll_delay_ms=300,
        ):
            paths = {Path(path) for (_, path) in changes}
            event_types = {change_type_map.get(change, "modified") for (change, _) in changes}
            yield (paths, event_types)


def create_watcher(
    paths: list[Path],
    ignore_filter: Callable[[Path], bool],
    stop_event: asyncio.Event | None = None,
    *,
    force_polling: bool | None = None,
) -> WatchfilesWatcher:
    """
    Create a file watcher for the given paths.

    Args:
        paths: Directories to watch (resolved to absolute)
        ignore_filter: Function returning True if path should be ignored
        stop_event: Optional asyncio.Event to signal graceful shutdown
        force_polling: Use polling mode (None=auto for macOS)

    Returns:
        Configured FileWatcher instance

    Example:
            >>> filter = IgnoreFilter(glob_patterns=["*.pyc"])
            >>> watcher = create_watcher([Path(".")], filter)

    """
    logger.debug("file_watcher_backend", backend="watchfiles")
    return WatchfilesWatcher(paths, ignore_filter, stop_event, force_polling=force_polling)
