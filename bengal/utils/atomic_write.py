"""
Atomic file writing utilities.

Provides crash-safe file writes using the write-to-temp-then-rename pattern.
This ensures files are never left in a partially written state.

If a process crashes during write, the original file (if any) remains intact.
Files are always either in their old complete state or new complete state,
never partially written.

Example:
    >>> from bengal.utils.atomic_write import atomic_write_text
    >>> atomic_write_text('output.html', '<html>...</html>')
    # If crash occurs during write:
    # - output.html is either old version (if existed) or missing
    # - Never partially written!
"""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import IO, Any


def atomic_write_text(
    path: Path | str,
    content: str,
    encoding: str = "utf-8",
    mode: int | None = None,
    *,
    ensure_parent: bool = True,
) -> None:
    """
    Write text to a file atomically.

    Uses write-to-temp-then-rename to ensure the file is never partially written.
    If the process crashes during write, the original file (if any) remains intact.

    The rename operation is atomic on POSIX systems (Linux, macOS), meaning it
    either completely succeeds or completely fails - there's no partial state.

    Args:
        path: Destination file path
        content: Text content to write
        encoding: Text encoding (default: utf-8)
        mode: File permissions (default: None, keeps system default)

    Raises:
        OSError: If write or rename fails

    Example:
        >>> atomic_write_text('output.html', '<html>...</html>')
        >>> atomic_write_text('data.json', json.dumps(data), encoding='utf-8')
    """
    path = Path(path)

    # Ensure parent directory exists (defensive; callers should ensure this but we harden here).
    # Hot path optimization: some callers already create parent dirs with caching;
    # allow them to skip the redundant mkdir syscalls.
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    # Create unique temp file in same directory (ensures same filesystem for atomic rename)
    # Use PID + thread ID + UUID to prevent race conditions in parallel builds
    pid = os.getpid()
    tid = threading.get_ident()
    unique_id = uuid.uuid4().hex[:8]
    tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{unique_id}.tmp"

    try:
        # Write to temp file
        tmp_path.write_text(content, encoding=encoding)

        # Set permissions if specified
        if mode is not None:
            os.chmod(tmp_path, mode)

        # Atomic rename (POSIX guarantees atomicity)
        # On Windows, replace() handles the case where target exists
        tmp_path.replace(path)

    except Exception:
        # Clean up temp file on any error
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_bytes(path: Path | str, content: bytes, mode: int | None = None) -> None:
    """
    Write binary data to a file atomically.

    Args:
        path: Destination file path
        content: Binary content to write
        mode: File permissions (default: None, keeps system default)

    Raises:
        OSError: If write or rename fails

    Example:
        >>> atomic_write_bytes('image.png', image_data)
    """
    path = Path(path)
    # Ensure parent directory exists (defensive; callers may choose to skip this for hot paths)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create unique temp file to prevent race conditions
    pid = os.getpid()
    tid = threading.get_ident()
    unique_id = uuid.uuid4().hex[:8]
    tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{unique_id}.tmp"

    try:
        tmp_path.write_bytes(content)

        if mode is not None:
            os.chmod(tmp_path, mode)

        tmp_path.replace(path)

    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


class AtomicFile:
    """
    Context manager for atomic file writing.

    Useful when you need to write incrementally or use file handle directly
    (e.g., with json.dump(), ElementTree.write(), etc.).

    The file is written to a temporary location, then atomically renamed
    on successful completion. If an exception occurs, the temp file is
    cleaned up and the original file remains unchanged.

    Example:
        >>> with AtomicFile('output.json', 'w') as f:
        ...     json.dump(data, f)
        # File is atomically renamed on successful __exit__

        >>> with AtomicFile('sitemap.xml', 'wb') as f:
        ...     tree.write(f, encoding='utf-8')
    """

    def __init__(
        self, path: Path | str, mode: str = "w", encoding: str | None = "utf-8", **kwargs: Any
    ) -> None:
        """
        Initialize atomic file writer.

        Args:
            path: Destination file path
            mode: File open mode ('w', 'wb', 'a', etc.)
            encoding: Text encoding (default: utf-8, ignored for binary modes)
            **kwargs: Additional arguments passed to open()
        """
        self.path = Path(path)
        self.mode = mode
        self.encoding = encoding if "b" not in mode else None
        self.kwargs = kwargs

        # Create unique temp file to prevent race conditions
        pid = os.getpid()
        tid = threading.get_ident()
        unique_id = uuid.uuid4().hex[:8]
        self.tmp_path = self.path.parent / f".{self.path.name}.{pid}.{tid}.{unique_id}.tmp"
        self.file: IO[Any] | None = None

    def __enter__(self) -> IO[Any]:
        """Open temp file for writing."""
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        open_kwargs: dict[str, Any] = {}
        if self.encoding:
            open_kwargs["encoding"] = self.encoding
        open_kwargs.update(self.kwargs)

        self.file = open(self.tmp_path, self.mode, **open_kwargs)
        return self.file

    def __exit__(self, exc_type: type[BaseException] | None, *args: Any) -> None:
        """Close temp file and rename atomically if successful."""
        if self.file:
            self.file.close()

        # If exception occurred, clean up and don't rename
        if exc_type is not None:
            self.tmp_path.unlink(missing_ok=True)
            return

        # Success - rename atomically
        self.tmp_path.replace(self.path)
