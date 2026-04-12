from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


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


def test_content_orchestrator_matches_site_asset_inheritance(tmp_path: Path):
    parent_asset = tmp_path / "themes" / "parent" / "assets" / "css" / "base.css"
    write_file(parent_asset, "parent-base")

    child_theme_dir = tmp_path / "themes" / "child"
    write_file(child_theme_dir / "theme.toml", 'name = "child"\nextends = "parent"\n')
    write_file(child_theme_dir / "assets" / "css" / "style.css", "child-style")

    site_asset = tmp_path / "assets" / "css" / "style.css"
    write_file(site_asset, "site-style")

    site = Site.from_config(tmp_path)
    site.theme = "child"

    orchestrator = ContentOrchestrator(site)
    orchestrator.discover_assets()

    assets_by_output = {str(asset.output_path): asset.source_path for asset in site.assets}

    assert assets_by_output["css/base.css"] == parent_asset
    assert assets_by_output["css/style.css"] == site_asset


def test_content_orchestrator_incremental_cache_matches_full_discovery(tmp_path: Path):
    parent_asset = tmp_path / "themes" / "parent" / "assets" / "css" / "base.css"
    write_file(parent_asset, "parent-base")

    child_theme_dir = tmp_path / "themes" / "child"
    write_file(child_theme_dir / "theme.toml", 'name = "child"\nextends = "parent"\n')
    write_file(child_theme_dir / "assets" / "css" / "style.css", "child-style")

    site_asset = tmp_path / "assets" / "css" / "style.css"
    write_file(site_asset, "site-style")

    full_site = Site.from_config(tmp_path)
    full_site.theme = "child"
    full_site.discover_assets()
    expected_assets = {str(asset.output_path): asset.source_path for asset in full_site.assets}

    cached_assets = {
        asset.source_path.relative_to(full_site.root_path): str(asset.output_path)
        for asset in full_site.assets
    }

    cached_site = Site.from_config(tmp_path)
    cached_site.theme = "child"
    cached_site._last_build_options = SimpleNamespace(
        incremental=True,
        changed_sources=[tmp_path / "content" / "page.md"],
        structural_changed=False,
    )
    cached_site._cache = SimpleNamespace(discovered_assets=cached_assets)

    orchestrator = ContentOrchestrator(cached_site)
    orchestrator.discover_assets()

    assets_by_output = {str(asset.output_path): asset.source_path for asset in cached_site.assets}
    assert assets_by_output == expected_assets
