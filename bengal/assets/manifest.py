"""
Persistent asset manifest for deterministic asset URL resolution.

The manifest maps logical asset paths (e.g. ``css/style.css``) to the
fingerprinted files actually written to ``public/assets`` along with basic
metadata that deployment tooling can inspect.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from bengal.utils.atomic_write import atomic_write_text
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def _isoformat(timestamp: float | None) -> str | None:
    """Convert a POSIX timestamp (seconds) to an ISO-8601 string."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def _posix(path_like: str) -> str:
    """Normalize to POSIX-style paths for portability."""
    return PurePosixPath(path_like).as_posix()


@dataclass(slots=True)
class AssetManifestEntry:
    """
    Immutable manifest entry for a single logical asset.

    Attributes:
        logical_path: Logical path requested from templates (e.g. ``css/style.css``).
        output_path: Relative path under the output directory (e.g. ``assets/css/style.X.css``).
        fingerprint: Optional hash used when fingerprinting is enabled.
        size_bytes: File size for visibility / debugging.
        updated_at: ISO-8601 timestamp of the file write.
    """

    logical_path: str
    output_path: str
    fingerprint: str | None = None
    size_bytes: int | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, str | int]:
        """Serialize entry to a JSON-friendly dict."""
        data: dict[str, str | int] = {
            "output_path": self.output_path,
        }
        if self.fingerprint:
            data["fingerprint"] = self.fingerprint
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        if self.updated_at:
            data["updated_at"] = self.updated_at
        return data

    @classmethod
    def from_dict(cls, logical_path: str, data: Mapping[str, object]) -> AssetManifestEntry:
        """Create an entry from a JSON payload."""
        size_bytes_val = data.get("size_bytes")
        return cls(
            logical_path=_posix(logical_path),
            output_path=_posix(str(data.get("output_path", ""))),
            fingerprint=(str(data["fingerprint"]) if data.get("fingerprint") else None),
            size_bytes=int(size_bytes_val)
            if size_bytes_val is not None and isinstance(size_bytes_val, (int, str))
            else None,
            updated_at=str(data["updated_at"]) if data.get("updated_at") else None,
        )


@dataclass
class AssetManifest:
    """
    Asset manifest container with serialization helpers.

    Example usage:
        manifest = AssetManifest()
        manifest.set_entry("css/style.css", "assets/css/style.ABC.css", fingerprint="ABC123")
        manifest.write(path)
    """

    version: int = 1
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    _entries: dict[str, AssetManifestEntry] = field(default_factory=dict)

    def set_entry(
        self,
        logical_path: str,
        output_path: str,
        *,
        fingerprint: str | None,
        size_bytes: int | None,
        updated_at: float | None,
    ) -> None:
        """Add or replace a manifest entry for the logical asset."""
        normalized_logical = _posix(logical_path)
        self._entries[normalized_logical] = AssetManifestEntry(
            logical_path=normalized_logical,
            output_path=_posix(output_path),
            fingerprint=fingerprint,
            size_bytes=size_bytes,
            updated_at=_isoformat(updated_at),
        )

    def get(self, logical_path: str) -> AssetManifestEntry | None:
        """Return the entry for the logical path, if present."""
        return self._entries.get(_posix(logical_path))

    @property
    def entries(self) -> Mapping[str, AssetManifestEntry]:
        """Read-only view of entries for inspection."""
        return self._entries

    def write(self, path: Path) -> None:
        """Serialize the manifest to disk using an atomic write."""
        payload = {
            "version": self.version,
            "generated_at": self.generated_at,
            "assets": {key: entry.to_dict() for key, entry in sorted(self._entries.items())},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> AssetManifest | None:
        """Load a manifest from disk, returning None when missing or invalid."""
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning("asset_manifest_load_failed", path=str(path), error=str(exc))
            return None

        manifest = cls()
        manifest.generated_at = (
            str(data.get("generated_at")) if data.get("generated_at") else manifest.generated_at
        )
        manifest.version = int(data.get("version", manifest.version))
        manifest._entries = {}

        assets_section = data.get("assets") or {}
        for logical_path, entry_data in assets_section.items():
            manifest._entries[_posix(logical_path)] = AssetManifestEntry.from_dict(
                logical_path, entry_data
            )

        return manifest
