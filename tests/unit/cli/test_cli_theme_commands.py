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


class TestThemeInstallSecurity:
    """Security tests for theme install package name validation."""

    def test_rejects_path_traversal(self):
        """Test that path traversal attempts are rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "../malicious"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_absolute_path(self):
        """Test that absolute paths are rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "/etc/passwd"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_shell_injection(self):
        """Test that shell injection attempts are rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "theme; rm -rf /"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_backtick_injection(self):
        """Test that backtick command substitution is rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "theme`whoami`"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_dollar_injection(self):
        """Test that dollar sign command substitution is rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "theme$(whoami)"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_pipe_injection(self):
        """Test that pipe characters are rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "theme|cat /etc/passwd"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_name_starting_with_number(self):
        """Test that names starting with numbers are rejected."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "123theme"])
        assert r.exit_code != 0
        assert "Invalid package name" in r.output

    def test_rejects_name_starting_with_hyphen(self):
        """Test that names starting with hyphen are rejected.

        Note: Click's option parsing also catches this case, rejecting it as
        an invalid option. Either way, malicious names are blocked.
        """
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "-malicious"])
        assert r.exit_code != 0
        # Click may reject as "No such option" or our validation may reject
        assert "Invalid package name" in r.output or "No such option" in r.output

    def test_accepts_valid_package_name(self):
        """Test that valid package names pass validation."""
        # Note: This will fail at pip install stage, but should pass validation
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "bengal-theme-test"])
        # Either succeeds at validation (and fails at pip), or warns about non-standard
        # The key is it shouldn't fail with "Invalid package name"
        assert "Invalid package name" not in r.output

    def test_accepts_name_with_dots(self):
        """Test that names with dots (version specifiers) pass validation."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "bengal-theme-test.1.0"])
        assert "Invalid package name" not in r.output

    def test_accepts_name_with_underscores(self):
        """Test that names with underscores pass validation."""
        r = CliRunner().invoke(cli_main, ["utils", "theme", "install", "bengal_theme_test"])
        assert "Invalid package name" not in r.output
