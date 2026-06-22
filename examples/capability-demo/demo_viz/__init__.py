"""Reference third-party capability for docs and integration tests (#586)."""

from __future__ import annotations

from bengal.capabilities.spec import (
    CapabilityAsset,
    CapabilityInitContract,
    CapabilitySpec,
    FenceRenderSpec,
)

DEMO_VIZ_CAPABILITY = CapabilitySpec(
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
    fence_render=FenceRenderSpec(element="div", css_class="demo-viz", escape_content=True),
    init=CapabilityInitContract(
        load_position="body",
        defer=True,
        lazy_loader_key="demo_viz",
        lazy_selector=".demo-viz",
    ),
)
