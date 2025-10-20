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
