from __future__ import annotations


def test_theme_resolver_prefers_site_local_over_bundled(tmp_path):
    from bengal.themes.resolver import ThemeResolver

    theme_path = tmp_path / "themes" / "default"
    (theme_path / "templates").mkdir(parents=True)
    (theme_path / "theme.toml").write_text(
        'name = "Project default"\nversion = "9.0.0"\n',
        encoding="utf-8",
    )

    record = ThemeResolver(tmp_path).resolve("default")

    assert record is not None
    assert record.source == "site-local"
    assert record.name == "Project default"
    assert record.path == theme_path


def test_theme_resolver_lists_bundled_themes_without_duplicates(tmp_path):
    from bengal.themes.resolver import ThemeResolver

    # `default` is the bundled slug; a site-local theme with the same slug must
    # shadow the bundled one and appear exactly once in iter_available so the
    # dedup assertion fails if same-slug deduplication across the
    # site-local/bundled layers regresses.
    theme_path = tmp_path / "themes" / "default"
    (theme_path / "templates").mkdir(parents=True)
    (theme_path / "theme.toml").write_text('name = "Local Default"\n', encoding="utf-8")

    records = ThemeResolver(tmp_path).iter_available()
    by_slug = {record.slug: record for record in records}

    assert by_slug["default"].source == "site-local"
    assert by_slug["default"].name == "Local Default"
    assert [record.slug for record in records].count("default") == 1


def test_theme_resolver_accepts_explicit_theme_path(tmp_path):
    from bengal.themes.resolver import ThemeResolver

    theme_path = tmp_path / "loose-theme"
    (theme_path / "templates").mkdir(parents=True)
    (theme_path / "theme.yaml").write_text("name: Loose Theme\n", encoding="utf-8")

    record = ThemeResolver(tmp_path).resolve(str(theme_path))

    assert record is not None
    assert record.slug == "loose-theme"
    assert record.source == "path"
    assert record.name == "Loose Theme"


def test_theme_resolver_does_not_treat_plain_directory_as_slug_path(tmp_path):
    from bengal.themes.resolver import ThemeResolver

    docs_dir = tmp_path / "docs"
    (docs_dir / "templates").mkdir(parents=True)
    (docs_dir / "theme.toml").write_text('name = "Plain Docs Directory"\n', encoding="utf-8")
    theme_path = tmp_path / "themes" / "docs"
    (theme_path / "templates").mkdir(parents=True)
    (theme_path / "theme.toml").write_text('name = "Docs Theme"\n', encoding="utf-8")

    record = ThemeResolver(tmp_path).resolve("docs")

    assert record is not None
    assert record.source == "site-local"
    assert record.path == theme_path
