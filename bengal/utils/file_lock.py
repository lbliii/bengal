"""
File locking utilities for concurrent build safety.

Provides cross-platform file locking to prevent cache corruption when
multiple build processes run simultaneously.

On Unix/macOS: Uses fcntl.flock()
On Windows: Uses msvcrt.locking()

Example:
    >>> from bengal.utils.file_lock import file_lock
    >>> with file_lock(cache_path, exclusive=True):
    ...     # Safely read/write cache
    ...     cache.save(cache_path)
"""

from __future__ import annotations

import errno
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from bengal.errors import BengalCacheError
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Lock timeout in seconds
DEFAULT_LOCK_TIMEOUT = 30


class LockAcquisitionError(BengalCacheError):
    """
    Raised when a lock cannot be acquired within the timeout.

    Extends BengalCacheError for consistent error handling.
    """

    pass


@contextmanager
def file_lock(
    path: Path,
    exclusive: bool = True,
    timeout: float = DEFAULT_LOCK_TIMEOUT,
) -> Generator[None]:
    """
    Context manager for file locking.

    Acquires a lock on a .lock file adjacent to the target path.
    Uses non-blocking attempts with retry for better timeout control.

    Args:
        path: Path to the file to lock (lock file will be path.lock)
        exclusive: If True, acquire exclusive (write) lock; else shared (read) lock
        timeout: Maximum seconds to wait for lock (default: 30)

    Yields:
        None

    Raises:
        LockAcquisitionError: If lock cannot be acquired within timeout

    Example:
        >>> with file_lock(Path("cache.json"), exclusive=True):
        ...     # Safely write to cache
        ...     data = load_cache()
        ...     save_cache(data)
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Open lock file (create if doesn't exist)
    with open(lock_path, "w") as lock_file:
        _acquire_lock(lock_file, exclusive, timeout, lock_path)
        yield
        _release_lock(lock_file)


def _acquire_lock(
    lock_file: IO[str],
    exclusive: bool,
    timeout: float,
    lock_path: Path,
) -> None:
    """
    Acquire a lock with timeout using non-blocking retries.

    Args:
        lock_file: Open file handle for the lock file
        exclusive: If True, acquire exclusive lock; else shared lock
        timeout: Maximum seconds to wait
        lock_path: Path to lock file (for logging)

    Raises:
        LockAcquisitionError: If lock cannot be acquired within timeout
    """
    start_time = time.monotonic()
    retry_interval = 0.1  # Start with 100ms retries
    max_retry_interval = 1.0  # Cap at 1 second
    last_log_second = 0  # Track last logged second to log once per second

    while True:
        try:
            _try_lock_nonblocking(lock_file, exclusive)
            return  # Lock acquired!
        except BlockingIOError as err:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                raise LockAcquisitionError(
                    f"Could not acquire {'exclusive' if exclusive else 'shared'} lock on {lock_path} after {timeout}s. "
                    "Another build process may be running.",
                    file_path=lock_path,
                    suggestion="Wait for the other build process to finish, or remove the lock file if the process has terminated.",
                    original_error=err,
                ) from err

            # Log contention once per second (not on every retry)
            current_second = int(elapsed)
            if current_second > last_log_second:
                last_log_second = current_second
                logger.debug(
                    "lock_contention",
                    lock_path=str(lock_path),
                    elapsed_seconds=elapsed,
                    timeout=timeout,
                )

            # Exponential backoff with cap
            time.sleep(retry_interval)
            retry_interval = min(retry_interval * 1.5, max_retry_interval)


def _try_lock_nonblocking(lock_file: IO[str], exclusive: bool) -> None:
    """
    Try to acquire lock without blocking.

    Args:
        lock_file: Open file handle
        exclusive: If True, acquire exclusive lock

    Raises:
        BlockingIOError: If lock is held by another process
    """
    if sys.platform == "win32":
        _lock_windows(lock_file, exclusive, blocking=False)
    else:
        _lock_unix(lock_file, exclusive, blocking=False)


def _lock_unix(lock_file: IO[str], exclusive: bool, blocking: bool) -> None:
    """
    Acquire lock on Unix/macOS using fcntl.flock().

    Args:
        lock_file: Open file handle
        exclusive: If True, acquire exclusive (LOCK_EX); else shared (LOCK_SH)
        blocking: If False, raise BlockingIOError if lock unavailable

    Raises:
        BlockingIOError: If non-blocking and lock is held by another process
    """
    import fcntl

    lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    if not blocking:
        lock_type |= fcntl.LOCK_NB

    try:
        fcntl.flock(lock_file.fileno(), lock_type)
    except OSError as e:
        # EAGAIN or EWOULDBLOCK indicates lock is held by another process
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise BlockingIOError(f"Lock is held by another process: {e}") from e
        raise


def _lock_windows(lock_file: IO[str], exclusive: bool, blocking: bool) -> None:
    """
    Acquire lock on Windows using msvcrt.locking().

    Args:
        lock_file: Open file handle
        exclusive: If True, acquire exclusive lock (always exclusive on Windows)
        blocking: If False, raise BlockingIOError if lock unavailable

    Raises:
        BlockingIOError: If non-blocking and lock is held by another process
    """
    import msvcrt

    # Windows doesn't support shared locks with msvcrt.locking
    # LK_NBLCK = 2 (non-blocking), LK_LOCK = 1 (blocking)
    lock_mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK  # type: ignore[attr-defined]

    try:
        # Lock first byte (signals file is locked)
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), lock_mode, 1)  # type: ignore[attr-defined]
    except OSError as e:
        if e.errno == 36:  # EDEADLOCK - resource busy
            raise BlockingIOError(f"Lock is held by another process: {e}") from e
        raise


def _release_lock(lock_file: IO[str]) -> None:
    """
    Release lock on the file.

    Args:
        lock_file: Open file handle with lock
    """
    if sys.platform == "win32":
        _unlock_windows(lock_file)
    else:
        _unlock_unix(lock_file)


def _unlock_unix(lock_file: IO[str]) -> None:
    """Release Unix/macOS lock."""
    import contextlib
    import fcntl

    with contextlib.suppress(OSError):
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _unlock_windows(lock_file: IO[str]) -> None:
    """Release Windows lock."""
    import msvcrt

    try:
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
    except OSError:
        pass  # Ignore unlock errors


def is_locked(path: Path) -> bool:
    """
    Check if a file is currently locked.

    Args:
        path: Path to check

    Returns:
        True if file appears to be locked by another process
    """
    lock_path = path.with_suffix(path.suffix + ".lock")

    if not lock_path.exists():
        return False

    try:
        with open(lock_path, "w") as lock_file:
            _try_lock_nonblocking(lock_file, exclusive=True)
            # Successfully acquired lock, so it wasn't locked
            _release_lock(lock_file)
            return False
    except BlockingIOError:
        return True
    except OSError:
        # Can't open lock file, assume not locked
        return False


def remove_stale_lock(path: Path, max_age_seconds: float = 3600) -> bool:
    """
    Remove a stale lock file that may have been left by a crashed process.

    Args:
        path: Path to the file (not the lock file)
        max_age_seconds: Maximum age in seconds before considering stale

    Returns:
        True if stale lock was removed
    """
    lock_path = path.with_suffix(path.suffix + ".lock")

    if not lock_path.exists():
        return False

    try:
        stat = lock_path.stat()
        age = time.time() - stat.st_mtime

        if age > max_age_seconds:
            logger.warning(
                "removing_stale_lock",
                lock_path=str(lock_path),
                age_seconds=age,
                max_age_seconds=max_age_seconds,
            )
            lock_path.unlink()
            return True
    except OSError:
        pass

    return False
