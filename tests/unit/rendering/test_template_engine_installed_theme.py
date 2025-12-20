from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from bengal.core.site import Site


def test_engine_resolves_installed_theme_templates(tmp_path, monkeypatch):
    """Test TemplateEngine can load templates from installed theme - using Mock objects"""
    # Site root
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "templates").mkdir()
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    # Create mock theme directory
    theme_root = tmp_path / "mock_theme_acme"
    (theme_root / "templates").mkdir(parents=True)
    (theme_root / "assets").mkdir(parents=True)
    (theme_root / "templates" / "page.html").write_text("<main>ACME PAGE</main>", encoding="utf-8")
    (theme_root / "theme.toml").write_text('name="acme"\nextends="default"\n', encoding="utf-8")

    # Create a Mock ThemePackage
    mock_pkg = Mock()
    mock_pkg.slug = "acme"
    mock_pkg.package = "bengal_themes.acme"
    mock_pkg.distribution = "bengal-theme-acme"
    mock_pkg.version = "1.0.0"
    mock_pkg.templates_exists.return_value = True
    mock_pkg.assets_exists.return_value = True
    mock_pkg.resolve_resource_path = (
        lambda resource: theme_root / resource if (theme_root / resource).exists() else None
    )

    # Mock get_theme_package
    def mock_get_theme_package(slug: str):
        return mock_pkg if slug == "acme" else None

    # Patch the theme registry BEFORE creating Site
    import bengal.core.theme.registry

    monkeypatch.setattr(bengal.core.theme.registry, "get_theme_package", mock_get_theme_package)
    monkeypatch.setattr(
        bengal.core.theme.registry, "get_installed_themes", lambda: {"acme": mock_pkg}
    )

    from bengal.rendering.template_engine import TemplateEngine

    site = Site.from_config(site_root)
    engine = TemplateEngine(site)

    # Test that page.html from installed theme can be loaded
    mock_page = SimpleNamespace(url="/test/", title="Test", related_posts=[], metadata={})
    html = engine.render("page.html", {"title": "x", "page": mock_page})
    assert "ACME PAGE" in html


def test_extends_read_from_installed_theme(tmp_path, monkeypatch):
    """Test theme chain resolution with installed theme - using Mock objects"""
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "templates").mkdir()
    (site_root / "bengal.toml").write_text('[site]\nname="t"\ntheme="acme"\n', encoding="utf-8")

    # Create mock theme directory
    theme_root = tmp_path / "mock_theme_acme"
    (theme_root / "templates").mkdir(parents=True)
    (theme_root / "theme.toml").write_text('name="acme"\nextends="default"\n', encoding="utf-8")

    # Create a Mock ThemePackage
    mock_pkg = Mock()
    mock_pkg.slug = "acme"
    mock_pkg.package = "bengal_themes.acme"
    mock_pkg.distribution = "bengal-theme-acme"
    mock_pkg.version = "1.0.0"
    mock_pkg.manifest_exists.return_value = True
    mock_pkg.resolve_resource_path = (
        lambda resource: theme_root / resource if (theme_root / resource).exists() else None
    )

    def mock_get_theme_package(slug: str):
        return mock_pkg if slug == "acme" else None

    import bengal.core.theme.registry

    monkeypatch.setattr(bengal.core.theme.registry, "get_theme_package", mock_get_theme_package)
    monkeypatch.setattr(
        bengal.core.theme.registry, "get_installed_themes", lambda: {"acme": mock_pkg}
    )

    from bengal.rendering.template_engine import TemplateEngine

    site = Site.from_config(site_root)
    engine = TemplateEngine(site)
    chain = engine._resolve_theme_chain("acme")
    assert chain[0] == "acme"
