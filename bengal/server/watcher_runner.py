"""
Async-to-sync bridge for FileWatcher integration.

Runs the async FileWatcher in a background thread and triggers builds
via callback when changes are detected.

Architecture:
    WatcherRunner owns the file watching lifecycle:
    1. Creates IgnoreFilter from site config
    2. Creates FileWatcher (using watchfiles)
    3. Runs async watcher in background thread
    4. Collects and debounces changes
    5. Triggers builds via BuildTrigger

Related:
    - bengal/server/file_watcher.py: Async file watching (watchfiles)
    - bengal/server/ignore_filter.py: Path filtering
    - bengal/server/build_trigger.py: Build execution
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bengal.server.file_watcher import create_watcher
from bengal.server.ignore_filter import IgnoreFilter
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class WatcherRunner:
    """
    Runs FileWatcher in a background thread with debouncing.

    Features:
        - Async-to-sync bridge for FileWatcher
        - Built-in debouncing (configurable delay)
        - Event type tracking (created, modified, deleted)
        - Thread-safe change accumulation
        - Graceful shutdown

    Example:
        >>> def on_changes(paths, event_types):
        ...     print(f"Changed: {paths}")
        >>> runner = WatcherRunner(
        ...     paths=[Path("content"), Path("templates")],
        ...     ignore_filter=IgnoreFilter(),
        ...     on_changes=on_changes,
        ... )
        >>> runner.start()
        >>> # ... later
        >>> runner.stop()
    """

    def __init__(
        self,
        paths: list[Path],
        ignore_filter: IgnoreFilter,
        on_changes: Callable[[set[Path], set[str]], None],
        debounce_ms: int = 300,
    ) -> None:
        """
        Initialize watcher runner.

        Args:
            paths: Directories to watch recursively
            ignore_filter: Filter for paths to ignore
            on_changes: Callback when changes detected (paths, event_types)
            debounce_ms: Debounce delay in milliseconds
        """
        self.paths = paths
        self.ignore_filter = ignore_filter
        self.on_changes = on_changes
        self.debounce_ms = debounce_ms

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

        # Change accumulation (thread-safe)
        self._changes_lock = threading.Lock()
        self._pending_changes: set[Path] = set()
        self._pending_event_types: set[str] = set()
        self._last_change_time: float = 0

    def start(self) -> None:
        """
        Start the watcher in a background thread.

        Creates an asyncio event loop in the thread and runs the
        FileWatcher until stop() is called.
        """
        if self._thread is not None:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        logger.info(
            "watcher_runner_started",
            paths=[str(p) for p in self.paths],
            debounce_ms=self.debounce_ms,
        )

    def stop(self) -> None:
        """
        Stop the watcher and wait for thread to finish.

        Gracefully shuts down the async event loop and joins the thread.
        """
        if self._thread is None:
            return

        # Signal the watch loop to exit gracefully
        self._stop_event.set()

        # Wait for thread to finish (the loop will exit via stop_event check)
        self._thread.join(timeout=5.0)
        if self._thread.is_alive():
            # Force stop the loop if thread didn't exit gracefully
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                logger.warning("watcher_runner_thread_did_not_stop")
        else:
            logger.debug("watcher_runner_stopped")

        self._thread = None
        self._loop = None

    def _run(self) -> None:
        """
        Thread target - runs the async watcher loop.
        """
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._loop.run_until_complete(self._watch_loop())
        except Exception as e:
            logger.error("watcher_runner_error", error=str(e), error_type=type(e).__name__)
        finally:
            if self._loop is not None:
                self._loop.close()

    async def _watch_loop(self) -> None:
        """
        Main async watch loop.

        Creates the FileWatcher and processes changes until stopped.
        """
        watcher = create_watcher(
            paths=self.paths,
            ignore_filter=self.ignore_filter,
        )

        logger.debug("watcher_runner_watching", backend=type(watcher).__name__)

        # Run watcher and debounce tasks concurrently
        watch_task = asyncio.create_task(self._process_changes(watcher))
        debounce_task = asyncio.create_task(self._debounce_loop())

        try:
            # Wait until stop is requested
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
        finally:
            watch_task.cancel()
            debounce_task.cancel()

            # Wait for tasks to complete with timeout to avoid hanging
            # This prevents "Task was destroyed but it is pending!" warnings
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(
                    asyncio.gather(watch_task, debounce_task, return_exceptions=True),
                    timeout=1.0,
                )

    async def _process_changes(self, watcher: Any) -> None:
        """
        Process changes from the watcher.

        Accumulates changes for debouncing.
        """
        try:
            async for changed_paths, event_types in watcher.watch():
                if self._stop_event.is_set():
                    break

                with self._changes_lock:
                    self._pending_changes.update(changed_paths)
                    self._pending_event_types.update(event_types)
                    self._last_change_time = time.time()

                logger.debug(
                    "watcher_runner_changes_received",
                    count=len(changed_paths),
                    pending=len(self._pending_changes),
                    event_types=list(event_types),
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("watcher_runner_process_error", error=str(e))

    async def _debounce_loop(self) -> None:
        """
        Debounce loop - triggers callback after debounce delay.
        """
        debounce_seconds = self.debounce_ms / 1000.0

        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(0.05)  # Check every 50ms

                with self._changes_lock:
                    if not self._pending_changes:
                        continue

                    elapsed = time.time() - self._last_change_time
                    if elapsed < debounce_seconds:
                        continue

                    # Time to trigger
                    changes = self._pending_changes.copy()
                    event_types = self._pending_event_types.copy()
                    self._pending_changes.clear()
                    self._pending_event_types.clear()

                # Trigger callback outside lock
                try:
                    self.on_changes(changes, event_types)
                except Exception as e:
                    logger.error(
                        "watcher_runner_callback_error",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
        except asyncio.CancelledError:
            raise


def create_watcher_runner(
    site: Any,
    watch_dirs: list[Path],
    on_changes: Callable[[set[Path], set[str]], None],
    debounce_ms: int = 300,
) -> WatcherRunner:
    """
    Create a WatcherRunner configured for a site.

    Factory function that creates IgnoreFilter from site config
    and configures the watcher runner.

    Args:
        site: Site instance with config
        watch_dirs: Directories to watch
        on_changes: Callback for changes (paths, event_types)
        debounce_ms: Debounce delay in milliseconds

    Returns:
        Configured WatcherRunner instance
    """
    # Create ignore filter from site config
    config = getattr(site, "config", {}) or {}
    dev_server = config.get("dev_server", {})

    ignore_filter = IgnoreFilter(
        glob_patterns=dev_server.get("exclude_patterns", []),
        regex_patterns=dev_server.get("exclude_regex", []),
        directories=[site.output_dir] if hasattr(site, "output_dir") else [],
        include_defaults=True,
    )

    return WatcherRunner(
        paths=watch_dirs,
        ignore_filter=ignore_filter,
        on_changes=on_changes,
        debounce_ms=debounce_ms,
    )
