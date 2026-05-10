"""Sharded persistence for post-render page artifacts."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from bengal.utils.io import json_compat
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


class PageArtifactStore:
    """Persist page artifacts in small shards outside the main build cache."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self) -> dict[str, dict[str, Any]]:
        """Load all page artifact shards."""
        if not self.root.exists():
            return {}

        records: dict[str, dict[str, Any]] = {}
        for shard_path in self.root.glob("*.json"):
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
                    if isinstance(value, dict):
                        records[str(key)] = value
        return records

    def save(self, records: dict[str, dict[str, Any]]) -> None:
        """Write records into deterministic shards and prune stale shards."""
        self.root.mkdir(parents=True, exist_ok=True)
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
            if shard_path not in live_paths:
                shard_path.unlink()

        logger.debug(
            "page_artifact_shards_saved",
            records=len(records),
            shards=len(shards),
            path=str(self.root),
        )

    def _shard_name(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:2]
