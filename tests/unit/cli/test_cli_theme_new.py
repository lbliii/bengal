from click.testing import CliRunner

from bengal.cli import main as cli_main


def test_theme_new_site_scaffold(tmp_path):
    site_root = tmp_path / "site"
    site_root.mkdir()
    r = CliRunner().invoke(
        cli_main,
        ["theme", "new", "acme", "--mode", "site", "--output", str(site_root)],
    )
    assert r.exit_code == 0, r.output
    theme_dir = site_root / "themes" / "acme"
    assert (theme_dir / "templates" / "page.html").exists()
    assert (theme_dir / "assets" / "css" / "style.css").exists()
    assert (theme_dir / "theme.toml").exists()


def test_theme_new_package_scaffold(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = CliRunner().invoke(
        cli_main,
        ["theme", "new", "acme", "--mode", "package", "--output", str(out)],
    )
    assert r.exit_code == 0, r.output
    pkg = out / "bengal-theme-acme"
    assert (pkg / "pyproject.toml").exists()
    assert (pkg / "bengal_themes" / "acme" / "templates" / "page.html").exists()
    assert (pkg / "bengal_themes" / "acme" / "assets" / "css" / "style.css").exists()
    assert (pkg / "bengal_themes" / "acme" / "theme.toml").exists()
