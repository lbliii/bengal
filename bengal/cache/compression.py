"""
Cache compression utilities using Zstandard (PEP 784).

Python 3.14+ stdlib compression.zstd module for cache file compression.
Provides transparent compression/decompression with backward compatibility.

Performance (from spike benchmarks):
    - Compression ratio: 12-14x on typical cache files
    - Size savings: 92-93%
    - Compress time: <1ms for typical files
    - Decompress time: <0.3ms for typical files

Related:
    - plan/active/rfc-zstd-cache-compression.md - RFC with benchmarks
    - bengal/cache/cache_store.py - Uses these utilities
    - bengal/cache/build_cache.py - Uses these utilities
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Optimal compression level based on spike results
# Level 3: 93% savings, <1ms compress, <0.3ms decompress
# Level 1: Slightly faster, similar savings (92%)
# Level 6+: Diminishing returns, slower
COMPRESSION_LEVEL = 3

# Try to import compression.zstd (Python 3.14+)
# Fallback to zstandard package if available
# Fallback to mock if neither (allows running in older environments)
try:
    # Try stdlib first (Python 3.14+)
    from compression import zstd

    # Re-export ZstdError
    ZstdError: type[Exception] = zstd.ZstdError

except ImportError:
    try:
        # Try PyPI package
        import zstandard as zstd  # type: ignore

        # Re-export ZstdError
        ZstdError = zstd.ZstdError  # type: ignore[no-redef]

    except ImportError:
        # Fallback mock for environments without zstd
        logger.warning("zstd_not_available_using_mock", reason="compression_module_missing")

        class MockZstd:
            @staticmethod
            def compress(data: bytes, level: int = 3) -> bytes:
                return data

            @staticmethod
            def decompress(data: bytes) -> bytes:
                return data

            class ZstdError(Exception):
                pass

        zstd = MockZstd()  # type: ignore[assignment]
        ZstdError = MockZstd.ZstdError  # type: ignore[no-redef]


def save_compressed(data: dict[str, Any], path: Path, level: int = COMPRESSION_LEVEL) -> int:
    """
    Save data as compressed JSON (.json.zst).

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
    json_bytes = json.dumps(data, separators=(",", ":"), default=str).encode("utf-8")
    original_size = len(json_bytes)

    # Compress with Zstandard
    compressed = zstd.compress(json_bytes, level=level)
    compressed_size = len(compressed)

    # Write atomically
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compressed)

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
        zstd.ZstdError: If decompression fails
        json.JSONDecodeError: If JSON is invalid
    """
    compressed = path.read_bytes()
    json_bytes = zstd.decompress(compressed)
    data = json.loads(json_bytes)

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
        return load_compressed(compressed_path)

    # Fall back to uncompressed JSON
    json_path = path if path.suffix == ".json" else path.with_suffix(".json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))

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
        logger.warning(
            "cache_migration_failed",
            path=str(json_path),
            error=str(e),
        )
        return None
