"""Tests for capability entry-point registry (#572)."""

from __future__ import annotations

import pytest

from bengal.capabilities.registry import (
    CapabilityRegistry,
    load_capability_registry,
    reset_capability_registry,
)
from bengal.capabilities.runtime import capability_names, is_capability_requested
from bengal.capabilities.spec import CapabilityAsset, CapabilitySpec


@pytest.fixture(autouse=True)
def _restore_registry():
    reset_capability_registry()
    yield
    reset_capability_registry()


class TestDiscoverBuiltins:
    def test_entry_points_include_first_party_capabilities(self) -> None:
        registry = load_capability_registry()
        names = registry.names
        assert names == frozenset({"mermaid", "katex", "iconify"})

    def test_capability_names_matches_registry(self) -> None:
        reset_capability_registry()
        assert capability_names() == frozenset({"mermaid", "katex", "iconify"})


class TestRegistryValidation:
    def test_rejects_duplicate_names(self) -> None:
        dup = CapabilitySpec(
            name="mermaid",
            default_pin="1",
            assets=(CapabilityAsset("x.js", "https://example.com/x.js"),),
            html_patterns=(r"mermaid",),
        )
        with pytest.raises(ValueError, match="Duplicate"):
            CapabilityRegistry.from_specs([dup, dup])

    def test_rejects_unknown_dependency(self) -> None:
        spec = CapabilitySpec(
            name="orphan",
            default_pin="1",
            assets=(CapabilityAsset("x.js", "https://example.com/x.js"),),
            html_patterns=(r"orphan",),
            depends_on=("missing",),
        )
        with pytest.raises(ValueError, match="unknown capability"):
            CapabilityRegistry.from_specs([spec])

    def test_allows_imply_only_capability(self) -> None:
        parent = CapabilitySpec(
            name="parent",
            default_pin="1",
            assets=(CapabilityAsset("p.js", "https://example.com/p.js"),),
            html_patterns=(r"parent",),
            implies=("child",),
        )
        child = CapabilitySpec(
            name="child",
            default_pin="1",
            assets=(CapabilityAsset("c.js", "https://example.com/c.js"),),
            depends_on=("parent",),
        )
        registry = CapabilityRegistry.from_specs([parent, child])
        assert registry.get("child") is not None


class TestThirdPartyRegistration:
    def test_extra_spec_is_merged_into_registry(self) -> None:
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
        )
        registry = load_capability_registry(extra_specs=[demo])
        assert "demo_viz" in registry.names
        assert registry.get("demo_viz") is demo

    def test_third_party_name_is_configurable(self) -> None:
        demo = CapabilitySpec(
            name="demo_viz",
            default_pin="0.1.0",
            assets=(
                CapabilityAsset(
                    rel_path="demo.min.js",
                    url_template="https://cdn.example.com/demo@{pin}/demo.min.js",
                ),
            ),
            html_patterns=(r"demo-viz",),
        )
        reset_capability_registry(load_capability_registry(extra_specs=[demo]))
        config = {"capabilities": {"demo_viz": True, "mermaid": False}}
        assert is_capability_requested(config, "demo_viz") is True
        assert is_capability_requested(config, "mermaid") is False
