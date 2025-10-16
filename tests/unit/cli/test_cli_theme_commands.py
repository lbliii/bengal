import sys
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from bengal.cli import main as cli_main


def _fake_theme(tmp_path: Path, slug: str = "acme"):
    pkg_root = tmp_path / "bengal_themes" / slug
    (pkg_root / "templates").mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("__all__=[]", encoding="utf-8")
    (pkg_root / "templates" / "a.html").write_text("A", encoding="utf-8")
    (tmp_path / "bengal_themes" / "__init__.py").write_text("__all__=[]", encoding="utf-8")
    return f"bengal_themes.{slug}", pkg_root


def test_theme_list_and_info(tmp_path, monkeypatch):
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "bengal.toml").write_text('[site]\nname="t"\n', encoding="utf-8")

    pkg, _ = _fake_theme(tmp_path)
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    from importlib import metadata

    from bengal.utils.theme_registry import clear_theme_cache

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)
    clear_theme_cache()

    r = CliRunner().invoke(cli_main, ["utils", "theme", "list", str(site_root)])
    assert r.exit_code == 0
    assert "Installed themes:" in r.stdout
    assert "acme" in r.stdout

    r2 = CliRunner().invoke(cli_main, ["utils", "theme", "info", "acme", str(site_root)])
    assert r2.exit_code == 0
    assert "Theme: acme" in r2.stdout


def test_theme_discover_lists_templates(tmp_path, monkeypatch):
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    pkg, _ = _fake_theme(tmp_path)
    sys.path.insert(0, str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))

    from importlib import metadata

    from bengal.utils.theme_registry import clear_theme_cache

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [SimpleNamespace(name="acme", value=pkg)]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)
    clear_theme_cache()

    r = CliRunner().invoke(cli_main, ["utils", "theme", "discover", str(site_root)])
    assert r.exit_code == 0
    assert "a.html" in r.stdout
