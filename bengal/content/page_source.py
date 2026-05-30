"""Helpers for reading raw source from page-like objects."""

from __future__ import annotations

from typing import Any


def get_raw_source(page: Any) -> str:
    """Return raw authored source from a page-like object."""
    source = getattr(page, "_raw_content", None)
    if isinstance(source, str):
        return source
    if isinstance(source, bytes):
        return source.decode("utf-8", errors="replace")

    legacy_source = getattr(page, "_source", "")
    if isinstance(legacy_source, str):
        return legacy_source
    if isinstance(legacy_source, bytes):
        return legacy_source.decode("utf-8", errors="replace")
    return ""
