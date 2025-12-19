"""
Tests for content type detection in SectionOrchestrator.
"""

from datetime import datetime
from pathlib import Path

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.orchestration.section import SectionOrchestrator


class TestContentTypeDetection:
    """Test automatic content type detection for sections."""

    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        return site

    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)

    def test_explicit_content_type_override(self, orchestrator):
        """Test that explicit content_type in metadata takes precedence."""
        section = Section(
            name="docs", path=Path("/content/docs"), metadata={"content_type": "custom"}
        )

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "custom"

    @pytest.mark.parametrize(
        "section_name,expected_type",
        [
            # API Reference detection
            ("api", "autodoc/python"),
            ("reference", "autodoc/python"),
            ("autodoc/python", "autodoc/python"),
            ("api-docs", "autodoc/python"),
            # CLI Reference detection
            ("cli", "autodoc/cli"),
            ("commands", "autodoc/cli"),
            ("autodoc/cli", "autodoc/cli"),
            ("command-line", "autodoc/cli"),
            # Tutorial detection
            ("tutorials", "tutorial"),
            ("guides", "tutorial"),
            ("how-to", "tutorial"),
            # Blog detection (chronological content)
            ("blog", "blog"),
            ("posts", "blog"),
            ("news", "blog"),
            ("articles", "blog"),
        ],
        ids=[
            "api",
            "reference",
            "autodoc/python",
            "api-docs",
            "cli",
            "commands",
            "autodoc/cli",
            "command-line",
            "tutorials",
            "guides",
            "how-to",
            "blog",
            "posts",
            "news",
            "articles",
        ],
    )
    def test_content_type_detection_by_name(self, orchestrator, section_name, expected_type):
        """
        Test that section names are correctly mapped to content types.

        This is critical for automatic template selection and feature activation.
        The content type determines:
        - Which template is used for rendering
        - Whether pagination is enabled
        - How pages are sorted and grouped

        Tests multiple section naming conventions to ensure robust detection.
        """
        section = Section(name=section_name, path=Path(f"/content/{section_name}"))
        detected_type = orchestrator._detect_content_type(section)

        assert detected_type == expected_type, (
            f"Section '{section_name}' should be detected as '{expected_type}' "
            f"but was detected as '{detected_type}'"
        )

    def test_api_reference_by_page_metadata(self, orchestrator):
        """Test API reference detection by page metadata."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add pages with API reference type
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/docs/module{i}.md"),
                content="API docs",
                metadata={"type": "python-module"},
            )
            section.add_page(page)

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "autodoc/python"

    def test_cli_reference_by_page_metadata(self, orchestrator):
        """Test CLI reference detection by page metadata."""
        section = Section(name="commands", path=Path("/content/commands"))

        # Add pages with CLI command type
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/commands/cmd{i}.md"),
                content="Command docs",
                metadata={"type": "command"},
            )
            section.add_page(page)

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "autodoc/cli"

    def test_archive_by_date_heuristic(self, orchestrator):
        """Test blog detection when pages have dates."""
        section = Section(name="articles", path=Path("/content/articles"))

        # Add pages with dates (60%+ should trigger blog detection)
        for i in range(5):
            page = Page(
                source_path=Path(f"/content/articles/post{i}.md"),
                content="Post content",
                metadata={"title": f"Post {i}", "date": datetime(2025, 1, i + 1)},
            )
            section.add_page(page)

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "blog"

    def test_list_when_few_dates(self, orchestrator):
        """Test doc detection for sections named 'docs'."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add 2 pages with dates, 3 without (40% with dates)
        for i in range(2):
            page = Page(
                source_path=Path(f"/content/docs/dated{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, i + 1)},
            )
            section.add_page(page)

        for i in range(3):
            page = Page(
                source_path=Path(f"/content/docs/page{i}.md"), content="Content", metadata={}
            )
            section.add_page(page)

        content_type = orchestrator._detect_content_type(section)
        # "docs" is detected by DocsStrategy
        assert content_type == "doc"

    def test_list_default_for_unknown(self, orchestrator):
        """Test that unknown sections default to 'list' not 'archive'."""
        section = Section(name="random", path=Path("/content/random"))

        # Add some regular pages without dates
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/random/page{i}.md"),
                content="Content",
                metadata={"title": f"Page {i}"},
            )
            section.add_page(page)

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "list"

    def test_empty_section_defaults_to_list(self, orchestrator):
        """Test that empty sections default to 'list'."""
        section = Section(name="empty", path=Path("/content/empty"))

        content_type = orchestrator._detect_content_type(section)
        assert content_type == "list"


class TestTemplateSelection:
    """Test template selection based on content type."""

    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        return site

    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)

    def test_api_reference_template(self, orchestrator):
        """Test API reference uses autodoc/python/list.html."""
        template = orchestrator._get_template_for_content_type("autodoc/python")
        assert template == "autodoc/python/list.html"

    def test_cli_reference_template(self, orchestrator):
        """Test CLI reference uses autodoc/cli/list.html."""
        template = orchestrator._get_template_for_content_type("autodoc/cli")
        assert template == "autodoc/cli/list.html"

    def test_tutorial_template(self, orchestrator):
        """Test tutorial uses tutorial/list.html."""
        template = orchestrator._get_template_for_content_type("tutorial")
        assert template == "tutorial/list.html"

    def test_archive_template(self, orchestrator):
        """Test archive uses archive.html."""
        template = orchestrator._get_template_for_content_type("archive")
        assert template == "archive.html"

    def test_list_template(self, orchestrator):
        """Test generic list uses index.html."""
        template = orchestrator._get_template_for_content_type("list")
        assert template == "index.html"

    def test_unknown_type_defaults_to_index(self, orchestrator):
        """Test unknown content type defaults to index.html."""
        template = orchestrator._get_template_for_content_type("unknown-type")
        assert template == "index.html"


class TestPaginationDecision:
    """Test pagination decisions based on content type."""

    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        site.config = {"pagination": {"per_page": 10, "threshold": 20}}
        return site

    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)

    def test_reference_never_paginates(self, orchestrator):
        """Test that reference docs never paginate."""
        section = Section(name="api", path=Path("/content/api"))

        # Add many pages
        for i in range(100):
            page = Page(
                source_path=Path(f"/content/api/page{i}.md"), content="Content", metadata={}
            )
            section.add_page(page)

        # API reference should not paginate
        assert not orchestrator._should_paginate(section, "autodoc/python")
        # CLI reference should not paginate
        assert not orchestrator._should_paginate(section, "autodoc/cli")
        # Tutorial should not paginate
        assert not orchestrator._should_paginate(section, "tutorial")

    def test_archive_paginates_when_threshold_exceeded(self, orchestrator):
        """Test that archives paginate when exceeding threshold."""
        section = Section(name="blog", path=Path("/content/blog"))

        # Add pages exceeding threshold (20)
        for i in range(25):
            page = Page(
                source_path=Path(f"/content/blog/post{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, 1)},
            )
            section.add_page(page)

        assert orchestrator._should_paginate(section, "archive")

    def test_archive_no_pagination_below_threshold(self, orchestrator):
        """Test that archives don't paginate below threshold."""
        section = Section(name="blog", path=Path("/content/blog"))

        # Add pages below threshold (20)
        for i in range(10):
            page = Page(
                source_path=Path(f"/content/blog/post{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, 1)},
            )
            section.add_page(page)

        assert not orchestrator._should_paginate(section, "archive")

    def test_explicit_pagination_override(self, orchestrator):
        """Test explicit pagination metadata overrides heuristics."""
        section = Section(name="docs", path=Path("/content/docs"), metadata={"paginate": True})

        # Even with few pages, explicit override should enable pagination
        for i in range(5):
            page = Page(
                source_path=Path(f"/content/docs/page{i}.md"), content="Content", metadata={}
            )
            section.add_page(page)

        # Note: reference docs still won't paginate (explicit check first)
        # But for 'list' type, explicit override works
        assert orchestrator._should_paginate(section, "list")
