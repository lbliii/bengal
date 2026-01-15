"""Edge case tests for Patitas parser.

Tests for edge cases that ensure parity with Mistune parser output:
- Nested lists
- Task lists
- Multi-line list items (loose lists)
- Table rendering
- Footnotes
- Strikethrough

These tests verify both AST construction and HTML rendering.
"""

from __future__ import annotations

import pytest

from patitas.nodes import (
    FootnoteDef,
    FootnoteRef,
    List,
    ListItem,
    Paragraph,
)


class TestNestedLists:
    """Nested list parsing and rendering."""

    def test_nested_unordered_list_ast(self, parse_ast):
        """Nested unordered list produces correct AST structure."""
        source = "- Item 1\n  - Sub item 1a\n  - Sub item 1b\n- Item 2"
        ast = parse_ast(source)

        assert len(ast) == 1
        lst = ast[0]
        assert isinstance(lst, List)
        assert not lst.ordered
        assert len(lst.items) == 2

        # First item should have nested list
        first_item = lst.items[0]
        assert isinstance(first_item, ListItem)
        # Should have paragraph + nested list as children
        assert len(first_item.children) == 2
        assert isinstance(first_item.children[0], Paragraph)
        assert isinstance(first_item.children[1], List)

        # Nested list should have 2 items
        nested = first_item.children[1]
        assert len(nested.items) == 2

    def test_nested_ordered_list_ast(self, parse_ast):
        """Nested ordered list produces correct AST structure."""
        source = "1. Item 1\n   1. Sub item 1a\n   2. Sub item 1b\n2. Item 2"
        ast = parse_ast(source)

        assert len(ast) == 1
        lst = ast[0]
        assert isinstance(lst, List)
        assert lst.ordered

    def test_nested_list_html(self, parse_md):
        """Nested list renders to correct HTML."""
        source = "- Item 1\n  - Sub 1\n  - Sub 2\n- Item 2"
        html = parse_md(source)

        # Should contain nested ul
        assert "<ul>" in html
        assert html.count("<ul>") == 2
        assert html.count("</ul>") == 2
        assert "<li>" in html
        # Verify nesting structure
        assert "Item 1" in html
        assert "Sub 1" in html
        assert "Item 2" in html


class TestTaskLists:
    """Task list (checkbox) parsing and rendering."""

    def test_task_list_unchecked_ast(self, parse_ast):
        """Unchecked task list item has checked=False."""
        source = "- [ ] Unchecked item"
        ast = parse_ast(source)

        lst = ast[0]
        item = lst.items[0]
        assert item.checked is False

    def test_task_list_checked_ast(self, parse_ast):
        """Checked task list item has checked=True."""
        source = "- [x] Checked item"
        ast = parse_ast(source)

        lst = ast[0]
        item = lst.items[0]
        assert item.checked is True

    def test_task_list_checked_uppercase(self, parse_ast):
        """Uppercase X is also accepted."""
        source = "- [X] Checked item"
        ast = parse_ast(source)

        lst = ast[0]
        item = lst.items[0]
        assert item.checked is True

    def test_regular_list_no_checked(self, parse_ast):
        """Regular list items have checked=None."""
        source = "- Regular item"
        ast = parse_ast(source)

        lst = ast[0]
        item = lst.items[0]
        assert item.checked is None

    def test_task_list_html(self, parse_md):
        """Task list renders with checkboxes."""
        source = "- [ ] Unchecked\n- [x] Checked"
        html = parse_md(source)

        assert 'class="task-list-item"' in html
        assert 'class="task-list-item-checkbox"' in html
        assert 'type="checkbox"' in html
        assert "disabled" in html
        # Checked item should have checked attribute
        assert " checked" in html


class TestMultiLineListItems:
    """Multi-line list items (loose lists) parsing and rendering."""

    def test_loose_list_detection(self, parse_ast):
        """List with blank lines between items is loose."""
        source = "- Item 1\n\n  Continuation\n\n- Item 2"
        ast = parse_ast(source)

        lst = ast[0]
        assert lst.tight is False

    def test_tight_list_detection(self, parse_ast):
        """List without blank lines is tight."""
        source = "- Item 1\n- Item 2\n- Item 3"
        ast = parse_ast(source)

        lst = ast[0]
        assert lst.tight is True

    def test_loose_list_multiple_paragraphs(self, parse_ast):
        """Loose list item has multiple paragraphs."""
        source = "- Item 1\n\n  Continuation paragraph.\n\n- Item 2"
        ast = parse_ast(source)

        lst = ast[0]
        first_item = lst.items[0]
        # Should have two paragraphs
        paragraphs = [c for c in first_item.children if isinstance(c, Paragraph)]
        assert len(paragraphs) == 2

    def test_loose_list_html(self, parse_md):
        """Loose list renders paragraphs inside list items."""
        source = "- Item 1\n\n  Continuation paragraph.\n\n- Item 2"
        html = parse_md(source)

        # Both items should have <p> tags
        assert html.count("<p>") >= 3  # 2 for first item, 1 for second
        # Check that list items contain paragraphs (newline-tolerant)
        assert "<li>" in html and "<p>" in html


class TestTableRendering:
    """Table rendering with wrapper div."""

    def test_table_has_wrapper(self, parse_md):
        """Table is wrapped in table-wrapper div."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = parse_md(source)

        assert 'class="table-wrapper"' in html
        assert "<table>" in html
        assert "</table></div>" in html

    def test_table_pretty_printing(self, parse_md):
        """Table rows are pretty-printed with newlines."""
        source = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = parse_md(source)

        assert "<tr>\n" in html
        assert "<th>" in html
        assert "<td>" in html


class TestFootnotes:
    """Footnote parsing and rendering."""

    def test_footnote_ref_ast(self, parse_ast):
        """Footnote reference in AST."""
        source = "Text with footnote[^1]."
        ast = parse_ast(source)

        para = ast[0]
        refs = [c for c in para.children if isinstance(c, FootnoteRef)]
        assert len(refs) == 1
        assert refs[0].identifier == "1"

    def test_footnote_def_ast(self, parse_ast):
        """Footnote definition in AST."""
        source = "[^1]: This is the footnote."
        ast = parse_ast(source)

        defs = [n for n in ast if isinstance(n, FootnoteDef)]
        assert len(defs) == 1
        assert defs[0].identifier == "1"
        assert len(defs[0].children) > 0

    def test_footnote_alphanumeric_id(self, parse_ast):
        """Footnote with alphanumeric identifier."""
        source = "Text[^note-1].\n\n[^note-1]: Note content."
        ast = parse_ast(source)

        # Find the footnote ref
        para = ast[0]
        refs = [c for c in para.children if isinstance(c, FootnoteRef)]
        assert len(refs) == 1
        assert refs[0].identifier == "note-1"

    def test_footnote_html(self, parse_md):
        """Footnotes render correctly."""
        source = "Text with footnote[^1].\n\n[^1]: This is the footnote."
        html = parse_md(source)

        # Reference
        assert 'class="footnote-ref"' in html
        assert 'href="#fn-1"' in html
        assert 'id="fnref-1"' in html

        # Definition section
        assert 'class="footnotes"' in html
        assert 'id="fn-1"' in html
        assert 'href="#fnref-1"' in html
        assert "&#8617;" in html  # Back reference character


class TestStrikethrough:
    """Strikethrough parsing and rendering."""

    def test_strikethrough_html(self, parse_md):
        """Strikethrough renders with del tags."""
        source = "This is ~~deleted~~ text."
        html = parse_md(source)

        assert "<del>" in html
        assert "</del>" in html
        assert "deleted" in html


class TestMistuneParserParity:
    """Tests ensuring parity between Patitas and Mistune parsers."""

    @pytest.fixture
    def mistune_parser(self):
        """Create a Mistune parser for comparison."""
        from bengal.parsing import create_markdown_parser

        return create_markdown_parser("mistune")

    @pytest.fixture
    def patitas_parser_cmp(self):
        """Create a Patitas parser for comparison."""
        from bengal.parsing import create_markdown_parser

        return create_markdown_parser("patitas")

    def _normalize_html(self, html: str) -> str:
        """Normalize HTML for comparison (remove extra whitespace)."""
        import re

        # Remove extra whitespace between tags
        html = re.sub(r">\s+<", "><", html)
        # Remove trailing whitespace before opening tags (e.g., "text <ul>" -> "text<ul>")
        html = re.sub(r"\s+<", "<", html)
        # Normalize whitespace
        html = " ".join(html.split())
        return html.strip()

    @pytest.mark.parametrize(
        "name,source",
        [
            ("nested_list", "- Item 1\n  - Sub 1\n  - Sub 2\n- Item 2"),
            ("task_list", "- [ ] Unchecked\n- [x] Checked"),
            ("table", "| A | B |\n|---|---|\n| 1 | 2 |"),
            ("strikethrough", "This is ~~deleted~~ text."),
            ("footnotes", "Text[^1].\n\n[^1]: Note."),
        ],
    )
    def test_html_parity(self, mistune_parser, patitas_parser_cmp, name, source):
        """Verify HTML output parity for common edge cases."""
        mistune_html = self._normalize_html(mistune_parser.parse(source, {}))
        patitas_html = self._normalize_html(patitas_parser_cmp.parse(source, {}))

        assert mistune_html == patitas_html, (
            f"HTML parity failed for {name}:\n"
            f"Mistune:  {mistune_html[:200]}\n"
            f"Patitas: {patitas_html[:200]}"
        )

    def test_loose_list_parity(self, mistune_parser, patitas_parser_cmp):
        """Verify loose list parity."""
        source = "- Item 1\n\n  Continuation.\n\n- Item 2"
        mistune_html = self._normalize_html(mistune_parser.parse(source, {}))
        patitas_html = self._normalize_html(patitas_parser_cmp.parse(source, {}))

        assert mistune_html == patitas_html


class TestEdgeCasesRegression:
    """Regression tests for specific edge cases."""

    def test_empty_list_item(self, parse_ast):
        """List can have empty items."""
        source = "- \n- Item 2"
        ast = parse_ast(source)

        lst = ast[0]
        assert len(lst.items) == 2

    def test_list_with_code_block(self, parse_md):
        """List item can contain code block."""
        source = "- Item with code:\n\n  ```python\n  print(1)\n  ```"
        html = parse_md(source)

        assert "<li>" in html
        assert "<pre>" in html or "<code>" in html

    def test_deeply_nested_list(self, parse_ast):
        """Deeply nested lists parse correctly."""
        source = "- L1\n  - L2\n    - L3\n      - L4"
        ast = parse_ast(source)

        # Navigate to deepest level
        l1 = ast[0]
        assert isinstance(l1, List)

    def test_mixed_list_markers(self, parse_ast):
        """Different list markers create separate lists per CommonMark spec."""
        source = "- Item 1\n* Item 2\n+ Item 3"
        ast = parse_ast(source)

        # CommonMark: different markers create separate lists
        # - creates one list, * creates another, + creates another
        assert len(ast) == 3
        for node in ast:
            assert isinstance(node, List)

    def test_footnote_without_definition(self, parse_md):
        """Footnote reference without definition renders as text."""
        source = "Text[^undefined]."
        html = parse_md(source)
        # Should still have the reference markup
        assert "undefined" in html

    def test_multiple_footnotes(self, parse_md):
        """Multiple footnotes are collected and rendered."""
        source = "Text[^1] and[^2].\n\n[^1]: First.\n[^2]: Second."
        html = parse_md(source)

        assert html.count('id="fn-') == 2
        assert "First" in html
        assert "Second" in html
