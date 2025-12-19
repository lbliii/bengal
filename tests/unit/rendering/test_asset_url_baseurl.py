from __future__ import annotations

from pathlib import Path

from bengal.assets.manifest import AssetManifest
from bengal.core.theme import Theme
from bengal.rendering.template_engine import TemplateEngine


class DummySite:
    def __init__(self, root_path: Path, baseurl: str | None = ""):
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config = {"baseurl": baseurl or ""}
        self.theme = "default"
        # Required Site attributes for template engine
        self.dev_mode = False
        self.versioning_enabled = False
        self.versions: list[str] = []
        self._bengal_template_dirs_cache = None
        self._bengal_theme_chain_cache = None
        self._bengal_template_metadata_cache = None
        self._asset_manifest_fallbacks_global: set[str] = set()
        self._asset_manifest_fallbacks_lock = None

    @property
    def theme_config(self) -> Theme:
        """Return a default Theme for testing."""
        return Theme(name=self.theme)


def test_asset_url_no_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="")
    engine = TemplateEngine(site)
    url = engine._asset_url("css/style.css")
    assert url == "/assets/css/style.css"


def test_asset_url_path_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="/bengal")
    engine = TemplateEngine(site)
    url = engine._asset_url("css/style.css")
    assert url == "/bengal/assets/css/style.css"


def test_asset_url_absolute_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="https://docs.example.com/sub")
    engine = TemplateEngine(site)
    url = engine._asset_url("css/style.css")
    assert url == "https://docs.example.com/sub/assets/css/style.css"


def test_asset_url_prefers_fingerprinted_when_present_with_baseurl(tmp_path: Path):
    site = DummySite(tmp_path, baseurl="/bengal")
    engine = TemplateEngine(site)

    out = site.output_dir / "assets" / "css"
    out.mkdir(parents=True, exist_ok=True)
    (out / "style.css").write_text("body{}", encoding="utf-8")
    (out / "style.12345678.css").write_text("body{color:black}", encoding="utf-8")

    url = engine._asset_url("css/style.css")
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

    engine = TemplateEngine(site)
    url = engine._asset_url("css/style.css")
    assert url == "/docs/assets/css/style.deadbeef.css"
