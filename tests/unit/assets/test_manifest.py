from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.assets.manifest import AssetManifest, inspect_asset_outputs

if TYPE_CHECKING:
    from pathlib import Path


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


def test_inspect_asset_outputs_detects_missing_manifest_output(tmp_path: Path) -> None:
    """Missing manifest-referenced outputs are reported."""
    manifest = AssetManifest()
    manifest.set_entry(
        logical_path="css/style.css",
        output_path="assets/css/style.css",
        fingerprint=None,
        size_bytes=None,
        updated_at=None,
    )
    manifest.set_entry(
        logical_path="js/main.js",
        output_path="assets/js/main.js",
        fingerprint=None,
        size_bytes=None,
        updated_at=None,
    )
    manifest.write(tmp_path / "asset-manifest.json")

    css_dir = tmp_path / "assets" / "css"
    css_dir.mkdir(parents=True)
    (css_dir / "style.css").write_text("body {}")

    integrity = inspect_asset_outputs(tmp_path)
    assert integrity.is_complete is False
    assert integrity.manifest_present is True
    assert integrity.total_entries == 2
    assert integrity.missing_count == 1
    assert integrity.missing_outputs == ("assets/js/main.js",)


def test_inspect_asset_outputs_accepts_complete_manifest_outputs(tmp_path: Path) -> None:
    """Complete manifest-backed output is treated as healthy."""
    manifest = AssetManifest()
    manifest.set_entry(
        logical_path="css/style.css",
        output_path="assets/css/style.css",
        fingerprint=None,
        size_bytes=None,
        updated_at=None,
    )
    manifest.write(tmp_path / "asset-manifest.json")

    css_dir = tmp_path / "assets" / "css"
    css_dir.mkdir(parents=True)
    (css_dir / "style.css").write_text("body {}")

    integrity = inspect_asset_outputs(tmp_path)
    assert integrity.is_complete is True
    assert integrity.missing_count == 0
