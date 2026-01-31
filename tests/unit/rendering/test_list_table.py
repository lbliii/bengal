"""Tests for list-table directive.

Note: These tests were originally written for the Mistune parser which has been
deprecated. The Patitas parser's list-table directive has a known issue where
raw_content is not being preserved correctly for list-like content inside
directives. This requires a fix in the Patitas library.

TODO: Once the Patitas list-table directive is fixed, remove the skip markers.
See: https://github.com/bengal-ssg/patitas/issues/TBD
"""

from __future__ import annotations

import pytest

from bengal.parsing import PatitasParser


@pytest.mark.skip(
    reason="Patitas list-table directive has a bug where raw_content for list "
    "content is not preserved correctly. Requires fix in Patitas library."
)
class TestListTableDirective:
    """Test list-table directive rendering."""

    @pytest.fixture
    def parser(self):
        """Create PatitasParser for list-table tests."""
        return PatitasParser()

    def test_basic_list_table(self, parser):
        """Test basic list-table rendering."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description
* - foo
  - str
  - A string value
* - bar
  - int
  - An integer value
:::
"""
        html = parser.parse(markdown, {})

        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th>Name</th>" in html
        # Check for data-label attributes in responsive table format
        assert 'data-label="Name">foo</td>' in html
        assert 'data-label="Type">str</td>' in html

    def test_list_table_with_widths(self, parser):
        """Test list-table with column widths."""
        markdown = """
:::{list-table}
:header-rows: 1
:widths: 20 30 50

* - Col1
  - Col2
  - Col3
* - A
  - B
  - C
:::
"""
        html = parser.parse(markdown, {})

        assert "<colgroup>" in html
        assert 'style="width: 20%;"' in html
        assert 'style="width: 30%;"' in html
        assert 'style="width: 50%;"' in html

    def test_list_table_with_pipes_in_content(self, parser):
        """Test list-table handles pipe characters in content."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Name
  - Type
* - value
  - `str | None`
* - count
  - `int | float`
:::
"""
        html = parser.parse(markdown, {})

        # Verify pipes in content don't break the table
        assert "<table" in html
        assert 'data-label="' in html  # Check for responsive data-label attributes
        # Backticks should render as code tags
        assert "<code>str | None</code>" in html
        assert "<code>int | float</code>" in html
        # Pipes should be preserved
        assert "str | None" in html
        assert "int | float" in html

    def test_list_table_with_markdown_in_cells(self, parser):
        """Test list-table with markdown syntax in cells."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Name
  - Description
* - **bold**
  - Text with `code`
* - _italic_
  - More text
:::
"""
        html = parser.parse(markdown, {})

        # List-table now renders cell content with markdown parsing
        assert "<strong>bold</strong>" in html or "<b>bold</b>" in html
        assert "<code>code</code>" in html
        assert "<em>italic</em>" in html or "<i>italic</i>" in html

    def test_list_table_no_header(self, parser):
        """Test list-table without header rows."""
        markdown = """
:::{list-table}
:header-rows: 0

* - A
  - B
* - C
  - D
:::
"""
        html = parser.parse(markdown, {})

        assert "<table" in html
        assert "<thead>" not in html
        assert "<tbody>" in html
        # With no header, first row still gets data-labels based on column position
        assert ">A</td>" in html

    def test_list_table_with_css_class(self, parser):
        """Test list-table with custom CSS class."""
        markdown = """
:::{list-table}
:header-rows: 1
:class: custom-table

* - Header
* - Data
:::
"""
        html = parser.parse(markdown, {})

        assert 'class="bengal-list-table custom-table"' in html

    def test_list_table_with_markdown_lists_in_cells(self, parser):
        """Test list-table with markdown lists in cells."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Feature
  - Description
* - Performance
  - Fast builds with:

    - Parallel processing
    - Incremental updates
    - Smart caching
  - Easy deployment:

    - Static hosting
    - No server required
    - CDN friendly
:::
"""
        html = parser.parse(markdown, {})

        # Should contain table structure
        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html

        # Should contain cell-content wrapper for cells with lists
        assert '<div class="cell-content">' in html

        # Should contain actual <ul> elements
        assert "<ul>" in html
        assert "</ul>" in html

        # Should contain list items
        assert "<li>Parallel processing</li>" in html
        assert "<li>Incremental updates</li>" in html
        assert "<li>Smart caching</li>" in html
        assert "<li>Static hosting</li>" in html

    def test_list_table_with_multiple_paragraphs_in_cells(self, parser):
        """Test list-table with multiple paragraphs in cells."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Column 1
  - Column 2
* - Single paragraph
  - First paragraph

    Second paragraph

    Third paragraph
:::
"""
        html = parser.parse(markdown, {})

        # Should contain table
        assert "<table" in html

        # Should contain cell-content wrapper for multi-paragraph cells
        assert '<div class="cell-content">' in html

        # Should contain <p> tags for paragraphs
        assert "<p>First paragraph</p>" in html
        assert "<p>Second paragraph</p>" in html
        assert "<p>Third paragraph</p>" in html

        # Single paragraph cells should NOT have cell-content wrapper
        # They should just have the unwrapped text
        assert "Single paragraph" in html

    def test_list_table_mixed_content_types(self, parser):
        """Test list-table with mixed inline and block content."""
        markdown = """
:::{list-table}
:header-rows: 1

* - Type
  - Example
* - Inline
  - Just **bold** text with `code`
* - Block
  - Multiple paragraphs:

    Paragraph one.

    Paragraph two.
* - List
  - Items:

    - First
    - Second
:::
"""
        html = parser.parse(markdown, {})

        # Should handle inline content without cell-content wrapper
        assert "<strong>bold</strong>" in html or "<b>bold</b>" in html
        assert "<code>code</code>" in html

        # Should wrap block content
        assert '<div class="cell-content">' in html

        # Should contain paragraphs
        assert "<p>Paragraph one.</p>" in html

        # Should contain lists
        assert "<li>First</li>" in html
        assert "<li>Second</li>" in html
