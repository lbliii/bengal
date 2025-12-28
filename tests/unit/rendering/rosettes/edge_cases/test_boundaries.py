"""Tests for boundary conditions."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import get_lexer, list_languages


class TestEmptyInput:
    """Test empty input handling."""

    @pytest.mark.parametrize("language", list_languages()[:10])  # Test first 10 languages
    def test_empty_input(self, language: str) -> None:
        """Empty input should not crash."""
        lexer = get_lexer(language)
        tokens = list(lexer.tokenize(""))
        # Should return empty list or whitespace token
        assert isinstance(tokens, list)

    def test_single_character(self) -> None:
        """Single character should tokenize."""
        lexer = get_lexer("python")
        tokens = list(lexer.tokenize("x"))
        assert len(tokens) > 0

    def test_only_whitespace(self) -> None:
        """Whitespace-only input should not crash."""
        lexer = get_lexer("python")
        tokens = list(lexer.tokenize("   \n\t  "))
        assert isinstance(tokens, list)


class TestLargeInput:
    """Test large input handling."""

    def test_very_long_line(self) -> None:
        """Very long line should complete in reasonable time."""
        import time

        lexer = get_lexer("python")
        code = "x" * 100_000  # 100K chars

        start = time.perf_counter()
        tokens = list(lexer.tokenize(code))
        elapsed = time.perf_counter() - start

        # Should complete in < 1 second (O(n) guarantee)
        assert elapsed < 1.0, f"Took {elapsed:.3f}s for 100K chars"
        assert len(tokens) > 0

    def test_many_tokens(self) -> None:
        """Many tokens should complete in reasonable time."""
        import time

        lexer = get_lexer("python")
        code = "x " * 50_000  # 100K tokens

        start = time.perf_counter()
        tokens = list(lexer.tokenize(code))
        elapsed = time.perf_counter() - start

        # Should complete in < 1 second
        assert elapsed < 1.0, f"Took {elapsed:.3f}s for 100K tokens"
        assert len(tokens) > 0
