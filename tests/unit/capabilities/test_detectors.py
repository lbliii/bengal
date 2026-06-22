"""Tests for capability content detectors (#571)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestDetectCapabilitiesInSource:
    def test_mermaid_fence(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_source

        needed = detect_capabilities_in_source("```mermaid\ngraph TD\n  A-->B\n```")
        assert needed["mermaid"] is True
        assert needed["iconify"] is True
        assert needed["katex"] is False

    def test_inline_math(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_source

        needed = detect_capabilities_in_source("The equation $E = mc^2$ is famous.")
        assert needed["katex"] is True
        assert needed["mermaid"] is False

    def test_block_math(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_source

        needed = detect_capabilities_in_source("$$\n\\int_0^1 x\\,dx\n$$")
        assert needed["katex"] is True


class TestDetectCapabilitiesInHtml:
    def test_mermaid_div(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_html

        needed = detect_capabilities_in_html('<div class="mermaid">graph TD\nA-->B</div>')
        assert needed["mermaid"] is True
        assert needed["iconify"] is True

    def test_math_span(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_html

        needed = detect_capabilities_in_html('<span class="math">E = mc^2</span>')
        assert needed["katex"] is True
        assert needed["mermaid"] is False

    def test_plain_page(self) -> None:
        from bengal.capabilities.detectors import detect_capabilities_in_html

        needed = detect_capabilities_in_html("<p>Hello world</p>")
        assert all(not v for v in needed.values())


class TestResolveEffectiveCapabilities:
    def test_intersects_site_enabled_with_page_needed(self) -> None:
        from bengal.capabilities.detectors import resolve_effective_capabilities

        site = {
            "mermaid": True,
            "katex": True,
            "iconify": True,
            "prebuilt_search": True,
        }
        needed = {"mermaid": False, "katex": True, "iconify": False}
        effective = resolve_effective_capabilities(site, needed)
        assert effective["mermaid"] is False
        assert effective["katex"] is True
        assert effective["iconify"] is False
        assert effective["prebuilt_search"] is True

    def test_disabled_site_capability_stays_off(self) -> None:
        from bengal.capabilities.detectors import resolve_effective_capabilities

        site = {"mermaid": False, "katex": False, "iconify": False}
        needed = {"mermaid": True, "katex": True, "iconify": True}
        effective = resolve_effective_capabilities(site, needed)
        assert effective == {"mermaid": False, "katex": False, "iconify": False}


class TestBuildPageContextCapabilityGating:
    def test_page_without_mermaid_excludes_mermaid_from_context(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from bengal.capabilities.runtime import resolve_runtime_capabilities
        from bengal.rendering.context import build_page_context

        vendor_dir = tmp_path / "assets" / "vendor"
        vendor_dir.mkdir(parents=True)
        (vendor_dir / "mermaid.min.js").write_bytes(b"mermaid")
        (vendor_dir / "katex.min.js").write_bytes(b"katex")
        (vendor_dir / "katex.min.css").write_bytes(b"css")

        site = MagicMock()
        site.dev_mode = True
        site.theme = "default"
        site.baseurl = ""
        site.build_time = None
        site.root_path = tmp_path
        site.config = {
            "expose_metadata": "minimal",
            "capabilities": {"mermaid": True, "katex": True},
        }
        site.versioning_enabled = False
        site.versions = []

        page = MagicMock()
        page.metadata = {"title": "Plain"}
        page.title = "Plain"
        page.source_path = tmp_path / "plain.md"
        page.source_path.write_text("# Plain\n\nNo diagrams here.\n")

        context = build_page_context(
            page,
            site,
            content="<p>No diagrams here.</p>",
            lazy=False,
        )

        assert context["page_capabilities"]["mermaid"] is False
        assert context["page_capabilities"]["katex"] is False
        assert context["bengal"]["capabilities"]["mermaid"] is False
        assert context["bengal"]["capabilities"]["katex"] is False

        # Sanity: site-level resolution would still be active
        site_caps = resolve_runtime_capabilities(site.config, vendor_dir)
        assert site_caps["mermaid"] is True
        assert site_caps["katex"] is True

    def test_page_with_mermaid_includes_mermaid_in_context(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from bengal.rendering.context import build_page_context

        vendor_dir = tmp_path / "assets" / "vendor"
        vendor_dir.mkdir(parents=True)
        (vendor_dir / "mermaid.min.js").write_bytes(b"mermaid")

        site = MagicMock()
        site.dev_mode = True
        site.theme = "default"
        site.baseurl = ""
        site.build_time = None
        site.root_path = tmp_path
        site.config = {
            "expose_metadata": "minimal",
            "capabilities": {"mermaid": True},
        }
        site.versioning_enabled = False
        site.versions = []

        page = MagicMock()
        page.metadata = {"title": "Diagram"}
        page.title = "Diagram"
        page.source_path = tmp_path / "diagram.md"
        page.source_path.write_text("```mermaid\ngraph TD\n  A-->B\n```\n")

        context = build_page_context(
            page,
            site,
            content='<div class="mermaid">graph TD\n  A-->B</div>',
            lazy=False,
        )

        assert context["page_capabilities"]["mermaid"] is True
        assert context["bengal"]["capabilities"]["mermaid"] is True
