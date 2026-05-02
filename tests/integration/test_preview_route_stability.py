"""Local preview route-stability regression coverage."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.core.output import BuildOutputCollector
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.rendering.pipeline.output import write_output
from bengal.server.live_reload import LIVE_RELOAD_SCRIPT

if TYPE_CHECKING:
    from pathlib import Path


def test_local_preview_route_stability_contract(tmp_path: Path) -> None:
    """Preview should avoid route flashes unless the current route changed."""
    site_root = tmp_path / "preview-site"
    (site_root / "content").mkdir(parents=True)
    (site_root / "bengal.toml").write_text(
        """
[site]
title = "Preview Contract"

[build]
output_dir = "public"
""",
        encoding="utf-8",
    )
    (site_root / "content" / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n", encoding="utf-8"
    )

    site = Site.from_config(site_root)
    site.build(BuildOptions(force_sequential=True, incremental=False))
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")

    assert "css/base/transitions.css" not in html
    assert "currentRouteMatchesChangedPath" in LIVE_RELOAD_SCRIPT

    out = site.output_dir / "index.html"
    page = SimpleNamespace(
        source_path=site_root / "content" / "index.md",
        output_path=out,
        rendered_html=out.read_text(encoding="utf-8"),
        metadata={},
    )
    collector = BuildOutputCollector(output_dir=site.output_dir)

    write_output(page, site, collector=collector)

    assert collector.get_outputs() == []
