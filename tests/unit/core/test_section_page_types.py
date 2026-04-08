"""
Tests for Section handling of Page types.

These tests verify that Section.add_page correctly handles:
- Regular Page objects
- Multiple pages in a section
- Filtering and querying pages via Section
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.core.page import Page
from bengal.core.section import Section

if TYPE_CHECKING:
    from pathlib import Path


def make_page(source_path: Path, title: str = "Test", content: str = "") -> Page:
    """Helper to create a Page for testing."""
    return Page(
        source_path=source_path,
        _raw_content=content,
        _raw_metadata={"title": title},
    )


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create a test content directory."""
    content = tmp_path / "content"
    content.mkdir()
    return content


@pytest.fixture
def docs_section(content_dir: Path) -> Section:
    """Create a test section."""
    docs = content_dir / "docs"
    docs.mkdir()
    return Section(name="docs", path=docs)


@pytest.fixture
def sample_page(content_dir: Path) -> Page:
    """Create a sample page."""
    file_path = content_dir / "docs" / "guide.md"
    file_path.write_text("---\ntitle: Guide\n---\n# Guide")
    return make_page(file_path, "Guide", "# Guide")


class TestSectionAddPage:
    """Test Section.add_page method."""

    def test_add_regular_page(self, docs_section: Section, sample_page: Page) -> None:
        """Section should accept regular Page objects."""
        docs_section.add_page(sample_page)

        assert len(docs_section.pages) == 1
        assert docs_section.pages[0] is sample_page

    def test_add_multiple_pages(self, docs_section: Section, content_dir: Path) -> None:
        """Section should handle multiple Page objects."""
        page1 = make_page(content_dir / "p1.md", "First")
        page2 = make_page(content_dir / "p2.md", "Second")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        assert len(docs_section.pages) == 2
        assert isinstance(docs_section.pages[0], Page)
        assert isinstance(docs_section.pages[1], Page)


class TestSectionQueries:
    """Test section query methods work with pages."""

    def test_pages_list(self, docs_section: Section, content_dir: Path) -> None:
        """pages list should include all added pages."""
        page1 = make_page(content_dir / "p1.md", "First")
        page2 = make_page(content_dir / "p2.md", "Second")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        all_pages = docs_section.pages
        assert len(all_pages) == 2

    def test_find_page_by_title(self, docs_section: Section, content_dir: Path) -> None:
        """Finding pages by attribute should work."""
        page1 = make_page(content_dir / "p1.md", "First")
        page2 = make_page(content_dir / "p2.md", "Second")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        # Find by title
        found = [p for p in docs_section.pages if p.title == "First"]

        assert len(found) == 1
        assert found[0].title == "First"


class TestSectionIteration:
    """Test Section iteration methods."""

    def test_iterate_pages(self, docs_section: Section, content_dir: Path) -> None:
        """Iterating section.pages should yield Page objects."""
        page1 = make_page(content_dir / "p1.md", "First")
        page2 = make_page(content_dir / "p2.md", "Second")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        types = [type(p) for p in docs_section.pages]
        assert all(t is Page for t in types)

    def test_pages_len(self, docs_section: Section, sample_page: Page) -> None:
        """len(pages) should count all pages."""
        docs_section.add_page(sample_page)
        assert len(docs_section.pages) == 1


class TestSectionPageFiltering:
    """Test filtering operations work with pages."""

    def test_filter_by_attribute(self, docs_section: Section, content_dir: Path) -> None:
        """Filtering pages by attribute should work."""
        page1 = make_page(content_dir / "p1.md", "Python Guide")
        page2 = make_page(content_dir / "p2.md", "Java Guide")

        docs_section.add_page(page1)
        docs_section.add_page(page2)

        # Filter by title containing "Python"
        python_pages = [p for p in docs_section.pages if "Python" in p.title]

        assert len(python_pages) == 1
        assert python_pages[0].title == "Python Guide"


class TestTypeAnnotationCompatibility:
    """Test that type annotations are consistent."""

    def test_pages_list_type(self, docs_section: Section, sample_page: Page) -> None:
        """pages list should accept Page via add_page."""
        docs_section.add_page(sample_page)
        assert len(docs_section.pages) == 1

    def test_section_builder_compatibility(self, content_dir: Path) -> None:
        """SectionBuilder should work with Page."""
        from bengal.content.discovery.section_builder import SectionBuilder

        builder = SectionBuilder(content_dir)

        page = make_page(content_dir / "test.md", "Test")

        # Should not raise
        builder.pages.append(page)

        assert len(builder.pages) == 1
