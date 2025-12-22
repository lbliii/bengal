"""
Persistent asset manifest for deterministic asset URL resolution.

This module provides the AssetManifest and AssetManifestEntry classes for
tracking the mapping between logical asset paths and their fingerprinted
output files.

The manifest maps logical asset paths (e.g. ``css/style.css``) to the
fingerprinted files actually written to ``public/assets`` along with basic
metadata that deployment tooling can inspect.

Key Features:
    - **Deterministic URLs**: Logical paths resolve to consistent output paths
    - **Fingerprinting Support**: Tracks content hashes for cache-busting
    - **Metadata Tracking**: Records file size and update timestamps
    - **Atomic Writes**: Uses atomic file operations for safe updates
    - **JSON Serialization**: Human-readable manifest format

Manifest Format:
    The manifest is stored as JSON with the following structure::

        {
            "version": 1,
            "generated_at": "2025-01-15T10:30:00Z",
            "assets": {
                "css/style.css": {
                    "output_path": "assets/css/style.abc123.css",
                    "fingerprint": "abc123def456",
                    "size_bytes": 4096,
                    "updated_at": "2025-01-15T10:30:00Z"
                }
            }
        }

Architecture:
    This module is designed to be used by AssetOrchestrator during builds.
    Templates access resolved URLs via the ``asset()`` filter, which reads
    from the manifest to resolve logical paths.

Related:
    - bengal/orchestration/asset_orchestrator.py: Uses manifest during builds
    - bengal/rendering/filters.py: asset() filter reads from manifest
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
    """
    Convert a POSIX timestamp to an ISO-8601 UTC string.

    Args:
        timestamp: Unix timestamp in seconds, or None.

    Returns:
        ISO-8601 formatted string with 'Z' suffix for UTC, or None if input is None.

    Example:
        >>> _isoformat(1705315800.0)
        '2024-01-15T10:30:00Z'
    """
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def _posix(path_like: str) -> str:
    """
    Normalize a path to POSIX-style forward slashes for cross-platform portability.

    Args:
        path_like: Path string, potentially with backslashes on Windows.

    Returns:
        Path string with forward slashes only.

    Example:
        >>> _posix("css\\\\style.css")
        'css/style.css'
    """
    return PurePosixPath(path_like).as_posix()


@dataclass(slots=True)
class AssetManifestEntry:
    """
    Manifest entry for a single logical asset.

    Represents the mapping from a logical asset path (as used in templates) to
    its actual output location, along with metadata for debugging and deployment.

    Uses ``slots=True`` for memory efficiency when tracking many assets.

    Attributes:
        logical_path: Logical path requested from templates (e.g. ``css/style.css``).
        output_path: Relative path under the output directory (e.g. ``assets/css/style.X.css``).
        fingerprint: Content hash used for cache-busting, or None if disabled.
        size_bytes: File size in bytes for visibility and debugging.
        updated_at: ISO-8601 timestamp of the last file write.

    Example:
        >>> entry = AssetManifestEntry(
        ...     logical_path="css/style.css",
        ...     output_path="assets/css/style.abc123.css",
        ...     fingerprint="abc123def456",
        ...     size_bytes=4096,
        ...     updated_at="2025-01-15T10:30:00Z",
        ... )
        >>> entry.to_dict()
        {'output_path': 'assets/css/style.abc123.css', 'fingerprint': 'abc123def456', ...}
    """

    logical_path: str
    output_path: str
    fingerprint: str | None = None
    size_bytes: int | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, str | int]:
        """
        Serialize entry to a JSON-friendly dictionary.

        Only includes non-None optional fields to keep the manifest compact.

        Returns:
            Dictionary with 'output_path' and any present optional fields.
        """
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
        """
        Create an entry from a JSON payload.

        Args:
            logical_path: The logical asset path (dict key from manifest).
            data: Dictionary containing 'output_path' and optional metadata.

        Returns:
            Populated AssetManifestEntry with normalized paths.
        """
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

    Manages a collection of AssetManifestEntry objects and provides methods
    for reading, writing, and querying the manifest.

    The manifest is the single source of truth for asset URL resolution during
    rendering. Templates use the ``asset()`` filter which queries this manifest
    to resolve logical paths to fingerprinted output URLs.

    Attributes:
        version: Manifest format version for future compatibility.
        generated_at: ISO-8601 timestamp when manifest was created/updated.
        _entries: Internal dictionary mapping logical paths to entries.

    Example:
        >>> manifest = AssetManifest()
        >>> manifest.set_entry(
        ...     "css/style.css",
        ...     "assets/css/style.ABC.css",
        ...     fingerprint="ABC123",
        ...     size_bytes=4096,
        ...     updated_at=time.time(),
        ... )
        >>> manifest.get("css/style.css").output_path
        'assets/css/style.ABC.css'
        >>> manifest.write(Path("public/asset-manifest.json"))
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
        """
        Add or replace a manifest entry for a logical asset.

        Args:
            logical_path: Logical path as used in templates (e.g. ``css/style.css``).
            output_path: Actual output path relative to public dir.
            fingerprint: Content hash for cache-busting, or None if disabled.
            size_bytes: File size in bytes, or None if unknown.
            updated_at: Unix timestamp of last modification, or None.
        """
        normalized_logical = _posix(logical_path)
        self._entries[normalized_logical] = AssetManifestEntry(
            logical_path=normalized_logical,
            output_path=_posix(output_path),
            fingerprint=fingerprint,
            size_bytes=size_bytes,
            updated_at=_isoformat(updated_at),
        )

    def get(self, logical_path: str) -> AssetManifestEntry | None:
        """
        Retrieve the entry for a logical path.

        Args:
            logical_path: Logical asset path to look up.

        Returns:
            AssetManifestEntry if found, None otherwise.
        """
        return self._entries.get(_posix(logical_path))

    @property
    def entries(self) -> Mapping[str, AssetManifestEntry]:
        """
        Read-only view of all manifest entries.

        Returns:
            Mapping from logical paths to their AssetManifestEntry objects.
        """
        return self._entries

    def write(self, path: Path) -> None:
        """
        Serialize the manifest to disk using an atomic write.

        Creates parent directories if needed. Entries are sorted by key
        for deterministic output.

        Args:
            path: Destination path for the manifest JSON file.
        """
        payload = {
            "version": self.version,
            "generated_at": self.generated_at,
            "assets": {key: entry.to_dict() for key, entry in sorted(self._entries.items())},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> AssetManifest | None:
        """
        Load a manifest from disk.

        Gracefully handles missing or malformed files by returning None,
        allowing callers to fall back to a fresh manifest.

        Args:
            path: Path to the manifest JSON file.

        Returns:
            Populated AssetManifest, or None if file is missing or invalid.
        """
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
