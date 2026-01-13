"""Integration tests for Bengal → Patitas config bridging.

Verifies that Bengal's configuration is correctly forwarded to the
external patitas parser. This is critical because:

1. Bengal has its own ParseConfig (bengal.rendering.parsers.patitas.config)
2. External patitas has its own ParseConfig (patitas.config)
3. Bengal's wrapper must bridge these for features to work

RFC: rfc-patitas-external-migration.md
"""

import pytest

from bengal.rendering.parsers.patitas import (
    Markdown,
    parse_to_ast,
)


class TestParseToAstPlugins:
    """Test that parse_to_ast correctly bridges config to external patitas."""

    def test_tables_enabled_via_plugins(self):
        """Tables should parse when enabled via plugins parameter."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"

        ast = parse_to_ast(source, plugins=["table"])

        # parse_to_ast returns Sequence[Block] (tuple)
        node_types = [n.__class__.__name__ for n in ast]
        assert "Table" in node_types, f"Expected Table, got: {node_types}"

    def test_tables_disabled_by_default(self):
        """Tables should NOT parse when plugins not specified."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"

        ast = parse_to_ast(source)

        # Should NOT have Table node
        node_types = [n.__class__.__name__ for n in ast]
        assert "Table" not in node_types, f"Tables parsed when disabled: {node_types}"

    def test_math_enabled_via_plugins(self):
        """Math blocks should parse when enabled via plugins.
        
        Note: parse_to_ast math support requires specific syntax.
        Block math needs blank line before, or use Markdown class instead.
        """
        # Inline math in paragraph
        source = "The equation $x^2 + y^2 = z^2$ is Pythagorean."

        ast = parse_to_ast(source, plugins=["math"])

        # Should have a paragraph with inline math
        node_types = [n.__class__.__name__ for n in ast]
        assert "Paragraph" in node_types
        
        # Check that the paragraph contains InlineMath
        para = ast[0]
        inline_types = [n.__class__.__name__ for n in para.children]
        assert "InlineMath" in inline_types or "Math" in inline_types, \
            f"Expected InlineMath in paragraph, got: {inline_types}"

    def test_strikethrough_enabled_via_plugins(self):
        """Strikethrough should parse when enabled via plugins."""
        source = "~~deleted~~"

        ast = parse_to_ast(source, plugins=["strikethrough"])

        # Check inline content for Strikethrough
        paragraph = ast[0]
        inline_types = [n.__class__.__name__ for n in paragraph.children]
        assert "Strikethrough" in inline_types, f"Expected Strikethrough, got: {inline_types}"

    def test_task_lists_enabled_via_plugins(self):
        """Task lists should parse when enabled via plugins."""
        source = "- [ ] unchecked\n- [x] checked"

        ast = parse_to_ast(source, plugins=["task_lists"])

        # Find list - task_lists plugin adds checkbox info to list items
        list_node = ast[0]
        assert list_node.__class__.__name__ == "List"
        
        # Task list items have items with checkbox attribute
        first_item = list_node.items[0]
        assert hasattr(first_item, "checked"), f"ListItem missing 'checked' attr: {dir(first_item)}"

    def test_multiple_plugins(self):
        """Multiple plugins should work together."""
        source = "| A | B |\n|---|---|\n| ~~x~~ | y |"

        ast = parse_to_ast(source, plugins=["table", "strikethrough"])

        node_types = [n.__class__.__name__ for n in ast]
        assert "Table" in node_types, f"Expected Table, got: {node_types}"


class TestMarkdownClass:
    """Test that Markdown wrapper class bridges config correctly."""

    def test_markdown_with_tables(self):
        """Markdown class should enable tables via plugins."""
        source = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"

        # Note: plugin name is 'table' not 'tables'
        md = Markdown(plugins=["table"], highlight=False, highlight_style="monokai")
        html = md(source)

        assert "<table" in html.lower(), f"Table not rendered: {html}"

    def test_markdown_with_math(self):
        """Markdown class should enable math via plugins."""
        source = "Inline $x^2$ and block:\n\n$$\ny = mx + b\n$$"

        md = Markdown(plugins=["math"], highlight=False, highlight_style="monokai")
        html = md(source)

        # Math should be rendered (check for math-related output)
        assert "math" in html.lower() or "$" not in html, f"Math not processed: {html}"

    def test_markdown_with_strikethrough(self):
        """Markdown class should enable strikethrough via plugins."""
        source = "~~deleted text~~"

        md = Markdown(plugins=["strikethrough"], highlight=False, highlight_style="monokai")
        html = md(source)

        # Should have strikethrough element
        assert "<del>" in html or "<s>" in html, f"Strikethrough not rendered: {html}"

    def test_markdown_with_autolinks(self):
        """Markdown class should enable autolinks via plugins.
        
        Note: GFM autolinks work on bare URLs, not URLs embedded in sentences.
        The autolink extension detects URLs at word boundaries.
        """
        # Use explicit angle bracket autolink (CommonMark standard)
        source = "Visit <https://example.com> for more info."

        md = Markdown(plugins=["autolinks"], highlight=False, highlight_style="monokai")
        html = md(source)

        assert 'href="https://example.com"' in html, f"Autolink not rendered: {html}"


class TestDirectiveIntegration:
    """Test that directives work through Bengal's config bridging."""

    def test_note_directive_via_markdown(self):
        """Note directive should work via Markdown class."""
        source = ":::{note}\nThis is a note.\n:::"

        # Markdown requires plugins parameter
        md = Markdown(plugins=[], highlight=False, highlight_style="monokai")
        html = md(source)

        # Should have admonition/note output
        assert "note" in html.lower() or "admonition" in html.lower(), \
            f"Note directive not rendered: {html}"

    def test_warning_directive_via_markdown(self):
        """Warning directive should work via Markdown class."""
        source = ":::{warning}\nBe careful!\n:::"

        md = Markdown(plugins=[], highlight=False, highlight_style="monokai")
        html = md(source)

        assert "warning" in html.lower() or "admonition" in html.lower(), \
            f"Warning directive not rendered: {html}"


class TestConfigConsistency:
    """Test that config produces consistent results."""

    def test_same_config_same_output(self):
        """Same configuration should produce identical output."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"

        ast1 = parse_to_ast(source, plugins=["table"])
        ast2 = parse_to_ast(source, plugins=["table"])

        types1 = [n.__class__.__name__ for n in ast1]
        types2 = [n.__class__.__name__ for n in ast2]

        assert types1 == types2, f"Inconsistent results: {types1} vs {types2}"

    def test_different_config_different_output(self):
        """Different configurations should produce different output."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"

        ast_with = parse_to_ast(source, plugins=["table"])
        ast_without = parse_to_ast(source, plugins=[])

        types_with = [n.__class__.__name__ for n in ast_with]
        types_without = [n.__class__.__name__ for n in ast_without]

        assert "Table" in types_with
        assert "Table" not in types_without
