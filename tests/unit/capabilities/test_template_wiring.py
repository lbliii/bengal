"""Tests for registry-driven capability template wiring (#585)."""

from __future__ import annotations

from bengal.capabilities.registry import CapabilityRegistry
from bengal.capabilities.template_wiring import build_capability_wiring


class TestBuildCapabilityWiring:
    def test_cache_key_is_sorted_active_names(self) -> None:
        wiring = build_capability_wiring(
            {"mermaid": True, "katex": True, "iconify": True},
            {},
        )
        assert wiring["cache_key"] == "iconify-katex-mermaid"

    def test_katex_emits_css_and_js(self) -> None:
        wiring = build_capability_wiring({"katex": True}, {"katex.min.css": "sha384-test"})
        paths = [item["path"] for item in wiring["stylesheets"]]
        assert "vendor/katex.min.css" in paths
        script_paths = [item["path"] for item in wiring["scripts"]]
        assert "vendor/katex.min.js" in script_paths
        assert "js/enhancements/math.js" in script_paths

    def test_mermaid_uses_lazy_loader(self) -> None:
        wiring = build_capability_wiring({"mermaid": True, "iconify": True}, {})
        assert len(wiring["lazy_loaders"]) == 1
        loader = wiring["lazy_loaders"][0]
        assert loader["key"] == "mermaid"
        assert loader["selector"] == ".mermaid"
        assert loader["script"] == "vendor/mermaid.min.js"
        assert "js/mermaid-toolbar.js" in loader["companions"]

    def test_iconify_emits_runtime_fetch_global(self) -> None:
        wiring = build_capability_wiring({"mermaid": True, "iconify": True}, {})
        assert len(wiring["runtime_globals"]) == 1
        runtime = wiring["runtime_globals"][0]
        assert runtime["name"] == "BENGAL_MERMAID_ICON_PACKS"
        pack_names = {pack["name"] for pack in runtime["packs"]}
        assert pack_names == {"fa", "mdi", "logos"}

    def test_inactive_capabilities_emit_nothing(self) -> None:
        wiring = build_capability_wiring({"mermaid": False, "katex": False}, {})
        assert wiring["stylesheets"] == []
        assert wiring["scripts"] == []
        assert wiring["lazy_loaders"] == []
        assert wiring["runtime_globals"] == []

    def test_custom_registry_demo_capability(self) -> None:
        from bengal.capabilities.spec import (
            CapabilityAsset,
            CapabilityInitContract,
            CapabilitySpec,
            FenceRenderSpec,
        )

        demo = CapabilitySpec(
            name="demo_viz",
            default_pin="0.1.0",
            assets=(CapabilityAsset("demo.min.js", "https://example.com/demo.js"),),
            html_patterns=(r"demo-viz",),
            fence_languages=("demo",),
            fence_render=FenceRenderSpec(css_class="demo-viz"),
            init=CapabilityInitContract(
                lazy_selector=".demo-viz",
                lazy_loader_key="demo_viz",
            ),
        )
        registry = CapabilityRegistry.from_specs([demo])
        wiring = build_capability_wiring({"demo_viz": True}, {}, registry=registry)
        assert wiring["lazy_loaders"][0]["selector"] == ".demo-viz"
