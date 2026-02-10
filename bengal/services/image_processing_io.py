"""I/O helpers for image processing backend."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_cache_metadata(meta_path: Path) -> dict[str, Any]:
    """Read JSON metadata for cached image output."""
    with open(meta_path) as file_obj:
        data = json.load(file_obj)
    return data if isinstance(data, dict) else {}


def write_cache_metadata_atomic(cache_dir: Path, cache_key: str, meta: dict[str, Any]) -> None:
    """Write cache metadata atomically via temp file + rename."""
    meta_path = cache_dir / f"{cache_key}.json"
    fd, temp_path = tempfile.mkstemp(
        dir=cache_dir,
        prefix=f".{cache_key}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as file_obj:
            json.dump(meta, file_obj)
        os.replace(temp_path, meta_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(temp_path)
        raise
