"""
File utility functions for common file operations.

Provides file hashing and other file manipulation utilities used throughout
the codebase. Focuses on efficient file operations with chunked reading.

Key Concepts:
    - File hashing: SHA256 hash computation for change detection
    - Chunked reading: Efficient file reading in chunks for large files
    - Path handling: Path-based file operations

Related Modules:
    - bengal.cache.build_cache: Uses file hashing for change detection
    - bengal.core.asset: Asset fingerprinting using file hashes

See Also:
    - bengal/utils/file_utils.py:hash_file() for file hashing
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def hash_file(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of file content."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hasher = sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()
