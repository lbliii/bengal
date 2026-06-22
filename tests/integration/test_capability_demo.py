"""
Integration tests for third-party capability end-to-end flow (#586).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.capabilities.registry import load_capability_registry, reset_capability_registry
from bengal.capabilities.spec import (
    CapabilityAsset,
    CapabilityInitContract,
    CapabilitySpec,
    FenceRenderSpec,
)
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path

DEMO_SPEC = CapabilitySpec(
    name="demo_viz",
    default_pin="0.1.0",
    assets=(
        CapabilityAsset(
            rel_path="demo.min.js",
            url_template="https://cdn.example.com/demo@{pin}/demo.min.js",
        ),
    ),
    html_patterns=(r"""class=["']demo-viz["']""",),
    source_patterns=(r"```demo",),
    fence_languages=("demo",),
    fence_render=FenceRenderSpec(element="div", css_class="demo-viz"),
    init=CapabilityInitContract(
        lazy_selector=".demo-viz",
        lazy_loader_key="demo_viz",
    ),
)


@pytest.fixture(autouse=True)
def _demo_registry(monkeypatch):
    registry = load_capability_registry(extra_specs=[DEMO_SPEC])
    reset_capability_registry(registry)
    monkeypatch.setattr(
        "bengal.capabilities.registry.get_capability_registry",
        lambda: registry,
    )
    yield
    reset_capability_registry()


class TestThirdPartyCapabilityEndToEnd:
    def test_demo_fence_renders_and_gates_vendor_assets(self, tmp_path: Path) -> None:
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        vendor_dir = site_dir / "assets" / "vendor"
        vendor_dir.mkdir(parents=True)
        (vendor_dir / "demo.min.js").write_text("window.DEMO_VIZ = {};\n")

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Demo Capability Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"

[capabilities]
demo_viz = true
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("---\ntitle: Home\n---\nNo demo here.\n")
        (content_dir / "demo.md").write_text("---\ntitle: Demo\n---\n```demo\nA --> B\n```\n")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        home_html = (site_dir / "public" / "index.html").read_text()
        demo_html = (site_dir / "public" / "demo" / "index.html").read_text()

        assert "vendor/demo.min.js" not in home_html
        assert 'class="demo-viz"' not in home_html

        assert 'class="demo-viz"' in demo_html
        assert "A --&gt; B" in demo_html
        assert "vendor/demo.min" in demo_html
        assert "BENGAL_CAPABILITY_LOADERS" in demo_html
