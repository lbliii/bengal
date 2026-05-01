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
    rendered_html: str = "",
) -> MagicMock:
    page = MagicMock()
    page.title = title
    page._path = path
    page.href = path
    page.description = description
    page.output_path = Path(output_path) if output_path else Path(f"public{path}index.html")
    page._raw_content = raw_content or None
    page.plain_text = plain_text or None
    page.rendered_html = rendered_html

    if section_name:
        section = MagicMock()
        section.name = section_name
        page._section = section
    else:
        page._section = None

    # Prevent MagicMock from creating virtual as a truthy mock
    page.virtual = False
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

    def test_includes_agent_directive(self):
        site = _make_site(baseurl="/bengal")
        gen = PageMarkdownGenerator(site)
        page = _make_page(raw_content="Body text.")

        result = gen._page_to_markdown(page)

        assert "> For a complete page index, fetch /bengal/llms.txt." in result

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


class TestContentParityThreshold:
    """Test _get_best_content falls back to plain_text when raw is incomplete."""

    def test_uses_raw_when_coverage_high(self):
        """Raw content covering >=75% of plain_text is preserved."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        raw = "## Setup\n\nInstall with pip.\n\n## Usage\n\nRun the command."
        # plain_text is similar length — raw has good coverage
        plain = "Setup\nInstall with pip.\nUsage\nRun the command."
        page = _make_page(title="Guide", raw_content=raw, plain_text=plain)

        result = gen._page_to_markdown(page)

        # Should use raw (has markdown formatting)
        assert "## Setup" in result
        assert "## Usage" in result

    def test_falls_back_to_plain_when_coverage_low(self):
        """Raw content covering <75% of plain_text triggers fallback."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        # Raw has shortcode syntax, not real content
        raw = "## Intro\n\nShort intro.\n\n{{< tabs >}}\n{{< /tabs >}}"
        # plain_text has the full expanded content from shortcodes
        plain = (
            "Intro\nShort intro.\n\n"
            "Python\nInstall with pip install bengal.\n"
            "Run bengal serve to start.\n\n"
            "JavaScript\nInstall with npm install bengal.\n"
            "Run npx bengal serve to start.\n\n"
            "Go\nInstall with go install bengal.\n"
            "Run bengal serve to start."
        )
        page = _make_page(title="Guide", raw_content=raw, plain_text=plain)

        result = gen._page_to_markdown(page)

        # Should fall back to plain_text (has full content)
        assert "Python" in result
        assert "JavaScript" in result
        assert "{{< tabs >}}" not in result

    def test_uses_plain_text_when_no_raw(self):
        """Empty raw content always falls back to plain_text."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        page = _make_page(raw_content="", plain_text="Full plain text content.")

        result = gen._get_best_content(page)

        assert result == "Full plain text content."

    def test_threshold_boundary_at_75_percent(self):
        """Coverage exactly at 75% should use raw content."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        # Create content where raw is exactly 75% of plain length
        plain = "a" * 100
        raw = "b" * 75  # 75/100 = 0.75, not < 0.75
        page = _make_page(title="Test", raw_content=raw, plain_text=plain)

        result = gen._get_best_content(page)

        assert result == raw

    def test_uses_rendered_content_when_template_adds_substantial_content(self):
        """Rendered primary content fills parity gaps on generated pages."""
        site = _make_site()
        gen = PageMarkdownGenerator(site)
        raw = "Short intro."
        rendered = """
        <main id="main-content">
          <article class="prose">
            <div class="docs-content"><p>Short intro.</p></div>
            <section class="docs-children">
              <h2>In This Section</h2>
              <article><h3>Installation</h3><p>Install Bengal.</p></article>
              <article><h3>Configuration</h3><p>Configure output formats.</p></article>
            </section>
          </article>
        </main>
        """
        page = _make_page(title="Guide", raw_content=raw, rendered_html=rendered)

        result = gen._get_best_content(page)

        assert "In This Section" in result
        assert "Installation" in result
        assert "Configuration" in result


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
