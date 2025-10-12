"""
Tests for weight-based sorting of pages and sections.

Tests the sorting functionality that orders pages and sections
by their frontmatter weight field (ascending), with title as secondary sort.
"""

from bengal.core.page import Page
from bengal.core.section import Section


class TestSectionSortedPagesProperty:
    """Test Section.sorted_pages property."""

    def test_sorted_pages_basic(self, tmp_path):
        """Pages are sorted by weight (ascending)."""
        section = Section(name="docs", path=tmp_path / "docs")

        # Add pages with different weights
        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content 1",
            metadata={"title": "Page 1", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content 2",
            metadata={"title": "Page 2", "weight": 1},
        )
        page3 = Page(
            source_path=tmp_path / "docs/page3.md",
            content="Content 3",
            metadata={"title": "Page 3", "weight": 5},
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # Should be sorted by weight: page2(1), page3(5), page1(10)
        assert sorted_pages[0] == page2
        assert sorted_pages[1] == page3
        assert sorted_pages[2] == page1

    def test_sorted_pages_no_weights(self, tmp_path):
        """Pages without weights default to weight=0 and sort by title."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/zebra.md", content="Content", metadata={"title": "Zebra"}
        )
        page2 = Page(
            source_path=tmp_path / "docs/alpha.md", content="Content", metadata={"title": "Alpha"}
        )
        page3 = Page(
            source_path=tmp_path / "docs/beta.md", content="Content", metadata={"title": "Beta"}
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # All have weight=0, so sorted by title: Alpha, Beta, Zebra
        assert sorted_pages[0] == page2  # Alpha
        assert sorted_pages[1] == page3  # Beta
        assert sorted_pages[2] == page1  # Zebra

    def test_sorted_pages_mixed_weights(self, tmp_path):
        """Pages with and without weights are sorted correctly."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "Zebra", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "Alpha"},  # No weight = 0
        )
        page3 = Page(
            source_path=tmp_path / "docs/page3.md",
            content="Content",
            metadata={"title": "Beta", "weight": 5},
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # Alpha(0), Beta(5), Zebra(10)
        assert sorted_pages[0] == page2
        assert sorted_pages[1] == page3
        assert sorted_pages[2] == page1

    def test_sorted_pages_same_weight_sort_by_title(self, tmp_path):
        """Pages with same weight are sorted alphabetically by title."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "Zebra", "weight": 5},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "Alpha", "weight": 5},
        )
        page3 = Page(
            source_path=tmp_path / "docs/page3.md",
            content="Content",
            metadata={"title": "Moose", "weight": 5},
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # All weight=5, sorted by title: Alpha, Moose, Zebra
        assert sorted_pages[0] == page2
        assert sorted_pages[1] == page3
        assert sorted_pages[2] == page1

    def test_sorted_pages_case_insensitive_title_sort(self, tmp_path):
        """Title sorting is case-insensitive."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "zebra", "weight": 5},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "Alpha", "weight": 5},
        )
        page3 = Page(
            source_path=tmp_path / "docs/page3.md",
            content="Content",
            metadata={"title": "MOOSE", "weight": 5},
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # Case-insensitive sort: Alpha, MOOSE, zebra
        assert sorted_pages[0] == page2
        assert sorted_pages[1] == page3
        assert sorted_pages[2] == page1

    def test_sorted_pages_empty_section(self, tmp_path):
        """Empty section returns empty list."""
        section = Section(name="docs", path=tmp_path / "docs")

        sorted_pages = section.sorted_pages

        assert sorted_pages == []

    def test_sorted_pages_single_page(self, tmp_path):
        """Section with single page returns that page."""
        section = Section(name="docs", path=tmp_path / "docs")

        page = Page(
            source_path=tmp_path / "docs/page.md",
            content="Content",
            metadata={"title": "Page", "weight": 5},
        )
        section.pages = [page]

        sorted_pages = section.sorted_pages

        assert sorted_pages == [page]

    def test_sorted_pages_negative_weights(self, tmp_path):
        """Negative weights are supported and sort before positive."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "Page 1", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "Page 2", "weight": -5},
        )
        page3 = Page(
            source_path=tmp_path / "docs/page3.md",
            content="Content",
            metadata={"title": "Page 3", "weight": 0},
        )

        section.pages = [page1, page2, page3]

        sorted_pages = section.sorted_pages

        # -5, 0, 10
        assert sorted_pages[0] == page2
        assert sorted_pages[1] == page3
        assert sorted_pages[2] == page1


class TestSectionSortedSubsectionsProperty:
    """Test Section.sorted_subsections property."""

    def test_sorted_subsections_basic(self, tmp_path):
        """Subsections are sorted by weight (ascending)."""
        section = Section(name="docs", path=tmp_path / "docs")

        # Create subsections with index pages that have weights
        sub1 = Section(name="advanced", path=tmp_path / "docs/advanced")
        sub1.metadata = {"weight": 10}

        sub2 = Section(name="beginner", path=tmp_path / "docs/beginner")
        sub2.metadata = {"weight": 1}

        sub3 = Section(name="intermediate", path=tmp_path / "docs/intermediate")
        sub3.metadata = {"weight": 5}

        section.subsections = [sub1, sub2, sub3]

        sorted_subs = section.sorted_subsections

        # Should be sorted by weight: sub2(1), sub3(5), sub1(10)
        assert sorted_subs[0] == sub2
        assert sorted_subs[1] == sub3
        assert sorted_subs[2] == sub1

    def test_sorted_subsections_no_weights(self, tmp_path):
        """Subsections without weights default to weight=0 and sort by title."""
        section = Section(name="docs", path=tmp_path / "docs")

        sub1 = Section(name="zebra", path=tmp_path / "docs/zebra")
        sub1.metadata = {"title": "Zebra"}

        sub2 = Section(name="alpha", path=tmp_path / "docs/alpha")
        sub2.metadata = {"title": "Alpha"}

        sub3 = Section(name="beta", path=tmp_path / "docs/beta")
        sub3.metadata = {"title": "Beta"}

        section.subsections = [sub1, sub2, sub3]

        sorted_subs = section.sorted_subsections

        # All have weight=0, so sorted by title: Alpha, Beta, Zebra
        assert sorted_subs[0] == sub2
        assert sorted_subs[1] == sub3
        assert sorted_subs[2] == sub1

    def test_sorted_subsections_empty(self, tmp_path):
        """Empty subsections returns empty list."""
        section = Section(name="docs", path=tmp_path / "docs")

        sorted_subs = section.sorted_subsections

        assert sorted_subs == []

    def test_sorted_subsections_uses_section_title_property(self, tmp_path):
        """Sorting uses Section.title property which handles missing title."""
        section = Section(name="docs", path=tmp_path / "docs")

        # Subsections without explicit title in metadata use name
        sub1 = Section(name="zebra-guide", path=tmp_path / "docs/zebra-guide")
        sub2 = Section(name="alpha-guide", path=tmp_path / "docs/alpha-guide")

        section.subsections = [sub1, sub2]

        sorted_subs = section.sorted_subsections

        # Should sort by generated titles: "Alpha Guide", "Zebra Guide"
        assert sorted_subs[0] == sub2
        assert sorted_subs[1] == sub1


class TestSectionSortChildrenByWeight:
    """Test Section.sort_children_by_weight() method."""

    def test_sort_children_modifies_in_place(self, tmp_path):
        """sort_children_by_weight() modifies pages and subsections in place."""
        section = Section(name="docs", path=tmp_path / "docs")

        # Add pages with weights
        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "Page 1", "weight": 10},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "Page 2", "weight": 1},
        )

        section.pages = [page1, page2]

        # Add subsections with weights
        sub1 = Section(name="advanced", path=tmp_path / "docs/advanced")
        sub1.metadata = {"weight": 10}

        sub2 = Section(name="beginner", path=tmp_path / "docs/beginner")
        sub2.metadata = {"weight": 1}

        section.subsections = [sub1, sub2]

        # Sort in place
        section.sort_children_by_weight()

        # Pages should be sorted
        assert section.pages[0] == page2
        assert section.pages[1] == page1

        # Subsections should be sorted
        assert section.subsections[0] == sub2
        assert section.subsections[1] == sub1

    def test_sort_children_handles_empty_lists(self, tmp_path):
        """sort_children_by_weight() handles empty pages/subsections."""
        section = Section(name="docs", path=tmp_path / "docs")

        # Should not raise error
        section.sort_children_by_weight()

        assert section.pages == []
        assert section.subsections == []

    def test_sort_children_with_only_pages(self, tmp_path):
        """sort_children_by_weight() works with only pages."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "B", "weight": 2},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "A", "weight": 1},
        )

        section.pages = [page1, page2]
        section.sort_children_by_weight()

        assert section.pages[0] == page2
        assert section.pages[1] == page1

    def test_sort_children_with_only_subsections(self, tmp_path):
        """sort_children_by_weight() works with only subsections."""
        section = Section(name="docs", path=tmp_path / "docs")

        sub1 = Section(name="b", path=tmp_path / "docs/b")
        sub1.metadata = {"weight": 2}

        sub2 = Section(name="a", path=tmp_path / "docs/a")
        sub2.metadata = {"weight": 1}

        section.subsections = [sub1, sub2]
        section.sort_children_by_weight()

        assert section.subsections[0] == sub2
        assert section.subsections[1] == sub1


class TestSectionMetadataInheritance:
    """Test that section metadata is inherited from index page."""

    def test_index_page_weight_copied_to_section_metadata(self, tmp_path):
        """When index page is added, its metadata (including weight) is copied to section."""
        section = Section(name="docs", path=tmp_path / "docs")

        index_page = Page(
            source_path=tmp_path / "docs/_index.md",
            content="Index content",
            metadata={"title": "Documentation", "weight": 42, "description": "All the docs"},
        )

        section.add_page(index_page)

        # Section metadata should include all metadata from index page
        assert section.metadata.get("weight") == 42
        assert section.metadata.get("title") == "Documentation"
        assert section.metadata.get("description") == "All the docs"

    def test_regular_page_does_not_affect_section_metadata(self, tmp_path):
        """Regular pages (non-index) don't affect section metadata."""
        section = Section(name="docs", path=tmp_path / "docs")

        regular_page = Page(
            source_path=tmp_path / "docs/guide.md",
            content="Guide content",
            metadata={"title": "Guide", "weight": 100},
        )

        section.add_page(regular_page)

        # Section metadata should not include page metadata
        assert section.metadata.get("weight") is None
        assert section.metadata.get("title") is None


class TestSortingStability:
    """Test that sorting is stable and predictable."""

    def test_repeated_sorting_same_result(self, tmp_path):
        """Sorting multiple times gives same result."""
        section = Section(name="docs", path=tmp_path / "docs")

        pages = []
        for i in range(10):
            page = Page(
                source_path=tmp_path / f"docs/page{i}.md",
                content=f"Content {i}",
                metadata={"title": f"Page {i}", "weight": i % 3},
            )
            pages.append(page)

        section.pages = pages.copy()

        # Sort multiple times
        section.sort_children_by_weight()
        first_result = section.pages.copy()

        section.sort_children_by_weight()
        second_result = section.pages.copy()

        section.sort_children_by_weight()
        third_result = section.pages.copy()

        # All results should be identical
        assert first_result == second_result
        assert second_result == third_result

    def test_sorted_pages_property_consistent(self, tmp_path):
        """sorted_pages property returns consistent results."""
        section = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(
            source_path=tmp_path / "docs/page1.md",
            content="Content",
            metadata={"title": "B", "weight": 1},
        )
        page2 = Page(
            source_path=tmp_path / "docs/page2.md",
            content="Content",
            metadata={"title": "A", "weight": 1},
        )

        section.pages = [page1, page2]

        # Multiple accesses should return same order
        result1 = section.sorted_pages
        result2 = section.sorted_pages
        result3 = section.sorted_pages

        assert result1 == result2 == result3
