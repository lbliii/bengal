import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.utils.theme_registry import (
    clear_theme_cache,
    get_installed_themes,
    get_theme_package,
)


def _make_fake_theme_package(tmp_path: Path, slug: str = "acme") -> tuple[str, Path]:
    root = tmp_path / "bengal_themes" / slug
    (root / "templates").mkdir(parents=True)
    (root / "assets").mkdir(parents=True)
    (root / "dev" / "components").mkdir(parents=True)
    (root / "__init__.py").write_text("__all__ = []", encoding="utf-8")
    (root / "templates" / "index.html").write_text("<h1>ACME</h1>", encoding="utf-8")
    (root / "assets" / "style.css").write_text("body{}", encoding="utf-8")
    (root / "theme.toml").write_text('name="acme"\nextends="default"\n', encoding="utf-8")
    pkg_root = tmp_path / "bengal_themes"
    (pkg_root / "__init__.py").write_text("__all__ = []", encoding="utf-8")
    return f"bengal_themes.{slug}", root


@pytest.mark.xdist_group(name="theme_registry_import")
def test_get_installed_themes_discovers_entry_point(tmp_path, monkeypatch):
    pkg, root = _make_fake_theme_package(tmp_path, slug="acme")

    # Make importable
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    # Fake entry points
    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    # Fake distribution metadata (best-effort)
    def fake_packages_distributions():
        return {"bengal_themes": ["bengal-theme-acme"]}

    def fake_version(dist_name):
        return "1.2.3"

    from importlib import metadata

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)
    monkeypatch.setattr(metadata, "packages_distributions", fake_packages_distributions)
    monkeypatch.setattr(metadata, "version", fake_version)

    clear_theme_cache()
    themes = get_installed_themes()
    assert "acme" in themes
    pkginfo = get_theme_package("acme")
    assert pkginfo is not None
    assert pkginfo.package == pkg

    # Resources exist
    assert pkginfo.templates_exists()
    assert pkginfo.assets_exists()
    assert pkginfo.manifest_exists()

    # Resolving paths yields real fs paths
    tpath = pkginfo.resolve_resource_path("templates")
    apath = pkginfo.resolve_resource_path("assets")
    mpath = pkginfo.resolve_resource_path("theme.toml")
    assert tpath and tpath.exists()
    assert apath and apath.exists()
    assert mpath and mpath.exists()
