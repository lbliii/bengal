from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.assets.manifest import AssetManifest
from bengal.rendering.assets import resolve_asset_url

if TYPE_CHECKING:
    from pathlib import Path


class DummySite:
    def __init__(self, root_path: Path, baseurl: str | None = ""):
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config = {"baseurl": baseurl or ""}
        self.theme = "default"
        self._baseurl = baseurl or ""
        self.dev_mode = False
        self.versioning_enabled = False
        self.versions: list[str] = []

    @property
    def baseurl(self) -> str:
        """Return baseurl (uses cached value or config)."""
        return self._baseurl


def test_asset_url_no_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="")
    url = resolve_asset_url("css/style.css", site)
    assert url == "/assets/css/style.css"


def test_asset_url_path_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="/bengal")
    url = resolve_asset_url("css/style.css", site)
    assert url == "/bengal/assets/css/style.css"


def test_asset_url_absolute_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="https://docs.example.com/sub")
    url = resolve_asset_url("css/style.css", site)
    assert url == "https://docs.example.com/sub/assets/css/style.css"


def test_asset_url_prefers_fingerprinted_when_present_with_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="/bengal")

    # Write a manifest with the fingerprinted entry
    manifest = AssetManifest()
    manifest.set_entry(
        logical_path="css/style.css",
        output_path="assets/css/style.12345678.css",
        fingerprint="12345678",
        size_bytes=100,
        updated_at=1_700_000_000.0,
    )
    manifest.write(site.output_dir / "asset-manifest.json")

    url = resolve_asset_url("css/style.css", site)
    assert url.endswith("/assets/css/style.12345678.css")
    assert url.startswith("/bengal/")


def test_asset_url_respects_manifest_mapping(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="/docs")
    manifest = AssetManifest()
    manifest.set_entry(
        logical_path="css/style.css",
        output_path="assets/css/style.deadbeef.css",
        fingerprint="deadbeef",
        size_bytes=512,
        updated_at=1_700_000_000.0,
    )
    manifest.write(site.output_dir / "asset-manifest.json")

    url = resolve_asset_url("css/style.css", site)
    assert url == "/docs/assets/css/style.deadbeef.css"
