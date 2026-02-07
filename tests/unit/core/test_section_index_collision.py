"""
Tests for index file collision detection (_index.md vs index.md).
"""

from pathlib import Path

from bengal.core.diagnostics import DiagnosticsCollector
from bengal.core.page import Page
from bengal.core.section import Section


class TestIndexFileCollision:
    """Test that collision between index.md and _index.md is handled correctly."""

    def test_underscore_index_added_first(self):
        """Test that _index.md becomes the index when added first."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Create _index page
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            _raw_content="Content from _index",
            _raw_metadata={"title": "Docs Index"},
        )

        section.add_page(underscore_index)

        assert section.index_page == underscore_index
        assert len(section.pages) == 1

    def test_regular_index_added_first(self):
        """Test that index.md becomes the index when added first."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Create index page
        regular_index = Page(
            source_path=Path("/content/docs/index.md"),
            _raw_content="Content from index",
            _raw_metadata={"title": "Docs Index"},
        )

        section.add_page(regular_index)

        assert section.index_page == regular_index
        assert len(section.pages) == 1

    def test_collision_prefers_underscore_index(self):
        """Test that _index.md takes precedence when both exist."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add regular index first
        regular_index = Page(
            source_path=Path("/content/docs/index.md"),
            _raw_content="Content from index",
            _raw_metadata={"title": "Index"},
        )
        section.add_page(regular_index)

        # Add underscore index second
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            _raw_content="Content from _index",
            _raw_metadata={"title": "Underscore Index"},
        )

        collector = DiagnosticsCollector()
        section._diagnostics = collector
        section.add_page(underscore_index)

        events = collector.drain()
        assert len(events) == 1
        assert events[0].level == "warning"
        assert events[0].code == "index_file_collision"
        assert events[0].data["section"] == "docs"
        assert events[0].data["action"] == "preferring_underscore_version"

        # _index.md should be the index page
        assert section.index_page == underscore_index
        # Both should be in pages list
        assert len(section.pages) == 2

    def test_collision_keeps_underscore_when_regular_added_second(self):
        """Test that _index.md is kept when index.md is added after."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add underscore index first
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            _raw_content="Content from _index",
            _raw_metadata={"title": "Underscore Index"},
        )
        section.add_page(underscore_index)

        # Add regular index second
        regular_index = Page(
            source_path=Path("/content/docs/index.md"),
            _raw_content="Content from index",
            _raw_metadata={"title": "Index"},
        )

        collector = DiagnosticsCollector()
        section._diagnostics = collector
        section.add_page(regular_index)

        events = collector.drain()
        assert len(events) == 1
        assert events[0].level == "warning"
        assert events[0].code == "index_file_collision"

        # _index.md should remain the index page
        assert section.index_page == underscore_index
        assert len(section.pages) == 2

    def test_regular_pages_not_affected(self):
        """Test that regular pages are not affected by index collision logic."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add some regular pages
        page1 = Page(
            source_path=Path("/content/docs/guide.md"),
            _raw_content="Guide content",
            _raw_metadata={"title": "Guide"},
        )
        page2 = Page(
            source_path=Path("/content/docs/tutorial.md"),
            _raw_content="Tutorial content",
            _raw_metadata={"title": "Tutorial"},
        )

        section.add_page(page1)
        section.add_page(page2)

        # No index page should be set
        assert section.index_page is None
        assert len(section.pages) == 2

    def test_collision_with_cascade_metadata(self):
        """Test that cascade metadata is preserved with collision handling."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add regular index with cascade
        regular_index = Page(
            source_path=Path("/content/docs/index.md"),
            _raw_content="Regular index",
            _raw_metadata={"title": "Index", "cascade": {"layout": "doc"}},
        )
        section.add_page(regular_index)
        assert "cascade" in section.metadata

        # Add underscore index with different cascade
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            _raw_content="Underscore index",
            _raw_metadata={"title": "Underscore Index", "cascade": {"layout": "guide"}},
        )

        collector = DiagnosticsCollector()
        section._diagnostics = collector
        section.add_page(underscore_index)

        # _index.md cascade should override
        assert section.metadata["cascade"]["layout"] == "guide"
        assert section.index_page == underscore_index
