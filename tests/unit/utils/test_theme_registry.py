from types import SimpleNamespace
from unittest.mock import Mock

import bengal.core.theme.registry as theme_registry_module
from bengal.core.theme import get_installed_themes, get_theme_package


def test_get_installed_themes_discovers_entry_point(monkeypatch, tmp_path):
    """Test theme discovery via entry points - mocked to avoid sys.path manipulation"""
    from importlib import metadata

    # Create a real directory structure for the mock to reference
    theme_root = tmp_path / "mock_theme"
    (theme_root / "templates").mkdir(parents=True)
    (theme_root / "assets").mkdir(parents=True)
    (theme_root / "templates" / "page.html").write_text("<h1>TEST</h1>", encoding="utf-8")
    (theme_root / "assets" / "style.css").write_text("body{}", encoding="utf-8")
    (theme_root / "theme.toml").write_text('name="acme"\n', encoding="utf-8")

    # Mock entry points
    fake_entry = SimpleNamespace(name="acme", value="bengal_themes.acme")

    def fake_entry_points(group=None):
        if group == "bengal.themes":
            return [fake_entry]
        return []

    # Mock metadata functions
    def fake_packages_distributions():
        return {"bengal_themes": ["bengal-theme-acme"]}

    def fake_version(dist_name):
        return "1.2.3"

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)
    monkeypatch.setattr(metadata, "packages_distributions", fake_packages_distributions)
    monkeypatch.setattr(metadata, "version", fake_version)

    # Create a Mock ThemePackage
    def create_mock_pkg(slug, package, distribution, version):
        mock_pkg = Mock()
        mock_pkg.slug = slug
        mock_pkg.package = package
        mock_pkg.distribution = distribution
        mock_pkg.version = version
        mock_pkg.templates_exists.return_value = (theme_root / "templates").is_dir()
        mock_pkg.assets_exists.return_value = (theme_root / "assets").is_dir()
        mock_pkg.manifest_exists.return_value = (theme_root / "theme.toml").is_file()
        mock_pkg.resolve_resource_path = (
            lambda resource: theme_root / resource if (theme_root / resource).exists() else None
        )
        return mock_pkg

    # Mock ThemePackage constructor
    monkeypatch.setattr(
        theme_registry_module,
        "ThemePackage",
        lambda slug, package, distribution, version: create_mock_pkg(
            slug, package, distribution, version
        ),
    )

    # Test discovery
    themes = get_installed_themes()
    assert "acme" in themes

    # Test retrieval
    pkginfo = get_theme_package("acme")
    assert pkginfo is not None
    assert pkginfo.package == "bengal_themes.acme"

    # Test resource checks
    assert pkginfo.templates_exists()
    assert pkginfo.assets_exists()
    assert pkginfo.manifest_exists()

    # Test path resolution
    tpath = pkginfo.resolve_resource_path("templates")
    apath = pkginfo.resolve_resource_path("assets")
    mpath = pkginfo.resolve_resource_path("theme.toml")
    assert tpath and tpath.exists()
    assert apath and apath.exists()
    assert mpath and mpath.exists()
