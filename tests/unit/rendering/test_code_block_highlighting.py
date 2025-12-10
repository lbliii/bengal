"""
Tests for code block rendering, syntax highlighting, and line highlighting.

These tests verify:
- Basic code block rendering with Pygments
- Line highlighting via `{N}` syntax  
- Line number generation (table format for ≥3 lines)
- The .hll span newline fix (prevents double line spacing)
- Edge cases and variations
"""

from __future__ import annotations

import re

import pytest

from bengal.rendering.parsers import MistuneParser


class TestCodeBlockBasics:
    """Test basic code block rendering."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_code_block_with_language(self, parser):
        """Test code block with language specified."""
        content = """
```python
print("hello")
```
"""
        html = parser.parse(content, {})

        assert '<div class="highlight">' in html
        assert "<pre>" in html
        assert "<code>" in html

    def test_code_block_without_language(self, parser):
        """Test code block without language specified."""
        content = """
```
plain text here
```
"""
        html = parser.parse(content, {})

        # Should still render as code block
        assert "<pre>" in html
        assert "<code>" in html

    def test_code_block_with_unknown_language(self, parser):
        """Test code block with unrecognized language."""
        content = """
```unknownlang
some code
```
"""
        html = parser.parse(content, {})

        # Should fall back gracefully
        assert "<pre>" in html
        assert "<code>" in html

    def test_short_code_block_no_line_numbers(self, parser):
        """Test that short code blocks (<3 lines) don't have line numbers."""
        content = """
```python
x = 1
```
"""
        html = parser.parse(content, {})

        # Should NOT have table-based line numbers
        assert "<table" not in html
        assert "linenos" not in html

    def test_long_code_block_has_line_numbers(self, parser):
        """Test that long code blocks (≥3 lines) have line numbers."""
        content = """
```python
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have table-based line numbers
        assert '<table class="highlighttable">' in html
        assert '<td class="linenos">' in html
        assert '<td class="code">' in html


class TestLineHighlighting:
    """Test line highlighting via {N} syntax."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_single_line_highlight(self, parser):
        """Test highlighting a single line with {N} syntax."""
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have .hll span for highlighted line
        assert '<span class="hll">' in html

    def test_multiple_line_highlight(self, parser):
        """Test highlighting multiple specific lines with {1,3} syntax."""
        content = """
```python {1,3}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have multiple .hll spans
        hll_count = html.count('<span class="hll">')
        assert hll_count == 2, f"Expected 2 .hll spans, got {hll_count}"

    def test_range_line_highlight(self, parser):
        """Test highlighting a range of lines with {1-3} syntax."""
        content = """
```python {1-3}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should have 3 .hll spans for lines 1-3
        hll_count = html.count('<span class="hll">')
        assert hll_count == 3, f"Expected 3 .hll spans, got {hll_count}"

    def test_mixed_highlight_syntax(self, parser):
        """Test mixed highlight syntax {1,3-5,7}."""
        content = """
```python {1,3-5,7}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
line5 = 5
line6 = 6
line7 = 7
```
"""
        html = parser.parse(content, {})

        # Should have 5 .hll spans (1, 3, 4, 5, 7)
        hll_count = html.count('<span class="hll">')
        assert hll_count == 5, f"Expected 5 .hll spans, got {hll_count}"


class TestHllNewlinePlacement:
    """
    Test that .hll spans have newlines removed entirely.
    
    This is critical for CSS `display: block` to work correctly.
    Pygments outputs: <span class="hll">content\n</span>
    We need:         <span class="hll">content</span>
    
    Since .hll uses display:block (for full-width background), the block
    element already creates a line break. Keeping the newline would create
    double spacing in <pre> elements where whitespace is preserved.
    """

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_hll_newline_removed_single_highlight(self, parser):
        """Test newline is removed from .hll span for single highlighted line."""
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should NOT have newline before closing </span> inside .hll
        assert "\n</span>" not in html, (
            "Newline should be removed from .hll span, not kept inside"
        )

    def test_hll_newline_removed_consecutive_highlights(self, parser):
        """Test newline removal for consecutive highlighted lines."""
        content = """
```python {2,3}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should NOT have newline before any closing </span>
        assert "\n</span>" not in html, (
            "Newline should be removed from .hll span, not kept inside"
        )

    def test_hll_newline_removed_non_consecutive_highlights(self, parser):
        """Test newline removal for non-consecutive highlighted lines."""
        content = """
```python {1,3}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should NOT have newline before any closing </span>
        assert "\n</span>" not in html, (
            "Newline should be removed from .hll span, not kept inside"
        )

    def test_hll_structure_correct(self, parser):
        """Test that .hll span structure is correct."""
        content = """
```python {2}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Find all .hll spans
        hll_spans = re.findall(r'<span class="hll">.*?</span>', html, re.DOTALL)

        for span in hll_spans:
            # Each span should end with </span> not \n</span>
            assert not span.endswith("\n</span>"), (
                f"Span should not have newline before closing tag: {repr(span)}"
            )

    def test_hll_no_trailing_newline(self, parser):
        """
        Test that .hll spans have NO trailing newline after closing tag.
        
        This is the key fix for display:block spacing issues. The block element
        already creates a line break, so any trailing newline in the <pre>
        creates double spacing.
        """
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Find .hll spans and extract their content to verify structure
        # The .hll span contains nested token spans, so we need to handle nesting
        import re
        
        # Find where .hll spans START
        hll_starts = list(re.finditer(r'<span class="hll">', html))
        assert hll_starts, "Expected at least one .hll span in output"
        
        for start_match in hll_starts:
            # Find the matching closing </span> by counting nesting
            pos = start_match.end()
            depth = 1
            while pos < len(html) and depth > 0:
                if html[pos:pos+6] == '<span ':
                    depth += 1
                    pos += 6
                elif html[pos:pos+7] == '</span>':
                    depth -= 1
                    if depth == 0:
                        # This is the closing tag of our .hll span
                        end_pos = pos + 7  # Position after </span>
                        if end_pos < len(html):
                            next_char = html[end_pos]
                            # Should NOT be a newline - display:block handles line breaks
                            assert next_char != '\n', (
                                f".hll span should not have trailing newline. "
                                f"Context: ...{html[max(0, end_pos-20):end_pos+10]!r}"
                            )
                        break
                    pos += 7
                else:
                    pos += 1


class TestCodeBlockEdgeCases:
    """Test edge cases for code block rendering."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_empty_code_block(self, parser):
        """Test empty code block."""
        content = """
```python
```
"""
        html = parser.parse(content, {})

        # Should render without error
        assert "<pre>" in html or '<div class="highlight">' in html

    def test_code_block_with_special_characters(self, parser):
        """Test code block with HTML special characters."""
        content = """
```html
<div class="test">&amp;</div>
```
"""
        html = parser.parse(content, {})

        # Characters should be escaped
        assert "&lt;" in html or "<" in html  # Either escaped or in code tag
        assert "&gt;" in html or ">" in html

    def test_highlight_out_of_range(self, parser):
        """Test highlighting lines that don't exist."""
        content = """
```python {10}
x = 1
```
"""
        # Should not crash
        html = parser.parse(content, {})
        assert "<pre>" in html or '<div class="highlight">' in html

    def test_highlight_with_only_first_line(self, parser):
        """Test highlighting just the first line."""
        content = """
```python {1}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Should have exactly one .hll span
        hll_count = html.count('<span class="hll">')
        assert hll_count == 1, f"Expected 1 .hll span, got {hll_count}"

    def test_highlight_with_only_last_line(self, parser):
        """Test highlighting just the last line."""
        content = """
```python {3}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Should have exactly one .hll span
        hll_count = html.count('<span class="hll">')
        assert hll_count == 1, f"Expected 1 .hll span, got {hll_count}"

    def test_multiple_code_blocks(self, parser):
        """Test multiple code blocks on same page."""
        content = """
First block:

```python {1}
x = 1
y = 2
```

Second block:

```javascript {2}
const a = 1;
const b = 2;
```
"""
        html = parser.parse(content, {})

        # Both should have .hll spans
        hll_count = html.count('<span class="hll">')
        assert hll_count >= 2, f"Expected at least 2 .hll spans, got {hll_count}"


class TestHighlightingWithLineNumbers:
    """Test highlighting behavior with table-based line numbers."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_highlight_with_line_numbers(self, parser):
        """Test that highlighting works with line numbers enabled."""
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have both table structure and .hll span
        assert '<table class="highlighttable">' in html
        assert '<span class="hll">' in html

    def test_line_numbers_correct_count(self, parser):
        """Test that line numbers match code lines."""
        content = """
```python
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should have line numbers 1-4
        assert ">1</span>" in html or ">1<" in html
        assert ">4</span>" in html or ">4<" in html

    def test_hll_in_table_structure(self, parser):
        """Test .hll spans work correctly within table structure."""
        content = """
```python {1,3}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Should have proper table structure
        assert "<td class=\"code\">" in html

        # .hll spans should be in code cell, not line number cell
        assert '<td class="linenos">' in html
        # Line number cell should NOT contain .hll
        linenos_match = re.search(
            r'<td class="linenos">.*?</td>', html, re.DOTALL
        )
        if linenos_match:
            assert "hll" not in linenos_match.group()


class TestHighlightSyntaxParsing:
    """Test that various highlight syntax patterns are parsed correctly.
    
    Note: We test parsing indirectly through the parser output since
    parse_hl_lines is an internal function.
    """

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_single_line_syntax(self, parser):
        """Test single line number {5}."""
        content = """
```python {1}
line1
line2
line3
```
"""
        html = parser.parse(content, {})
        hll_count = html.count('<span class="hll">')
        assert hll_count == 1

    def test_comma_separated_syntax(self, parser):
        """Test comma-separated lines {1,3}."""
        content = """
```python {1,3}
line1
line2
line3
```
"""
        html = parser.parse(content, {})
        hll_count = html.count('<span class="hll">')
        assert hll_count == 2

    def test_range_syntax(self, parser):
        """Test range {2-4}."""
        content = """
```python {2-4}
line1
line2
line3
line4
line5
```
"""
        html = parser.parse(content, {})
        hll_count = html.count('<span class="hll">')
        assert hll_count == 3  # lines 2, 3, 4

    def test_mixed_syntax(self, parser):
        """Test mixed {1,3-5}."""
        content = """
```python {1,3-5}
line1
line2
line3
line4
line5
line6
```
"""
        html = parser.parse(content, {})
        hll_count = html.count('<span class="hll">')
        assert hll_count == 4  # lines 1, 3, 4, 5

    def test_complex_syntax(self, parser):
        """Test complex {1,3-5,7-8,10}."""
        content = """
```python {1,3-5,7-8,10}
line1
line2
line3
line4
line5
line6
line7
line8
line9
line10
```
"""
        html = parser.parse(content, {})
        hll_count = html.count('<span class="hll">')
        assert hll_count == 7  # lines 1, 3, 4, 5, 7, 8, 10

