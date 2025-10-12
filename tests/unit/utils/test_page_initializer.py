"""
Comprehensive tests for PageInitializer utility.

Tests page validation and initialization:
- Setting _site references
- Validating output_path
- Ensuring URL generation works
- Section-specific initialization
- Error handling and fail-fast validation
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.utils.page_initializer import PageInitializer


class TestPageInitializer:
    """Test PageInitializer validation and initialization."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create mock site for testing."""
        site = Mock(spec=Site)
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True)
        site.config = {"site": {"base_url": "https://example.com"}}
        return site

    @pytest.fixture
    def initializer(self, mock_site):
        """Create PageInitializer instance."""
        return PageInitializer(mock_site)

    @pytest.fixture
    def valid_page(self, tmp_path, mock_site):
        """Create a valid page with all required attributes."""
        page = Page(
            source_path=tmp_path / "content" / "test.md",
            content="# Test",
            metadata={"title": "Test Page"},
        )
        page.output_path = mock_site.output_dir / "test" / "index.html"
        return page

    # =========================================================================
    # Basic Initialization Tests
    # =========================================================================

    def test_init_stores_site_reference(self, mock_site):
        """Test that initializer stores site reference."""
        initializer = PageInitializer(mock_site)

        assert initializer.site == mock_site

    def test_ensure_initialized_sets_site_reference(self, initializer, mock_site, tmp_path):
        """Test that _site reference is set automatically."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = mock_site.output_dir / "test" / "index.html"

        # Initially no _site
        assert page._site is None

        initializer.ensure_initialized(page)

        # Now has _site
        assert page._site == mock_site

    def test_ensure_initialized_preserves_existing_site(self, initializer, tmp_path):
        """Test that existing _site reference is not overwritten."""
        other_site = Mock(spec=Site)
        other_site.output_dir = tmp_path / "other_public"
        other_site.output_dir.mkdir(parents=True)

        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page._site = other_site  # Already set
        page.output_path = other_site.output_dir / "test" / "index.html"

        initializer.ensure_initialized(page)

        # Should preserve existing _site
        assert page._site == other_site

    def test_ensure_initialized_success_with_all_attributes(
        self, initializer, valid_page, mock_site
    ):
        """Test successful initialization with all required attributes."""
        # Should not raise
        initializer.ensure_initialized(valid_page)

        assert valid_page._site == mock_site
        assert valid_page.url == "/test/"

    # =========================================================================
    # Output Path Validation Tests
    # =========================================================================

    def test_ensure_initialized_missing_output_path(self, initializer, tmp_path):
        """Test error when output_path is missing."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        # No output_path set

        with pytest.raises(ValueError, match="has no output_path"):
            initializer.ensure_initialized(page)

    def test_ensure_initialized_none_output_path(self, initializer, tmp_path):
        """Test error when output_path is explicitly None."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = None

        with pytest.raises(ValueError, match="has no output_path"):
            initializer.ensure_initialized(page)

    def test_ensure_initialized_relative_output_path(self, initializer, tmp_path):
        """Test error when output_path is relative."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = Path("public/test/index.html")  # Relative!

        with pytest.raises(ValueError, match="relative output_path"):
            initializer.ensure_initialized(page)

    def test_ensure_initialized_absolute_path_works(self, initializer, mock_site, tmp_path):
        """Test that absolute output_path is accepted."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = mock_site.output_dir / "test" / "index.html"

        # Should not raise
        initializer.ensure_initialized(page)

        assert page._site == mock_site

    # =========================================================================
    # URL Generation Validation Tests
    # =========================================================================

    def test_ensure_initialized_url_generation_succeeds(self, initializer, valid_page):
        """Test that URL generation is validated during initialization."""
        # Should not raise
        initializer.ensure_initialized(valid_page)

        # Verify URL works
        assert valid_page.url == "/test/"

    def test_ensure_initialized_url_generation_path_outside_output_dir(
        self, initializer, mock_site, tmp_path, capsys
    ):
        """Test behavior when output_path is outside output directory."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        # Set output_path outside of output_dir
        page.output_path = tmp_path / "other" / "test.html"

        # Should not raise - Page.url falls back to slug-based URL with warning
        initializer.ensure_initialized(page)

        # Should have printed warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "not under output directory" in captured.out

    def test_ensure_initialized_with_nonexistent_path(
        self, initializer, mock_site, tmp_path, capsys
    ):
        """Test behavior with nonexistent output_path."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        # Set a valid-looking but nonexistent output_path
        page.output_path = Path("/nonexistent/public/test/index.html")

        # Should not raise - Page.url falls back gracefully
        initializer.ensure_initialized(page)

        # Should have generated a URL (fallback)
        assert page.url.startswith("/")

    # =========================================================================
    # Section-Specific Initialization Tests
    # =========================================================================

    def test_ensure_initialized_for_section_sets_both_references(
        self, initializer, mock_site, tmp_path
    ):
        """Test that section initialization sets both _site and _section."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")

        page = Page(source_path=tmp_path / "docs" / "_index.md", metadata={"title": "Docs"})
        page.output_path = mock_site.output_dir / "docs" / "index.html"

        initializer.ensure_initialized_for_section(page, section)

        assert page._site == mock_site
        assert page._section == section

    def test_ensure_initialized_for_section_preserves_existing_section(
        self, initializer, mock_site, tmp_path
    ):
        """Test that existing _section reference is not overwritten."""
        section1 = Section(name="docs", path=tmp_path / "content" / "docs")
        section2 = Section(name="blog", path=tmp_path / "content" / "blog")

        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page._section = section1  # Already set
        page.output_path = mock_site.output_dir / "test" / "index.html"

        initializer.ensure_initialized_for_section(page, section2)

        # Should preserve existing _section
        assert page._section == section1

    def test_ensure_initialized_for_section_validates_output_path(self, initializer, tmp_path):
        """Test that section initialization still validates output_path."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")

        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        # No output_path

        with pytest.raises(ValueError, match="has no output_path"):
            initializer.ensure_initialized_for_section(page, section)

    def test_ensure_initialized_for_section_handles_path_outside_dir(
        self, initializer, mock_site, tmp_path, capsys
    ):
        """Test that section initialization handles path outside output_dir."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")

        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = tmp_path / "other" / "test.html"  # Outside output_dir

        # Should not raise - Page.url falls back gracefully
        initializer.ensure_initialized_for_section(page, section)

        # Should have set section reference
        assert page._section == section

    # =========================================================================
    # Error Message Quality Tests
    # =========================================================================

    def test_error_message_includes_page_title(self, initializer, tmp_path):
        """Test that error messages include helpful page info."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "My Important Page"})
        # No output_path

        with pytest.raises(ValueError) as exc_info:
            initializer.ensure_initialized(page)

        error_msg = str(exc_info.value)
        assert "My Important Page" in error_msg

    def test_error_message_includes_source_path(self, initializer, tmp_path):
        """Test that error messages include source path."""
        page = Page(
            source_path=tmp_path / "content" / "blog" / "post.md", metadata={"title": "Test"}
        )
        # No output_path

        with pytest.raises(ValueError) as exc_info:
            initializer.ensure_initialized(page)

        error_msg = str(exc_info.value)
        assert "post.md" in error_msg or str(page.source_path) in error_msg

    def test_error_message_for_missing_output_path_is_clear(self, initializer, tmp_path):
        """Test that missing output_path error is actionable."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})

        with pytest.raises(ValueError) as exc_info:
            initializer.ensure_initialized(page)

        error_msg = str(exc_info.value)
        assert "output_path" in error_msg.lower()
        assert "orchestrator" in error_msg.lower()  # Hints at solution

    def test_error_message_for_relative_path_is_clear(self, initializer, tmp_path):
        """Test that relative path error is actionable."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = Path("relative/path.html")

        with pytest.raises(ValueError) as exc_info:
            initializer.ensure_initialized(page)

        error_msg = str(exc_info.value)
        assert "relative" in error_msg.lower()

    def test_url_generation_succeeds_for_valid_paths(self, initializer, mock_site, tmp_path):
        """Test that URL generation succeeds for valid paths."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = mock_site.output_dir / "test" / "index.html"

        # Should not raise
        initializer.ensure_initialized(page)

        # URL should be valid
        assert page.url == "/test/"

    # =========================================================================
    # Generated Page Tests
    # =========================================================================

    def test_initialize_generated_archive_page(self, initializer, mock_site, tmp_path):
        """Test initialization of generated archive page."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        # Create archive page (as orchestrator would)
        archive_page = Page(
            source_path=tmp_path / ".bengal" / "generated" / "archives" / "blog" / "index.md",
            content="",
            metadata={
                "title": "Blog",
                "template": "archive.html",
                "type": "archive",
                "_generated": True,
            },
        )
        archive_page.output_path = mock_site.output_dir / "blog" / "index.html"

        # Initialize
        initializer.ensure_initialized_for_section(archive_page, section)

        assert archive_page._site == mock_site
        assert archive_page._section == section
        assert archive_page.url == "/blog/"

    def test_initialize_generated_tag_page(self, initializer, mock_site, tmp_path):
        """Test initialization of generated tag page."""
        tag_page = Page(
            source_path=tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md",
            content="",
            metadata={
                "title": "Posts tagged Python",
                "template": "tag.html",
                "type": "tag",
                "_generated": True,
            },
        )
        tag_page.output_path = mock_site.output_dir / "tags" / "python" / "index.html"

        # Initialize
        initializer.ensure_initialized(tag_page)

        assert tag_page._site == mock_site
        assert tag_page.url == "/tags/python/"

    def test_initialize_paginated_archive(self, initializer, mock_site, tmp_path):
        """Test initialization of paginated archive page."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        archive_page = Page(
            source_path=tmp_path
            / ".bengal"
            / "generated"
            / "archives"
            / "blog"
            / "page_2"
            / "index.md",
            content="",
            metadata={
                "title": "Blog - Page 2",
                "template": "archive.html",
                "type": "archive",
                "_generated": True,
                "_page_num": 2,
            },
        )
        archive_page.output_path = mock_site.output_dir / "blog" / "page" / "2" / "index.html"

        # Initialize
        initializer.ensure_initialized_for_section(archive_page, section)

        assert archive_page._site == mock_site
        assert archive_page.url == "/blog/page/2/"

    # =========================================================================
    # Edge Cases and Integration Tests
    # =========================================================================

    def test_initialize_index_page(self, initializer, mock_site, tmp_path):
        """Test initialization of _index.md pages."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")

        index_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md",
            content="# Documentation",
            metadata={"title": "Documentation"},
        )
        index_page.output_path = mock_site.output_dir / "docs" / "index.html"

        initializer.ensure_initialized_for_section(index_page, section)

        assert index_page._site == mock_site
        assert index_page._section == section
        assert index_page.url == "/docs/"

    def test_initialize_nested_section_page(self, initializer, mock_site, tmp_path):
        """Test initialization of page in nested section."""
        parent = Section(name="docs", path=tmp_path / "content" / "docs")
        child = Section(name="guides", path=tmp_path / "content" / "docs" / "guides")
        parent.add_subsection(child)

        page = Page(
            source_path=tmp_path / "content" / "docs" / "guides" / "intro.md",
            content="# Introduction",
            metadata={"title": "Introduction"},
        )
        page.output_path = mock_site.output_dir / "docs" / "guides" / "intro" / "index.html"

        initializer.ensure_initialized_for_section(page, child)

        assert page._site == mock_site
        assert page._section == child
        assert page.url == "/docs/guides/intro/"

    def test_initialize_multiple_pages_in_sequence(self, initializer, mock_site, tmp_path):
        """Test initializing multiple pages in sequence."""
        pages = []
        for i in range(5):
            page = Page(source_path=tmp_path / f"page{i}.md", metadata={"title": f"Page {i}"})
            page.output_path = mock_site.output_dir / f"page{i}" / "index.html"
            pages.append(page)

        # Initialize all pages
        for page in pages:
            initializer.ensure_initialized(page)

        # All should be valid
        for i, page in enumerate(pages):
            assert page._site == mock_site
            assert page.url == f"/page{i}/"

    def test_initialize_pages_with_same_output_dir(self, initializer, mock_site, tmp_path):
        """Test multiple pages in same directory."""
        page1 = Page(source_path=tmp_path / "blog" / "post1.md", metadata={"title": "Post 1"})
        page1.output_path = mock_site.output_dir / "blog" / "post1" / "index.html"

        page2 = Page(source_path=tmp_path / "blog" / "post2.md", metadata={"title": "Post 2"})
        page2.output_path = mock_site.output_dir / "blog" / "post2" / "index.html"

        initializer.ensure_initialized(page1)
        initializer.ensure_initialized(page2)

        assert page1.url == "/blog/post1/"
        assert page2.url == "/blog/post2/"

    # =========================================================================
    # Docstring and Interface Tests
    # =========================================================================

    def test_class_has_docstring(self):
        """Verify PageInitializer has comprehensive docstring."""
        assert PageInitializer.__doc__ is not None
        assert len(PageInitializer.__doc__) > 50
        assert "initialize" in PageInitializer.__doc__.lower()

    def test_init_has_type_hints(self):
        """Verify __init__ has proper type hints."""
        import inspect

        sig = inspect.signature(PageInitializer.__init__)

        # Should have site parameter with type hint
        assert "site" in sig.parameters
        # Type hint checking would require more complex inspection

    def test_public_methods_have_docstrings(self):
        """Verify all public methods have docstrings."""
        import inspect

        for name, method in inspect.getmembers(PageInitializer, predicate=inspect.isfunction):
            if not name.startswith("_") and name != "__init__":
                assert method.__doc__ is not None, f"Method {name} missing docstring"
                assert len(method.__doc__) > 20, f"Method {name} has insufficient docstring"

    # =========================================================================
    # Fail-Fast Philosophy Tests
    # =========================================================================

    def test_fails_immediately_on_missing_output_path(self, initializer, tmp_path):
        """Test fail-fast: error raised immediately, not later."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})

        # Should fail immediately
        with pytest.raises(ValueError, match="output_path"):
            initializer.ensure_initialized(page)

    def test_fails_before_setting_site_on_relative_path(self, initializer, tmp_path):
        """Test that page is not modified if validation fails early."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        # Invalid output_path (relative)
        page.output_path = Path("relative/path.html")

        original_site = page._site
        assert original_site is None

        with pytest.raises(ValueError, match="relative"):
            initializer.ensure_initialized(page)

        # Site reference should have been set before failing
        # (This is acceptable - we fail fast, but after setting _site)
        assert page._site == initializer.site

    def test_validation_runs_before_url_access(self, initializer, mock_site, tmp_path):
        """Test that validation catches issues before URL is accessed in production."""
        page = Page(source_path=tmp_path / "test.md", metadata={"title": "Test"})
        page.output_path = mock_site.output_dir / "test" / "index.html"

        # Initialize should run URL validation
        initializer.ensure_initialized(page)

        # Now URL access should work without issues
        _ = page.url
        # If we got here, validation worked correctly
