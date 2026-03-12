"""Unit tests for per-page JSON navigation and freshness fields.

Covers:
- navigation.parent from page section
- navigation.prev / navigation.next from section ordering
- navigation.related from related_posts
- content_hash SHA-256 of plain text
- last_modified from frontmatter and file mtime fallback
- Graceful handling when navigation properties are absent
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.output_formats.json_generator import PageJSONGenerator


def _make_site(baseurl: str = "") -> MagicMock:
    site = MagicMock()
    site.title = "Test"
    site.baseurl = baseurl
    return site


def _make_page(
    title: str = "Page",
    path: str = "/docs/page/",
    plain_text: str = "Hello world",
    section_name: str = "docs",
    section_href: str = "/docs/",
    prev_href: str | None = None,
    next_href: str | None = None,
    related_hrefs: list[str] | None = None,
    metadata: dict | None = None,
    source_path: Path | None = None,
    html_content: str | None = None,
    toc_items: list | None = None,
) -> MagicMock:
    page = MagicMock()
    page.title = title
    page._path = path
    page.href = path
    page.plain_text = plain_text
    page.html_content = html_content if html_content is not None else f"<p>{plain_text}</p>"
    page.date = None
    page.toc_items = toc_items if toc_items is not None else []
    page.tags = []
    page.metadata = metadata or {}
    page.source_path = source_path or Path(f"content{path}index.md")
    page.output_path = Path(f"public{path}index.html")

    if section_name:
        section = MagicMock()
        section.name = section_name
        section.href = section_href
        page._section = section
    else:
        page._section = None

    if prev_href:
        prev_page = MagicMock()
        prev_page.href = prev_href
        page.prev_in_section = prev_page
    else:
        page.prev_in_section = None

    if next_href:
        next_page = MagicMock()
        next_page.href = next_href
        page.next_in_section = next_page
    else:
        page.next_in_section = None

    if related_hrefs:
        page.related_posts = [MagicMock(href=h) for h in related_hrefs]
    else:
        page.related_posts = []

    return page


class TestNavigationFields:
    """Test navigation relationship fields in per-page JSON."""

    def test_parent_from_section(self):
        site = _make_site()
        page = _make_page(section_name="docs", section_href="/docs/")
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["navigation"]["parent"] == "/docs/"

    def test_prev_in_section(self):
        site = _make_site()
        page = _make_page(prev_href="/docs/install/")
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["navigation"]["prev"] == "/docs/install/"

    def test_next_in_section(self):
        site = _make_site()
        page = _make_page(next_href="/docs/config/")
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["navigation"]["next"] == "/docs/config/"

    def test_related_posts(self):
        site = _make_site()
        page = _make_page(related_hrefs=["/blog/a/", "/blog/b/"])
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["navigation"]["related"] == ["/blog/a/", "/blog/b/"]

    def test_full_navigation(self):
        site = _make_site()
        page = _make_page(
            section_href="/docs/",
            prev_href="/docs/prev/",
            next_href="/docs/next/",
            related_hrefs=["/blog/related/"],
        )
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        nav = data["navigation"]
        assert nav["parent"] == "/docs/"
        assert nav["prev"] == "/docs/prev/"
        assert nav["next"] == "/docs/next/"
        assert nav["related"] == ["/blog/related/"]

    def test_no_navigation_when_no_relationships(self):
        site = _make_site()
        page = _make_page(
            section_name="",
            section_href="",
            prev_href=None,
            next_href=None,
            related_hrefs=None,
        )
        page._section = None
        page.parent = None
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert "navigation" not in data

    def test_empty_related_not_included(self):
        site = _make_site()
        page = _make_page(related_hrefs=None)
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert "related" not in data.get("navigation", {})


class TestContentHash:
    """Test content_hash field in per-page JSON."""

    def test_content_hash_is_sha256(self):
        site = _make_site()
        text = "Hello world content"
        page = _make_page(plain_text=text)
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert data["content_hash"] == expected

    def test_content_hash_changes_with_content(self):
        site = _make_site()
        page_a = _make_page(plain_text="Version 1")
        page_b = _make_page(plain_text="Version 2")
        gen = PageJSONGenerator(site)
        hash_a = gen.page_to_json(page_a)["content_hash"]
        hash_b = gen.page_to_json(page_b)["content_hash"]
        assert hash_a != hash_b

    def test_content_hash_always_present(self):
        site = _make_site()
        page = _make_page(plain_text="")
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert "content_hash" in data
        assert len(data["content_hash"]) == 64


class TestLastModified:
    """Test last_modified field in per-page JSON."""

    def test_lastmod_from_frontmatter(self):
        site = _make_site()
        dt = datetime(2025, 6, 15, 10, 30, 0)
        page = _make_page(metadata={"lastmod": dt})
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["last_modified"] == "2025-06-15T10:30:00"

    def test_last_modified_from_frontmatter_key(self):
        site = _make_site()
        dt = datetime(2025, 3, 1)
        page = _make_page(metadata={"last_modified": dt})
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["last_modified"] == "2025-03-01T00:00:00"

    def test_updated_from_frontmatter_key(self):
        site = _make_site()
        page = _make_page(metadata={"updated": "2025-01-20"})
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["last_modified"] == "2025-01-20"

    def test_lastmod_string_passthrough(self):
        site = _make_site()
        page = _make_page(metadata={"lastmod": "2025-06-15"})
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert data["last_modified"] == "2025-06-15"

    def test_fallback_to_source_mtime(self, tmp_path):
        site = _make_site()
        source = tmp_path / "page.md"
        source.write_text("# Test")
        page = _make_page(metadata={}, source_path=source)
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert "last_modified" in data
        assert "T" in data["last_modified"]

    def test_no_last_modified_when_unavailable(self):
        site = _make_site()
        page = _make_page(metadata={})
        page.source_path = Path("/nonexistent/path/page.md")
        gen = PageJSONGenerator(site)
        data = gen.page_to_json(page)
        assert "last_modified" not in data


class TestHeadingChunks:
    """Test heading-level chunks in per-page JSON."""

    def test_chunks_included_when_headings_present(self):
        site = _make_site()
        page = _make_page(
            path="/docs/install/",
            plain_text="Install Bengal",
            metadata={},
        )
        page.html_content = (
            '<h2 id="installation">Installation</h2>'
            "<p>Install Bengal with pip.</p>"
            '<h3 id="step-3">Step 3</h3>'
            "<p>Configure your project.</p>"
        )
        page.toc_items = [
            {"id": "installation", "title": "Installation", "level": 1},
            {"id": "step-3", "title": "Step 3", "level": 2},
        ]
        gen = PageJSONGenerator(site, include_chunks=True)
        data = gen.page_to_json(page, include_chunks=True)
        assert "chunks" in data
        chunks = data["chunks"]
        assert len(chunks) == 2
        assert chunks[0]["anchor"] == "installation"
        assert chunks[0]["title"] == "Installation"
        assert chunks[0]["level"] == 1
        assert "Install Bengal" in chunks[0]["content"]
        assert "content_hash" in chunks[0]
        assert chunks[1]["anchor"] == "step-3"
        assert "Configure" in chunks[1]["content"]

    def test_chunks_excluded_when_disabled(self):
        site = _make_site()
        page = _make_page(html_content="<h2 id='x'>X</h2><p>Content</p>")
        page.toc_items = [{"id": "x", "title": "X", "level": 1}]
        gen = PageJSONGenerator(site, include_chunks=False)
        data = gen.page_to_json(page, include_chunks=False)
        assert "chunks" not in data

    def test_chunks_single_when_no_headings(self):
        site = _make_site()
        page = _make_page(plain_text="No headings", html_content="<p>No headings</p>")
        page.toc_items = []
        gen = PageJSONGenerator(site, include_chunks=True)
        data = gen.page_to_json(page, include_chunks=True)
        assert "chunks" in data
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["content"] == "No headings"
        assert data["chunks"][0]["anchor"] == ""
