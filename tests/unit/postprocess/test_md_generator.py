"""Unit tests for bengal/postprocess/output_formats/md_generator.py.

Covers:
- File path mapping (index.html → index.md, page.html → page.md)
- Content header with title, URL, section, description
- H1 deduplication (only stripped when matching page.title)
- Raw content preservation and plain_text fallback
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.output_formats.md_generator import PageMarkdownGenerator


def _make_site(baseurl: str = "") -> MagicMock:
    site = MagicMock()
    site.baseurl = baseurl
    return site


def _make_page(
    title: str = "Page",
    path: str = "/docs/page/",
    description: str = "",
    section_name: str = "docs",
    output_path: str | None = None,
    raw_content: str = "",
    plain_text: str = "",
) -> MagicMock:
    page = MagicMock()
    page.title = title
    page._path = path
    page.href = path
    page.description = description
    page.output_path = Path(output_path) if output_path else Path(f"public{path}index.html")
    page._raw_content = raw_content or None
    page.plain_text = plain_text or None

    if section_name:
        section = MagicMock()
        section.name = section_name
        page._section = section
    else:
        page._section = None

    # Prevent MagicMock from creating is_virtual as a truthy mock
    page.is_virtual = False
    page.in_ai_input = True

    return page


class TestPageToMarkdown:
    """Test markdown content generation for individual pages."""

    def test_includes_title_header(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(title="Getting Started", raw_content="Some content.")

        result = gen._page_to_markdown(page)

        assert result.startswith("# Getting Started\n")

    def test_includes_url(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(path="/docs/install/", raw_content="Content.")

        result = gen._page_to_markdown(page)

        assert "URL: /docs/install/" in result

    def test_includes_section(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(section_name="guides", raw_content="Content.")

        result = gen._page_to_markdown(page)

        assert "Section: guides" in result

    def test_includes_description(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(description="A helpful guide.", raw_content="Content.")

        result = gen._page_to_markdown(page)

        assert "Description: A helpful guide." in result

    def test_omits_section_when_none(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(section_name="", raw_content="Content.")

        result = gen._page_to_markdown(page)

        assert "Section:" not in result

    def test_omits_description_when_empty(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(description="", raw_content="Content.")

        result = gen._page_to_markdown(page)

        assert "Description:" not in result

    def test_has_separator(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(raw_content="Body text.")

        result = gen._page_to_markdown(page)

        assert "\n---\n" in result

    def test_preserves_raw_content(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        raw = "## Installation\n\nRun `pip install bengal`.\n"
        page = _make_page(raw_content=raw)

        result = gen._page_to_markdown(page)

        assert "## Installation" in result
        assert "Run `pip install bengal`." in result


class TestH1Deduplication:
    """Test that H1 stripping only happens when it matches page.title."""

    def test_strips_matching_h1(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(
            title="Getting Started",
            raw_content="# Getting Started\n\nBody content here.",
        )

        result = gen._page_to_markdown(page)

        # Title appears in header, not duplicated in body
        lines = result.split("\n")
        assert lines[0] == "# Getting Started"
        # The raw H1 should be stripped — body should not have another "# Getting Started"
        body_start = result.index("---\n") + 4
        body = result[body_start:]
        assert "# Getting Started" not in body
        assert "Body content here." in body

    def test_preserves_non_matching_h1(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(
            title="Install Guide",
            raw_content="# Different Title\n\nBody content.",
        )

        result = gen._page_to_markdown(page)

        # Non-matching H1 should be preserved in body
        body_start = result.index("---\n") + 4
        body = result[body_start:]
        assert "# Different Title" in body

    def test_h1_only_content(self):
        """H1-only content matching title produces empty body."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(title="Solo", raw_content="# Solo")

        result = gen._page_to_markdown(page)

        # Should not error out
        assert "# Solo" in result


class TestPlainTextFallback:
    """Test fallback to plain_text when raw content unavailable."""

    def test_uses_plain_text_when_no_raw(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(raw_content="", plain_text="Fallback plain text.")

        result = gen._page_to_markdown(page)

        assert "Fallback plain text." in result


class TestGenerate:
    """Test the generate() method writes files."""

    def test_writes_md_files(self, tmp_path):
        site = _make_site()
        site.output_dir = tmp_path
        gen = PageMarkdownGenerator(site)

        page = _make_page(
            title="Test Page",
            path="/test/",
            raw_content="# Test Page\n\nContent.",
            output_path=str(tmp_path / "test" / "index.html"),
        )

        count = gen.generate([page])

        assert count == 1
        md_path = tmp_path / "test" / "index.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "# Test Page" in content

    def test_skips_pages_without_output_path(self):
        site = _make_site()
        gen = PageMarkdownGenerator(site)

        page = _make_page(raw_content="Content.")
        page.output_path = None

        count = gen.generate([page])

        assert count == 0
