"""
Resource lifecycle management for Bengal dev server.

Provides centralized cleanup handling for all termination scenarios:
- Normal exit (context manager)
- Ctrl+C (KeyboardInterrupt + signal handler)
- kill/SIGTERM (signal handler)
- Parent death (atexit handler)
- Exceptions (context manager __exit__)
"""

from __future__ import annotations

import atexit
import contextlib
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class ResourceManager:
    """
    Centralized resource lifecycle management.

    Ensures all resources are cleaned up regardless of how the process exits.

    Usage:
        with ResourceManager() as rm:
            server = rm.register_server(httpd)
            observer = rm.register_observer(watcher)
            # Resources automatically cleaned up on exit

    Features:
    - Idempotent cleanup (safe to call multiple times)
    - LIFO cleanup order (like context managers)
    - Timeout protection (won't hang forever)
    - Thread-safe registration
    - Handles all termination scenarios
    """

    def __init__(self) -> None:
        """Initialize resource manager."""
        self._resources: list[tuple[str, Any, Callable[[Any], None]]] = []
        self._cleanup_done = False
        self._lock = threading.Lock()
        self._original_signals: dict[signal.Signals, Any] = {}

    def register(self, name: str, resource: Any, cleanup_fn: Callable[[Any], None]) -> Any:
        """
        Register a resource with its cleanup function.

        Args:
            name: Human-readable name for debugging
            resource: The resource object
            cleanup_fn: Function to call to clean up (takes resource as arg)

        Returns:
            The resource (for chaining)
        """
        with self._lock:
            self._resources.append((name, resource, cleanup_fn))
        return resource

    def register_server(self, server: Any) -> Any:
        """
        Register HTTP server for cleanup.

        Args:
            server: socketserver.TCPServer instance

        Returns:
            The server
        """

        def cleanup(s: Any) -> None:
            try:
                # Shutdown in a thread with timeout to avoid hanging
                shutdown_thread = threading.Thread(target=s.shutdown)
                shutdown_thread.daemon = True
                shutdown_thread.start()
                shutdown_thread.join(timeout=2.0)

                if shutdown_thread.is_alive():
                    print("  ⚠️  Server shutdown timed out (press Ctrl+C again to force quit)")

                s.server_close()
            except Exception as e:
                print(f"  ⚠️  Error closing server: {e}")

        return self.register("HTTP Server", server, cleanup)

    def register_observer(self, observer: Any) -> Any:
        """
        Register file system observer for cleanup.

        Args:
            observer: watchdog.observers.Observer instance

        Returns:
            The observer
        """

        def cleanup(o: Any) -> None:
            try:
                o.stop()
                # Don't hang forever waiting for observer (reduced from 5s to 2s)
                o.join(timeout=2.0)
                if o.is_alive():
                    print("  ⚠️  File observer did not stop cleanly (still running)")
            except Exception as e:
                print(f"  ⚠️  Error stopping observer: {e}")

        return self.register("File Observer", observer, cleanup)

    def register_pidfile(self, pidfile_path: Path) -> Path:
        """
        Register PID file for cleanup.

        Args:
            pidfile_path: Path object to PID file

        Returns:
            The path
        """

        def cleanup(path: Path) -> None:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.debug(
                    "resource_manager_cleanup_failed",
                    path=str(path),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_cleanup",
                )
                pass

        self.register("PID File", pidfile_path, cleanup)
        return pidfile_path

    def register_watcher_runner(self, runner: Any) -> Any:
        """
        Register WatcherRunner for cleanup.

        Args:
            runner: WatcherRunner instance

        Returns:
            The runner
        """

        def cleanup(r: Any) -> None:
            try:
                r.stop()
            except Exception as e:
                logger.debug(
                    "watcher_runner_cleanup_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

        return self.register("Watcher Runner", runner, cleanup)

    def register_build_trigger(self, trigger: Any) -> Any:
        """
        Register BuildTrigger for cleanup.

        Args:
            trigger: BuildTrigger instance

        Returns:
            The trigger
        """

        def cleanup(t: Any) -> None:
            try:
                t.shutdown()
            except Exception as e:
                logger.debug(
                    "build_trigger_cleanup_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

        return self.register("Build Trigger", trigger, cleanup)

    def cleanup(self, signum: int | None = None) -> None:
        """
        Clean up all resources (idempotent).

        Args:
            signum: Signal number if cleanup triggered by signal
        """
        with self._lock:
            if self._cleanup_done:
                return
            self._cleanup_done = True

        if signum:
            sig_name = (
                signal.Signals(signum).name
                if hasattr(signal.Signals, "__contains__")
                else str(signum)
            )
            if sig_name == "SIGINT":
                print("\n  👋 Shutting down gracefully... (press Ctrl+C again to force quit)")
            else:
                print(f"\n  👋 Received {sig_name}, shutting down...")

        # Clean up in reverse order (LIFO - like context managers)
        start_time = time.time()

        for name, resource, cleanup_fn in reversed(self._resources):
            try:
                cleanup_fn(resource)
            except Exception as e:
                print(f"  ⚠️  Error cleaning up {name}: {e}")

        self._restore_signals()

        # Show completion message if shutdown was fast enough
        elapsed = time.time() - start_time
        if signum and elapsed < 3.0:  # Only show if cleanup was reasonably quick
            print("  ✅ Server stopped")

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle termination signals."""
        # Check if this is the first or second interrupt
        if not self._cleanup_done:
            # First interrupt - start graceful shutdown
            self.cleanup(signum=signum)
            sys.exit(0)
        else:
            # Second interrupt - force exit
            print("\n  ⚠️  Force shutdown")
            sys.exit(1)

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for cleanup."""
        # Store original handlers so we can restore them
        signals_to_catch: list[signal.Signals] = [signal.SIGINT, signal.SIGTERM]

        # SIGHUP only exists on Unix
        if hasattr(signal, "SIGHUP"):
            signals_to_catch.append(signal.SIGHUP)

        import contextlib

        for sig in signals_to_catch:
            with contextlib.suppress(OSError, ValueError):
                # Some signals can't be caught (e.g., in threads, Windows limitations)
                self._original_signals[sig] = signal.signal(sig, self._signal_handler)

    def _restore_signals(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_signals.items():
            with contextlib.suppress(OSError, ValueError):
                signal.signal(sig, handler)

    def __enter__(self) -> ResourceManager:
        """Context manager entry."""
        self._register_signal_handlers()
        atexit.register(self.cleanup)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *args: Any) -> None:
        """Context manager exit - ensure cleanup runs."""
        self.cleanup()
        # Don't suppress exceptions (return None implicitly)
