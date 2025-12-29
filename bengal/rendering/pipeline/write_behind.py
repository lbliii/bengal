"""
Write-behind buffer for async page output.

RFC: rfc-path-to-200-pgs (Phase III)

Overlaps CPU-bound rendering with I/O-bound file writes by queuing
rendered pages for a dedicated writer thread.

Usage:
    collector = WriteBehindCollector()

    # In render workers:
    collector.enqueue(output_path, html_content)  # Non-blocking

    # After all rendering:
    collector.flush_and_close()  # Wait for writes to complete

Thread Safety:
    Queue operations are thread-safe. Multiple render threads can
    enqueue simultaneously while the writer thread drains.
"""

from __future__ import annotations

import threading
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class WriteBehindCollector:
    """Async write-behind buffer for rendered pages.

    Worker threads push (path, content) pairs to a queue.
    A dedicated writer thread drains the queue to disk.

    Benefits:
        - Overlaps CPU (rendering) with I/O (writing)
        - Reduces worker thread blocking on disk
        - Batches directory creation

    Attributes:
        _queue: Thread-safe queue of (Path, str) pairs
        _writer_thread: Background thread draining to disk
        _shutdown: Event signaling shutdown
        _error: Any error from writer thread
        _writes_completed: Count of successful writes
    """

    __slots__ = (
        "_queue",
        "_writer_thread",
        "_shutdown",
        "_error",
        "_writes_completed",
        "_fast_writes",
        "_created_dirs",
    )

    def __init__(self, site: Site | None = None, max_queue_size: int = 500) -> None:
        """Initialize write-behind collector.

        Args:
            site: Site instance for config (fast_writes setting)
            max_queue_size: Maximum queue depth before blocking (backpressure)
        """
        self._queue: Queue[tuple[Path, str] | None] = Queue(maxsize=max_queue_size)
        self._shutdown = threading.Event()
        self._error: Exception | None = None
        self._writes_completed = 0
        self._created_dirs: set[str] = set()

        # Get fast_writes setting from config
        self._fast_writes = False
        if site:
            self._fast_writes = site.config.get("build", {}).get("fast_writes", False)

        # Start writer thread
        self._writer_thread = threading.Thread(
            target=self._drain_loop,
            name="WriteBehindWriter",
            daemon=True,
        )
        self._writer_thread.start()

    def enqueue(self, output_path: Path, content: str) -> None:
        """Queue a page for writing.

        Non-blocking unless queue is full (backpressure).

        Args:
            output_path: Destination file path
            content: Rendered HTML content

        Raises:
            RuntimeError: If writer thread has failed
        """
        if self._error:
            raise RuntimeError(f"Writer thread failed: {self._error}") from self._error

        self._queue.put((output_path, content))

    def _drain_loop(self) -> None:
        """Background thread: drain queue to disk."""
        try:
            while True:
                try:
                    # Wait for item with timeout to check shutdown
                    item = self._queue.get(timeout=0.1)
                except Empty:
                    if self._shutdown.is_set() and self._queue.empty():
                        break
                    continue

                if item is None:
                    # Explicit shutdown signal
                    break

                path, content = item
                self._write_file(path, content)
                self._writes_completed += 1
                self._queue.task_done()

        except Exception as e:
            self._error = e
            logger.error(
                "write_behind_error",
                error=str(e),
                error_type=type(e).__name__,
            )

    def _write_file(self, path: Path, content: str) -> None:
        """Write a single file to disk.

        Args:
            path: Destination path
            content: File content
        """
        # Ensure parent directory exists (with caching)
        parent = str(path.parent)
        if parent not in self._created_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(parent)

        if self._fast_writes:
            # Direct write (faster, not crash-safe)
            path.write_text(content, encoding="utf-8")
        else:
            # Atomic write (crash-safe)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(path, content, encoding="utf-8", ensure_parent=False)

    def flush_and_close(self, timeout: float = 30.0) -> int:
        """Wait for all queued writes to complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Number of files written

        Raises:
            RuntimeError: If writer thread failed or timed out
        """
        # Signal shutdown
        self._shutdown.set()
        self._queue.put(None)  # Sentinel to wake up blocked get()

        # Wait for thread
        self._writer_thread.join(timeout=timeout)

        if self._writer_thread.is_alive():
            raise RuntimeError(f"Writer thread did not complete within {timeout}s")

        if self._error:
            raise RuntimeError(f"Writer thread failed: {self._error}") from self._error

        return self._writes_completed

    @property
    def pending_count(self) -> int:
        """Number of items waiting in queue."""
        return self._queue.qsize()

    @property
    def completed_count(self) -> int:
        """Number of writes completed."""
        return self._writes_completed
