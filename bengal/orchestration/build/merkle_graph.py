"""Merkle graph snapshot + advisory diff for build planning.

Phase A (read-only): persist graph snapshot.
Phase B (advisory): compare with previous snapshot and report dirty sets.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bengal.snapshots.utils import resolve_template_name

_MERKLE_STATE_RELATIVE = Path(".bengal/state/merkle_graph.json")
_MERKLE_VERSION = 1


@dataclass(frozen=True, slots=True)
class MerkleAdvisory:
    """Read-only comparison summary between two Merkle snapshots."""

    dirty_content: frozenset[str]
    dirty_templates: frozenset[str]
    dirty_pages: frozenset[str]
    previous_root: str | None
    current_root: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dirty_content_count": len(self.dirty_content),
            "dirty_templates_count": len(self.dirty_templates),
            "dirty_pages_count": len(self.dirty_pages),
            "previous_root": self.previous_root,
            "current_root": self.current_root,
            "dirty_content": sorted(self.dirty_content),
            "dirty_templates": sorted(self.dirty_templates),
            "dirty_pages": sorted(self.dirty_pages),
        }


def analyze_merkle_advisory(
    site: Any,
    root_path: Path,
    *,
    persist: bool,
) -> MerkleAdvisory:
    """Build current snapshot, compare against previous, optionally persist."""
    previous = _load_snapshot(root_path)
    current = _build_snapshot(site)
    advisory = _compare_snapshots(previous, current)
    if persist:
        _save_snapshot(root_path, current)
    return advisory


def collect_merkle_advisory(site: Any, root_path: Path) -> MerkleAdvisory:
    """Build current snapshot, compare against previous, then persist current."""
    return analyze_merkle_advisory(site, root_path, persist=True)


def _state_file(root_path: Path) -> Path:
    return root_path / _MERKLE_STATE_RELATIVE


def _load_snapshot(root_path: Path) -> dict[str, Any] | None:
    path = _state_file(root_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _save_snapshot(root_path: Path, snapshot: dict[str, Any]) -> None:
    path = _state_file(root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_canonicalize(snapshot), indent=2, sort_keys=True))


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(_canonicalize(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _build_snapshot(site: Any) -> dict[str, Any]:
    pages = list(getattr(site, "pages", []) or [])

    content_hashes: dict[str, str] = {}
    template_names: set[str] = set()
    page_to_template: dict[str, str] = {}

    for page in pages:
        source_path = getattr(page, "source_path", None)
        if source_path is None:
            continue
        page_key = str(source_path)
        content_hashes[page_key] = _hash_file(Path(source_path))

        template_name = resolve_template_name(page)
        template_names.add(template_name)
        page_to_template[page_key] = template_name

    templates = _collect_template_manifests(site, template_names)
    page_hashes: dict[str, str] = {}
    for page_key, template_name in page_to_template.items():
        template_info = templates.get(template_name, {})
        template_hash = template_info.get("manifest_hash", "")
        page_hashes[page_key] = _hash_payload(
            {
                "content_hash": content_hashes.get(page_key, ""),
                "template": template_name,
                "template_hash": template_hash,
            }
        )

    root_hash = _hash_payload(
        {
            "content": content_hashes,
            "templates": {name: data.get("manifest_hash", "") for name, data in templates.items()},
            "pages": page_hashes,
        }
    )
    return {
        "version": _MERKLE_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "root_hash": root_hash,
        "content_hashes": content_hashes,
        "templates": templates,
        "page_hashes": page_hashes,
    }


def _hash_file(path: Path) -> str:
    try:
        return _hash_bytes(path.read_bytes())
    except OSError:
        return ""


def _collect_template_manifests(site: Any, template_names: set[str]) -> dict[str, dict[str, Any]]:
    engine = getattr(site, "template_engine", None)
    if engine is None:
        return {}
    get_manifest = getattr(engine, "get_template_manifest", None)
    if not callable(get_manifest):
        return {}

    manifests: dict[str, dict[str, Any]] = {}
    for template_name in sorted(template_names):
        try:
            manifest = get_manifest(template_name)
        except Exception:
            manifest = None
        if not isinstance(manifest, dict):
            manifests[template_name] = {"manifest_hash": "", "manifest": None}
            continue
        safe_manifest = _canonicalize(manifest)
        manifest_hash = _hash_payload(safe_manifest)
        manifests[template_name] = {"manifest_hash": manifest_hash, "manifest": safe_manifest}
    return manifests


def _compare_snapshots(previous: dict[str, Any] | None, current: dict[str, Any]) -> MerkleAdvisory:
    current_content = _as_dict(current.get("content_hashes"))
    current_templates = _as_dict(current.get("templates"))
    current_page_hashes = _as_dict(current.get("page_hashes"))

    if previous is None:
        return MerkleAdvisory(
            dirty_content=frozenset(current_content.keys()),
            dirty_templates=frozenset(current_templates.keys()),
            dirty_pages=frozenset(current_page_hashes.keys()),
            previous_root=None,
            current_root=str(current.get("root_hash", "")),
        )

    prev_content = _as_dict(previous.get("content_hashes"))
    prev_templates = _as_dict(previous.get("templates"))
    prev_page_hashes = _as_dict(previous.get("page_hashes"))

    dirty_content = {
        key for key, value in current_content.items() if prev_content.get(key) != value
    } | (prev_content.keys() - current_content.keys())

    dirty_templates = {
        key
        for key, value in current_templates.items()
        if _manifest_hash(prev_templates.get(key)) != _manifest_hash(value)
    } | (prev_templates.keys() - current_templates.keys())

    dirty_pages = {
        key for key, value in current_page_hashes.items() if prev_page_hashes.get(key) != value
    } | (prev_page_hashes.keys() - current_page_hashes.keys())

    return MerkleAdvisory(
        dirty_content=frozenset(dirty_content),
        dirty_templates=frozenset(dirty_templates),
        dirty_pages=frozenset(dirty_pages),
        previous_root=str(previous.get("root_hash", "")),
        current_root=str(current.get("root_hash", "")),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _manifest_hash(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    raw = value.get("manifest_hash")
    return raw if isinstance(raw, str) else ""


def _canonicalize(value: Any) -> Any:
    """Convert values to deterministic JSON-safe structures."""
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_canonicalize(item) for item in value)
    return value
