from pathlib import Path

from bengal.core.site import Site


def write_file(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_theme_asset_dedup_child_overrides_parent(tmp_path: Path):
    # Parent theme asset
    parent_asset = tmp_path / "themes" / "parent" / "assets" / "css" / "style.css"
    write_file(parent_asset, "parent")

    # Child theme extends parent with same asset path
    child_theme_dir = tmp_path / "themes" / "child"
    write_file(child_theme_dir / "theme.toml", 'name = "child"\nextends = "parent"\n')
    write_file(child_theme_dir / "assets" / "css" / "style.css", "child")

    # Site assets override all
    site_asset = tmp_path / "assets" / "css" / "style.css"
    write_file(site_asset, "site")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    site.discover_assets()

    # There should be only one style.css in final asset list (dedup by rel path)
    css_assets = [a for a in site.assets if str(a.output_path).endswith("css/style.css")]
    assert len(css_assets) == 1
    # The one retained should be the site asset
    assert css_assets[0].source_path == site_asset
