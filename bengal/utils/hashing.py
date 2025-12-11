"""
Cryptographic hashing utilities for Bengal.

Provides standardized hashing for file fingerprinting, cache keys,
and content-addressable storage.

Example:

```python
from bengal.utils.hashing import hash_str, hash_file, hash_dict

# Hash string content
key = hash_str("hello world")  # "b94d27b9..."

# Hash with truncation (for fingerprints)
fingerprint = hash_str("hello world", truncate=8)  # "b94d27b9"

# Hash file content
file_hash = hash_file(Path("content/post.md"))

# Hash dict deterministically
config_hash = hash_dict({"key": "value", "nested": [1, 2, 3]})
```

Related Modules:
    - bengal.cache.build_cache: Uses for file fingerprinting
    - bengal.core.asset: Asset fingerprinting
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_str(
    content: str,
    truncate: int | None = None,
    algorithm: str = "sha256",
) -> str:
    """
    Hash string content using specified algorithm.

    Args:
        content: String content to hash
        truncate: Truncate result to N characters (None = full hash)
        algorithm: Hash algorithm ('sha256', 'md5')

    Returns:
        Hex digest of hash, optionally truncated

    Examples:
        >>> hash_str("hello")
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
        >>> hash_str("hello", truncate=16)
        '2cf24dba5fb0a30e'
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode("utf-8"))
    digest = hasher.hexdigest()
    return digest[:truncate] if truncate else digest


def hash_bytes(
    content: bytes,
    truncate: int | None = None,
    algorithm: str = "sha256",
) -> str:
    """
    Hash bytes content using specified algorithm.

    Args:
        content: Bytes content to hash
        truncate: Truncate result to N characters (None = full hash)
        algorithm: Hash algorithm ('sha256', 'md5')

    Returns:
        Hex digest of hash, optionally truncated
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    digest = hasher.hexdigest()
    return digest[:truncate] if truncate else digest


def hash_dict(
    data: dict[str, Any],
    truncate: int | None = 16,
    algorithm: str = "sha256",
) -> str:
    """
    Hash dictionary deterministically (sorted keys, string serialization).

    Args:
        data: Dictionary to hash
        truncate: Truncate result to N characters (default: 16)
        algorithm: Hash algorithm ('sha256', 'md5')

    Returns:
        Hex digest of hash

    Examples:
        >>> hash_dict({"b": 2, "a": 1})
        '...'  # Same as hash_dict({"a": 1, "b": 2})
    """
    # Deterministic serialization: sort keys, use default=str for non-JSON types
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hash_str(serialized, truncate=truncate, algorithm=algorithm)


def hash_file(
    path: Path,
    truncate: int | None = None,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
) -> str:
    """
    Hash file content by streaming (memory-efficient for large files).

    Args:
        path: Path to file
        truncate: Truncate result to N characters (None = full hash)
        algorithm: Hash algorithm ('sha256', 'md5')
        chunk_size: Read buffer size in bytes

    Returns:
        Hex digest of file content hash

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    hasher = hashlib.new(algorithm)

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    digest = hasher.hexdigest()
    return digest[:truncate] if truncate else digest


def hash_file_with_stat(
    path: Path,
    truncate: int | None = 8,
    algorithm: str = "sha256",
) -> str:
    """
    Hash file for fingerprinting (includes mtime for fast invalidation).

    Combines file content hash with modification time for efficient
    cache invalidation without re-hashing unchanged files.

    Args:
        path: Path to file
        truncate: Truncate result to N characters (default: 8 for URLs)
        algorithm: Hash algorithm

    Returns:
        Fingerprint string suitable for URLs
    """
    stat = path.stat()
    content_hash = hash_file(path, algorithm=algorithm)
    # Combine with mtime for fast invalidation
    combined = f"{content_hash}:{stat.st_mtime_ns}"
    return hash_str(combined, truncate=truncate, algorithm=algorithm)
