from __future__ import annotations

import pytest

from bengal.core.site import Site
from bengal.errors import BengalAssetError
from bengal.orchestration.build.options import BuildOptions


def _write_site_with_missing_asset_reference(site_root) -> None:
    (site_root / "content").mkdir(parents=True)
    (site_root / "templates").mkdir()
    (site_root / "content" / "missing.md").write_text(
        "---\ntitle: Missing Asset\n---\n\nBody",
        encoding="utf-8",
    )
    (site_root / "templates" / "page.html").write_text(
        """
<!doctype html>
<html>
<head>
  <link rel="stylesheet" href="/assets/vendor/missing.css">
</head>
<body>{{ content }}</body>
</html>
""".lstrip(),
        encoding="utf-8",
    )
    (site_root / "bengal.toml").write_text(
        """
[site]
title = "Missing Asset Fixture"

[build]
content_dir = "content"
output_dir = "public"
""".lstrip(),
        encoding="utf-8",
    )


def test_missing_rendered_asset_reference_warns_without_strict(tmp_path, capsys) -> None:
    _write_site_with_missing_asset_reference(tmp_path)
    site = Site.from_config(tmp_path)

    site.build(BuildOptions(incremental=False, quiet=True, strict=False))

    captured = capsys.readouterr()
    assert "rendered local CSS/JS asset reference" in captured.out
    assert "vendor/missing.css" in captured.out


def test_missing_rendered_asset_reference_fails_in_strict_mode(tmp_path) -> None:
    from bengal.rendering.assets import resolve_asset_url

    _write_site_with_missing_asset_reference(tmp_path)
    site = Site.from_config(tmp_path)
    resolve_asset_url("stale/previous-build.css", site)

    with pytest.raises(BengalAssetError, match=r"vendor/missing\.css"):
        site.build(BuildOptions(incremental=False, quiet=True, strict=True))
