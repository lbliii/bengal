from __future__ import annotations


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
