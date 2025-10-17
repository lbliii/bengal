from pathlib import Path

from bengal.rendering.template_engine import TemplateEngine


class DummySite:
    def __init__(self, root_path: Path, baseurl: str | None = ""):
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config = {"baseurl": baseurl or ""}
        self.theme = "default"


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
