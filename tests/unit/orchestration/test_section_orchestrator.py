"""
Tests for SectionOrchestrator.

Tests the new section lifecycle management that ensures all sections
have index pages (either explicit _index.md or auto-generated archives).
"""

from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.orchestration.section import SectionOrchestrator


class TestSectionOrchestrator:
    """Test the SectionOrchestrator class."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for testing."""
        from bengal.cache.paths import BengalPaths

        site = Mock(spec=Site)
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.paths = BengalPaths(tmp_path)
        site.sections = []
        site.pages = []
        site.config = {"pagination": {"per_page": 10}}
        return site

    @pytest.fixture
    def orchestrator(self, mock_site):
        """Create a SectionOrchestrator instance."""
        return SectionOrchestrator(mock_site)

    def test_init(self, mock_site):
        """Test orchestrator initialization."""
        orch = SectionOrchestrator(mock_site)
        assert orch.site == mock_site

    def test_finalize_sections_empty_site(self, orchestrator, mock_site):
        """Test finalization with no sections."""
        mock_site.sections = []

        orchestrator.finalize_sections()

        # Should handle empty sections gracefully
        assert len(mock_site.pages) == 0

    def test_finalize_section_with_explicit_index(self, orchestrator, mock_site, tmp_path):
        """Test that sections with explicit _index.md are not modified."""
        # Create section with explicit index page
        section = Section(name="docs", path=tmp_path / "content" / "docs")
        index_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md",
            _raw_metadata={"title": "Documentation"},
        )
        section.add_page(index_page)

        mock_site.sections = [section]

        # Store reference to original index
        original_index = section.index_page

        orchestrator.finalize_sections()

        # Should not create new index page
        assert section.index_page == original_index
        assert len(mock_site.pages) == 0  # No archive pages added

    def test_finalize_section_without_index(self, orchestrator, mock_site, tmp_path):
        """Test that sections without _index.md get auto-generated archive."""
        # Create section without index page
        section = Section(name="blog", path=tmp_path / "content" / "blog")
        page1 = Page(
            source_path=tmp_path / "content" / "blog" / "post1.md",
            _raw_metadata={"title": "Post 1"},
        )
        section.add_page(page1)

        mock_site.sections = [section]

        orchestrator.finalize_sections()

        # Should create archive index page
        assert section.index_page is not None
        assert section.index_page.metadata.get("_generated") is True
        # Blog sections get content-type-specific template
        assert section.index_page.metadata.get("template") == "blog/list.html"
        assert len(mock_site.pages) == 1  # Archive page added

    def test_finalize_section_only_subsections(self, orchestrator, mock_site, tmp_path):
        """Test sections with only subsections (no direct pages)."""
        # Create parent section with no direct pages
        parent = Section(name="docs", path=tmp_path / "content" / "docs")

        # Create subsection with a page
        child = Section(name="guides", path=tmp_path / "content" / "docs" / "guides")
        child_page = Page(
            source_path=tmp_path / "content" / "docs" / "guides" / "intro.md",
            _raw_metadata={"title": "Introduction"},
        )
        child.add_page(child_page)
        parent.add_subsection(child)

        mock_site.sections = [parent]

        orchestrator.finalize_sections()

        # Parent should have auto-generated index (even with no direct pages)
        assert parent.index_page is not None
        assert parent.index_page.metadata.get("_generated") is True

        # Child should also have auto-generated index
        assert child.index_page is not None
        assert child.index_page.metadata.get("_generated") is True

        # Should have 2 archive pages added (parent + child)
        assert len(mock_site.pages) == 2

    def test_finalize_nested_sections_recursive(self, orchestrator, mock_site, tmp_path):
        """Test that nested sections are finalized recursively."""
        # Create 3-level hierarchy
        top = Section(name="api", path=tmp_path / "content" / "api")
        middle = Section(name="v2", path=tmp_path / "content" / "api" / "v2")
        bottom = Section(name="users", path=tmp_path / "content" / "api" / "v2" / "users")

        top.add_subsection(middle)
        middle.add_subsection(bottom)

        mock_site.sections = [top]

        orchestrator.finalize_sections()

        # All three sections should have indexes
        assert top.index_page is not None
        assert middle.index_page is not None
        assert bottom.index_page is not None

        # All should be auto-generated
        assert all(s.index_page.metadata.get("_generated") for s in [top, middle, bottom])

        # Should have 3 archive pages
        assert len(mock_site.pages) == 3

    def test_finalize_root_section_skipped(self, orchestrator, mock_site, tmp_path):
        """Test that root section is skipped (no index generated)."""
        root = Section(name="root", path=tmp_path / "content")

        mock_site.sections = [root]

        orchestrator.finalize_sections()

        # Root should not have index page generated
        assert root.index_page is None
        assert len(mock_site.pages) == 0

    def test_archive_page_metadata(self, orchestrator, mock_site, tmp_path):
        """Test that generated archive pages have correct metadata."""
        section = Section(name="posts", path=tmp_path / "content" / "posts")
        page1 = Page(
            source_path=tmp_path / "content" / "posts" / "hello.md",
            _raw_metadata={"title": "Hello"},
        )
        section.add_page(page1)

        mock_site.sections = [section]

        orchestrator.finalize_sections()

        archive = section.index_page

        # Check metadata
        assert archive.metadata["title"] == section.title
        # "posts" section is detected as blog content type, gets blog/list.html template
        assert archive.metadata["template"] == "blog/list.html"
        assert archive.metadata["type"] == "blog"
        assert archive.metadata["_generated"] is True
        assert archive.metadata["_virtual"] is True
        assert archive.metadata["_section"] == section
        assert archive.metadata["_posts"] == section.pages
        assert archive.metadata["_subsections"] == section.subsections
        # Note: _paginator is only added for sections with >20 pages (pagination threshold)
        # This test has only 1 page, so no pagination
        assert archive.metadata["_content_type"] == "blog"

    def test_archive_output_path(self, orchestrator, mock_site, tmp_path):
        """Test that archive pages have correct output paths."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        mock_site.sections = [section]
        mock_site.output_dir = tmp_path / "public"

        orchestrator.finalize_sections()

        archive = section.index_page

        expected_path = tmp_path / "public" / "blog" / "index.html"
        assert archive.output_path == expected_path

    def test_archive_virtual_path(self, orchestrator, mock_site, tmp_path):
        """Test that archive pages use virtual path namespace."""
        section = Section(name="guides", path=tmp_path / "content" / "guides")

        mock_site.sections = [section]

        orchestrator.finalize_sections()

        archive = section.index_page

        # Should be in .bengal/generated namespace
        assert ".bengal" in str(archive.source_path)
        assert "generated" in str(archive.source_path)
        assert "archives" in str(archive.source_path)


class TestSectionValidation:
    """Test section validation methods."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for testing."""
        site = Mock(spec=Site)
        site.root_path = tmp_path
        site.sections = []
        return site

    @pytest.fixture
    def orchestrator(self, mock_site):
        """Create a SectionOrchestrator instance."""
        return SectionOrchestrator(mock_site)

    def test_validate_sections_all_valid(self, orchestrator, mock_site, tmp_path):
        """Test validation with all sections having indexes."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")
        section.index_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md", _raw_metadata={"title": "Docs"}
        )

        mock_site.sections = [section]

        errors = orchestrator.validate_sections()

        assert len(errors) == 0

    def test_validate_section_missing_index(self, orchestrator, mock_site, tmp_path):
        """Test validation catches sections without index pages."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")
        # No index_page set

        mock_site.sections = [section]

        errors = orchestrator.validate_sections()

        assert len(errors) == 1
        assert "blog" in errors[0]
        assert "no index page" in errors[0].lower()

    def test_validate_nested_sections(self, orchestrator, mock_site, tmp_path):
        """Test validation of nested sections."""
        parent = Section(name="api", path=tmp_path / "content" / "api")
        child = Section(name="v1", path=tmp_path / "content" / "api" / "v1")

        # Parent has index, child doesn't
        parent.index_page = Page(
            source_path=tmp_path / "content" / "api" / "_index.md", _raw_metadata={"title": "API"}
        )
        parent.add_subsection(child)

        mock_site.sections = [parent]

        errors = orchestrator.validate_sections()

        # Should catch child section missing index
        assert len(errors) == 1
        assert "v1" in errors[0]

    def test_validate_root_section_skipped(self, orchestrator, mock_site, tmp_path):
        """Test that root section is skipped in validation."""
        root = Section(name="root", path=tmp_path / "content")
        # No index_page (intentionally)

        mock_site.sections = [root]

        errors = orchestrator.validate_sections()

        # Root section should not generate errors
        assert len(errors) == 0

    def test_validate_multiple_sections_multiple_errors(self, orchestrator, mock_site, tmp_path):
        """Test validation collects multiple errors."""
        section1 = Section(name="docs", path=tmp_path / "content" / "docs")
        section2 = Section(name="blog", path=tmp_path / "content" / "blog")
        section3 = Section(name="api", path=tmp_path / "content" / "api")

        # Only section3 has index
        section3.index_page = Page(
            source_path=tmp_path / "content" / "api" / "_index.md", _raw_metadata={"title": "API"}
        )

        mock_site.sections = [section1, section2, section3]

        errors = orchestrator.validate_sections()

        # Should have errors for section1 and section2
        assert len(errors) == 2
        error_text = " ".join(errors)
        assert "docs" in error_text
        assert "blog" in error_text
        assert "api" not in error_text  # API has index, so no error


class TestSectionHelperMethods:
    """Test helper methods added to Section class."""

    def test_needs_auto_index_true(self, tmp_path):
        """Test needs_auto_index returns True for sections without index."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        assert section.needs_auto_index() is True

    def test_needs_auto_index_false_has_index(self, tmp_path):
        """Test needs_auto_index returns False when section has index."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")
        section.index_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md", _raw_metadata={"title": "Docs"}
        )

        assert section.needs_auto_index() is False

    def test_needs_auto_index_false_root(self, tmp_path):
        """Test needs_auto_index returns False for root section."""
        section = Section(name="root", path=tmp_path / "content")

        assert section.needs_auto_index() is False

    def test_has_index_true(self, tmp_path):
        """Test has_index returns True when index page exists."""
        section = Section(name="docs", path=tmp_path / "content" / "docs")
        section.index_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md", _raw_metadata={"title": "Docs"}
        )

        assert section.has_index() is True

    def test_has_index_false(self, tmp_path):
        """Test has_index returns False when no index page."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        assert section.has_index() is False


class TestIntegrationScenarios:
    """Test real-world scenarios."""

    @pytest.fixture
    def site(self, tmp_path):
        """Create a real site instance for integration tests."""
        site = Site(root_path=tmp_path, config={})
        site.output_dir = tmp_path / "public"
        site.sections = []
        site.pages = []
        site.config = {"pagination": {"per_page": 10}}
        return site

    def test_showcase_site_structure(self, site, tmp_path):
        """Test the exact structure that was failing in showcase site."""
        # Recreate the showcase structure:
        # docs/
        #   markdown/
        #     kitchen-sink.md
        #   templates/
        #     function-reference/
        #       _index.md
        #       collections.md

        docs = Section(name="docs", path=tmp_path / "content" / "docs")

        markdown = Section(name="markdown", path=tmp_path / "content" / "docs" / "markdown")
        kitchen_sink = Page(
            source_path=tmp_path / "content" / "docs" / "markdown" / "kitchen-sink.md",
            _raw_metadata={"title": "Kitchen Sink"},
        )
        markdown.add_page(kitchen_sink)
        docs.add_subsection(markdown)

        templates = Section(name="templates", path=tmp_path / "content" / "docs" / "templates")
        func_ref = Section(
            name="function-reference",
            path=tmp_path / "content" / "docs" / "templates" / "function-reference",
        )
        func_ref_index = Page(
            source_path=tmp_path
            / "content"
            / "docs"
            / "templates"
            / "function-reference"
            / "_index.md",
            _raw_metadata={"title": "Function Reference"},
        )
        func_ref.add_page(func_ref_index)
        templates.add_subsection(func_ref)
        docs.add_subsection(templates)

        site.sections = [docs]

        orchestrator = SectionOrchestrator(site)
        orchestrator.finalize_sections()

        # Verify all sections have indexes
        assert docs.has_index(), "docs section should have index"
        assert markdown.has_index(), "markdown section should have index"
        assert templates.has_index(), "templates section should have index"
        assert func_ref.has_index(), "function-reference section should have index"

        # Verify function-reference still has its explicit index
        assert func_ref.index_page == func_ref_index, "Explicit _index.md should not be replaced"

        # Verify generated indexes for others
        assert docs.index_page.metadata.get("_generated"), "docs should have auto-generated index"
        assert markdown.index_page.metadata.get("_generated"), (
            "markdown should have auto-generated index"
        )
        assert templates.index_page.metadata.get("_generated"), (
            "templates should have auto-generated index"
        )

        # Validate no errors
        errors = orchestrator.validate_sections()
        assert len(errors) == 0, f"Should have no validation errors: {errors}"

    def test_mixed_explicit_and_auto_indexes(self, site, tmp_path):
        """Test site with mix of explicit and auto-generated indexes."""
        # Create structure with some explicit indexes
        docs = Section(name="docs", path=tmp_path / "content" / "docs")
        docs_index = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md",
            _raw_metadata={"title": "Documentation"},
        )
        docs.add_page(docs_index)

        # Subsection without explicit index
        guides = Section(name="guides", path=tmp_path / "content" / "docs" / "guides")
        guide_page = Page(
            source_path=tmp_path / "content" / "docs" / "guides" / "intro.md",
            _raw_metadata={"title": "Introduction"},
        )
        guides.add_page(guide_page)
        docs.add_subsection(guides)

        site.sections = [docs]

        orchestrator = SectionOrchestrator(site)
        orchestrator.finalize_sections()

        # docs should keep explicit index
        assert docs.index_page == docs_index
        assert not docs.index_page.metadata.get("_generated")

        # guides should get auto-generated index
        assert guides.index_page is not None
        assert guides.index_page.metadata.get("_generated")

        # Validate
        errors = orchestrator.validate_sections()
        assert len(errors) == 0

    def test_incremental_build_finalizesections_without_indexes(self, site, tmp_path):
        """
        Test that sections without indexes are finalized even in incremental builds.

        This tests the fix for the autodoc bug where sections created by autodoc
        (which don't have _index.md files) would never get indexes in incremental builds
        because they weren't marked as "affected".
        """
        # Create an API section like autodoc would (no _index.md)
        api = Section(name="api", path=tmp_path / "content" / "api")
        api_page = Page(
            source_path=tmp_path / "content" / "api" / "module.md",
            _raw_metadata={"title": "Module"},
        )
        api.add_page(api_page)

        # Create subsection also without index
        apps = Section(name="apps", path=tmp_path / "content" / "api" / "apps")
        apps_page = Page(
            source_path=tmp_path / "content" / "api" / "apps" / "app1.md",
            _raw_metadata={"title": "App 1"},
        )
        apps.add_page(apps_page)
        api.add_subsection(apps)

        site.sections = [api]

        # Simulate incremental build where this section isn't "affected"
        # (no pages changed in this section)
        affected_sections = set()  # Empty - nothing changed

        orchestrator = SectionOrchestrator(site)
        orchestrator.finalize_sections(affected_sections=affected_sections)

        # CRITICAL: Even though section wasn't affected, it should still get indexes
        # because it was missing them
        assert api.index_page is not None, "API section should have auto-generated index"
        assert api.index_page.metadata.get("_generated"), "Index should be auto-generated"

        assert apps.index_page is not None, "Apps subsection should have auto-generated index"
        assert apps.index_page.metadata.get("_generated"), (
            "Subsection index should be auto-generated"
        )

        # Validate - should pass
        errors = orchestrator.validate_sections()
        assert len(errors) == 0, f"Should have no validation errors: {errors}"
