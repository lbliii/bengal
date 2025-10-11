"""
Tests for index file collision detection (_index.md vs index.md).
"""

from pathlib import Path
from unittest.mock import patch

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
            content="Content from _index",
            metadata={"title": "Docs Index"}
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
            content="Content from index",
            metadata={"title": "Docs Index"}
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
            content="Content from index",
            metadata={"title": "Index"}
        )
        section.add_page(regular_index)

        # Add underscore index second
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            content="Content from _index",
            metadata={"title": "Underscore Index"}
        )

        with patch('bengal.core.section.logger') as mock_logger:
            section.add_page(underscore_index)

            # Should log warning about collision
            mock_logger.warning.assert_called_once()
            # First argument is the message key
            call_args_positional = mock_logger.warning.call_args[0]
            call_args_kwargs = mock_logger.warning.call_args[1]

            assert call_args_positional[0] == 'index_file_collision'
            assert call_args_kwargs['section'] == 'docs'
            assert call_args_kwargs['action'] == 'preferring_underscore_version'

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
            content="Content from _index",
            metadata={"title": "Underscore Index"}
        )
        section.add_page(underscore_index)

        # Add regular index second
        regular_index = Page(
            source_path=Path("/content/docs/index.md"),
            content="Content from index",
            metadata={"title": "Index"}
        )

        with patch('bengal.core.section.logger') as mock_logger:
            section.add_page(regular_index)

            # Should log warning about collision
            mock_logger.warning.assert_called_once()
            call_args_positional = mock_logger.warning.call_args[0]
            assert call_args_positional[0] == 'index_file_collision'

        # _index.md should remain the index page
        assert section.index_page == underscore_index
        assert len(section.pages) == 2

    def test_regular_pages_not_affected(self):
        """Test that regular pages are not affected by index collision logic."""
        section = Section(name="docs", path=Path("/content/docs"))

        # Add some regular pages
        page1 = Page(
            source_path=Path("/content/docs/guide.md"),
            content="Guide content",
            metadata={"title": "Guide"}
        )
        page2 = Page(
            source_path=Path("/content/docs/tutorial.md"),
            content="Tutorial content",
            metadata={"title": "Tutorial"}
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
            content="Regular index",
            metadata={
                "title": "Index",
                "cascade": {"layout": "doc"}
            }
        )
        section.add_page(regular_index)
        assert "cascade" in section.metadata

        # Add underscore index with different cascade
        underscore_index = Page(
            source_path=Path("/content/docs/_index.md"),
            content="Underscore index",
            metadata={
                "title": "Underscore Index",
                "cascade": {"layout": "guide"}
            }
        )

        with patch('bengal.core.section.logger'):
            section.add_page(underscore_index)

        # _index.md cascade should override
        assert section.metadata["cascade"]["layout"] == "guide"
        assert section.index_page == underscore_index

