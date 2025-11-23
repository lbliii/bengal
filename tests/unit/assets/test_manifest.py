from __future__ import annotations

from pathlib import Path

from bengal.assets.manifest import AssetManifest


def test_manifest_roundtrip(tmp_path: Path) -> None:
    """Asset manifests should serialize deterministically and reload cleanly."""
    manifest = AssetManifest()
    manifest.set_entry(
        logical_path="css/style.css",
        output_path="assets/css/style.12345678.css",
        fingerprint="12345678",
        size_bytes=1024,
        updated_at=1_700_000_000.0,
    )

    manifest_path = tmp_path / "asset-manifest.json"
    manifest.write(manifest_path)

    loaded = AssetManifest.load(manifest_path)
    assert loaded is not None
    entry = loaded.get("css/style.css")
    assert entry is not None
    assert entry.output_path == "assets/css/style.12345678.css"
    assert entry.fingerprint == "12345678"
    assert entry.size_bytes == 1024
    assert entry.updated_at.endswith("Z")
