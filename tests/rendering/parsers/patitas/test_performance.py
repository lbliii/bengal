"""Performance regression tests for Patitas parser (Phase 5 of CommonMark compliance RFC).

Ensures parser maintains O(n) performance characteristics and doesn't regress
on performance-critical operations like list parsing.

See: plan/rfc-patitas-commonmark-compliance.md (Phase 5: Performance Regression Tests)
"""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse

try:
    import pytest_benchmark
except ImportError:
    pytest_benchmark = None


@pytest.mark.skipif(pytest_benchmark is None, reason="pytest-benchmark not installed")
class TestPerformanceRegression:
    """Performance regression tests to ensure O(n) parsing."""

    def test_list_performance(self, benchmark) -> None:
        """List parsing stays O(n).

        Verifies that parsing large lists maintains linear time complexity.
        This is critical for Patitas's O(n) guarantee.

        Args:
            benchmark: pytest-benchmark fixture
        """
        # Generate a large list (1000 items)
        md = "- item\n" * 1000
        result = benchmark(parse, md)
        # Sanity check - should produce valid HTML
        assert result
        assert "<ul>" in result or "<li>" in result

    def test_paragraph_performance(self, benchmark) -> None:
        """Paragraph parsing stays O(n)."""
        # Generate many paragraphs
        md = "Paragraph text here.\n\n" * 500
        result = benchmark(parse, md)
        assert result
        assert "<p>" in result

    def test_code_block_performance(self, benchmark) -> None:
        """Code block parsing stays O(n)."""
        # Generate large code block
        md = "```python\n" + "x = 1\n" * 1000 + "```"
        result = benchmark(parse, md)
        assert result
        assert "<pre>" in result or "<code>" in result

    def test_heading_performance(self, benchmark) -> None:
        """Heading parsing stays O(n)."""
        # Generate many headings
        md = "\n".join(f"# Heading {i}" for i in range(500))
        result = benchmark(parse, md)
        assert result
        assert "<h" in result

    def test_mixed_content_performance(self, benchmark) -> None:
        """Mixed content parsing stays O(n)."""
        # Generate mixed markdown content
        md_parts = []
        for i in range(100):
            md_parts.append(f"# Heading {i}")
            md_parts.append(f"Paragraph {i} with **bold** and *italic*.")
            md_parts.append(f"- List item {i}")
            md_parts.append("")
        md = "\n".join(md_parts)
        result = benchmark(parse, md)
        assert result

    def test_nested_list_performance(self, benchmark) -> None:
        """Nested list parsing stays O(n)."""
        # Generate deeply nested lists
        md_parts = []
        for i in range(100):
            indent = "  " * (i % 5)  # Nest up to 5 levels
            md_parts.append(f"{indent}- Item {i}")
        md = "\n".join(md_parts)
        result = benchmark(parse, md)
        assert result
        assert "<ul>" in result or "<li>" in result


class TestPerformanceSanity:
    """Basic performance sanity checks (no benchmark dependency)."""

    def test_large_list_doesnt_hang(self) -> None:
        """Large lists parse in reasonable time."""
        import time

        md = "- item\n" * 10000
        start = time.time()
        result = parse(md)
        elapsed = time.time() - start
        # Should complete in under 1 second for 10k items
        assert elapsed < 1.0, f"Parsing took {elapsed:.2f}s (too slow)"
        assert result

    def test_deeply_nested_doesnt_hang(self) -> None:
        """Deeply nested structures parse in reasonable time."""
        import time

        # Create deeply nested block quotes
        md = "> " * 100 + "text"
        start = time.time()
        result = parse(md)
        elapsed = time.time() - start
        # Should complete quickly even with deep nesting
        assert elapsed < 0.5, f"Parsing took {elapsed:.2f}s (too slow)"
        assert result
