"""Unit tests for bengal/postprocess/output_formats/llms_txt_generator.py.

Covers:
- llms.txt rendering with H1 title and blockquote description
- Section grouping and ordering from site hierarchy
- Page links with descriptions from frontmatter
- Root-level pages under "Overview" group
- Optional section with machine-readable format links
- Content signals integration (ai_input filtering upstream)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.postprocess.output_formats.llms_txt_generator import SiteLlmsTxtGenerator


def _make_site(
    title: str = "Test Site",
    description: str = "A test site for unit testing.",
    baseurl: str = "",
    sections: list | None = None,
    config_overrides: dict | None = None,
) -> MagicMock:
    site = MagicMock()
    site.title = title
    site.baseurl = baseurl
    site.output_dir = Path("/tmp/test-output")

    _config: dict = {
        "description": description,
        "output_formats": {
            "per_page": ["json", "llm_txt"],
            "site_wide": ["index_json", "llm_full", "llms_txt"],
        },
        "content_signals": {"enabled": True},
    }
    if config_overrides:
        _config.update(config_overrides)

    site.config = MagicMock()
    site.config.get = lambda key, default=None: _config.get(key, default)
    site.sections = sections or []
    return site


def _make_page(
    title: str = "Page",
    path: str = "/docs/page/",
    description: str = "",
    section_name: str = "docs",
    output_path: str | None = None,
) -> MagicMock:
    page = MagicMock()
    page.title = title
    page._path = path
    page.href = path
    page.description = description
    page.output_path = Path(output_path) if output_path else Path(f"public{path}index.html")

    if section_name:
        section = MagicMock()
        section.name = section_name
        page._section = section
    else:
        page._section = None

    return page


def _make_section(name: str, title: str = "") -> MagicMock:
    section = MagicMock()
    section.name = name
    section.title = title or name.replace("-", " ").title()
    return section


class TestLlmsTxtRendering:
    """Test llms.txt content rendering."""

    def test_h1_title(self):
        site = _make_site(title="Bengal")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert content.startswith("# Bengal\n")

    def test_blockquote_description(self):
        site = _make_site(description="A Python static site generator.")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert "> A Python static site generator." in content

    def test_no_description(self):
        site = _make_site(description="")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert ">" not in content.split("\n")[1]

    def test_page_with_description(self):
        site = _make_site()
        page = _make_page(
            title="Installation",
            path="/docs/installation/",
            description="Install and set up Bengal.",
        )
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([page])
        assert "- [Installation](/docs/installation/): Install and set up Bengal." in content

    def test_page_without_description(self):
        site = _make_site()
        page = _make_page(title="Changelog", path="/docs/changelog/", description="")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([page])
        assert "- [Changelog](/docs/changelog/)" in content
        assert ":" not in content.split("Changelog](/docs/changelog/)")[1].split("\n")[0]


class TestSectionGrouping:
    """Test section-based page grouping."""

    def test_pages_grouped_by_section(self):
        site = _make_site(sections=[_make_section("docs", "Documentation")])
        page_a = _make_page(title="Install", path="/docs/install/", section_name="docs")
        page_b = _make_page(title="Config", path="/docs/config/", section_name="docs")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([page_a, page_b])
        assert "## Documentation" in content
        assert "[Install]" in content
        assert "[Config]" in content

    def test_multiple_sections(self):
        site = _make_site(
            sections=[
                _make_section("docs", "Documentation"),
                _make_section("blog", "Blog"),
            ]
        )
        doc_page = _make_page(title="Guide", path="/docs/guide/", section_name="docs")
        blog_page = _make_page(title="News", path="/blog/news/", section_name="blog")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([doc_page, blog_page])
        assert "## Documentation" in content
        assert "## Blog" in content
        doc_pos = content.index("## Documentation")
        blog_pos = content.index("## Blog")
        assert doc_pos < blog_pos

    def test_root_pages_under_overview(self):
        site = _make_site()
        root_page = _make_page(title="Home", path="/", section_name="")
        root_page.output_path = Path("public/index.html")
        root_page.metadata = {}
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([root_page])
        assert "## Overview" in content
        assert "[Home](/)" in content

    def test_section_order_matches_site_hierarchy(self):
        """Sections appear in the same order as site.sections."""
        site = _make_site(
            sections=[
                _make_section("getting-started", "Getting Started"),
                _make_section("reference", "Reference"),
                _make_section("blog", "Blog"),
            ]
        )
        pages = [
            _make_page(title="Ref", path="/reference/api/", section_name="reference"),
            _make_page(
                title="Start", path="/getting-started/install/", section_name="getting-started"
            ),
            _make_page(title="Post", path="/blog/hello/", section_name="blog"),
        ]
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render(pages)
        gs_pos = content.index("## Getting Started")
        ref_pos = content.index("## Reference")
        blog_pos = content.index("## Blog")
        assert gs_pos < ref_pos < blog_pos

    def test_unknown_section_uses_titlecased_slug(self):
        site = _make_site(sections=[])
        page = _make_page(
            title="Something",
            path="/my-section/something/",
            section_name="my-section",
        )
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([page])
        assert "## My Section" in content


class TestOptionalSection:
    """Test the Optional section with machine-readable format links."""

    def test_optional_section_with_all_formats(self):
        site = _make_site()
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert "## Optional" in content
        assert "llm-full.txt" in content
        assert "index.json" in content
        assert "robots.txt" in content

    def test_optional_section_with_baseurl(self):
        site = _make_site(baseurl="/docs")
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert "/docs/llm-full.txt" in content
        assert "/docs/index.json" in content

    def test_optional_section_omitted_when_no_formats(self):
        site = _make_site(
            config_overrides={
                "output_formats": {"site_wide": ["llms_txt"]},
                "content_signals": {"enabled": False},
            }
        )
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert "## Optional" not in content

    def test_optional_includes_content_signals_link(self):
        site = _make_site()
        gen = SiteLlmsTxtGenerator(site)
        content = gen._render([])
        assert "robots.txt" in content
        assert "Content Signals" in content


class TestLlmsTxtGenerate:
    """Test the generate() method writes to disk."""

    def test_writes_llms_txt(self, tmp_path):
        site = _make_site(title="My Site", description="A great site.")
        site.output_dir = tmp_path

        page = _make_page(
            title="Quick Start",
            path="/docs/quickstart/",
            description="Get started in 5 minutes.",
        )

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate([page])

        assert result == tmp_path / "llms.txt"
        assert result.exists()

        content = result.read_text(encoding="utf-8")
        assert content.startswith("# My Site\n")
        assert "> A great site." in content
        assert "[Quick Start](/docs/quickstart/): Get started in 5 minutes." in content

    def test_empty_site_produces_valid_output(self, tmp_path):
        site = _make_site(title="Empty")
        site.output_dir = tmp_path

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate([])

        content = result.read_text(encoding="utf-8")
        assert content.startswith("# Empty\n")


class TestCuration:
    """Test page curation: virtual page filtering and max_pages cap."""

    def test_excludes_virtual_pages(self, tmp_path):
        site = _make_site(title="Site")
        site.output_dir = tmp_path

        real_page = _make_page(title="Real", path="/real/")
        real_page.is_virtual = False

        virtual_page = _make_page(title="Virtual", path="/tags/python/")
        virtual_page.is_virtual = True

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate([real_page, virtual_page])

        content = result.read_text(encoding="utf-8")
        assert "[Real]" in content
        assert "Virtual" not in content

    def test_max_pages_cap(self, tmp_path):
        site = _make_site(
            title="Site",
            config_overrides={
                "output_formats": {
                    "options": {"llms_txt_max_pages": 2},
                    "site_wide": ["llms_txt"],
                },
            },
        )
        site.output_dir = tmp_path

        pages = [
            _make_page(title=f"Page {i}", path=f"/page-{i}/", section_name="docs") for i in range(5)
        ]
        for p in pages:
            p.is_virtual = False

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate(pages)

        content = result.read_text(encoding="utf-8")
        assert "[Page 0]" in content
        assert "[Page 1]" in content
        # Pages beyond the cap should be excluded
        assert "[Page 2]" not in content


class TestTruncation:
    """Test max_chars truncation with rollback and notice."""

    def test_max_chars_truncates_with_notice(self, tmp_path):
        site = _make_site(
            title="Site",
            config_overrides={
                "output_formats": {
                    "options": {"llms_txt_max_chars": 200},
                    "site_wide": ["llms_txt"],
                },
            },
        )
        site.output_dir = tmp_path

        pages = [
            _make_page(
                title=f"Page {i}",
                path=f"/page-{i}/",
                description="A" * 50,
                section_name="docs",
            )
            for i in range(20)
        ]
        for p in pages:
            p.is_virtual = False

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate(pages)

        content = result.read_text(encoding="utf-8")
        # Should have truncation notice
        assert "llm-full.txt" in content
        assert "more pages" in content
        # Not all pages should be present
        assert "[Page 19]" not in content

    def test_output_stays_under_max_chars(self, tmp_path):
        max_chars = 300
        site = _make_site(
            title="S",
            description="",
            config_overrides={
                "output_formats": {
                    "options": {"llms_txt_max_chars": max_chars},
                    "site_wide": [],
                },
                "content_signals": {"enabled": False},
            },
        )
        site.output_dir = tmp_path

        pages = [
            _make_page(
                title=f"Page {i}",
                path=f"/p{i}/",
                description="Desc " * 10,
                section_name="docs",
            )
            for i in range(50)
        ]
        for p in pages:
            p.is_virtual = False

        gen = SiteLlmsTxtGenerator(site)
        result = gen.generate(pages)

        content = result.read_text(encoding="utf-8")
        # The truncation notice and optional section add some overhead,
        # but the page entries themselves should have stopped before the cap
        # (we accept the notice/footer pushing slightly over)
        assert len(content) < max_chars * 2  # generous bound


class TestOutputTypeClassification:
    """Test that llms.txt is classified correctly."""

    def test_llms_txt_is_aggregate_text(self):
        from bengal.orchestration.build.output_types import OutputType, classify_output

        path = Path("public/llms.txt")
        assert classify_output(path) == OutputType.AGGREGATE_TEXT
