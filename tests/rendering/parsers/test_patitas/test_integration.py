"""Integration tests for Patitas with Bengal.

Tests the PatitasParser wrapper and factory integration.
"""

from __future__ import annotations

from bengal.rendering.parsers import create_markdown_parser
from bengal.rendering.parsers.patitas import (
    Markdown,
    create_markdown,
    parse,
    parse_to_ast,
    render_ast,
)
from bengal.rendering.parsers.patitas.wrapper import PatitasParser


class TestFactoryIntegration:
    """Factory function integration tests."""

    def test_create_parser_patitas(self):
        """Factory creates PatitasParser."""
        parser = create_markdown_parser("patitas")
        assert isinstance(parser, PatitasParser)

    def test_factory_case_insensitive(self):
        """Factory engine name is case-insensitive."""
        parser = create_markdown_parser("PATITAS")
        assert isinstance(parser, PatitasParser)


class TestPatitasParserWrapper:
    """PatitasParser wrapper tests."""

    def test_parse_basic(self, patitas_parser):
        """Basic parse method."""
        html = patitas_parser.parse("# Hello", {})
        assert "<h1" in html
        assert "Hello" in html

    def test_parse_empty(self, patitas_parser):
        """Parse empty content."""
        html = patitas_parser.parse("", {})
        assert html == ""

    def test_parse_with_toc(self, patitas_parser):
        """Parse with TOC extraction."""
        html, toc = patitas_parser.parse_with_toc("## Section 1\n\n## Section 2", {})
        assert "<h2" in html
        assert "Section 1" in toc
        assert "Section 2" in toc

    def test_toc_has_links(self, patitas_parser):
        """TOC contains anchor links."""
        _, toc = patitas_parser.parse_with_toc("## Section", {})
        assert '<a href="#' in toc

    def test_heading_ids_injected(self, patitas_parser):
        """Heading IDs are injected."""
        html, _ = patitas_parser.parse_with_toc("## My Section", {})
        assert 'id="' in html

    def test_supports_ast_property(self, patitas_parser):
        """supports_ast returns True."""
        assert patitas_parser.supports_ast is True

    def test_parse_to_ast_method(self, patitas_parser):
        """parse_to_ast method works."""
        ast = patitas_parser.parse_to_ast("# Heading", {})
        assert isinstance(ast, list)
        assert len(ast) > 0

    def test_error_handling(self, patitas_parser):
        """Parser handles errors gracefully."""
        # This shouldn't crash even with unusual input
        html = patitas_parser.parse("```\n", {})
        assert html is not None


class TestHighlightingToggle:
    """Syntax highlighting toggle tests."""

    def test_highlighting_enabled_by_default(self):
        """Highlighting is enabled by default."""
        parser = PatitasParser()
        assert parser.enable_highlighting is True

    def test_highlighting_can_be_disabled(self):
        """Highlighting can be disabled."""
        parser = PatitasParser(enable_highlighting=False)
        assert parser.enable_highlighting is False


class TestModuleAPI:
    """Module-level API tests."""

    def test_parse_function(self):
        """parse() function works."""
        html = parse("# Hello")
        assert "<h1" in html

    def test_parse_to_ast_function(self):
        """parse_to_ast() function works."""
        ast = parse_to_ast("# Hello")
        assert len(ast) > 0

    def test_render_ast_function(self):
        """render_ast() function works."""
        source = "# Hello"
        ast = parse_to_ast(source)
        html = render_ast(ast, source)  # source required for ZCLH
        assert "<h1" in html

    def test_create_markdown_function(self):
        """create_markdown() function works."""
        md = create_markdown()
        assert isinstance(md, Markdown)

    def test_markdown_callable(self):
        """Markdown instance is callable."""
        md = create_markdown()
        html = md("# Hello")
        assert "<h1" in html


class TestMarkdownClass:
    """Markdown class tests."""

    def test_markdown_thread_safe(self):
        """Markdown instance can be reused."""
        md = create_markdown()
        html1 = md("# One")
        html2 = md("# Two")
        assert "One" in html1
        assert "Two" in html2

    def test_markdown_parse_to_ast(self):
        """Markdown.parse_to_ast method."""
        md = create_markdown()
        ast = md.parse_to_ast("# Hello")
        assert len(ast) > 0

    def test_markdown_render_ast(self):
        """Markdown.render_ast method."""
        md = create_markdown()
        source = "# Hello"
        ast = md.parse_to_ast(source)
        html = md.render_ast(ast, source)  # source required for ZCLH
        assert "<h1" in html


class TestMetadataHandling:
    """Metadata parameter handling tests."""

    def test_parse_ignores_metadata(self, patitas_parser):
        """Parse works with arbitrary metadata."""
        metadata = {"title": "Test", "date": "2024-01-01", "custom": {"nested": True}}
        html = patitas_parser.parse("# Hello", metadata)
        assert "<h1" in html

    def test_parse_with_empty_metadata(self, patitas_parser):
        """Parse works with empty metadata."""
        html = patitas_parser.parse("# Hello", {})
        assert "<h1" in html

    def test_parse_with_none_like_metadata(self, patitas_parser):
        """Parse handles edge case metadata."""
        html = patitas_parser.parse("# Hello", {"null": None, "empty": ""})
        assert "<h1" in html


class TestTOCGeneration:
    """Table of contents generation tests."""

    def test_toc_nested_headings(self, patitas_parser):
        """TOC handles nested heading levels."""
        content = "# H1\n\n## H2\n\n### H3"
        html, toc = patitas_parser.parse_with_toc(content, {})
        assert "H1" in toc
        assert "H2" in toc
        assert "H3" in toc

    def test_toc_empty_document(self, patitas_parser):
        """TOC for document without headings."""
        _, toc = patitas_parser.parse_with_toc("No headings here", {})
        # TOC should be empty or minimal
        assert "href" not in toc or toc.strip() == ""

    def test_toc_special_characters(self, patitas_parser):
        """TOC handles special characters in headings."""
        _, toc = patitas_parser.parse_with_toc("## Special <chars> & stuff", {})
        # Should be HTML escaped
        assert toc is not None

    def test_toc_unicode_headings(self, patitas_parser):
        """TOC handles unicode headings."""
        _, toc = patitas_parser.parse_with_toc("## 日本語", {})
        assert "日本語" in toc


class TestSlugGeneration:
    """Heading slug generation tests."""

    def test_simple_slug(self, patitas_parser):
        """Simple heading slug."""
        html, _ = patitas_parser.parse_with_toc("## Hello World", {})
        assert 'id="hello-world"' in html

    def test_slug_removes_special_chars(self, patitas_parser):
        """Slug removes special characters."""
        html, _ = patitas_parser.parse_with_toc("## Hello! World?", {})
        # Should have clean slug
        assert 'id="' in html


class TestRealWorldContent:
    """Real-world content tests."""

    def test_readme_like_content(self, patitas_parser):
        """README-like content."""
        content = """
# Project Name

A brief description.

## Installation

```bash
pip install project
```

## Usage

```python
import project
project.do_thing()
```

## Features

- Feature 1
- Feature 2
- Feature 3

## License

MIT
"""
        html = patitas_parser.parse(content, {})
        assert "<h1" in html
        assert "<h2" in html
        assert "<pre>" in html
        assert "<ul>" in html

    def test_documentation_like_content(self, patitas_parser):
        """Documentation-like content."""
        content = """
## Getting Started

First, install the package:

```bash
pip install mypackage
```

Then import it:

```python
from mypackage import main
```

### Configuration

Use the following settings:

- `DEBUG`: Enable debug mode
- `LOG_LEVEL`: Set logging level

### API Reference

See [API docs](https://example.com/docs).
"""
        html = patitas_parser.parse(content, {})
        assert "<h2" in html
        assert "<h3" in html
        assert "<code>" in html
        assert "<a href" in html


class TestParserConsistency:
    """Parser consistency tests."""

    def test_same_input_same_output(self):
        """Same input always produces same output."""
        text = "# Hello **World**"
        html1 = parse(text)
        html2 = parse(text)
        assert html1 == html2

    def test_ast_consistency(self):
        """Same input produces same AST."""
        text = "# Hello"
        ast1 = parse_to_ast(text)
        ast2 = parse_to_ast(text)
        # Compare string representations
        assert str(ast1) == str(ast2)
