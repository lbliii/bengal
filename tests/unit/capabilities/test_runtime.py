"""Tests for opt-in runtime capabilities (#550)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestResolveRuntimeCapabilities:
    def test_all_off_by_default(self, tmp_path: Path) -> None:
        from bengal.capabilities.runtime import resolve_runtime_capabilities

        caps = resolve_runtime_capabilities({}, tmp_path / "assets" / "vendor")
        assert caps == {"mermaid": False, "katex": False, "iconify": False}

    def test_config_without_vendors_is_inactive(self, tmp_path: Path) -> None:
        from bengal.capabilities.runtime import resolve_runtime_capabilities

        config = {"capabilities": {"mermaid": True, "katex": True, "iconify": True}}
        vendor_dir = tmp_path / "assets" / "vendor"
        vendor_dir.mkdir(parents=True)
        caps = resolve_runtime_capabilities(config, vendor_dir)
        assert all(not v for v in caps.values())

    def test_active_when_config_and_vendors_present(self, tmp_path: Path) -> None:
        from bengal.capabilities.runtime import resolve_runtime_capabilities

        vendor_dir = tmp_path / "assets" / "vendor"
        vendor_dir.mkdir(parents=True)
        (vendor_dir / "mermaid.min.js").write_bytes(b"mermaid")
        (vendor_dir / "katex.min.js").write_bytes(b"katex")
        (vendor_dir / "katex.min.css").write_bytes(b"css")
        iconify = vendor_dir / "iconify"
        iconify.mkdir()
        (iconify / "fa.json").write_text("{}")
        (iconify / "mdi.json").write_text("{}")
        (iconify / "logos.json").write_text("{}")

        config = {"capabilities": {"mermaid": True, "katex": True, "iconify": True}}
        caps = resolve_runtime_capabilities(config, vendor_dir)
        assert caps == {"mermaid": True, "katex": True, "iconify": True}

    def test_iconify_requires_mermaid(self, tmp_path: Path) -> None:
        from bengal.capabilities.runtime import resolve_runtime_capabilities

        vendor_dir = tmp_path / "assets" / "vendor"
        iconify = vendor_dir / "iconify"
        iconify.mkdir(parents=True)
        (iconify / "fa.json").write_text("{}")
        (iconify / "mdi.json").write_text("{}")
        (iconify / "logos.json").write_text("{}")

        config = {"capabilities": {"mermaid": False, "iconify": True}}
        caps = resolve_runtime_capabilities(config, vendor_dir)
        assert caps["iconify"] is False


class TestTemplateMetadataCapabilities:
    def test_metadata_merges_runtime_capabilities(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from bengal.rendering.metadata import build_template_metadata

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

        meta = build_template_metadata(site)
        assert meta["capabilities"]["mermaid"] is True
        assert meta["capabilities"]["prebuilt_search"] in (True, False)


class TestZeroExternalOriginWithCapabilities:
    def test_theme_templates_still_have_no_cdn_origins(self) -> None:
        from tests.unit.themes.test_zero_external_origin import (
            test_default_theme_has_no_external_cdn_origins,
        )

        test_default_theme_has_no_external_cdn_origins()
