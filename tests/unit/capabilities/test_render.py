"""Tests for capability fence render dispatch (#584)."""

from __future__ import annotations

import pytest

from bengal.capabilities.registry import CapabilityRegistry, reset_capability_registry
from bengal.capabilities.render import render_fence_html, render_fenced_code
from bengal.capabilities.spec import CapabilityAsset, CapabilitySpec, FenceRenderSpec


@pytest.fixture(autouse=True)
def _restore_registry():
    reset_capability_registry()
    yield
    reset_capability_registry()


class TestRenderFenceHtml:
    def test_renders_div_with_class(self) -> None:
        html = render_fence_html(
            FenceRenderSpec(element="div", css_class="demo-viz"),
            "graph TD\n  A --> B",
        )
        assert html == '<div class="demo-viz">graph TD\n  A --&gt; B</div>\n'

    def test_mermaid_contract_matches_legacy_output(self) -> None:
        from bengal.capabilities.builtins import MERMAID_CAPABILITY

        render = MERMAID_CAPABILITY.resolved_fence_render()
        assert render is not None
        html = render_fence_html(render, "graph TD\n  A --> B")
        assert html == '<div class="mermaid">graph TD\n  A --&gt; B</div>\n'


class TestRenderFencedCode:
    def test_unknown_language_returns_none(self) -> None:
        assert render_fenced_code("python", "print('hi')") is None

    def test_third_party_fence_renders_without_core_edits(self) -> None:
        demo = CapabilitySpec(
            name="demo_viz",
            default_pin="0.1.0",
            assets=(
                CapabilityAsset(
                    rel_path="demo.min.js",
                    url_template="https://cdn.example.com/demo@{pin}/demo.min.js",
                ),
            ),
            html_patterns=(r"""class=["']demo-viz["']""",),
            fence_languages=("demo",),
            fence_render=FenceRenderSpec(element="div", css_class="demo-viz"),
        )
        registry = CapabilityRegistry.from_specs([demo])
        html = render_fenced_code("demo", "hello", registry=registry)
        assert html == '<div class="demo-viz">hello</div>\n'

    def test_registry_rejects_duplicate_fence_languages(self) -> None:
        first = CapabilitySpec(
            name="one",
            default_pin="1",
            assets=(CapabilityAsset("a.js", "https://example.com/a.js"),),
            html_patterns=(r"one",),
            fence_languages=("demo",),
            fence_render=FenceRenderSpec(css_class="one"),
        )
        second = CapabilitySpec(
            name="two",
            default_pin="1",
            assets=(CapabilityAsset("b.js", "https://example.com/b.js"),),
            html_patterns=(r"two",),
            fence_languages=("demo",),
            fence_render=FenceRenderSpec(css_class="two"),
        )
        with pytest.raises(ValueError, match="Duplicate fence language"):
            CapabilityRegistry.from_specs([first, second])
