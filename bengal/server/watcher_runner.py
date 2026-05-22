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

Dashboard Integration (RFC: rfc-dashboard-api-integration):
- on_file_change callback: Called immediately when a file change is detected
  (before debouncing), allowing the dashboard to show real-time file activity.

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
from enum import Enum
from typing import TYPE_CHECKING, Any

from bengal.protocols import SiteLike
from bengal.server.file_watcher import create_watcher
from bengal.server.ignore_filter import IgnoreFilter
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = get_logger(__name__)


class _WatcherState(Enum):
    NEW = "new"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


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

    _READY_TIMEOUT_SECONDS = 1.0
    _JOIN_TIMEOUT_SECONDS = 5.0
    _FORCE_JOIN_TIMEOUT_SECONDS = 1.0

    def __init__(
        self,
        paths: list[Path],
        ignore_filter: IgnoreFilter,
        on_changes: Callable[[set[Path], set[str]], None],
        debounce_ms: int = 300,
        *,
        on_file_change: Callable[[Path, str], None] | None = None,
        force_polling: bool | None = None,
    ) -> None:
        """
        Initialize watcher runner.

        Args:
            paths: Directories to watch recursively (resolved to absolute)
            ignore_filter: Filter for paths to ignore
            on_changes: Callback when changes detected (paths, event_types) - debounced
            debounce_ms: Debounce delay in milliseconds
            on_file_change: Optional callback for immediate file change events (path, event_type).
                            Called before debouncing for real-time dashboard updates.
                            (RFC: rfc-dashboard-api-integration)
            force_polling: Use polling mode for reliable detection (None=auto for macOS)
        """
        self.paths = paths
        self.ignore_filter = ignore_filter
        self.on_changes = on_changes
        self.debounce_ms = debounce_ms
        self.on_file_change = on_file_change
        self._force_polling = force_polling

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._async_stop_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._state = _WatcherState.NEW
        self._state_lock = threading.Lock()
        self._ready_event = threading.Event()
        self._stopped_event = threading.Event()
        self._failure: Exception | None = None

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
        with self._state_lock:
            if self._state in {
                _WatcherState.STARTING,
                _WatcherState.RUNNING,
                _WatcherState.STOPPING,
            }:
                return

            self._stop_event.clear()
            self._ready_event.clear()
            self._stopped_event.clear()
            self._failure = None
            self._loop = None
            self._async_stop_event = None
            self._state = _WatcherState.STARTING
            thread = threading.Thread(target=self._run, daemon=True)
            self._thread = thread

        try:
            thread.start()
        except Exception as e:
            with self._state_lock:
                if self._thread is thread:
                    self._thread = None
                self._failure = e
                self._state = _WatcherState.FAILED
                self._ready_event.set()
                self._stopped_event.set()
            raise

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
        with self._state_lock:
            if self._thread is None and self._state in {
                _WatcherState.NEW,
                _WatcherState.STOPPED,
                _WatcherState.FAILED,
            }:
                return

            thread = self._thread
            loop = self._loop
            async_stop_event = self._async_stop_event
            should_wait_ready = self._state is _WatcherState.STARTING and (
                loop is None or async_stop_event is None
            )
            if self._state is not _WatcherState.STOPPING:
                self._state = _WatcherState.STOPPING

        # Signal the watch loop to exit gracefully
        self._stop_event.set()

        if should_wait_ready:
            self._ready_event.wait(timeout=self._READY_TIMEOUT_SECONDS)
            with self._state_lock:
                loop = self._loop
                async_stop_event = self._async_stop_event

        # Set the async stop event (must be done from the loop's thread)
        if loop is not None and async_stop_event is not None:
            self._call_loop_threadsafe(
                async_stop_event.set,
                reason="watcher_runner_loop_closed_before_stop_event",
                loop=loop,
            )

        if thread is None:
            self._finish_stop(thread)
            return

        # Wait for thread to finish (the loop will exit via stop_event check)
        thread.join(timeout=self._JOIN_TIMEOUT_SECONDS)
        if thread.is_alive():
            # Force stop the loop if thread didn't exit gracefully
            with self._state_lock:
                loop = self._loop
            if loop is not None:
                self._call_loop_threadsafe(
                    loop.stop,
                    reason="watcher_runner_loop_closed_before_force_stop",
                    loop=loop,
                )
            thread.join(timeout=self._FORCE_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.warning("watcher_runner_thread_did_not_stop")
        else:
            logger.debug("watcher_runner_stopped")

        self._finish_stop(thread)

    def _run(self) -> None:
        """
        Thread target - runs the async watcher loop.
        """
        loop: asyncio.AbstractEventLoop | None = None
        failure: Exception | None = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create the async stop event in the loop's context
            async_stop_event = asyncio.Event()
            self._publish_loop(loop, async_stop_event)

            loop.run_until_complete(self._watch_loop())
        except Exception as e:
            failure = e
            logger.error("watcher_runner_error", error=str(e), error_type=type(e).__name__)
        finally:
            if loop is not None:
                loop.close()
            self._mark_stopped(failure)

    def _publish_loop(
        self,
        loop: asyncio.AbstractEventLoop,
        async_stop_event: asyncio.Event,
    ) -> None:
        """Publish loop handles created by the watcher thread."""
        with self._state_lock:
            self._loop = loop
            self._async_stop_event = async_stop_event
            if self._state is _WatcherState.STARTING:
                self._state = _WatcherState.RUNNING
            self._ready_event.set()

    def _mark_stopped(self, failure: Exception | None) -> None:
        """Record that the watcher thread has exited."""
        with self._state_lock:
            self._loop = None
            self._async_stop_event = None
            if failure is not None:
                self._failure = failure
                self._state = _WatcherState.FAILED
            elif self._state is not _WatcherState.FAILED:
                self._state = _WatcherState.STOPPED
            self._ready_event.set()
            self._stopped_event.set()

    def _finish_stop(self, thread: threading.Thread | None) -> None:
        """Clear lifecycle handles after a stop attempt completes."""
        with self._state_lock:
            if thread is not None and thread.is_alive():
                self._failure = RuntimeError("watcher runner thread did not stop")
                self._state = _WatcherState.FAILED
            elif self._state is _WatcherState.STOPPING:
                self._state = _WatcherState.STOPPED
            if self._thread is thread:
                self._thread = None
            self._loop = None
            self._async_stop_event = None
            self._stopped_event.set()

    def _call_loop_threadsafe(
        self,
        callback: Callable[[], Any],
        *,
        reason: str,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> bool:
        """Post a callback to the watcher loop if it is still accepting work."""
        if loop is None:
            with self._state_lock:
                loop = self._loop
        if loop is None:
            return False

        try:
            loop.call_soon_threadsafe(callback)
        except RuntimeError as e:
            with self._state_lock:
                state = self._state
            if "Event loop is closed" in str(e) and state in {
                _WatcherState.STOPPING,
                _WatcherState.STOPPED,
                _WatcherState.FAILED,
            }:
                logger.debug(reason)
                return False
            raise
        return True

    async def _watch_loop(self) -> None:
        """
        Main async watch loop.

        Creates the FileWatcher and processes changes until stopped.
        """
        watcher = create_watcher(
            paths=self.paths,
            ignore_filter=self.ignore_filter,
            stop_event=self._async_stop_event,
            force_polling=self._force_polling,
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
            with contextlib.suppress(
                asyncio.CancelledError, asyncio.TimeoutError
            ):  # silent: graceful shutdown on cancel/timeout
                await asyncio.wait_for(
                    asyncio.gather(watch_task, debounce_task, return_exceptions=True),
                    timeout=1.0,
                )

    async def _process_changes(self, watcher: Any) -> None:
        """
        Process changes from the watcher.

        Accumulates changes for debouncing and notifies dashboard immediately.
        """
        try:
            async for changed_paths, event_types in watcher.watch():
                if self._stop_event.is_set():
                    break

                # Notify dashboard immediately for real-time file activity display
                # (RFC: rfc-dashboard-api-integration)
                if self.on_file_change is not None:
                    for path in changed_paths:
                        # Use first event type for the path (typically consistent)
                        event_type = next(iter(event_types), "modified")
                        try:
                            self.on_file_change(path, event_type)
                        except Exception as e:
                            logger.debug(
                                "file_change_callback_error",
                                path=str(path),
                                error=str(e),
                            )

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
    *,
    on_file_change: Callable[[Path, str], None] | None = None,
    force_polling: bool | None = None,
) -> WatcherRunner:
    """
    Create a WatcherRunner configured for a site.

    Factory function that creates IgnoreFilter from site config
    and configures the watcher runner.

    Args:
        site: Site instance with config
        watch_dirs: Directories to watch (resolved to absolute)
        on_changes: Callback for changes (paths, event_types) - debounced
        debounce_ms: Debounce delay in milliseconds
        on_file_change: Optional callback for immediate file change events (path, event_type).
                        Called before debouncing for real-time dashboard updates.
                        (RFC: rfc-dashboard-api-integration)
        force_polling: Use polling mode (None=auto for macOS)

    Returns:
        Configured WatcherRunner instance

    """
    # Create ignore filter from site config using class method
    config = getattr(site, "config", {}) or {}
    # Handle ConfigSection objects that need .raw for dict access
    raw = getattr(config, "raw", config)
    config_dict: dict[str, Any] = raw if isinstance(raw, dict) else {}
    output_dir = site.output_dir if isinstance(site, SiteLike) else None
    ignore_filter = IgnoreFilter.from_config(config_dict, output_dir=output_dir)

    return WatcherRunner(
        paths=watch_dirs,
        ignore_filter=ignore_filter,
        on_changes=on_changes,
        debounce_ms=debounce_ms,
        on_file_change=on_file_change,
        force_polling=force_polling,
    )
