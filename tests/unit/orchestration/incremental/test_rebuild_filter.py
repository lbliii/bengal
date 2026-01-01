"""
Tests for RebuildFilter component of the incremental package.
"""

from unittest.mock import Mock

import pytest

from bengal.cache import BuildCache
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.orchestration.incremental.rebuild_filter import RebuildFilter


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with sections and pages."""
    site = Mock()
    site.root_path = tmp_path
    site.sections = []
    site.pages = []
    # page_by_source_path is a dict property built from site.pages
    # The real implementation is a cached property on PageCachesMixin
    site.page_by_source_path = {}
    return site


@pytest.fixture
def mock_cache():
    """Create a mock BuildCache."""
    cache = Mock(spec=BuildCache)
    cache.last_build = None
    return cache


@pytest.fixture
def rebuild_filter(mock_site, mock_cache):
    """Create a RebuildFilter instance."""
    return RebuildFilter(mock_site, mock_cache)


class TestSectionLevelFiltering:
    """Test section-level change detection optimization."""

    def test_no_sections_returns_empty(self, rebuild_filter, mock_site):
        """No sections means no changed sections."""
        mock_site.sections = []

        result = rebuild_filter.get_changed_sections()

        assert result == set()

    def test_section_with_recent_changes_detected(self, rebuild_filter, mock_site, tmp_path):
        """Section with modified files should be detected."""
        # Create section
        section = Section(name="docs", path=tmp_path / "content" / "docs")

        # Create a page file
        page_path = tmp_path / "content" / "docs" / "page.md"
        page_path.parent.mkdir(parents=True)
        page_path.write_text("Content")

        page = Page(
            source_path=page_path,
            _raw_content="Content",
            metadata={"title": "Page"},
        )
        section.pages = [page]
        mock_site.sections = [section]

        # Cache has old last_build
        rebuild_filter.cache.last_build = "2020-01-01T00:00:00"

        result = rebuild_filter.get_changed_sections()

        # Section should be detected as changed
        assert section in result

    def test_section_without_pages_not_detected(self, rebuild_filter, mock_site, tmp_path):
        """Section with no pages should not be detected."""
        section = Section(name="empty", path=tmp_path / "content" / "empty")
        section.pages = []
        mock_site.sections = [section]

        result = rebuild_filter.get_changed_sections()

        assert section not in result


class TestPageSelection:
    """Test page selection based on changes."""

    def test_select_pages_no_sections(self, rebuild_filter, mock_site, tmp_path):
        """Without section filtering, all pages are selected."""
        page1 = Page(
            source_path=tmp_path / "content" / "page1.md",
            _raw_content="Page 1",
            metadata={"title": "Page 1"},
        )
        page2 = Page(
            source_path=tmp_path / "content" / "page2.md",
            _raw_content="Page 2",
            metadata={"title": "Page 2"},
        )
        mock_site.pages = [page1, page2]

        result = rebuild_filter.select_pages_to_check(
            changed_sections=None,
            forced_changed=set(),
            nav_changed=set(),
        )

        assert result == [page1, page2]

    def test_select_pages_filters_by_section(self, rebuild_filter, mock_site, tmp_path):
        """Pages in unchanged sections should be filtered out."""
        # Create two mock sections
        section1 = Mock()
        section1.name = "docs"
        section1.path = tmp_path / "content" / "docs"

        section2 = Mock()
        section2.name = "blog"
        section2.path = tmp_path / "content" / "blog"

        # Use Mock pages for full control over _section attribute
        page1 = Mock()
        page1.metadata = {"title": "Page 1"}
        page1.source_path = tmp_path / "content" / "docs" / "page1.md"
        page1._section = section1

        page2 = Mock()
        page2.metadata = {"title": "Page 2"}
        page2.source_path = tmp_path / "content" / "blog" / "page2.md"
        page2._section = section2

        mock_site.pages = [page1, page2]
        mock_site.sections = [section1, section2]

        # Only section1 changed
        result = rebuild_filter.select_pages_to_check(
            changed_sections={section1},
            forced_changed=set(),
            nav_changed=set(),
        )

        assert page1 in result
        assert page2 not in result

    def test_forced_changed_bypasses_section_filter(self, rebuild_filter, mock_site, tmp_path):
        """Forced changed sources should be included regardless of section."""
        section = Section(name="blog", path=tmp_path / "content" / "blog")

        page = Page(
            source_path=tmp_path / "content" / "blog" / "page.md",
            _raw_content="Page",
            metadata={"title": "Page"},
        )
        page._section = section

        mock_site.pages = [page]

        # No sections changed, but page is in forced_changed
        result = rebuild_filter.select_pages_to_check(
            changed_sections=set(),  # Empty - no sections changed
            forced_changed={page.source_path},
            nav_changed=set(),
        )

        assert page in result

    def test_generated_pages_always_included(self, rebuild_filter, mock_site, tmp_path):
        """Generated pages should always be included for checking."""
        generated = Page(
            source_path=tmp_path / "content" / "_generated" / "tags.md",
            _raw_content="",
            metadata={"title": "Tags", "_generated": True},
        )

        mock_site.pages = [generated]

        # No sections changed
        result = rebuild_filter.select_pages_to_check(
            changed_sections=set(),
            forced_changed=set(),
            nav_changed=set(),
        )

        assert generated in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
