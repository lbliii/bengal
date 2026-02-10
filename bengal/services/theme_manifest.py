"""Theme manifest I/O helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def read_theme_manifest(path: Path) -> dict[str, Any] | None:
    """Read a theme manifest from disk as a dict."""
    with open(path, "rb") as file_obj:
        data = tomllib.load(file_obj)
    return data if isinstance(data, dict) else None


def read_theme_extends(path: Path) -> str | None:
    """Read only the `extends` field from a theme manifest."""
    data = read_theme_manifest(path)
    if data is None:
        return None
    extends = data.get("extends")
    if extends is None:
        return None
    return str(extends)
