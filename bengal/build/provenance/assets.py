"""Asset hash helpers for provenance filtering.

Session caches (_file_hashes) are protected by pf._session_lock. Asset hash
dict updates stay per-key as in the original filter methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey, content_key
from bengal.build.provenance.types import ContentHash, hash_file
from bengal.utils.io.json_compat import JSONDecodeError
from bengal.utils.io.json_compat import dump as json_dump
from bengal.utils.io.json_compat import load as json_load

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.asset import Asset


def load_asset_hashes(pf: Any) -> None:
    """Load asset hashes from disk. Accepts legacy str or new dict format."""
    asset_cache_path = pf.cache.cache_dir / "asset_hashes.json"
    try:
        data = json_load(asset_cache_path)
        result: dict[CacheKey, ContentHash | dict[str, Any]] = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[CacheKey(k)] = v
            else:
                result[CacheKey(k)] = ContentHash(str(v))
        pf._asset_hashes = result
    except FileNotFoundError, JSONDecodeError, KeyError:
        pf._asset_hashes = {}


def save_asset_hashes(pf: Any) -> None:
    """Save asset hashes to disk (atomic write for crash safety)."""
    asset_cache_path = pf.cache.cache_dir / "asset_hashes.json"
    json_dump(dict(pf._asset_hashes), asset_cache_path)


def get_file_hash(pf: Any, path: Path) -> ContentHash:
    """Get file hash from session cache or compute it (thread-safe)."""
    # Fast path: protect reads as well as writes for free-threaded builds.
    with pf._session_lock:
        cached = pf._file_hashes.get(path)
    if cached is not None:
        return cached

    # Compute hash (outside lock - I/O)
    computed = hash_file(path)

    # Store in cache with lock
    with pf._session_lock:
        # Double-check in case another thread computed it
        if path not in pf._file_hashes:
            pf._file_hashes[path] = computed
        return pf._file_hashes[path]


def is_forced_by_dependency(pf: Any, asset: Asset, forced: set[Path]) -> bool:
    """
    True if any path in forced is a dependency of this asset (e.g. @import'd CSS).

    When notebook.css (imported by style.css) changes, the watcher reports
    notebook.css in forced_changed. The style.css asset has source_path to
    style.css, so the direct check fails. We must reprocess style.css when
    any file under its directory changes, since bundle_css() inlines @imports.
    """
    if not forced:
        return False
    asset_key = content_key(asset.source_path, pf.site.root_path)
    forced_keys = {content_key(p.resolve(), pf.site.root_path) for p in forced}
    if asset_key in forced_keys:
        return True  # Direct match
    if not asset.is_css_entry_point():
        return False
    try:
        asset_dir = asset.source_path.parent.resolve()
        for p in forced:
            try:
                p.resolve().relative_to(asset_dir)
                return True  # p is under asset's directory (e.g. layouts/notebook.css)
            except ValueError, OSError:
                continue
    except OSError:
        pass
    return False


def is_asset_changed(pf: Any, asset: Asset) -> bool:
    """
    Check if an asset has changed based on content hash.

    OPTIMIZATION: Uses mtime+size check first to avoid hashing unchanged files.

    Thread Safety:
        Uses local variables for hash comparisons. Asset hash dict
        updates are safe because each asset has a unique key.
    """
    try:
        if not asset.source_path.exists():
            return True
    except OSError:
        return True  # File system error - treat as changed

    asset_path = get_asset_key(pf, asset)
    stored = pf._asset_hashes.get(asset_path)

    try:
        stat = asset.source_path.stat()
        current_mtime = stat.st_mtime
        current_size = stat.st_size
    except OSError:
        return True  # File error - treat as changed

    # Short-circuit: mtime+size match stored → unchanged
    if (
        stored is not None
        and isinstance(stored, dict)
        and (
            stored.get("mtime_ns") == stat.st_mtime_ns
            if "mtime_ns" in stored
            else stored.get("mtime") == current_mtime
        )
        and stored.get("size") == current_size
    ):
        return False

    # Compute hash (necessary when no short-circuit)
    try:
        current_hash = get_file_hash(pf, asset.source_path)
    except OSError:
        return True  # File error - treat as changed

    cached_hash: ContentHash | None = None
    if stored is not None:
        cached_hash = stored.get("hash") if isinstance(stored, dict) else stored

    if stored is None:
        # First time seeing this asset
        pf._asset_hashes[asset_path] = {
            "hash": current_hash,
            "mtime": current_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "size": current_size,
        }
        return True

    if cached_hash != current_hash:
        # Asset content changed
        pf._asset_hashes[asset_path] = {
            "hash": current_hash,
            "mtime": current_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "size": current_size,
        }
        return True

    # Content same but mtime/size changed (e.g. touch) - update stored metadata
    if isinstance(stored, dict):
        pf._asset_hashes[asset_path] = {
            "hash": current_hash,
            "mtime": current_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "size": current_size,
        }
    else:
        # Legacy format: upgrade to structured
        pf._asset_hashes[asset_path] = {
            "hash": current_hash,
            "mtime": current_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "size": current_size,
        }
    return False


def get_asset_key(pf: Any, asset: Asset) -> CacheKey:
    """Get canonical asset key for cache lookups."""
    return content_key(asset.source_path, pf.site.root_path)


def record_asset_hash(pf: Any, asset: Asset) -> None:
    """
    Record an asset's hash without checking if changed.

    Used during full builds to populate the asset hash cache for
    subsequent incremental builds. Without this, the first incremental
    build after a full build would see all assets as "changed".
    """
    try:
        if not asset.source_path.exists():
            return
        stat = asset.source_path.stat()
        current_hash = get_file_hash(pf, asset.source_path)
        asset_key = get_asset_key(pf, asset)
        pf._asset_hashes[asset_key] = {
            "hash": current_hash,
            "mtime": stat.st_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
    except OSError:
        pass  # Skip assets that can't be hashed
