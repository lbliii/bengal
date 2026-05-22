"""Sharded persistence for post-render page artifacts."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from bengal.utils.io import json_compat
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

_MANIFEST_NAME = "manifest.json"


class PageArtifactStore:
    """Persist page artifacts in small shards outside the main build cache."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self, keys: set[str] | None = None) -> dict[str, dict[str, Any]]:
        """Load page artifact shards, optionally limited to selected keys."""
        if not self.root.exists():
            return {}

        manifest = self._load_manifest()
        if manifest is not None:
            if keys is None:
                shard_names = set(manifest.values())
                wanted_keys: set[str] | None = None
            else:
                shard_names = {manifest[key] for key in keys if key in manifest}
                wanted_keys = keys
            return self._load_shards(shard_names, wanted_keys)

        return self._load_legacy_shards(keys)

    def _load_legacy_shards(self, keys: set[str] | None) -> dict[str, dict[str, Any]]:
        """Load shards by scanning the directory when no manifest exists."""
        shard_names = {
            shard_path.stem
            for shard_path in self.root.glob("*.json")
            if shard_path.name != _MANIFEST_NAME
        }
        return self._load_shards(shard_names, keys)

    def _load_shards(
        self,
        shard_names: set[str],
        keys: set[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Load selected shard files."""
        records: dict[str, dict[str, Any]] = {}
        for shard in sorted(shard_names):
            shard_path = self.root / f"{shard}.json"
            try:
                data = json_compat.load(shard_path)
            except Exception as e:
                logger.warning(
                    "page_artifact_shard_load_failed",
                    path=str(shard_path),
                    error=str(e),
                    action="ignoring_shard",
                )
                continue
            if isinstance(data, dict):
                for key, value in data.items():
                    if (keys is None or str(key) in keys) and isinstance(value, dict):
                        records[str(key)] = value
        return records

    def save(
        self,
        records: dict[str, dict[str, Any]],
        *,
        dirty_keys: set[str] | None = None,
        deleted_keys: set[str] | None = None,
    ) -> None:
        """Write records into deterministic shards and prune stale shards."""
        self.root.mkdir(parents=True, exist_ok=True)

        if dirty_keys is not None or deleted_keys is not None:
            self._save_dirty(records, dirty_keys or set(), deleted_keys or set())
            return

        shards: dict[str, dict[str, dict[str, Any]]] = {}
        for key, record in records.items():
            shard = self._shard_name(key)
            shards.setdefault(shard, {})[key] = record

        live_paths = set()
        for shard, shard_records in shards.items():
            shard_path = self.root / f"{shard}.json"
            live_paths.add(shard_path)
            json_compat.dump(shard_records, shard_path, indent=None)

        for shard_path in self.root.glob("*.json"):
            if shard_path.name != _MANIFEST_NAME and shard_path not in live_paths:
                shard_path.unlink()

        self._save_manifest(records)

        logger.debug(
            "page_artifact_shards_saved",
            records=len(records),
            shards=len(shards),
            path=str(self.root),
        )

    def _save_dirty(
        self,
        records: dict[str, dict[str, Any]],
        dirty_keys: set[str],
        deleted_keys: set[str],
    ) -> None:
        """Rewrite only shards affected by dirty or deleted record keys."""
        affected_shards = {self._shard_name(key) for key in dirty_keys | deleted_keys}
        for shard in affected_shards:
            shard_path = self.root / f"{shard}.json"
            shard_records = {
                key: record for key, record in records.items() if self._shard_name(key) == shard
            }
            if shard_records:
                json_compat.dump(shard_records, shard_path, indent=None)
            elif shard_path.exists():
                shard_path.unlink()

        self._save_manifest(records)

        logger.debug(
            "page_artifact_dirty_shards_saved",
            records=len(records),
            dirty_keys=len(dirty_keys),
            deleted_keys=len(deleted_keys),
            shards=len(affected_shards),
            path=str(self.root),
        )

    def _shard_name(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:2]

    def _manifest_path(self) -> Path:
        return self.root / _MANIFEST_NAME

    def _load_manifest(self) -> dict[str, str] | None:
        """Load key-to-shard manifest, returning None for missing/invalid data."""
        manifest_path = self._manifest_path()
        try:
            data = json_compat.load(manifest_path)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(
                "page_artifact_manifest_load_failed",
                path=str(manifest_path),
                error=str(e),
                action="falling_back_to_shard_scan",
            )
            return None

        if not isinstance(data, dict) or data.get("version") != 1:
            return None
        records = data.get("records")
        if not isinstance(records, dict):
            return None
        return {str(key): str(shard) for key, shard in records.items()}

    def _save_manifest(self, records: dict[str, dict[str, Any]]) -> None:
        """Persist the key-to-shard manifest."""
        manifest_path = self._manifest_path()
        if not records:
            if manifest_path.exists():
                manifest_path.unlink()
            return

        json_compat.dump(
            {
                "version": 1,
                "records": {key: self._shard_name(key) for key in sorted(records)},
            },
            manifest_path,
            indent=None,
        )
