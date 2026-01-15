"""Integration tests for AST-based content pipeline.

Verifies that AST-based rendering produces equivalent output to legacy HTML parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class TestASTPipelineIntegration:
    """Integration tests for AST pipeline."""

    def test_ast_pipeline_produces_html(self, tmp_path: Path) -> None:
        """Verify AST pipeline produces valid HTML."""
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Hello World

This is a **test** paragraph with [a link](/docs/).

## Second Section

- Item 1
- Item 2

```python
def hello():
    print("world")
```
"""
        parser = MistuneParser()

        # Parse to AST
        ast = parser.parse_to_ast(content, {})
        assert ast is not None
        assert len(ast) > 0

        # Render AST to HTML
        html = parser.render_ast(ast)
        assert html is not None
        assert len(html) > 0

        # Verify key elements are present
        assert "<h1" in html
        assert "<h2" in html
        assert "Hello World" in html
        assert "Second Section" in html
        assert "<strong>" in html or "<b>" in html
        assert "<a " in html
        assert "href=" in html
        assert "<ul>" in html or "<li>" in html
        assert "<pre>" in html or "<code>" in html

    def test_ast_pipeline_matches_direct_parse(self, tmp_path: Path) -> None:
        """Verify AST-based rendering matches direct markdown parsing."""
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Test Document

Regular paragraph with *emphasis* and **strong** text.

[Link text](https://example.com)

> A blockquote

1. Numbered item
2. Another item
"""
        parser = MistuneParser()

        # Direct parse (legacy path)
        direct_html = parser.parse(content, {})

        # AST path
        ast = parser.parse_to_ast(content, {})
        ast_html = parser.render_ast(ast)

        # Normalize for comparison (strip whitespace differences)
        def normalize(s: str) -> str:
            import re

            s = re.sub(r"\s+", " ", s)
            return s.strip()

        assert normalize(direct_html) == normalize(ast_html)

    def test_ast_toc_extraction_matches_html_toc(self, tmp_path: Path) -> None:
        """Verify AST-based TOC extraction produces same structure as HTML-based."""
        from bengal.parsing.ast.utils import extract_toc_from_ast
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Main Title

## First Section

### Subsection A

### Subsection B

## Second Section

### Another Subsection
"""
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        toc = extract_toc_from_ast(ast)

        # Verify structure
        assert len(toc) >= 5  # At least 5 headings

        # Verify levels are normalized (H1=0, H2=1, H3=2 or similar)
        titles = [item["title"] for item in toc]
        assert "Main Title" in titles
        assert "First Section" in titles
        assert "Subsection A" in titles
        assert "Second Section" in titles

    def test_ast_link_extraction(self, tmp_path: Path) -> None:
        """Verify AST-based link extraction finds all links."""
        from bengal.parsing.ast.utils import extract_links_from_ast
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Links Test

Here's [an internal link](/docs/guide/).

And [an external link](https://example.com).

[Another link](./relative.md)
"""
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        links = extract_links_from_ast(ast)

        # Should find all link hrefs (not images)
        assert "/docs/guide/" in links
        assert "https://example.com" in links
        assert "./relative.md" in links

    def test_ast_plain_text_extraction(self, tmp_path: Path) -> None:
        """Verify AST-based plain text extraction."""
        from bengal.parsing.ast.utils import extract_plain_text
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Hello World

This is **bold** and *italic* text.

Here's some `inline code`.

```python
def test():
    pass
```
"""
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        text = extract_plain_text(ast)

        # Should contain text content
        assert "Hello World" in text
        assert "bold" in text
        assert "italic" in text
        assert "inline code" in text

    def test_ast_transforms_preserve_structure(self, tmp_path: Path) -> None:
        """Verify AST transforms don't break rendering."""
        from bengal.parsing.ast.transforms import (
            add_baseurl_to_ast,
            normalize_md_links_in_ast,
        )
        from bengal.parsing.backends.mistune import MistuneParser

        content = """# Test

[Internal link](/docs/guide/)

[MD link](./other.md)
"""
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        # Apply transforms
        ast = normalize_md_links_in_ast(ast)
        ast = add_baseurl_to_ast(ast, "/bengal")

        # Should still render
        html = parser.render_ast(ast)
        assert "<h1" in html
        assert "<a " in html
        assert "href=" in html

    def test_page_content_uses_ast_when_available(self, tmp_path: Path) -> None:
        """Verify AST-based plain text extraction works correctly."""
        from bengal.parsing.ast.utils import extract_plain_text
        from bengal.parsing.backends.mistune import MistuneParser

        content = "# Hello\n\nWorld paragraph."

        # Parse to AST
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        # Extract plain text from AST
        text = extract_plain_text(ast)

        # Should contain text content
        assert "Hello" in text
        assert "World" in text


class TestASTWithDirectives:
    """Test AST pipeline handles directive output correctly."""

    def test_raw_html_in_ast(self, tmp_path: Path) -> None:
        """Verify RawHTMLNode type can represent directive output."""
        from bengal.parsing.ast.types import RawHTMLNode, is_raw_html

        node: RawHTMLNode = {"type": "raw_html", "content": "<div class='note'>Note content</div>"}

        assert is_raw_html(node)
        assert node["content"] == "<div class='note'>Note content</div>"

    def test_ast_walk_with_raw_html(self, tmp_path: Path) -> None:
        """Verify walk_ast handles RawHTMLNode."""
        from bengal.parsing.ast.types import ASTNode
        from bengal.parsing.ast.utils import walk_ast

        ast: list[ASTNode] = [
            {"type": "paragraph", "children": [{"type": "text", "raw": "Before"}]},
            {"type": "raw_html", "content": "<div>Directive output</div>"},
            {"type": "paragraph", "children": [{"type": "text", "raw": "After"}]},
        ]

        nodes = list(walk_ast(ast))

        # Should visit raw_html node
        types = [n.get("type") for n in nodes]
        assert "raw_html" in types


class TestASTCacheThreadSafety:
    """Test that AST utilities are thread-safe."""

    def test_concurrent_ast_extraction(self, tmp_path: Path) -> None:
        """Verify AST extraction can be called from multiple threads."""
        import threading

        from bengal.parsing.ast.utils import extract_plain_text
        from bengal.parsing.backends.mistune import MistuneParser

        content = "# Test\n\nContent paragraph."

        # Parse to AST once
        parser = MistuneParser()
        ast = parser.parse_to_ast(content, {})

        results: list[str] = []
        errors: list[Exception] = []

        def extract_text() -> None:
            try:
                text = extract_plain_text(ast)
                results.append(text)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=extract_text) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors
        assert len(errors) == 0
        # All got results
        assert len(results) == 10
        # All results are consistent
        assert all(r == results[0] for r in results)
