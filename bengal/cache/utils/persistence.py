"""
Persistent cache mixin for standardized load/save with compression.

Provides a common pattern for cache classes that need:
- Zstandard compression (.json.zst)
- Version checking with graceful fallback
- Auto-detection of compressed vs uncompressed formats
- Standardized error handling with ErrorCodes

Usage:
    class MyCache(PersistentCacheMixin):
        VERSION = 2

        def __init__(self, cache_path: Path):
            self.cache_path = cache_path
            self.entries: dict[str, MyEntry] = {}
            self._load_cache()

        def _deserialize(self, data: dict[str, Any]) -> None:
            for key, entry_data in data.get("entries", {}).items():
                self.entries[key] = MyEntry.from_cache_dict(entry_data)

        def _serialize(self) -> dict[str, Any]:
            return {
                "entries": {k: v.to_cache_dict() for k, v in self.entries.items()},
            }

"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


@runtime_checkable
class PersistentCache(Protocol):
    """Protocol for persistent cache classes."""

    VERSION: int
    cache_path: Path

    def _deserialize(self, data: dict[str, Any]) -> None:
        """Deserialize loaded data into cache state."""
        ...

    def _serialize(self) -> dict[str, Any]:
        """Serialize cache state for saving."""
        ...

    def _on_version_mismatch(self) -> None:
        """Called when version mismatch occurs (clear state)."""
        ...


class PersistentCacheMixin:
    """
    Mixin providing standardized load/save with compression and versioning.

    Subclasses must:
    - Define VERSION class attribute
    - Set self.cache_path in __init__
    - Implement _deserialize(data: dict) to restore state
    - Implement _serialize() -> dict to create save data
    - Implement _on_version_mismatch() to clear state on version change

    Features:
    - Auto-detects .json.zst (compressed) vs .json (uncompressed)
    - Version checking with graceful fallback
    - Standardized error handling with ErrorCodes
    - Atomic writes via save_compressed

    """

    # Subclass must define
    VERSION: int
    cache_path: Path

    def _load_cache(self) -> None:
        """
        Load cache from disk with auto-detection and version checking.

        Tries compressed (.json.zst) first, falls back to uncompressed (.json).
        On version mismatch or errors, calls _on_version_mismatch() and continues.
        """
        compressed_path = self.cache_path.with_suffix(".json.zst")

        if not compressed_path.exists() and not self.cache_path.exists():
            logger.debug(
                "cache_not_found",
                cache_type=type(self).__name__,
                path=str(self.cache_path),
            )
            return

        try:
            from bengal.cache.compression import load_auto

            data = load_auto(self.cache_path)

            # Version check
            from bengal.errors import ErrorCode

            file_version = data.get("version")
            if file_version != self.VERSION:
                logger.warning(
                    "cache_version_mismatch",
                    cache_type=type(self).__name__,
                    expected=self.VERSION,
                    found=file_version,
                    action="rebuilding_cache",
                    error_code=ErrorCode.A002.value,
                )
                self._on_version_mismatch()
                return

            # Deserialize
            self._deserialize(data)

            logger.info(
                "cache_loaded",
                cache_type=type(self).__name__,
                path=str(self.cache_path),
            )

        except Exception as e:
            from bengal.errors import ErrorCode

            logger.warning(
                "cache_load_failed",
                cache_type=type(self).__name__,
                error=str(e),
                path=str(self.cache_path),
                error_code=ErrorCode.A003.value,
                suggestion="Cache will be rebuilt automatically.",
            )
            self._on_version_mismatch()

    def _save_cache(self) -> None:
        """
        Save cache to disk with compression.

        Uses Zstandard compression for 92-93% size reduction.
        Atomic writes prevent corruption on crash/interruption.
        """
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            data = {"version": self.VERSION, **self._serialize()}

            from bengal.cache.compression import save_compressed

            compressed_path = self.cache_path.with_suffix(".json.zst")
            save_compressed(data, compressed_path)

            logger.info(
                "cache_saved",
                cache_type=type(self).__name__,
                path=str(self.cache_path),
            )

        except Exception as e:
            from bengal.errors import ErrorCode

            logger.error(
                "cache_save_failed",
                cache_type=type(self).__name__,
                error=str(e),
                path=str(self.cache_path),
                error_code=ErrorCode.A004.value,
                suggestion="Check disk space and permissions.",
            )

    def _deserialize(self, data: dict[str, Any]) -> None:
        """Deserialize loaded data into cache state. Override in subclass."""
        raise NotImplementedError("Subclass must implement _deserialize")

    def _serialize(self) -> dict[str, Any]:
        """Serialize cache state for saving. Override in subclass."""
        raise NotImplementedError("Subclass must implement _serialize")

    def _on_version_mismatch(self) -> None:
        """Called when version mismatch occurs. Override to clear state."""
        raise NotImplementedError("Subclass must implement _on_version_mismatch")
