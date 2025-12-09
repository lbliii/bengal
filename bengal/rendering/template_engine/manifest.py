"""
Asset manifest handling for template engine.

Provides manifest loading and caching for fingerprinted asset resolution.

Related Modules:
    - bengal.rendering.template_engine.core: Uses these helpers
    - bengal.assets.manifest: AssetManifest data model
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from bengal.assets.manifest import AssetManifest, AssetManifestEntry
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class ManifestHelpersMixin:
    """
    Mixin providing asset manifest helper methods for TemplateEngine.

    Requires these attributes on the host class:
        - site: Site instance
        - _asset_manifest_path: Path
        - _asset_manifest_mtime: float | None
        - _asset_manifest_cache: dict[str, AssetManifestEntry]
        - _asset_manifest_fallbacks: set[str]
    """

    site: Any
    _asset_manifest_path: Path
    _asset_manifest_mtime: float | None
    _asset_manifest_cache: dict[str, AssetManifestEntry]
    _asset_manifest_fallbacks: set[str]

    def _get_manifest_entry(self, logical_path: str) -> AssetManifestEntry | None:
        """
        Return manifest entry for logical path if the manifest is present.

        Args:
            logical_path: Logical asset path (e.g., 'css/style.css')

        Returns:
            AssetManifestEntry if found, None otherwise
        """
        cache = self._load_asset_manifest()
        return cache.get(PurePosixPath(logical_path).as_posix())

    def _load_asset_manifest(self) -> dict[str, AssetManifestEntry]:
        """
        Load and cache the asset manifest based on file mtime.

        Returns:
            Dictionary of asset path to manifest entry
        """
        manifest_path = self._asset_manifest_path
        try:
            stat = manifest_path.stat()
        except FileNotFoundError:
            self._asset_manifest_mtime = None
            self._asset_manifest_cache = {}
            return self._asset_manifest_cache

        if self._asset_manifest_mtime == stat.st_mtime:
            return self._asset_manifest_cache

        manifest = AssetManifest.load(manifest_path)
        if manifest is None:
            self._asset_manifest_cache = {}
        else:
            self._asset_manifest_cache = dict(manifest.entries)
        self._asset_manifest_mtime = stat.st_mtime
        return self._asset_manifest_cache

    def _warn_manifest_fallback(self, logical_path: str) -> None:
        """
        Warn once per logical path when manifest lookup misses and fallback is used.

        Args:
            logical_path: Asset path that was not found in manifest
        """
        if logical_path in self._asset_manifest_fallbacks:
            return
        self._asset_manifest_fallbacks.add(logical_path)
        logger.warning(
            "asset_manifest_miss",
            logical_path=logical_path,
            manifest=str(self._asset_manifest_path),
        )

        logger.debug(
            "asset_manifest_fallback",
            logical_path=logical_path,
            manifest=str(self._asset_manifest_path),
        )


