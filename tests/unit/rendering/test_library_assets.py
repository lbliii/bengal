from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.core.theme.providers import LibraryAsset, ThemeLibraryProvider
from bengal.rendering.library_assets import render_library_asset_tags


class MockSite:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.config: dict[str, Any] = {}
        self.dev_mode = True

    @property
    def baseurl(self) -> str:
        return ""


def test_render_library_asset_tags_includes_declared_attributes(tmp_path: Path) -> None:
    provider = ThemeLibraryProvider(
        package="fake_ui",
        loader=None,
        asset_root=tmp_path,
        asset_prefix="fake_ui",
        register_env=None,
        assets=(
            LibraryAsset(
                source_path=tmp_path / "ui.css",
                logical_path=Path("fake_ui/ui.css"),
                asset_type="css",
                mode="link",
                tag_attrs=(("media", "screen & (min-width: 40rem)"),),
            ),
            LibraryAsset(
                source_path=tmp_path / "ui.js",
                logical_path=Path("fake_ui/ui.js"),
                asset_type="javascript",
                mode="link",
                tag_attrs=(("defer", True), ("type", "module"), ("async", False)),
            ),
        ),
    )

    html = str(render_library_asset_tags((provider,), MockSite(tmp_path)))

    assert (
        '<link rel="stylesheet" href="/assets/fake_ui/ui.css" '
        'media="screen &amp; (min-width: 40rem)">'
    ) in html
    assert '<script src="/assets/fake_ui/ui.js" defer type="module"></script>' in html
    assert "async" not in html


def test_render_library_asset_tags_skips_none_mode_and_duplicates(tmp_path: Path) -> None:
    provider = ThemeLibraryProvider(
        package="fake_ui",
        loader=None,
        asset_root=tmp_path,
        asset_prefix="fake_ui",
        register_env=None,
        assets=(
            LibraryAsset(
                source_path=tmp_path / "ui.css",
                logical_path=Path("fake_ui/ui.css"),
                asset_type="css",
                mode="none",
            ),
            LibraryAsset(
                source_path=tmp_path / "ui.js",
                logical_path=Path("fake_ui/ui.js"),
                asset_type="javascript",
                mode="link",
            ),
            LibraryAsset(
                source_path=tmp_path / "ui-again.js",
                logical_path=Path("fake_ui/ui.js"),
                asset_type="javascript",
                mode="link",
            ),
        ),
    )

    html = str(render_library_asset_tags((provider,), MockSite(tmp_path)))

    assert "ui.css" not in html
    assert html.count("fake_ui/ui.js") == 1
