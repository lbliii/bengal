"""Compatibility wrappers for rendering-owned link resolution helpers."""

from __future__ import annotations

from bengal.rendering.reference_resolution import (
    base_url_from_page_url,
    resolve_internal_link,
)
from bengal.rendering.reference_resolution import (
    resolved_path_url_variants as _resolved_path_url_variants,
)

parent_url_from_page_url = base_url_from_page_url


def resolved_path_url_variants(resolved: str) -> list[str]:
    """Return legacy mutable URL variant list for compatibility callers."""
    return list(_resolved_path_url_variants(resolved))


__all__ = [
    "base_url_from_page_url",
    "parent_url_from_page_url",
    "resolve_internal_link",
    "resolved_path_url_variants",
]
