"""
Asset Dependency Map for incremental builds.

Tracks which pages reference which assets to enable on-demand asset discovery.
This allows incremental builds to discover only assets needed for changed pages,
skipping asset discovery for unchanged pages.

Architecture:
- Mapping: source_path → set[asset_urls] (which pages use which assets)
- Storage: .bengal/asset_deps.json (compact format)
- Tracking: Built during page parsing by extracting asset references
- Incremental: Only discover assets for changed pages

Performance Impact:
- Asset discovery skipped for unchanged pages (~50ms saved per 100 pages)
- Focus on only needed assets in incremental builds
- Incremental asset fingerprinting possible

Asset Types Tracked:
- Images: img src, picture sources
- Stylesheets: link href
- Scripts: script src
- Fonts: @font-face urls
- Other: data URLs, imports, includes
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.cache.cacheable import Cacheable
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AssetReference:
    """Reference to an asset from a page."""

    url: str  # Asset URL or path
    type: str  # Asset type: image, stylesheet, script, font, other
    source_page: str  # Source page path that references this asset


@dataclass
class AssetDependencyEntry(Cacheable):
    """
    Cache entry for asset dependencies.

    Implements the Cacheable protocol for type-safe serialization.
    """

    assets: set[str]  # Set of asset URLs/paths
    tracked_at: str  # ISO timestamp when tracked
    is_valid: bool = True  # Whether entry is still valid

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (Cacheable protocol)."""
        return {
            "assets": sorted(list(self.assets)),  # Sort for consistency
            "tracked_at": self.tracked_at,
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> AssetDependencyEntry:
        """Deserialize from cache dictionary (Cacheable protocol)."""
        return cls(
            assets=set(data["assets"]),
            tracked_at=data["tracked_at"],
            is_valid=data.get("is_valid", True),
        )

    # Aliases for test compatibility
    def to_dict(self) -> dict[str, Any]:
        """Alias for to_cache_dict (test compatibility)."""
        return self.to_cache_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetDependencyEntry:
        """Alias for from_cache_dict (test compatibility)."""
        return cls.from_cache_dict(data)


class AssetDependencyMap:
    """
    Persistent map of page-to-asset dependencies for incremental discovery.

    Purpose:
    - Track which assets each page references
    - Enable on-demand asset discovery
    - Skip asset discovery for unchanged pages
    - Support incremental asset fingerprinting

    Cache Format (JSON):
    {
        "version": 1,
        "pages": {
            "content/index.md": {
                "assets": [
                    "/images/logo.png",
                    "/css/style.css",
                    "/fonts/inter.woff2"
                ],
                "tracked_at": "2025-10-16T12:00:00",
                "is_valid": true
            }
        }
    }
    """

    VERSION = 1
    CACHE_FILE = ".bengal/asset_deps.json"

    def __init__(self, cache_path: Path | None = None):
        """
        Initialize asset dependency map.

        Args:
            cache_path: Path to cache file (defaults to .bengal/asset_deps.json)
        """
        if cache_path is None:
            cache_path = Path(self.CACHE_FILE)
        self.cache_path = Path(cache_path)
        self.pages: dict[str, AssetDependencyEntry] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load asset dependencies from disk if file exists."""
        if not self.cache_path.exists():
            logger.debug("asset_dependency_map_not_found", path=str(self.cache_path))
            return

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            # Validate version
            if data.get("version") != self.VERSION:
                logger.warning(
                    "asset_dependency_map_version_mismatch",
                    expected=self.VERSION,
                    found=data.get("version"),
                )
                self.pages = {}
                return

            # Load dependency entries
            for path_str, entry_data in data.get("pages", {}).items():
                self.pages[path_str] = AssetDependencyEntry.from_cache_dict(entry_data)

            logger.info(
                "asset_dependency_map_loaded",
                entries=len(self.pages),
                path=str(self.cache_path),
            )
        except Exception as e:
            logger.warning(
                "asset_dependency_map_load_failed",
                error=str(e),
                path=str(self.cache_path),
            )
            self.pages = {}

    def save_to_disk(self) -> None:
        """Save asset dependencies to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": self.VERSION,
                "pages": {path: entry.to_cache_dict() for path, entry in self.pages.items()},
            }

            # Atomic write to avoid partial/corrupt files on crash
            with AtomicFile(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(
                "asset_dependency_map_saved",
                entries=len(self.pages),
                path=str(self.cache_path),
            )
        except Exception as e:
            logger.error(
                "asset_dependency_map_save_failed",
                error=str(e),
                path=str(self.cache_path),
            )

    def track_page_assets(self, source_path: Path, assets: set[str]) -> None:
        """
        Track assets referenced by a page.

        Args:
            source_path: Path to source page
            assets: Set of asset URLs/paths referenced by the page
        """
        entry = AssetDependencyEntry(
            assets=assets,
            tracked_at=datetime.utcnow().isoformat(),
            is_valid=True,
        )
        self.pages[str(source_path)] = entry

    def get_page_assets(self, source_path: Path) -> set[str] | None:
        """
        Get assets referenced by a page.

        Args:
            source_path: Path to source page

        Returns:
            Set of asset URLs if found and valid, None otherwise
        """
        path_str = str(source_path)
        if path_str not in self.pages:
            return None

        entry = self.pages[path_str]
        if not entry.is_valid:
            return None

        return entry.assets.copy()

    def has_assets(self, source_path: Path) -> bool:
        """
        Check if page has tracked assets.

        Args:
            source_path: Path to source page

        Returns:
            True if page has valid asset tracking
        """
        path_str = str(source_path)
        if path_str not in self.pages:
            return False

        entry = self.pages[path_str]
        return entry.is_valid

    def get_all_assets(self) -> set[str]:
        """
        Get all unique assets referenced by any page.

        Returns:
            Set of all asset URLs across all pages
        """
        all_assets: set[str] = set()
        for entry in self.pages.values():
            if entry.is_valid:
                all_assets.update(entry.assets)
        return all_assets

    def get_assets_for_pages(self, source_paths: list[Path]) -> set[str]:
        """
        Get all assets referenced by a set of pages.

        Args:
            source_paths: List of page paths to find assets for

        Returns:
            Set of all asset URLs referenced by the given pages
        """
        needed_assets: set[str] = set()
        for path in source_paths:
            assets = self.get_page_assets(path)
            if assets:
                needed_assets.update(assets)
        return needed_assets

    def invalidate(self, source_path: Path) -> None:
        """
        Mark a page's asset tracking as invalid.

        Args:
            source_path: Path to source page
        """
        path_str = str(source_path)
        if path_str in self.pages:
            self.pages[path_str].is_valid = False

    def invalidate_all(self) -> None:
        """Invalidate all asset tracking entries."""
        for entry in self.pages.values():
            entry.is_valid = False

    def clear(self) -> None:
        """Clear all asset tracking."""
        self.pages.clear()

    def get_valid_entries(self) -> dict[str, set[str]]:
        """
        Get all valid asset tracking entries.

        Returns:
            Dictionary mapping source_path to asset set for valid entries
        """
        return {path: entry.assets.copy() for path, entry in self.pages.items() if entry.is_valid}

    def get_invalid_entries(self) -> dict[str, set[str]]:
        """
        Get all invalid asset tracking entries.

        Returns:
            Dictionary mapping source_path to asset set for invalid entries
        """
        return {
            path: entry.assets.copy() for path, entry in self.pages.items() if not entry.is_valid
        }

    def stats(self) -> dict[str, Any]:
        """
        Get asset dependency map statistics.

        Returns:
            Dictionary with cache stats
        """
        valid = sum(1 for e in self.pages.values() if e.is_valid)
        invalid = len(self.pages) - valid

        # Count total unique assets
        all_assets = self.get_all_assets()

        # Average assets per page
        avg_assets = 0.0
        if valid > 0:
            total_assets = sum(len(e.assets) for e in self.pages.values() if e.is_valid)
            avg_assets = total_assets / valid

        return {
            "total_pages": len(self.pages),
            "valid_pages": valid,
            "invalid_pages": invalid,
            "unique_assets": len(all_assets),
            "avg_assets_per_page": avg_assets,
            "cache_size_bytes": len(json.dumps([e.to_cache_dict() for e in self.pages.values()])),
        }

    def get_asset_pages(self, asset_url: str) -> set[str]:
        """
        Get all pages that reference a specific asset.

        Args:
            asset_url: Asset URL to find references for

        Returns:
            Set of page paths that reference this asset
        """
        referencing_pages: set[str] = set()
        for path, entry in self.pages.items():
            if entry.is_valid and asset_url in entry.assets:
                referencing_pages.add(path)
        return referencing_pages
