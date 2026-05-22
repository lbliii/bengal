from __future__ import annotations

from types import SimpleNamespace


def test_theme_new_site_mode_creates_site_local_theme(tmp_path):
    from bengal.cli.milo_commands.theme import theme_new, theme_validate
    from bengal.output import reset_cli_output

    reset_cli_output()
    result = theme_new("docs-theme", output=str(tmp_path))

    theme_path = tmp_path / "themes" / "docs-theme"
    assert result["path"] == str(theme_path)
    assert result["theme_path"] == str(theme_path)
    assert (theme_path / "theme.toml").is_file()
    assert (theme_path / "templates" / "base.html").is_file()
    assert (theme_path / "templates" / "home.html").is_file()
    assert (theme_path / "templates" / "page.html").is_file()
    assert (theme_path / "assets" / "css" / "style.css").is_file()

    validation = theme_validate(str(theme_path))
    assert validation == {"path": str(theme_path), "valid": True}


def test_theme_new_package_mode_creates_installable_theme_skeleton(tmp_path):
    from bengal.cli.milo_commands.theme import theme_new
    from bengal.output import reset_cli_output

    reset_cli_output()
    result = theme_new("docs-theme", mode="package", output=str(tmp_path))

    package_root = tmp_path / "bengal-theme-docs-theme"
    theme_path = package_root / "bengal_themes" / "docs_theme"
    pyproject = (package_root / "pyproject.toml").read_text(encoding="utf-8")

    assert result["path"] == str(package_root)
    assert result["theme_path"] == str(theme_path)
    assert 'docs-theme = "bengal_themes.docs_theme"' in pyproject
    assert (theme_path / "__init__.py").is_file()
    assert (theme_path / "theme.toml").is_file()
    assert (theme_path / "templates" / "page.html").is_file()


def test_theme_validate_reports_invalid_manifest(tmp_path):
    import pytest

    from bengal.cli.milo_commands.theme import theme_validate
    from bengal.output import reset_cli_output

    reset_cli_output()
    theme_path = tmp_path / "themes" / "broken"
    (theme_path / "templates").mkdir(parents=True)
    (theme_path / "templates" / "base.html").write_text("", encoding="utf-8")
    (theme_path / "templates" / "home.html").write_text("", encoding="utf-8")
    (theme_path / "templates" / "page.html").write_text("", encoding="utf-8")
    (theme_path / "theme.toml").write_text("name = [", encoding="utf-8")

    with pytest.raises(SystemExit):
        theme_validate(str(theme_path))


def test_theme_preview_reports_active_theme_before_serving(monkeypatch, tmp_path):
    from bengal.cli.milo_commands.theme import theme_preview
    from bengal.output import reset_cli_output

    reset_cli_output()
    theme_path = tmp_path / "themes" / "docs"
    (theme_path / "templates").mkdir(parents=True)
    for template in ["base.html", "home.html", "page.html"]:
        (theme_path / "templates" / template).write_text("", encoding="utf-8")
    (theme_path / "assets").mkdir()
    (theme_path / "theme.toml").write_text('name = "Docs"\n', encoding="utf-8")

    fake_site = SimpleNamespace(root_path=tmp_path, config={"build": {"theme": "docs"}})
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda *a, **kw: fake_site)

    called = {}

    def fake_serve(**kwargs):
        called.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr("bengal.cli.milo_commands.serve.serve", fake_serve)

    result = theme_preview(source=str(tmp_path), open_browser=False)

    assert result == {"status": "ok"}
    assert called["source"] == str(tmp_path)
    assert called["profile"] == "theme-dev"
    assert called["watch"] is True
    assert called["auto_port"] is True


def test_theme_preview_fails_before_serving_missing_active_theme(monkeypatch, tmp_path):
    import pytest

    from bengal.cli.milo_commands.theme import theme_preview
    from bengal.output import reset_cli_output

    reset_cli_output()
    fake_site = SimpleNamespace(root_path=tmp_path, config={"build": {"theme": "missing"}})
    monkeypatch.setattr("bengal.cli.utils.load_site_from_cli", lambda *a, **kw: fake_site)

    def fake_serve(**kwargs):
        raise AssertionError("serve should not start when the active theme is missing")

    monkeypatch.setattr("bengal.cli.milo_commands.serve.serve", fake_serve)

    with pytest.raises(SystemExit):
        theme_preview(source=str(tmp_path), open_browser=False)
