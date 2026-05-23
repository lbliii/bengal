"""Compatibility re-exports for pure internal reference URL helpers."""

from __future__ import annotations

from bengal.utils.paths.reference_resolution import (
    base_url_from_page_url,
    resolve_internal_link,
    resolved_path_url_variants,
)

__all__ = [
    "base_url_from_page_url",
    "resolve_internal_link",
    "resolved_path_url_variants",
]
