"""Parser tests for Patitas.

Tests the recursive descent parser for correct AST construction.
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Emphasis,
    FencedCode,
    Heading,
    Image,
    IndentedCode,
    LineBreak,
    Link,
    List,
    ListItem,
    Paragraph,
    SoftBreak,
    Strong,
    Text,
    ThematicBreak,
)


class TestParserBasics:
    """Basic parser functionality."""

    def test_empty_input(self, parse_ast):
        """Empty input produces empty AST."""
        ast = parse_ast("")
        assert len(ast) == 0

    def test_whitespace_only(self, parse_ast):
        """Whitespace-only input produces empty AST."""
        ast = parse_ast("   \n\n   ")
        assert len(ast) == 0

    def test_returns_tuple(self, parse_ast):
        """Parser returns immutable tuple."""
        ast = parse_ast("# Hello")
        assert isinstance(ast, tuple)


class TestHeadingParsing:
    """Heading AST construction."""

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
    def test_heading_levels(self, parse_ast, level):
        """All heading levels produce correct AST."""
        source = "#" * level + " Heading"
        ast = parse_ast(source)
        assert len(ast) == 1
        assert isinstance(ast[0], Heading)
        assert ast[0].level == level

    def test_heading_style(self, parse_ast):
        """ATX headings have correct style."""
        ast = parse_ast("# Heading")
        assert ast[0].style == "atx"

    def test_heading_children(self, parse_ast):
        """Heading children are parsed."""
        ast = parse_ast("# Hello World")
        heading = ast[0]
        assert isinstance(heading, Heading)
        # Should have text children
        assert len(heading.children) > 0
        assert any(isinstance(c, Text) for c in heading.children)

    def test_heading_with_emphasis(self, parse_ast):
        """Heading with inline emphasis."""
        ast = parse_ast("# Hello *World*")
        heading = ast[0]
        # Should contain Emphasis node
        assert any(isinstance(c, Emphasis) for c in heading.children)

    def test_heading_with_strong(self, parse_ast):
        """Heading with inline strong."""
        ast = parse_ast("# Hello **World**")
        heading = ast[0]
        assert any(isinstance(c, Strong) for c in heading.children)


class TestParagraphParsing:
    """Paragraph AST construction."""

    def test_simple_paragraph(self, parse_ast):
        """Simple paragraph parsing."""
        ast = parse_ast("Hello world")
        assert len(ast) == 1
        assert isinstance(ast[0], Paragraph)

    def test_paragraph_children(self, parse_ast):
        """Paragraph has text children."""
        ast = parse_ast("Hello world")
        para = ast[0]
        assert len(para.children) > 0
        assert isinstance(para.children[0], Text)

    def test_multiline_paragraph(self, parse_ast):
        """Multi-line paragraph becomes single paragraph."""
        ast = parse_ast("Line 1\nLine 2")
        assert len(ast) == 1
        assert isinstance(ast[0], Paragraph)

    def test_paragraphs_separated_by_blank_line(self, parse_ast):
        """Blank line separates paragraphs."""
        ast = parse_ast("Para 1\n\nPara 2")
        paragraphs = [n for n in ast if isinstance(n, Paragraph)]
        assert len(paragraphs) == 2


class TestFencedCodeParsing:
    """Fenced code block AST construction."""

    def test_basic_fenced_code(self, parse_ast):
        """Basic fenced code block."""
        ast = parse_ast("```\ncode\n```")
        assert len(ast) == 1
        assert isinstance(ast[0], FencedCode)

    def test_fenced_code_content(self, parse_ast):
        """Fenced code preserves content."""
        ast = parse_ast("```\nhello\nworld\n```")
        code = ast[0]
        assert "hello" in code.code
        assert "world" in code.code

    def test_fenced_code_info_string(self, parse_ast):
        """Fenced code captures info string."""
        ast = parse_ast("```python\ncode\n```")
        code = ast[0]
        assert code.info == "python"

    def test_fenced_code_marker(self, parse_ast):
        """Fenced code tracks marker character."""
        ast = parse_ast("```\ncode\n```")
        assert ast[0].marker == "`"

        ast = parse_ast("~~~\ncode\n~~~")
        assert ast[0].marker == "~"


class TestIndentedCodeParsing:
    """Indented code block AST construction."""

    def test_indented_code(self, parse_ast):
        """Indented code block."""
        ast = parse_ast("    code")
        assert len(ast) == 1
        assert isinstance(ast[0], IndentedCode)

    def test_indented_code_content(self, parse_ast):
        """Indented code preserves content."""
        ast = parse_ast("    hello")
        code = ast[0]
        assert "hello" in code.code


class TestBlockQuoteParsing:
    """Block quote AST construction."""

    def test_basic_block_quote(self, parse_ast):
        """Basic block quote."""
        ast = parse_ast("> quote")
        assert len(ast) == 1
        assert isinstance(ast[0], BlockQuote)

    def test_block_quote_children(self, parse_ast):
        """Block quote has paragraph children."""
        ast = parse_ast("> quoted text")
        quote = ast[0]
        assert len(quote.children) > 0


class TestListParsing:
    """List AST construction."""

    def test_unordered_list(self, parse_ast):
        """Unordered list parsing."""
        ast = parse_ast("- item 1\n- item 2")
        assert len(ast) == 1
        assert isinstance(ast[0], List)
        assert not ast[0].ordered

    def test_ordered_list(self, parse_ast):
        """Ordered list parsing."""
        ast = parse_ast("1. item 1\n2. item 2")
        assert len(ast) == 1
        assert isinstance(ast[0], List)
        assert ast[0].ordered

    def test_list_items(self, parse_ast):
        """List has ListItem children."""
        ast = parse_ast("- item 1\n- item 2")
        lst = ast[0]
        assert len(lst.items) == 2
        assert all(isinstance(item, ListItem) for item in lst.items)

    def test_list_start_number(self, parse_ast):
        """Ordered list tracks start number."""
        ast = parse_ast("5. item")
        lst = ast[0]
        assert lst.start == 5


class TestThematicBreakParsing:
    """Thematic break AST construction."""

    def test_thematic_break(self, parse_ast):
        """Thematic break parsing."""
        ast = parse_ast("---")
        assert len(ast) == 1
        assert isinstance(ast[0], ThematicBreak)


class TestInlineParsing:
    """Inline element AST construction."""

    def test_emphasis(self, parse_ast):
        """Emphasis parsing."""
        ast = parse_ast("*emphasis*")
        para = ast[0]
        assert any(isinstance(c, Emphasis) for c in para.children)

    def test_strong(self, parse_ast):
        """Strong parsing."""
        ast = parse_ast("**strong**")
        para = ast[0]
        assert any(isinstance(c, Strong) for c in para.children)

    def test_code_span(self, parse_ast):
        """Code span parsing."""
        ast = parse_ast("`code`")
        para = ast[0]
        assert any(isinstance(c, CodeSpan) for c in para.children)

    def test_link(self, parse_ast):
        """Link parsing."""
        ast = parse_ast("[text](url)")
        para = ast[0]
        links = [c for c in para.children if isinstance(c, Link)]
        assert len(links) == 1
        assert links[0].url == "url"

    def test_link_with_title(self, parse_ast):
        """Link with title parsing."""
        ast = parse_ast('[text](url "title")')
        para = ast[0]
        link = next(c for c in para.children if isinstance(c, Link))
        assert link.title == "title"

    def test_image(self, parse_ast):
        """Image parsing."""
        ast = parse_ast("![alt](url)")
        para = ast[0]
        images = [c for c in para.children if isinstance(c, Image)]
        assert len(images) == 1
        assert images[0].url == "url"
        assert images[0].alt == "alt"

    def test_hard_break(self, parse_ast):
        """Hard break parsing."""
        ast = parse_ast("line1\\\nline2")
        para = ast[0]
        assert any(isinstance(c, LineBreak) for c in para.children)

    def test_soft_break(self, parse_ast):
        """Soft break parsing."""
        ast = parse_ast("line1\nline2")
        para = ast[0]
        assert any(isinstance(c, SoftBreak) for c in para.children)


class TestASTImmutability:
    """AST node immutability tests."""

    def test_heading_is_frozen(self, parse_ast):
        """Heading nodes are frozen."""
        ast = parse_ast("# Heading")
        with pytest.raises(Exception):  # FrozenInstanceError
            ast[0].level = 2

    def test_paragraph_is_frozen(self, parse_ast):
        """Paragraph nodes are frozen."""
        ast = parse_ast("Text")
        with pytest.raises(Exception):
            ast[0].children = ()

    def test_fenced_code_is_frozen(self, parse_ast):
        """FencedCode nodes are frozen."""
        ast = parse_ast("```\ncode\n```")
        with pytest.raises(Exception):
            ast[0].code = "modified"


class TestLocationTracking:
    """AST node location tracking."""

    def test_nodes_have_location(self, parse_ast):
        """All nodes have location information."""
        ast = parse_ast("# Heading\n\nParagraph")
        for node in ast:
            assert node.location is not None
            assert node.location.lineno > 0

    def test_heading_location(self, parse_ast):
        """Heading tracks correct location."""
        ast = parse_ast("# Heading")
        assert ast[0].location.lineno == 1

    def test_second_block_location(self, parse_ast):
        """Second block has correct line number."""
        ast = parse_ast("# First\n\nSecond")
        # Second block should be on line 3
        assert ast[1].location.lineno == 3
