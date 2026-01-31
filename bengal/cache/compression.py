"""
Cache compression utilities using Zstandard (PEP 784).

This module leverages the Python 3.14+ standard library `compression.zstd` module
for high-performance cache file compression. Zstandard provides superior
compression ratios (92-93% savings) with sub-millisecond overhead.

Performance (from spike benchmarks):
- Compression ratio: 12-14x on typical cache files
- Size savings: 92-93%
- Compress time: <1ms for typical files
- Decompress time: <0.3ms for typical files

Related:
- plan/drafted/rfc-kida-modernization-314-315.md - Modernization RFC
- bengal/cache/cache_store.py - Uses these utilities
- bengal/cache/build_cache/core.py - Uses these utilities

"""

from __future__ import annotations

import json
import os
import tempfile
from compression import zstd
from pathlib import Path
from typing import Any, cast

from bengal.cache.version import (
    prepend_cache_header,
    validate_cache_header,
)
from bengal.errors.codes import ErrorCode
from bengal.errors.exceptions import BengalCacheError
from bengal.errors.session import record_error
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Optimal compression level based on spike results
# Level 3: 93% savings, <1ms compress, <0.3ms decompress
# Level 1: Slightly faster, similar savings (92%)
# Level 6+: Diminishing returns, slower
COMPRESSION_LEVEL = 3

# Re-export ZstdError for convenience
ZstdError = zstd.ZstdError


def save_compressed(data: dict[str, Any], path: Path, level: int = COMPRESSION_LEVEL) -> int:
    """
    Save data as compressed JSON (.json.zst) with atomic write.

    Args:
        data: Dictionary to serialize
        path: Output path (should end in .json.zst)
        level: Compression level 1-22 (default: 3)

    Returns:
        Number of bytes written (compressed size)

    Raises:
        OSError: If file cannot be written
        TypeError: If data is not JSON-serializable

    """
    # Serialize to compact JSON (no indentation).
    #
    # Cache payloads must be resilient: prefer best-effort serialization to avoid
    # disabling incremental builds if a value is not strictly JSON-native.
    # Uses to_jsonable to handle dataclasses and module reloads in dev server.
    from bengal.utils.serialization import to_jsonable

    json_bytes = json.dumps(data, separators=(",", ":"), default=to_jsonable).encode("utf-8")
    original_size = len(json_bytes)

    # Compress with Zstandard (PEP 784)
    compressed = zstd.compress(json_bytes, level=level)

    # Prepend magic header for version validation
    versioned = prepend_cache_header(compressed)
    compressed_size = len(versioned)

    # Atomic write: write to temp file, then rename
    # This prevents corrupted cache files on crash during write
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (ensures same filesystem for atomic rename)
    fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(versioned)
        # Atomic rename (POSIX guarantees this is atomic on same filesystem)
        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

    ratio = original_size / compressed_size if compressed_size > 0 else 0
    logger.debug(
        "cache_compressed",
        path=path.name,
        original_bytes=original_size,
        compressed_bytes=compressed_size,
        ratio=f"{ratio:.1f}x",
    )

    return compressed_size


def load_compressed(path: Path) -> dict[str, Any]:
    """
    Load compressed JSON (.json.zst).

    Args:
        path: Path to compressed cache file

    Returns:
        Deserialized dictionary

    Raises:
        FileNotFoundError: If path doesn't exist
        BengalCacheError: If cache version is incompatible (code A002)
        zstd.ZstdError: If decompression fails
        json.JSONDecodeError: If JSON is invalid

    """
    compressed = path.read_bytes()

    # Validate magic header before decompression
    is_valid, remaining = validate_cache_header(compressed)
    if not is_valid:
        # Create error and record in session for tracking
        error = BengalCacheError(
            f"Incompatible cache version or magic header: {path}. "
            "Delete .bengal/ directory to rebuild cache with current version.",
            code=ErrorCode.A002,
        )
        record_error(error, file_path=str(path))
        raise error

    # Decompress with Zstandard (PEP 784)
    json_bytes = zstd.decompress(remaining)
    data = json.loads(json_bytes)

    # Validate type to prevent 'str' object has no attribute 'get' errors
    if not isinstance(data, dict):
        error = BengalCacheError(
            f"Cache file {path} contains invalid data type: {type(data).__name__}. "
            "Expected dict. Delete .bengal/ directory to rebuild cache.",
            code=ErrorCode.A001,  # cache_corruption
        )
        record_error(error, file_path=str(path))
        raise error

    logger.debug(
        "cache_decompressed",
        path=path.name,
        compressed_bytes=len(compressed),
        original_bytes=len(json_bytes),
    )

    return cast(dict[str, Any], data)


def detect_format(path: Path) -> str:
    """
    Detect cache file format by extension.

    Args:
        path: Path to cache file

    Returns:
        "zstd" for .json.zst files, "json" for .json files, "unknown" otherwise

    """
    name = path.name
    if name.endswith(".json.zst"):
        return "zstd"
    elif name.endswith(".json"):
        return "json"
    return "unknown"


def get_compressed_path(json_path: Path) -> Path:
    """
    Get the compressed path for a JSON cache file.

    Args:
        json_path: Original JSON path (e.g., .bengal/cache.json)

    Returns:
        Compressed path (e.g., .bengal/cache.json.zst)

    """
    if json_path.name.endswith(".json.zst"):
        return json_path
    return json_path.with_suffix(".json.zst")


def get_json_path(compressed_path: Path) -> Path:
    """
    Get the JSON path for a compressed cache file.

    Args:
        compressed_path: Compressed path (e.g., .bengal/cache.json.zst)

    Returns:
        JSON path (e.g., .bengal/cache.json)

    """
    name = compressed_path.name
    if name.endswith(".json.zst"):
        return compressed_path.parent / name[:-4]  # Remove .zst
    return compressed_path


def load_auto(path: Path) -> dict[str, Any]:
    """
    Load cache file with automatic format detection.

    Tries compressed format first (.json.zst), falls back to JSON (.json).
    This enables seamless migration from uncompressed to compressed caches.

    Args:
        path: Base path (without .zst extension)

    Returns:
        Deserialized dictionary

    Raises:
        FileNotFoundError: If neither compressed nor JSON file exists

    """
    # Try compressed first
    compressed_path = get_compressed_path(path)
    if compressed_path.exists():
        try:
            return load_compressed(compressed_path)
        except BengalCacheError as e:
            # Check if it's a version error (code A002) - fallback to JSON
            if e.code == ErrorCode.A002:
                # Incompatible version - fallback to JSON or re-raise if no JSON
                logger.debug("compressed_cache_incompatible", path=str(compressed_path))
            else:
                # Other cache errors - re-raise
                raise

    # Fall back to uncompressed JSON
    json_path = path if path.suffix == ".json" else path.with_suffix(".json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise BengalCacheError(
                    f"Cache file contains invalid data type: {type(data).__name__}",
                    code=ErrorCode.A001,
                    file_path=json_path,
                    suggestion="Clear the cache with: rm -rf .bengal/cache/",
                )
            return cast(dict[str, Any], data)

    raise FileNotFoundError(f"Cache file not found: {path} (tried .json.zst and .json)")


def migrate_to_compressed(json_path: Path, remove_original: bool = True) -> Path | None:
    """
    Migrate an uncompressed JSON cache file to compressed format.

    Args:
        json_path: Path to uncompressed JSON file
        remove_original: Whether to remove the original JSON file after migration

    Returns:
        Path to compressed file, or None if migration failed/not needed

    """
    if not json_path.exists():
        return None

    if not json_path.name.endswith(".json"):
        return None

    try:
        # Load uncompressed
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        # Save compressed
        compressed_path = get_compressed_path(json_path)
        save_compressed(data, compressed_path)

        # Remove original if requested
        if remove_original:
            json_path.unlink()
            logger.info(
                "cache_migrated",
                from_path=json_path.name,
                to_path=compressed_path.name,
            )

        return compressed_path

    except (json.JSONDecodeError, OSError) as e:
        from bengal.errors import ErrorCode

        logger.warning(
            "cache_migration_failed",
            path=str(json_path),
            error=str(e),
            error_code=ErrorCode.A004.value,  # cache_write_error
        )
        return None
