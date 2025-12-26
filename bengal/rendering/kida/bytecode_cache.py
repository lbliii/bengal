"""Template Bytecode Cache.

Persists compiled template code objects to disk for near-instant
cold-start loading. Uses marshal for code object serialization.

Cache Invalidation:
    Uses source hash in filename. When source changes, hash changes,
    and old cache entry becomes orphan (cleaned up lazily).

Thread-Safety:
    File writes use atomic rename pattern to prevent corruption.
    Multiple processes can safely share the cache directory.

Example:
    >>> from pathlib import Path
    >>> from bengal.rendering.kida.bytecode_cache import BytecodeCache, hash_source
    >>>
    >>> cache = BytecodeCache(Path(".bengal-cache/kida"))
    >>>
    >>> # Check cache
    >>> code = cache.get("base.html", source_hash)
    >>> if code is None:
    ...     code = compile_template(source)
    ...     cache.set("base.html", source_hash, code)
    >>>
    >>> # Cache stats
    >>> stats = cache.stats()
    >>> print(f"Cached: {stats['file_count']} templates")
"""

from __future__ import annotations

import hashlib
import marshal
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import CodeType

# Python version tag for cache invalidation across Python upgrades
_PY_VERSION_TAG = f"py{sys.version_info.major}{sys.version_info.minor}"


class BytecodeCache:
    """Persist compiled template bytecode to disk.

    Uses marshal for code object serialization (Python stdlib).

    Thread-Safety:
        File writes use atomic rename pattern to prevent corruption.
        Multiple processes can safely share the cache directory.

    Cache Invalidation:
        Uses source hash in filename. When source changes, hash changes,
        and old cache entry becomes orphan (cleaned up lazily).

    Example:
        >>> cache = BytecodeCache(Path(".bengal-cache/kida"))
        >>>
        >>> # Miss: compile and cache
        >>> code = cache.get("base.html", source_hash)
        >>> if code is None:
        ...     code = compile_template(source)
        ...     cache.set("base.html", source_hash, code)
        >>>
        >>> # Hit: instant load
        >>> code = cache.get("base.html", source_hash)
    """

    def __init__(
        self,
        directory: Path,
        pattern: str = "__kida_{version}_{name}_{hash}.pyc",
    ):
        """Initialize bytecode cache.

        Args:
            directory: Cache directory (created if missing)
            pattern: Filename pattern with {version}, {name}, {hash} placeholders
        """
        self._dir = directory
        self._pattern = pattern
        self._dir.mkdir(parents=True, exist_ok=True)

    def _make_path(self, name: str, source_hash: str) -> Path:
        """Generate cache file path.

        Includes Python version in filename to prevent cross-version
        bytecode incompatibility (marshal format is version-specific).
        """
        # Sanitize name for filesystem
        safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        filename = self._pattern.format(
            version=_PY_VERSION_TAG,
            name=safe_name,
            hash=source_hash[:16],
        )
        return self._dir / filename

    def get(self, name: str, source_hash: str) -> CodeType | None:
        """Load cached bytecode if available.

        Args:
            name: Template name
            source_hash: Hash of template source (for invalidation)

        Returns:
            Compiled code object, or None if not cached
        """
        path = self._make_path(name, source_hash)

        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                return marshal.load(f)
        except (OSError, ValueError, EOFError):
            # Corrupted or incompatible cache file
            import contextlib

            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
            return None

    def set(self, name: str, source_hash: str, code: CodeType) -> None:
        """Cache compiled bytecode.

        Args:
            name: Template name
            source_hash: Hash of template source
            code: Compiled code object
        """
        path = self._make_path(name, source_hash)
        tmp_path = path.with_suffix(".tmp")

        try:
            # Write to temp file first (atomic pattern)
            with open(tmp_path, "wb") as f:
                marshal.dump(code, f)

            # Atomic rename
            tmp_path.rename(path)
        except OSError:
            # Best effort - caching failure shouldn't break compilation
            import contextlib

            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)

    def clear(self, current_version_only: bool = False) -> int:
        """Remove cached bytecode.

        Args:
            current_version_only: If True, only clear current Python version's cache

        Returns:
            Number of files removed
        """
        count = 0
        pattern = f"__kida_{_PY_VERSION_TAG}_*.pyc" if current_version_only else "__kida_*.pyc"
        for path in self._dir.glob(pattern):
            try:
                path.unlink(missing_ok=True)
                count += 1
            except OSError:
                pass
        return count

    def cleanup(self, max_age_days: int = 30) -> int:
        """Remove orphaned cache files older than max_age_days.
        
        Orphaned files are cache entries that are no longer referenced by
        active templates (e.g., after source changes or template deletion).
        
        Args:
            max_age_days: Maximum age in days before removal (default: 30)
            
        Returns:
            Number of files removed
            
        Example:
            >>> cache = BytecodeCache(Path(".bengal-cache/kida"))
            >>> removed = cache.cleanup(max_age_days=7)  # Remove files older than 7 days
            >>> print(f"Removed {removed} orphaned cache files")
        """
        threshold = time.time() - (max_age_days * 86400)
        count = 0
        
        for path in self._dir.glob("__kida_*.pyc"):
            try:
                if path.stat().st_mtime < threshold:
                    path.unlink(missing_ok=True)
                    count += 1
            except OSError:
                # Skip files that can't be accessed (permissions, etc.)
                pass
                
        return count

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with file_count, total_bytes
        """
        files = list(self._dir.glob("__kida_*.pyc"))
        total_bytes = sum(f.stat().st_size for f in files if f.exists())

        return {
            "file_count": len(files),
            "total_bytes": total_bytes,
        }


def hash_source(source: str) -> str:
    """Generate hash of template source for cache key."""
    return hashlib.sha256(source.encode()).hexdigest()
