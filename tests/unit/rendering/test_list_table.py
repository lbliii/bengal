"""Tests for list-table directive."""

import pytest

from bengal.rendering.parsers import create_markdown_parser


class TestListTableDirective:
    """Test list-table directive rendering."""

    @pytest.fixture
    def parser(self):
        """Create markdown parser with list-table support."""
        return create_markdown_parser("mistune")

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
        assert "<td>foo</td>" in html
        assert "<td>str</td>" in html

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
        assert "<td>" in html
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
        assert "<td>A</td>" in html

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
