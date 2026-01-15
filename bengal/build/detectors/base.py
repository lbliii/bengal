"""
Shared helpers for build change detectors.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey, content_key, data_key, parse_key

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page


def normalize_source_path(site_root: Path, value: str | Path) -> Path:
    """Normalize a path from cache to an absolute source path."""
    path = Path(value)
    if not path.is_absolute():
        return site_root / path
    return path


def page_key_for_page(site_root: Path, page: "Page") -> CacheKey:
    """Canonical cache key for a page."""
    return content_key(page.source_path, site_root)


def page_key_for_path(site_root: Path, path: Path) -> CacheKey:
    """Canonical cache key for a page path."""
    return content_key(path, site_root)


def asset_key_for_asset(site_root: Path, asset: "Asset") -> CacheKey:
    """Canonical cache key for an asset."""
    return content_key(asset.source_path, site_root)


def data_key_for_path(site_root: Path, path: Path) -> CacheKey:
    """Canonical cache key for a data file."""
    return data_key(path, site_root)


def key_to_path(site_root: Path, key: CacheKey) -> Path:
    """Convert a cache key back to a source path."""
    prefix, path = parse_key(key)
    if path.startswith("/"):
        return Path(path)
    # For prefixed keys (data:), the path still points under site_root.
    if prefix:
        return site_root / path
    return site_root / path
