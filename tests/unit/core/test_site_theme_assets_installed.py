import sys
from pathlib import Path
from types import SimpleNamespace

from bengal.core.site import Site


def _make_fake_theme(tmp_path: Path, slug: str = "acme"):
    pkg_root = tmp_path / "bengal_themes" / slug
    (pkg_root / "assets" / "css").mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("__all__=[]", encoding="utf-8")
    (pkg_root / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "bengal_themes" / "__init__.py").write_text("__all__=[]", encoding="utf-8")
    return f"bengal_themes.{slug}", pkg_root


def test_site_assets_include_installed_theme(tmp_path, monkeypatch):
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    pkg, _root = _make_fake_theme(tmp_path, slug="acme")
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    from importlib import metadata

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)

    site = Site.from_config(site_root)
    dirs = site._get_theme_assets_chain()
    paths = [str(p) for p in dirs]
    assert any("bengal_themes" in p and "/assets" in p for p in paths)
