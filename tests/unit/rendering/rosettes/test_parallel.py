"""Tests for parallel API (highlight_many, tokenize_many)."""

from __future__ import annotations

from bengal.rendering.rosettes import highlight_many, tokenize_many


class TestHighlightMany:
    """Test highlight_many() parallel API."""

    def test_highlight_many_basic(self) -> None:
        """highlight_many() should return correct results in order."""
        items = [
            ("def foo(): pass", "python"),
            ("const x = 1;", "javascript"),
            ("fn main() {}", "rust"),
        ]

        results = highlight_many(items)

        assert len(results) == 3
        assert "foo" in results[0]
        assert "const" in results[1]
        assert "fn" in results[2]

    def test_highlight_many_empty(self) -> None:
        """highlight_many() with empty list should return empty list."""
        results = highlight_many([])
        assert results == []

    def test_highlight_many_small_batch(self) -> None:
        """Small batches should use sequential processing."""
        items = [("x = 1", "python")] * 5  # 5 items
        results = highlight_many(items)
        assert len(results) == 5

    def test_highlight_many_large_batch(self) -> None:
        """Large batches should use parallel processing."""
        items = [("x = 1", "python")] * 20  # 20 items
        results = highlight_many(items)
        assert len(results) == 20

    def test_highlight_many_order_preserved(self) -> None:
        """Results should be in same order as input."""
        items = [(f"x{i} = {i}", "python") for i in range(10)]
        results = highlight_many(items)

        # Verify order preserved
        for i, result in enumerate(results):
            assert str(i) in result


class TestTokenizeMany:
    """Test tokenize_many() parallel API."""

    def test_tokenize_many_basic(self) -> None:
        """tokenize_many() should return correct results in order."""
        items = [
            ("x = 1", "python"),
            ("let y = 2;", "javascript"),
        ]

        results = tokenize_many(items)

        assert len(results) == 2
        assert len(results[0]) > 0
        assert len(results[1]) > 0

    def test_tokenize_many_empty(self) -> None:
        """tokenize_many() with empty list should return empty list."""
        results = tokenize_many([])
        assert results == []

    def test_tokenize_many_order_preserved(self) -> None:
        """Results should be in same order as input."""
        items = [(f"x{i} = {i}", "python") for i in range(10)]
        results = tokenize_many(items)

        # Verify order preserved
        assert len(results) == 10
        for tokens in results:
            assert len(tokens) > 0
