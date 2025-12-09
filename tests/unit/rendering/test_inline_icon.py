"""
Test inline icon plugin.

Validates {icon}`name` syntax for inline icons in tables, paragraphs, etc.
"""

from __future__ import annotations

import textwrap


class TestInlineIconBasic:
    """Test basic inline icon rendering."""

    def test_basic_inline_icon(self, parser):
        """Test basic inline icon syntax."""
        markdown = "Here is an icon: {icon}`terminal`"
        result = parser.parse(markdown, {})
        assert "<svg" in result
        assert "bengal-icon" in result
        assert "icon-terminal" in result

    def test_inline_icon_with_size(self, parser):
        """Test inline icon with custom size."""
        markdown = "{icon}`terminal:16`"
        result = parser.parse(markdown, {})
        assert 'width="16"' in result
        assert 'height="16"' in result

    def test_inline_icon_with_size_and_class(self, parser):
        """Test inline icon with size and class."""
        markdown = "{icon}`docs:32:icon-primary`"
        result = parser.parse(markdown, {})
        assert 'width="32"' in result
        assert 'height="32"' in result
        assert "icon-primary" in result
        assert "icon-docs" in result

    def test_inline_icon_default_size(self, parser):
        """Test inline icon uses default size 24."""
        markdown = "{icon}`terminal`"
        result = parser.parse(markdown, {})
        assert 'width="24"' in result
        assert 'height="24"' in result


class TestInlineIconInTables:
    """Test inline icons inside markdown tables."""

    def test_icon_in_table_cell(self, parser):
        """Test icon renders inside table cell."""
        markdown = textwrap.dedent("""
        | Icon | Name |
        |------|------|
        | {icon}`terminal` | Terminal |
        """)
        result = parser.parse(markdown, {})
        assert "<table>" in result
        assert "<svg" in result
        assert "icon-terminal" in result

    def test_multiple_icons_in_table(self, parser):
        """Test multiple icons in table."""
        markdown = textwrap.dedent("""
        | A | B | C |
        |---|---|---|
        | {icon}`terminal:16` | {icon}`docs:16` | {icon}`bengal-rosette:16` |
        """)
        result = parser.parse(markdown, {})
        assert result.count("<svg") == 3
        assert "icon-terminal" in result
        assert "icon-docs" in result
        assert "icon-bengal-rosette" in result

    def test_icon_with_other_content_in_table(self, parser):
        """Test icon mixed with text in table cell."""
        markdown = textwrap.dedent("""
        | Icon | Description |
        |------|-------------|
        | {icon}`terminal` | CLI commands |
        """)
        result = parser.parse(markdown, {})
        assert "<svg" in result
        assert "CLI commands" in result


class TestInlineIconEdgeCases:
    """Test edge cases for inline icons."""

    def test_missing_icon(self, parser):
        """Test non-existent icon shows missing indicator."""
        markdown = "{icon}`nonexistent-icon`"
        result = parser.parse(markdown, {})
        assert "bengal-icon-missing" in result or "❓" in result

    def test_icon_name_normalization(self, parser):
        """Test icon name is normalized."""
        markdown = "{icon}`TERMINAL`"
        result = parser.parse(markdown, {})
        assert "icon-terminal" in result

    def test_icon_with_spaces_in_name(self, parser):
        """Test icon name with spaces is normalized."""
        markdown = "{icon}`bengal rosette`"
        result = parser.parse(markdown, {})
        assert "icon-bengal-rosette" in result

    def test_multiple_classes(self, parser):
        """Test icon with multiple CSS classes."""
        # Class field can contain spaces for multiple classes
        markdown = "{icon}`terminal:24:icon-primary icon-lg`"
        result = parser.parse(markdown, {})
        assert "icon-primary" in result
        assert "icon-lg" in result


class TestInlineIconIntegration:
    """Test inline icon integration with markdown."""

    def test_icon_in_paragraph(self, parser):
        """Test icon in paragraph text."""
        markdown = "Click the {icon}`terminal:16` icon to open a terminal."
        result = parser.parse(markdown, {})
        assert "<p>" in result
        assert "<svg" in result
        assert "icon-terminal" in result

    def test_icon_in_list(self, parser):
        """Test icon in list item."""
        markdown = textwrap.dedent("""
        - {icon}`terminal` Terminal commands
        - {icon}`docs` Documentation
        """)
        result = parser.parse(markdown, {})
        assert "<li>" in result
        assert result.count("<svg") == 2

    def test_icon_in_bold_text(self, parser):
        """Test icon mixed with bold text."""
        markdown = "Use the **{icon}`terminal`** icon for CLI."
        result = parser.parse(markdown, {})
        assert "<strong>" in result
        assert "<svg" in result

    def test_multiple_icons_in_paragraph(self, parser):
        """Test multiple icons in one paragraph."""
        markdown = "{icon}`terminal` and {icon}`docs` and {icon}`bengal-rosette`"
        result = parser.parse(markdown, {})
        assert result.count("<svg") == 3


class TestInlineIconPlugin:
    """Test InlineIconPlugin directly."""

    def test_substitute_icons_no_icons(self):
        """Test substitution with no icons."""
        from bengal.rendering.plugins.inline_icon import InlineIconPlugin

        plugin = InlineIconPlugin()
        html = "<p>No icons here</p>"
        result = plugin._substitute_icons(html)
        assert result == html

    def test_substitute_icons_quick_rejection(self):
        """Test quick rejection for HTML without icons."""
        from bengal.rendering.plugins.inline_icon import InlineIconPlugin

        plugin = InlineIconPlugin()
        html = "<p>Regular paragraph</p>"
        # Should return immediately without regex processing
        result = plugin._substitute_icons(html)
        assert result == html

    def test_render_icon_with_class(self):
        """Test _render_icon with class option."""
        from bengal.rendering.plugins.inline_icon import InlineIconPlugin

        plugin = InlineIconPlugin()
        result = plugin._render_icon("terminal:24:my-class")
        assert "my-class" in result
        assert 'width="24"' in result


class TestBothSyntaxes:
    """Test that both block and inline syntaxes work together."""

    def test_block_and_inline_in_same_doc(self, parser):
        """Test block directive and inline syntax in same document."""
        markdown = textwrap.dedent("""
        # Icons Demo

        Block icon:

        :::{icon} terminal
        :size: 48
        :::

        Inline icon: {icon}`terminal:24`

        | Table Icon |
        |------------|
        | {icon}`docs` |
        """)
        result = parser.parse(markdown, {})
        # Should have 3 SVGs total
        assert result.count("<svg") == 3


class TestCodeBlockSkipping:
    """Test that inline icons are NOT processed inside code blocks."""

    def test_preserves_icon_syntax_in_code_block(self, parser):
        """Icon syntax inside fenced code blocks should be preserved."""
        markdown = textwrap.dedent("""
        ```markdown
        | Icon | Name |
        |------|------|
        | {icon}`terminal` | CLI |
        ```
        """)
        result = parser.parse(markdown, {})
        # Should NOT have any SVG - code block content preserved
        assert "<svg" not in result
        # Should have the literal syntax preserved (HTML-escaped in <code>)
        assert "{icon}" in result or "&#123;icon&#125;" in result

    def test_renders_icons_outside_code_block(self, parser):
        """Icons outside code blocks should render normally."""
        markdown = textwrap.dedent("""
        Here's an icon: {icon}`terminal`

        ```markdown
        Example: {icon}`terminal`
        ```

        Another icon: {icon}`docs`
        """)
        result = parser.parse(markdown, {})
        # Should have exactly 2 SVGs (before and after the code block)
        assert result.count("<svg") == 2

    def test_mixed_table_and_code_example(self, parser):
        """Real-world case: table with icons + code example showing syntax."""
        markdown = textwrap.dedent("""
        | Icon | Name |
        |------|------|
        | {icon}`terminal` | Terminal |

        Example markdown:

        ```markdown
        | Icon | Name |
        | {icon}`terminal` | Terminal |
        ```
        """)
        result = parser.parse(markdown, {})
        # Only 1 SVG - from the actual table, not the code example
        assert result.count("<svg") == 1
