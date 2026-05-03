"""Compatibility wrappers for rendering-owned link resolution helpers."""

from __future__ import annotations

from bengal.rendering.reference_resolution import (
    base_url_from_page_url,
    resolve_internal_link,
    resolved_path_url_variants,
)

parent_url_from_page_url = base_url_from_page_url

__all__ = [
    "base_url_from_page_url",
    "parent_url_from_page_url",
    "resolve_internal_link",
    "resolved_path_url_variants",
]
