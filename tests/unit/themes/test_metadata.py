from __future__ import annotations


def test_load_theme_metadata_normalizes_known_fields(tmp_path):
    from bengal.themes.metadata import load_theme_metadata

    theme_path = tmp_path / "theme"
    theme_path.mkdir()
    (theme_path / "theme.toml").write_text(
        "\n".join(
            [
                'name = "docs"',
                'version = "1.2.3"',
                'description = "Documentation theme"',
                'author = "Bengal"',
                'license = "MIT"',
                'extends = "default"',
                'libraries = ["chirp_ui"]',
            ]
        ),
        encoding="utf-8",
    )

    result = load_theme_metadata(theme_path)

    assert result.errors == []
    assert result.metadata.name == "docs"
    assert result.metadata.version == "1.2.3"
    assert result.metadata.parent_slug == "default"
    assert result.metadata.libraries == ("chirp_ui",)


def test_load_theme_metadata_reports_malformed_fields(tmp_path):
    from bengal.themes.metadata import load_theme_metadata

    theme_path = tmp_path / "theme"
    theme_path.mkdir()
    (theme_path / "theme.toml").write_text(
        'name = ["bad"]\nlibraries = "chirp_ui"\n',
        encoding="utf-8",
    )

    result = load_theme_metadata(theme_path)

    assert [issue.level for issue in result.errors] == ["error", "error"]
    assert "name" in result.errors[0].message
    assert "libraries" in result.errors[1].message


def test_load_theme_metadata_reports_missing_manifest(tmp_path):
    from bengal.themes.metadata import load_theme_metadata

    theme_path = tmp_path / "theme"
    theme_path.mkdir()

    result = load_theme_metadata(theme_path)

    assert len(result.errors) == 1
    assert result.errors[0].message == "Missing theme.toml or theme.yaml"
