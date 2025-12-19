"""
Asset manifest handling for template engine.

Provides manifest loading and caching for fingerprinted asset resolution.

Related Modules:
    - bengal.rendering.template_engine.core: Uses these helpers
    - bengal.assets.manifest: AssetManifest data model
"""

from __future__ import annotations

from pathlib import Path
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
        - _asset_manifest_present: bool
        - _asset_manifest_loaded: bool
    """

    site: Any
    _asset_manifest_path: Path
    _asset_manifest_mtime: float | None
    _asset_manifest_cache: dict[str, AssetManifestEntry]
    _asset_manifest_fallbacks: set[str]
    _asset_manifest_present: bool
    _asset_manifest_loaded: bool

    def _get_manifest_entry(self, logical_path: str) -> AssetManifestEntry | None:
        """
        Return manifest entry for logical path if the manifest is present.

        Args:
            logical_path: Logical asset path (e.g., 'css/style.css')

        Returns:
            AssetManifestEntry if found, None otherwise
        """
        # `logical_path` is already normalized (posix, no leading slash) by asset_url().
        cache = self._load_asset_manifest()
        return cache.get(logical_path)

    def _load_asset_manifest(self) -> dict[str, AssetManifestEntry]:
        """
        Load and cache the asset manifest based on file mtime.

        Returns:
            Dictionary of asset path to manifest entry
        """
        manifest_path = self._asset_manifest_path

        # In dev server mode, be conservative: allow the manifest to change while
        # the process is running (e.g., assets pipeline updates).
        if getattr(self.site, "dev_mode", False):
            try:
                stat = manifest_path.stat()
            except FileNotFoundError:
                self._asset_manifest_mtime = None
                self._asset_manifest_cache = {}
                self._asset_manifest_present = False
                return self._asset_manifest_cache

            self._asset_manifest_present = True
            if self._asset_manifest_mtime == stat.st_mtime:
                return self._asset_manifest_cache

            manifest = AssetManifest.load(manifest_path)
            if manifest is None:
                self._asset_manifest_cache = {}
            else:
                self._asset_manifest_cache = dict(manifest.entries)
            self._asset_manifest_mtime = stat.st_mtime
            return self._asset_manifest_cache

        # Performance: on a normal `bengal build`, the manifest is created in the
        # assets phase and does not change while templates render. Avoid repeated
        # stat+parse work on every asset_url() call.
        if getattr(self, "_asset_manifest_loaded", False):
            return self._asset_manifest_cache

        try:
            stat = manifest_path.stat()
        except FileNotFoundError:
            self._asset_manifest_mtime = None
            self._asset_manifest_cache = {}
            self._asset_manifest_present = False
            self._asset_manifest_loaded = True
            return self._asset_manifest_cache

        self._asset_manifest_present = True
        manifest = AssetManifest.load(manifest_path)
        if manifest is None:
            self._asset_manifest_cache = {}
        else:
            self._asset_manifest_cache = dict(manifest.entries)
        self._asset_manifest_mtime = stat.st_mtime
        self._asset_manifest_loaded = True
        return self._asset_manifest_cache

    def _warn_manifest_fallback(self, logical_path: str) -> None:
        """
        Warn once per logical path when manifest lookup misses and fallback is used.

        Args:
            logical_path: Asset path that was not found in manifest
        """
        # Suppress duplicates across the entire build if possible (parallel rendering
        # creates one TemplateEngine per worker thread).
        global_set = getattr(self.site, "_asset_manifest_fallbacks_global", None)
        global_lock = getattr(self.site, "_asset_manifest_fallbacks_lock", None)
        if isinstance(global_set, set) and global_lock is not None:
            try:
                with global_lock:
                    if logical_path in global_set:
                        return
                    global_set.add(logical_path)
            except Exception:
                # Fall back to per-engine suppression
                pass

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
