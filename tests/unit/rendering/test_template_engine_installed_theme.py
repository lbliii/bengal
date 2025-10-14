import sys
from pathlib import Path
from types import SimpleNamespace

from bengal.core.site import Site


def _make_fake_theme(tmp_path: Path, slug: str = "acme", extends: str | None = "default"):
    pkg_root = tmp_path / "bengal_themes" / slug
    (pkg_root / "templates" / "partials").mkdir(parents=True)
    (pkg_root / "assets" / "css").mkdir(parents=True)
    (pkg_root / "dev" / "components").mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("__all__ = []", encoding="utf-8")
    (pkg_root / "templates" / "page.html").write_text("<main>ACME PAGE</main>", encoding="utf-8")
    (pkg_root / "templates" / "partials" / "box.html").write_text(
        "<div>BOX</div>", encoding="utf-8"
    )
    (pkg_root / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
    if extends:
        (pkg_root / "theme.toml").write_text(
            f'name="{slug}"\nextends="{extends}"\n', encoding="utf-8"
        )
    else:
        (pkg_root / "theme.toml").write_text(f'name="{slug}"\n', encoding="utf-8")
    (tmp_path / "bengal_themes" / "__init__.py").write_text("__all__ = []", encoding="utf-8")
    return f"bengal_themes.{slug}", pkg_root


def test_engine_resolves_installed_theme_templates(tmp_path, monkeypatch):
    # Site root
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "templates").mkdir()
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    pkg, _root = _make_fake_theme(tmp_path, slug="acme")
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    # Fake entry points
    from importlib import metadata

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)

    from bengal.rendering.template_engine import TemplateEngine

    site = Site.from_config(site_root)
    engine = TemplateEngine(site)
    # page.html exists only in installed theme
    mock_page = SimpleNamespace(url="/test/", title="Test Page", metadata={})
    html = engine.render("page.html", {"title": "x", "page": mock_page})
    assert "ACME PAGE" in html


def test_extends_read_from_installed_theme(tmp_path, monkeypatch):
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "templates").mkdir()
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    pkg, _root = _make_fake_theme(tmp_path, slug="acme", extends="default")
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    from importlib import metadata

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)

    from bengal.rendering.template_engine import TemplateEngine

    site = Site.from_config(site_root)
    engine = TemplateEngine(site)
    chain = engine._resolve_theme_chain("acme")
    assert chain[0] == "acme"
