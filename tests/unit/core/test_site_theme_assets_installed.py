from unittest.mock import Mock

from bengal.core.site import Site


def test_site_assets_include_installed_theme(tmp_path, monkeypatch):
    """Test Site includes assets from installed theme - using Mock objects"""
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    # Create mock theme directory
    theme_root = tmp_path / "mock_theme_acme"
    (theme_root / "assets" / "css").mkdir(parents=True)
    (theme_root / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
    (theme_root / "theme.toml").write_text('name="acme"\n', encoding="utf-8")

    # Create a Mock ThemePackage
    mock_pkg = Mock()
    mock_pkg.slug = "acme"
    mock_pkg.package = "bengal_themes.acme"
    mock_pkg.distribution = "bengal-theme-acme"
    mock_pkg.version = "1.0.0"
    mock_pkg.assets_exists.return_value = True
    mock_pkg.resolve_resource_path = (
        lambda resource: theme_root / resource if (theme_root / resource).exists() else None
    )

    def mock_get_theme_package(slug: str):
        return mock_pkg if slug == "acme" else None

    import bengal.utils.theme_registry

    monkeypatch.setattr(bengal.utils.theme_registry, "get_theme_package", mock_get_theme_package)
    monkeypatch.setattr(
        bengal.utils.theme_registry, "get_installed_themes", lambda: {"acme": mock_pkg}
    )

    site = Site.from_config(site_root)
    dirs = site._get_theme_assets_chain()
    paths = [str(p) for p in dirs]

    # Should include the mock theme assets directory
    assert any("mock_theme_acme" in p and "assets" in p for p in paths)
