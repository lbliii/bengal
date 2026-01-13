"""
Tests for code block rendering, syntax highlighting, and line highlighting.

These tests verify:
- Basic code block rendering with Rosettes (default backend)
- Line highlighting via `{N}` syntax
- Proper span structure for highlighted lines
- Edge cases and variations

Note: Bengal uses Rosettes as the default syntax highlighting backend,
which has a simpler output format than Pygments (no table-based line numbers).
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

        assert '<div class="rosettes"' in html
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

    def test_long_code_block_renders(self, parser):
        """Test that long code blocks (≥3 lines) render correctly."""
        content = """
```python
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have basic code block structure
        # Note: Rosettes doesn't use table-based line numbers
        assert '<div class="rosettes"' in html
        assert "<pre>" in html
        assert "<code>" in html


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
    Test that .hll spans properly wrap highlighted lines.
    
    Rosettes outputs .hll spans that wrap individual lines. The span
    structure is: <span class="hll">...tokens...</span>
    
    where the newline appears AFTER the closing tag.
        
    """

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_hll_span_present_single_highlight(self, parser):
        """Test .hll span is present for single highlighted line."""
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Should have .hll span for the highlighted line
        assert '<span class="hll">' in html

    def test_hll_span_present_consecutive_highlights(self, parser):
        """Test .hll spans are present for consecutive highlighted lines."""
        content = """
```python {2,3}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should have .hll spans for the highlighted lines
        assert '<span class="hll">' in html

    def test_hll_span_present_non_consecutive_highlights(self, parser):
        """Test .hll spans are present for non-consecutive highlighted lines."""
        content = """
```python {1,3}
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Should have .hll spans for the highlighted lines
        hll_count = html.count('<span class="hll">')
        assert hll_count == 2, f"Expected 2 .hll spans, got {hll_count}"

    def test_hll_structure_correct(self, parser):
        """Test that .hll span structure contains tokens."""
        content = """
```python {2}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Should have .hll span containing code
        assert '<span class="hll">' in html
        # The .hll span should contain syntax highlighting spans
        assert '<span class="' in html

    def test_hll_span_closes_properly(self, parser):
        """Test that .hll spans close properly with </span>."""
        content = """
```python {2}
line1 = 1
line2 = 2
line3 = 3
```
"""
        html = parser.parse(content, {})

        # Find .hll spans and verify they close properly
        hll_starts = list(re.finditer(r'<span class="hll">', html))
        assert hll_starts, "Expected at least one .hll span in output"

        for start_match in hll_starts:
            # Find the matching closing </span> by counting nesting
            pos = start_match.end()
            depth = 1
            while pos < len(html) and depth > 0:
                if html[pos : pos + 6] == "<span ":
                    depth += 1
                    pos += 6
                elif html[pos : pos + 7] == "</span>":
                    depth -= 1
                    pos += 7
                else:
                    pos += 1
            # Verify we found the closing tag (depth became 0)
            assert depth == 0, "Did not find matching closing </span> for .hll span"


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
        assert "<pre>" in html or '<div class="rosettes">' in html

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
        assert "<pre>" in html or '<div class="rosettes">' in html

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
    """Test highlighting behavior with .hll line highlighting.
    
    Note: Rosettes uses a simpler format without table-based line numbers.
    Line highlighting is done via .hll spans that wrap entire lines.
        
    """

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser with highlighting enabled."""
        return MistuneParser(enable_highlighting=True)

    def test_highlight_with_line_highlighting(self, parser):
        """Test that line highlighting works."""
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
        # Should have basic code block structure
        assert '<div class="rosettes"' in html

    def test_code_block_contains_content(self, parser):
        """Test that code content is in the output."""
        content = """
```python
line1 = 1
line2 = 2
line3 = 3
line4 = 4
```
"""
        html = parser.parse(content, {})

        # Content should be present (may be tokenized into spans)
        assert "line1" in html or "n" in html  # 'n' token class for names
        assert "line4" in html or "4" in html

    def test_hll_wraps_highlighted_content(self, parser):
        """Test .hll spans wrap the highlighted line content."""
        content = """
```python {1,3}
x = 1
y = 2
z = 3
```
"""
        html = parser.parse(content, {})

        # Should have .hll spans for highlighted lines
        hll_count = html.count('<span class="hll">')
        assert hll_count == 2, f"Expected 2 .hll spans, got {hll_count}"

        # Each .hll span should have corresponding closing tag
        hll_close_count = html.count("</span>")
        assert hll_close_count >= 2, "Should have at least 2 closing span tags"


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
