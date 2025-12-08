from __future__ import annotations


from pathlib import Path

from bengal.core.theme import Theme
from bengal.rendering.template_engine import TemplateEngine


class DummySite:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config = {}
        self.theme = "default"

    @property
    def theme_config(self) -> Theme:
        """Return a default Theme for testing."""
        return Theme(name=self.theme)


def test_asset_url_prefers_hashed_file(tmp_path: Path):
    site = DummySite(tmp_path)
    engine = TemplateEngine(site)

    # Simulate built files
    out = site.output_dir / "assets" / "css"
    out.mkdir(parents=True, exist_ok=True)
    (out / "style.css").write_text("body{}", encoding="utf-8")
    (out / "style.abcdef12.css").write_text("body{color:black}", encoding="utf-8")

    url = engine._asset_url("css/style.css")
    assert url.endswith("/assets/css/style.abcdef12.css")
