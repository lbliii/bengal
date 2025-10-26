"""
Unit tests for Renderer template selection logic.
"""

from pathlib import Path
from unittest.mock import Mock

from bengal.core.page import Page
from bengal.rendering.renderer import Renderer


class MockTemplateEngine:
    """Mock template engine for testing."""

    def __init__(self, available_templates=None):
        self.available_templates = available_templates or []
        self.env = Mock()
        self.site = Mock()
        self.site.config = {}

        # Mock env.get_template to check availability
        def mock_get_template(name):
            if name in self.available_templates:
                return Mock()
            raise Exception(f"Template {name} not found")

        self.env.get_template = mock_get_template


class MockSection:
    """Mock section for testing."""

    def __init__(self, name):
        from pathlib import Path

        self.name = name
        self.path = Path(f"/content/{name}")  # Add required path attribute


class TestTemplateSelection:
    """Tests for Renderer._get_template_name() logic."""

    def _setup_page_with_section(self, source_path, metadata, section_name):
        """Helper to set up a page with a mock section and site registry."""
        from bengal.core.site import Site

        page = Page(source_path=source_path, metadata=metadata)
        section = MockSection(section_name)

        # Create minimal mock site with section registry
        site = Site(root_path=Path("/site"), config={})
        site._section_registry[section.path] = section

        page._site = site
        page._section = section
        return page

    def test_explicit_template_highest_priority(self):
        """Test that explicit template in frontmatter has highest priority."""
        # Setup
        engine = MockTemplateEngine(available_templates=["custom.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(
            Path("/content/docs/page.md"), {"template": "custom.html"}, "docs"
        )

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "custom.html"

    def test_section_auto_detection_flat(self):
        """Test section-based auto-detection with flat template."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs.html"

    def test_section_auto_detection_directory_single(self):
        """Test section-based auto-detection with directory structure (single.html)."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs/single.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs/single.html"

    def test_section_auto_detection_directory_page(self):
        """Test section-based auto-detection with directory structure (page.html)."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs/page.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs/page.html"

    def test_section_index_auto_detection_flat(self):
        """Test section index auto-detection with flat template."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/_index.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs.html"

    def test_section_index_auto_detection_list(self):
        """Test section index auto-detection with list.html."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs/list.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/_index.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs/list.html"

    def test_section_index_auto_detection_index(self):
        """Test section index auto-detection with index.html in directory."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs/index.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/_index.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs/index.html"

    def test_section_index_auto_detection_flat_with_suffix(self):
        """Test section index auto-detection with flat template with -list suffix."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs-list.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/_index.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "docs-list.html"

    def test_template_priority_order(self):
        """Test that templates are tried in correct priority order."""
        # Setup - have both flat and directory templates available
        engine = MockTemplateEngine(
            available_templates=[
                "docs/single.html",  # Should be tried first
                "docs.html",
            ]
        )
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert - should pick directory version (higher priority)
        assert template_name == "docs/single.html"

    def test_fallback_to_page_html(self):
        """Test fallback to page.html when no section template exists."""
        # Setup
        engine = MockTemplateEngine(available_templates=["page.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "page.html"

    def test_fallback_to_index_html_for_section_index(self):
        """Test fallback to index.html for section index pages."""
        # Setup
        engine = MockTemplateEngine(available_templates=["index.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(Path("/content/docs/_index.md"), {}, "docs")

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "index.html"

    def test_page_without_section(self):
        """Test template selection for pages without a section."""
        # Setup
        engine = MockTemplateEngine(available_templates=["page.html"])
        renderer = Renderer(engine)

        page = Page(source_path=Path("/content/about.md"), metadata={})
        # No section set

        # Test
        template_name = renderer._get_template_name(page)

        # Assert
        assert template_name == "page.html"

    def test_type_metadata_not_used_for_template_selection(self):
        """Test that 'type' metadata is NOT used for template selection."""
        # Setup
        engine = MockTemplateEngine(available_templates=["page.html"])
        renderer = Renderer(engine)

        page = self._setup_page_with_section(
            Path("/content/docs/guide.md"),
            {"type": "guide"},  # Semantic metadata, not for template selection
            "docs",
        )

        # Test
        template_name = renderer._get_template_name(page)

        # Assert - should fallback to page.html, not look for guide.html
        assert template_name == "page.html"

    def test_multiple_sections_different_templates(self):
        """Test that different sections can have different templates."""
        # Setup
        engine = MockTemplateEngine(
            available_templates=["docs.html", "blog.html", "tutorials.html"]
        )
        renderer = Renderer(engine)

        # Test docs section
        docs_page = self._setup_page_with_section(Path("/content/docs/page.md"), {}, "docs")
        assert renderer._get_template_name(docs_page) == "docs.html"

        # Test blog section
        blog_page = self._setup_page_with_section(Path("/content/blog/post.md"), {}, "blog")
        assert renderer._get_template_name(blog_page) == "blog.html"

        # Test tutorials section
        tutorial_page = self._setup_page_with_section(
            Path("/content/tutorials/intro.md"), {}, "tutorials"
        )
        assert renderer._get_template_name(tutorial_page) == "tutorials.html"


class TestTemplateExists:
    """Tests for Renderer._template_exists() helper."""

    def test_template_exists_returns_true(self):
        """Test that _template_exists returns True for available templates."""
        # Setup
        engine = MockTemplateEngine(available_templates=["docs.html"])
        renderer = Renderer(engine)

        # Mock the env.get_template method
        renderer.template_engine.env.get_template = lambda name: (
            Mock() if name == "docs.html" else (_ for _ in ()).throw(Exception())
        )

        # Test
        result = renderer._template_exists("docs.html")

        # Assert
        assert result is True

    def test_template_exists_returns_false(self):
        """Test that _template_exists returns False for missing templates."""
        # Setup
        engine = MockTemplateEngine(available_templates=[])
        renderer = Renderer(engine)

        # Mock the env.get_template method to raise exception
        renderer.template_engine.env.get_template = Mock(side_effect=Exception("Not found"))

        # Test
        result = renderer._template_exists("nonexistent.html")

        # Assert
        assert result is False


class TestTemplateMocking:
    """Test that the mock setup is working correctly."""

    def test_mock_template_engine(self):
        """Test mock template engine setup."""
        engine = MockTemplateEngine(available_templates=["test.html"])
        assert "test.html" in engine.available_templates

    def test_mock_section(self):
        """Test mock section setup."""
        section = MockSection("docs")
        assert section.name == "docs"

    def test_page_creation(self):
        """Test page creation for testing."""
        page = Page(source_path=Path("/content/test.md"), metadata={"title": "Test"})
        assert page.source_path.name == "test.md"
        assert page.metadata["title"] == "Test"
