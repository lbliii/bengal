"""Deterministic ordering for aggregate postprocess outputs (#431)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSitemapDeterministicOrdering:
    def test_pages_sorted_by_output_path_before_emit(self, tmp_path: Path) -> None:
        from bengal.postprocess.sitemap import SitemapGenerator

        page_z = MagicMock()
        page_z.in_sitemap = True
        page_z.output_path = tmp_path / "z-page" / "index.html"
        page_z.slug = "z-page"
        page_z.date = datetime(2024, 1, 1)
        page_z.translation_key = None

        page_a = MagicMock()
        page_a.in_sitemap = True
        page_a.output_path = tmp_path / "a-page" / "index.html"
        page_a.slug = "a-page"
        page_a.date = datetime(2024, 1, 2)
        page_a.translation_key = None

        site = MagicMock()
        site.pages = [page_z, page_a]
        site.baseurl = "https://example.com"
        site.output_dir = tmp_path
        site.config = {}
        site.versioning_enabled = False

        generator = SitemapGenerator(site)

        with patch("bengal.utils.io.atomic_write.AtomicFile") as mock_atomic:
            mock_file = MagicMock()
            mock_atomic.return_value.__enter__ = MagicMock(return_value=mock_file)
            mock_atomic.return_value.__exit__ = MagicMock(return_value=False)
            generator.generate()

        written = mock_file.write.call_args[0][0].decode("utf-8")
        assert written.index("a-page") < written.index("z-page")


class TestAgentManifestDeterministicOrdering:
    def test_section_pages_sorted_by_url(self) -> None:
        from bengal.postprocess.output_formats.agent_manifest_generator import (
            AgentManifestGenerator,
        )

        site = MagicMock()
        site.baseurl = ""
        site.config = {"output_formats": {}}
        generator = AgentManifestGenerator(site)

        page_by_href = {
            "/b": MagicMock(
                title="B",
                plain_text="b",
                metadata={},
                type="doc",
                description="",
            ),
            "/a": MagicMock(
                title="A",
                plain_text="a",
                metadata={},
                type="doc",
                description="",
            ),
        }
        for href, page in page_by_href.items():
            page.output_path = Path("out") / href.strip("/")
            type(page).kind = "doc"

        section = MagicMock()
        section.title = "Docs"
        section.href = "/docs/"
        section.sorted_pages = [MagicMock(), MagicMock()]
        section.sorted_pages[0].output_path = Path("out/b")
        section.sorted_pages[1].output_path = Path("out/a")

        with patch(
            "bengal.postprocess.output_formats.agent_manifest_generator.get_page_url",
            side_effect=["/b", "/a"],
        ):
            sections = generator._build_sections([section], page_by_href)

        urls = [entry["url"] for entry in sections[0]["pages"]]
        assert urls == sorted(urls)
