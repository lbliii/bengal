"""
Write-behind buffer for async page output.

RFC: rfc-path-to-200-pgs (Phase III)

Overlaps CPU-bound rendering with I/O-bound file writes by queuing
rendered pages for multiple writer threads.

Usage:
    collector = WriteBehindCollector()

# In render workers:
collector.enqueue(output_path, html_content)  # Non-blocking

# After all rendering:
collector.flush_and_close()  # Wait for writes to complete

Thread Safety:
Queue operations are thread-safe. Multiple render threads can
enqueue simultaneously while the writer pool drains.

Performance Optimizations:
- Multiple writer threads (8 by default) for SSD parallelism
- Auto-enables fast_writes in dev server mode (skips atomic rename)
- Pre-create directories to reduce lock contention
- Atomic counter for temp file names (faster than uuid4)

"""

from __future__ import annotations

import itertools
import os
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING

from bengal.errors import BengalRenderingError, ErrorCode
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

logger = get_logger(__name__)

# Module-level atomic counter for temp file names (faster than uuid4)
_temp_file_counter = itertools.count()


class WriteBehindCollector:
    """Async write-behind buffer for rendered pages.

    Worker threads push (path, content) pairs to a queue.
    A pool of writer threads drains the queue to disk in parallel.

    Benefits:
        - Overlaps CPU (rendering) with I/O (writing)
        - 8 writer threads for better I/O parallelism on SSDs
        - Auto-enables fast_writes in dev server mode
        - Pre-creates directories to reduce lock contention
        - Uses atomic counter instead of uuid4 for temp files

    Attributes:
        _queue: Thread-safe queue of (Path, str) pairs
        _writer_threads: Background threads draining to disk
        _shutdown: Event signaling shutdown
        _error: Any error from writer threads
        _writes_completed: Count of successful writes

    """

    __slots__ = (
        "_created_dirs",
        "_created_dirs_lock",
        "_error",
        "_fast_writes",
        "_num_writers",
        "_queue",
        "_shutdown",
        "_writer_threads",
        "_writes_completed",
        "_writes_lock",
    )

    def __init__(
        self,
        site: SiteLike | None = None,
        max_queue_size: int = 500,
        num_writers: int | None = None,
        dev_mode: bool | None = None,
    ) -> None:
        """Initialize write-behind collector.

        Args:
            site: Site instance for config (fast_writes setting)
            max_queue_size: Maximum queue depth before blocking (backpressure)
            num_writers: Number of writer threads (default: 8 for SSD parallelism)
            dev_mode: Override dev mode detection (auto-detects from site if None)
        """
        self._queue: Queue[tuple[Path, str] | None] = Queue(maxsize=max_queue_size)
        self._shutdown = threading.Event()
        self._error: Exception | None = None
        self._writes_completed = 0
        self._writes_lock = threading.Lock()
        self._created_dirs: set[str] = set()
        self._created_dirs_lock = threading.Lock()

        # Use 8 writer threads by default for better SSD saturation
        cpu_count = os.cpu_count() or 8
        self._num_writers = num_writers if num_writers else min(8, cpu_count)

        # Determine fast_writes mode:
        # 1. Explicit config setting takes precedence
        # 2. Auto-enable in dev server mode (crash safety less important)
        # 3. Default to False (safe atomic writes) for production
        self._fast_writes = False
        if site:
            config_fast_writes = site.config.get("build", {}).get("fast_writes")
            if config_fast_writes is not None:
                # Explicit config setting
                self._fast_writes = bool(config_fast_writes)
            elif dev_mode is not None:
                # Explicit dev_mode passed
                self._fast_writes = dev_mode
            else:
                # Auto-detect from site's build state
                build_state = getattr(site, "_current_build_state", None)
                if build_state and getattr(build_state, "dev_mode", False):
                    self._fast_writes = True
                    logger.debug("fast_writes_auto_enabled", reason="dev_server_mode")

        # Start writer threads
        self._writer_threads: list[threading.Thread] = []
        for i in range(self._num_writers):
            thread = threading.Thread(
                target=self._drain_loop,
                name=f"WriteBehindWriter-{i}",
                daemon=True,
            )
            thread.start()
            self._writer_threads.append(thread)

    def precreate_directories(self, paths: list[Path]) -> None:
        """Pre-create all unique parent directories in a single pass.

        Call this before enqueuing files to eliminate lock contention
        during parallel writes. Creates directories sequentially upfront.

        Args:
            paths: List of output file paths (directories extracted automatically)
        """
        # Collect unique parent directories
        unique_dirs = {str(p.parent) for p in paths}

        # Create all directories (no lock needed - single-threaded setup phase)
        for dir_path in unique_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)

        logger.debug(
            "directories_precreated",
            count=len(unique_dirs),
            files=len(paths),
        )

    def enqueue(self, output_path: Path, content: str) -> None:
        """Queue a page for writing.

        Non-blocking unless queue is full (backpressure).

        Args:
            output_path: Destination file path
            content: Rendered HTML content

        Raises:
            BengalRenderingError: If writer thread has failed
        """
        if self._error:
            raise BengalRenderingError(
                f"Background writer thread failed: {self._error}",
                code=ErrorCode.R010,
                original_error=self._error,
                suggestion="Check disk space and file permissions in output directory",
            ) from self._error

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
                    # Explicit shutdown signal - put it back for other threads
                    self._queue.put(None)
                    break

                path, content = item
                self._write_file(path, content)
                with self._writes_lock:
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
        # Ensure parent directory exists (thread-safe with lock)
        # Note: If precreate_directories() was called, this is a fast no-op
        parent = str(path.parent)
        if parent not in self._created_dirs:
            with self._created_dirs_lock:
                if parent not in self._created_dirs:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(parent)

        if self._fast_writes:
            # Direct write (faster, not crash-safe) - used in dev server mode
            path.write_text(content, encoding="utf-8")
        else:
            # Atomic write with fast temp file naming (counter instead of uuid4)
            self._atomic_write_fast(path, content)

    def _atomic_write_fast(self, path: Path, content: str) -> None:
        """Atomic write using counter-based temp file names.

        Faster than uuid4-based naming while maintaining crash safety.
        Uses PID + thread ID + atomic counter for uniqueness.

        Args:
            path: Destination path
            content: File content
        """
        # Use atomic counter instead of uuid4 (faster)
        pid = os.getpid()
        tid = threading.get_ident()
        counter = next(_temp_file_counter)
        tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{counter}.tmp"

        try:
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(path)  # Atomic rename on POSIX
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    def flush_and_close(self, timeout: float = 30.0) -> int:
        """Wait for all queued writes to complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Number of files written

        Raises:
            BengalRenderingError: If writer threads failed or timed out
        """
        # Signal shutdown
        self._shutdown.set()
        self._queue.put(None)  # Sentinel to wake up one thread, which propagates

        # Wait for all threads
        per_thread_timeout = timeout / max(len(self._writer_threads), 1)
        timed_out = False
        for thread in self._writer_threads:
            thread.join(timeout=per_thread_timeout)
            if thread.is_alive():
                timed_out = True

        if timed_out:
            alive_count = sum(1 for t in self._writer_threads if t.is_alive())
            raise BengalRenderingError(
                f"{alive_count} writer thread(s) did not complete within {timeout}s",
                code=ErrorCode.R010,
                suggestion="Increase timeout or check for slow disk I/O",
            )

        if self._error:
            raise BengalRenderingError(
                f"Background writer thread failed: {self._error}",
                code=ErrorCode.R010,
                original_error=self._error,
                suggestion="Check disk space and file permissions in output directory",
            ) from self._error

        return self._writes_completed

    @property
    def pending_count(self) -> int:
        """Number of items waiting in queue."""
        return self._queue.qsize()

    @property
    def completed_count(self) -> int:
        """Number of writes completed."""
        return self._writes_completed
