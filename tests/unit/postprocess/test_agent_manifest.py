"""Unit tests for AgentManifestGenerator.

Covers:
- Site info and formats in manifest
- Section hierarchy with children and pages
- Root-level pages in Overview section
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.output_formats.agent_manifest_generator import (
    AgentManifestGenerator,
)


def _make_site(
    output_dir: Path,
    title: str = "Test Site",
    baseurl: str = "",
) -> MagicMock:
    site = MagicMock()
    site.output_dir = output_dir
    site.title = title
    site.baseurl = baseurl
    site.description = "A test site"
    site.config = {"output_formats": {"site_wide": ["changelog", "llms_txt"], "per_page": ["json"]}}
    return site


def _make_page(
    href: str,
    title: str = "Page",
    description: str = "",
    page_type: str = "doc",
    plain_text: str = "content",
    section_name: str | None = "docs",
) -> MagicMock:
    page = MagicMock()
    page.href = href
    page.title = title
    page.description = description
    page.type = page_type
    page.kind = page_type
    page.plain_text = plain_text
    page.output_path = Path(f"public{href}index.html")
    page.metadata = {}
    page.source_path = Path(f"content{href}index.md")

    if section_name:
        section = MagicMock()
        section.name = section_name
        page._section = section
    else:
        page._section = None

    return page


def _make_section(
    name: str,
    path: str,
    pages: list | None = None,
    subsections: list | None = None,
) -> MagicMock:
    section = MagicMock()
    section.name = name
    section.title = name
    section.href = path
    section._path = path
    section.pages = pages or []
    section.sorted_pages = pages or []
    section.subsections = subsections or []
    section.sorted_subsections = subsections or []
    return section


class TestAgentManifestGenerator:
    def test_generates_site_info_and_formats(self, tmp_path: Path) -> None:
        site = _make_site(tmp_path, title="My Site", baseurl="https://example.com")
        site.sections = []
        pages = [_make_page("/", "Home", section_name=None)]
        gen = AgentManifestGenerator(site)
        path = gen.generate(pages)

        data = json.loads(path.read_text())
        assert data["site"]["title"] == "My Site"
        assert data["site"]["baseurl"] == "https://example.com"
        assert "formats" in data
        assert "changelog" in data["formats"] or "per_page_json" in data["formats"]

    def test_root_pages_in_overview_section(self, tmp_path: Path) -> None:
        site = _make_site(tmp_path)
        site.sections = []
        pages = [
            _make_page("/", "Home", section_name=None),
            _make_page("/about/", "About", section_name=None),
        ]
        gen = AgentManifestGenerator(site)
        path = gen.generate(pages)

        data = json.loads(path.read_text())
        overview = next(s for s in data["sections"] if s["name"] == "Overview")
        assert len(overview["pages"]) == 2
        urls = {p["url"] for p in overview["pages"]}
        assert "/" in urls
        assert "/about/" in urls

    def test_section_with_pages_includes_content_hash(self, tmp_path: Path) -> None:
        site = _make_site(tmp_path)
        page = _make_page("/docs/install/", "Install", section_name="docs")
        section = _make_section("Docs", "/docs/", pages=[page])
        site.sections = [section]

        gen = AgentManifestGenerator(site)
        path = gen.generate([page])

        data = json.loads(path.read_text())
        docs = next(s for s in data["sections"] if s["name"] == "Docs")
        assert len(docs["pages"]) == 1
        assert docs["pages"][0]["url"] == "/docs/install/"
        assert docs["pages"][0]["title"] == "Install"
        assert "content_hash" in docs["pages"][0]
        expected_hash = hashlib.sha256(b"content").hexdigest()
        assert docs["pages"][0]["content_hash"] == expected_hash
