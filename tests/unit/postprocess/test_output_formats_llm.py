"""
Tests for LLM.txt output format generation.

This test suite ensures that LLM.txt files are always available and correctly formatted:
- Per-page index.txt files are generated next to HTML
- Site-wide llm-full.txt is generated at site root
- Content follows the LLM.txt format specification
- URLs and paths are correct for action-bar copy/share functionality
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

from bengal.postprocess.output_formats import OutputFormatsGenerator


class TestPerPageLLMTextGeneration:
    """Test per-page LLM.txt file generation (index.txt)."""

    def test_generates_llm_txt_next_to_html(self, tmp_path):
        """Test that index.txt is generated next to index.html."""
        # Setup
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Getting Started",
            url="/docs/getting-started/",
            content="This is the getting started guide.",
            output_path=output_dir / "docs/getting-started/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        expected_txt_path = output_dir / "docs/getting-started/index.txt"
        assert expected_txt_path.exists(), "LLM.txt file should exist next to HTML"

        # Verify content format
        content = expected_txt_path.read_text()
        assert "# Getting Started" in content
        assert "URL: /docs/getting-started/" in content
        assert "This is the getting started guide." in content

    def test_llm_txt_includes_metadata(self, tmp_path):
        """Test that LLM.txt includes page metadata."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="API Reference",
            url="/api/",
            content="API documentation content",
            output_path=output_dir / "api/index.html",
            tags=["api", "reference"],
            section_name="api",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        txt_path = output_dir / "api/index.txt"
        content = txt_path.read_text()

        assert "Section: api" in content
        assert "Tags: api, reference" in content
        assert "Word Count:" in content
        assert "Reading Time:" in content

    def test_llm_txt_uses_plain_text(self, tmp_path):
        """Test that LLM.txt uses page.plain_text (pre-extracted via AST)."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Tutorial",
            url="/tutorial/",
            content="<p>This is <strong>bold</strong> and <em>italic</em> text.</p>",
            output_path=output_dir / "tutorial/index.html",
        )
        # plain_text should already be extracted (via AST walker in real usage)
        page.plain_text = "This is bold and italic text."
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        txt_path = output_dir / "tutorial/index.txt"
        content = txt_path.read_text()

        # Should have plain text from page.plain_text property
        assert "This is bold and italic text" in content
        assert "<p>" not in content
        assert "<strong>" not in content
        assert "<em>" not in content

    def test_llm_txt_uses_custom_separator_width(self, tmp_path):
        """Test that separator width can be customized."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test Page",
            url="/test/",
            content="Test content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {
            "enabled": True,
            "per_page": ["llm_txt"],
            "site_wide": [],
            "options": {"llm_separator_width": 60},
        }
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        txt_path = output_dir / "test/index.txt"
        content = txt_path.read_text()

        # Should have separator of exactly 60 dashes
        assert "\n" + ("-" * 60) + "\n" in content

    def test_llm_txt_disabled_by_config(self, tmp_path):
        """Test that LLM.txt is not generated when disabled."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test Page",
            url="/test/",
            content="Test content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": []}  # No llm_txt
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        txt_path = output_dir / "test/index.txt"
        assert not txt_path.exists(), "LLM.txt should not be generated when disabled"

    def test_llm_txt_skips_pages_without_output_path(self, tmp_path):
        """Test that pages without output_path are skipped."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Draft Page",
            url="/draft/",
            content="Draft content",
            output_path=None,  # No output path
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute - should not crash
        generator.generate()

        # Assert - no files should be created
        assert not list(output_dir.rglob("*.txt"))

    def test_llm_txt_excludes_by_pattern(self, tmp_path):
        """Test that pages matching exclusion patterns are skipped."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        page1 = self._create_mock_page(
            title="Normal Page",
            url="/normal/",
            content="Normal content",
            output_path=output_dir / "normal/index.html",
        )
        page2 = self._create_mock_page(
            title="404 Not Found",
            url="/404.html",
            content="404 content",
            output_path=output_dir / "404.html",
        )

        mock_site.pages = [page1, page2]

        config = {
            "enabled": True,
            "per_page": ["llm_txt"],
            "site_wide": [],
            "options": {"exclude_patterns": ["404.html"]},
        }
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        assert (output_dir / "normal/index.txt").exists()
        assert not (output_dir / "404.txt").exists()

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path) -> Mock:
        """Create a mock Site instance."""
        site = Mock()
        site.site_dir = site_dir
        site.output_dir = output_dir
        site.config = {
            "site": {"title": "Test Site", "baseurl": "https://example.com"},
            "build": {},
        }
        site.pages = []
        site.sections = {}
        site._tag_index = MagicMock()
        site._tag_index.all_tags.return_value = []
        return site

    def _create_mock_page(
        self,
        title: str,
        url: str,
        content: str,
        output_path: Path | None,
        tags: list[str] | None = None,
        section_name: str | None = None,
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.url = url
        page.content = content
        page.parsed_ast = content  # Simplified for testing
        page.plain_text = content  # For AST-based extraction
        page.output_path = output_path
        page.tags = tags or []
        page.date = None
        page.metadata = {}

        # Mock section
        if section_name:
            section = Mock()
            section.name = section_name
            page._section = section
        else:
            page._section = None

        return page


class TestSiteWideLLMFullGeneration:
    """Test site-wide llm-full.txt generation."""

    def test_generates_llm_full_at_site_root(self, tmp_path):
        """Test that llm-full.txt is generated at site root."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page1 = self._create_mock_page(
            title="Page One",
            url="/page1/",
            content="Content one",
            output_path=output_dir / "page1/index.html",
        )
        page2 = self._create_mock_page(
            title="Page Two",
            url="/page2/",
            content="Content two",
            output_path=output_dir / "page2/index.html",
        )
        mock_site.pages = [page1, page2]

        config = {"enabled": True, "per_page": [], "site_wide": ["llm_full"]}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        llm_full_path = output_dir / "llm-full.txt"
        assert llm_full_path.exists(), "llm-full.txt should exist at site root"

        content = llm_full_path.read_text()
        assert "## Page 1/2: Page One" in content
        assert "## Page 2/2: Page Two" in content
        assert "Page One" in content
        assert "Page Two" in content

    def test_llm_full_concatenates_all_pages(self, tmp_path):
        """Test that llm-full.txt contains all pages."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create 5 pages
        pages = []
        for i in range(5):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content for page {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        config = {"enabled": True, "per_page": [], "site_wide": ["llm_full"]}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        content = (output_dir / "llm-full.txt").read_text()
        for i in range(5):
            assert f"Page {i}" in content
            assert f"Content for page {i}" in content

    def test_llm_full_includes_page_numbers(self, tmp_path):
        """Test that llm-full.txt includes page numbers (PAGE X/Y)."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        pages = [
            self._create_mock_page(
                f"Page {i}", f"/p{i}/", f"Content {i}", output_dir / f"p{i}/index.html"
            )
            for i in range(3)
        ]
        mock_site.pages = pages

        config = {"enabled": True, "per_page": [], "site_wide": ["llm_full"]}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        content = (output_dir / "llm-full.txt").read_text()
        assert "## Page 1/3:" in content
        assert "## Page 2/3:" in content
        assert "## Page 3/3:" in content

    def test_llm_full_disabled_by_config(self, tmp_path):
        """Test that llm-full.txt is not generated when disabled."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page("Test", "/test/", "Content", output_dir / "test/index.html")
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": []}  # No llm_full
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        assert not (output_dir / "llm-full.txt").exists()

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path) -> Mock:
        """Create a mock Site instance."""
        site = Mock()
        site.site_dir = site_dir
        site.output_dir = output_dir
        site.config = {
            "site": {"title": "Test Site", "baseurl": "https://example.com"},
            "build": {},
        }
        site.pages = []
        site.sections = {}
        site._tag_index = MagicMock()
        site._tag_index.all_tags.return_value = []
        return site

    def _create_mock_page(
        self, title: str, url: str, content: str, output_path: Path | None
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.url = url
        page.content = content
        page.parsed_ast = content
        page.plain_text = content  # For AST-based extraction
        page.output_path = output_path
        page.tags = []
        page.date = None
        page.metadata = {}
        page._section = None
        return page


class TestLLMTextFormatSpec:
    """Test LLM.txt format specification compliance."""

    def test_format_has_title_header(self, tmp_path):
        """Test that format starts with # Title."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            "My Test Page", "/test/", "Content", output_dir / "test/index.html"
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        generator.generate()

        content = (output_dir / "test/index.txt").read_text()
        lines = content.split("\n")
        assert lines[0] == "# My Test Page"

    def test_format_has_separators(self, tmp_path):
        """Test that format includes separator lines."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page("Test", "/test/", "Content", output_dir / "test/index.html")
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        generator.generate()

        content = (output_dir / "test/index.txt").read_text()
        # Should have at least two 80-character separator lines
        assert ("-" * 80) in content

    def test_format_has_metadata_section(self, tmp_path):
        """Test that format includes metadata section at end."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            "Test", "/test/", "Content goes here", output_dir / "test/index.html"
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": ["llm_txt"], "site_wide": []}
        generator = OutputFormatsGenerator(mock_site, config)

        generator.generate()

        content = (output_dir / "test/index.txt").read_text()
        assert "Metadata:" in content
        assert "- Word Count:" in content
        assert "- Reading Time:" in content

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path) -> Mock:
        """Create a mock Site instance."""
        site = Mock()
        site.site_dir = site_dir
        site.output_dir = output_dir
        site.config = {
            "site": {"title": "Test Site", "baseurl": "https://example.com"},
            "build": {},
        }
        site.pages = []
        site.sections = {}
        site._tag_index = MagicMock()
        site._tag_index.all_tags.return_value = []
        return site

    def _create_mock_page(
        self, title: str, url: str, content: str, output_path: Path | None
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.url = url
        page.content = content
        page.parsed_ast = content
        page.plain_text = content  # For AST-based extraction
        page.output_path = output_path
        page.tags = []
        page.date = None
        page.metadata = {}
        page._section = None
        return page


class TestConfigurationHandling:
    """Test configuration parsing and handling."""

    def test_simple_config_format(self, tmp_path):
        """Test simple configuration format (from [build.output_formats])."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = Mock()
        mock_site.site_dir = tmp_path
        mock_site.output_dir = output_dir
        mock_site.config = {"site": {}, "build": {}}
        mock_site.pages = []

        # Simple format
        config = {"enabled": True, "llm_txt": True, "site_llm": True}
        generator = OutputFormatsGenerator(mock_site, config)

        # Should normalize to advanced format
        assert "llm_txt" in generator.config["per_page"]
        assert "llm_full" in generator.config["site_wide"]

    def test_advanced_config_format(self, tmp_path):
        """Test advanced configuration format (from [output_formats])."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = Mock()
        mock_site.site_dir = tmp_path
        mock_site.output_dir = output_dir
        mock_site.config = {"site": {}, "build": {}}
        mock_site.pages = []

        # Advanced format
        config = {
            "enabled": True,
            "per_page": ["llm_txt"],
            "site_wide": ["llm_full"],
            "options": {"llm_separator_width": 100},
        }
        generator = OutputFormatsGenerator(mock_site, config)

        # Should use as-is
        assert generator.config["per_page"] == ["llm_txt"]
        assert generator.config["site_wide"] == ["llm_full"]
        assert generator.config["options"]["llm_separator_width"] == 100

    def test_defaults_when_no_config(self, tmp_path):
        """Test that defaults are used when no config provided."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = Mock()
        mock_site.site_dir = tmp_path
        mock_site.output_dir = output_dir
        mock_site.config = {"site": {}, "build": {}}
        mock_site.pages = []

        generator = OutputFormatsGenerator(mock_site, None)

        # Should have defaults
        assert generator.config["enabled"] is True
        assert "llm_txt" in generator.config["per_page"]
        assert "llm_full" in generator.config["site_wide"]
