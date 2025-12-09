"""
File fingerprint for fast change detection.

Provides FileFingerprint dataclass for tracking file changes via mtime + size
with optional hash verification. Part of the build cache system.

Key Concepts:
    - Fast path: mtime + size comparison (single stat call, no file read)
    - Slow path: SHA256 hash only when mtime/size mismatch detected
    - Handles edge cases: touch/rsync may change mtime but not content

Related Modules:
    - bengal.cache.build_cache: Main BuildCache using FileFingerprint
    - bengal.orchestration.incremental: Incremental build logic

See Also:
    - plan/active/rfc-orchestrator-performance-improvements.md: Performance RFC
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bengal.utils.hashing import hash_file
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileFingerprint:
    """
    Fast file change detection using mtime + size, with optional hash verification.

    Performance Optimization:
        - mtime + size comparison is O(1) stat call (no file read)
        - Hash computed lazily only when mtime/size mismatch detected
        - Handles edge cases like touch/rsync that change mtime but not content

    Attributes:
        mtime: File modification time (seconds since epoch)
        size: File size in bytes
        hash: SHA256 hash (computed lazily, may be None for fast path)

    Thread Safety:
        Immutable after creation. Thread-safe for read operations.
    """

    mtime: float
    size: int
    hash: str | None = None

    def matches_stat(self, stat_result: os.stat_result) -> bool:
        """
        Fast path check: does mtime + size match?

        Args:
            stat_result: Result from Path.stat()

        Returns:
            True if mtime and size both match (definitely unchanged)
        """
        return self.mtime == stat_result.st_mtime and self.size == stat_result.st_size

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {"mtime": self.mtime, "size": self.size, "hash": self.hash}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileFingerprint:
        """Deserialize from JSON dict."""
        return cls(
            mtime=data.get("mtime", 0.0),
            size=data.get("size", 0),
            hash=data.get("hash"),
        )

    @classmethod
    def from_path(cls, file_path: Path, compute_hash: bool = True) -> FileFingerprint:
        """
        Create fingerprint from file path.

        Args:
            file_path: Path to file
            compute_hash: Whether to compute SHA256 hash (slower but more reliable)

        Returns:
            FileFingerprint with mtime, size, and optionally hash
        """
        stat = file_path.stat()
        file_hash = None

        if compute_hash:
            try:
                file_hash = hash_file(file_path)
            except Exception as e:
                # Hash will be None, rely on mtime/size (graceful degradation)
                logger.debug("file_hash_computation_failed", path=str(file_path), error=str(e))

        return cls(mtime=stat.st_mtime, size=stat.st_size, hash=file_hash)
