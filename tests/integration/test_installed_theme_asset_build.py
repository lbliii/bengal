from __future__ import annotations

from textwrap import dedent

from bengal.assets.manifest import AssetManifest
from bengal.core.site import Site
from bengal.core.theme.registry import ThemePackage
from bengal.orchestration.build.options import BuildOptions


def _write_text(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_full_build_includes_external_theme_assets(tmp_path, monkeypatch) -> None:
    """Full builds include assets from themes installed outside the site root."""
    site_root = tmp_path / "site"
    (site_root / "content").mkdir(parents=True)
    _write_text(
        site_root / "content" / "_index.md",
        dedent(
            """\
            ---
            title: Home
            ---

            External theme asset regression test.
            """
        ),
    )
    _write_text(
        site_root / "bengal.toml",
        dedent(
            """\
            [site]
            title = "Installed Theme Asset Build"
            theme = "acme"
            """
        ),
    )

    package_root = tmp_path / "external_theme_pkg"
    theme_pkg_dir = package_root / "bengal_themes" / "acme"
    _write_text(package_root / "bengal_themes" / "__init__.py", "")
    _write_text(theme_pkg_dir / "__init__.py", "")
    _write_text(
        theme_pkg_dir / "theme.toml",
        dedent(
            """\
            name = "acme"
            extends = "default"
            """
        ),
    )
    (theme_pkg_dir / "templates").mkdir(parents=True)
    _write_text(
        theme_pkg_dir / "assets" / "css" / "style.css",
        ":root{--acme-external-theme:1}",
    )
    _write_text(
        theme_pkg_dir / "assets" / "js" / "main.js",
        "window.__acme_external_theme__=true;",
    )

    monkeypatch.syspath_prepend(str(package_root))

    theme_package = ThemePackage(
        slug="acme",
        package="bengal_themes.acme",
        distribution="bengal-theme-acme",
        version="1.0.0",
    )

    import bengal.core.theme.registry as theme_registry

    monkeypatch.setattr(theme_registry, "get_installed_themes", lambda: {"acme": theme_package})

    site = Site.from_config(site_root)
    site.build(BuildOptions(incremental=False, quiet=True))

    manifest = AssetManifest.load(site.output_dir / "asset-manifest.json")
    assert manifest is not None

    style_entry = manifest.get("css/style.css")
    js_entry = manifest.get("js/main.js")

    assert style_entry is not None
    assert js_entry is not None

    style_output = site.output_dir / style_entry.output_path
    js_output = site.output_dir / js_entry.output_path

    assert style_output.exists()
    assert js_output.exists()
    assert "--acme-external-theme:1" in style_output.read_text(encoding="utf-8")
    assert "__acme_external_theme__=true" in js_output.read_text(encoding="utf-8")
