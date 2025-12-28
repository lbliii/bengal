"""Tests for Rosettes registry (get_lexer, list_languages, supports_language)."""

from __future__ import annotations

import pytest

from bengal.errors import BengalRenderingError
from bengal.rendering.rosettes import get_lexer, list_languages, supports_language


class TestRegistryBasics:
    """Test basic registry functionality."""

    def test_list_languages_returns_list(self) -> None:
        """list_languages() should return a list."""
        languages = list_languages()
        assert isinstance(languages, list)
        assert len(languages) >= 50  # Should have 54 languages

    def test_list_languages_includes_common(self) -> None:
        """list_languages() should include common languages."""
        languages = list_languages()
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages
        assert "go" in languages
        assert "kida" in languages

    def test_list_languages_sorted(self) -> None:
        """list_languages() should return sorted list."""
        languages = list_languages()
        assert languages == sorted(languages)

    def test_supports_language_known(self) -> None:
        """supports_language() should return True for known languages."""
        assert supports_language("python")
        assert supports_language("javascript")
        assert supports_language("rust")
        assert supports_language("go")
        assert supports_language("kida")

    def test_supports_language_unknown(self) -> None:
        """supports_language() should return False for unknown languages."""
        assert not supports_language("unknown-language-xyz")
        assert not supports_language("made-up-language")

    def test_supports_language_case_insensitive(self) -> None:
        """supports_language() should be case-insensitive."""
        assert supports_language("PYTHON")
        assert supports_language("Python")
        assert supports_language("JAVASCRIPT")


class TestLanguageAliases:
    """Test language alias resolution."""

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("py", "python"),
            ("js", "javascript"),
            ("ts", "typescript"),
            ("rb", "ruby"),
            ("yml", "yaml"),
            ("rs", "rust"),
            ("golang", "go"),
            ("sh", "bash"),
            ("shell", "bash"),
            ("jinja2", "jinja"),
            ("j2", "jinja"),
            ("django", "jinja"),
        ],
    )
    def test_aliases_resolve(self, alias: str, expected: str) -> None:
        """Common aliases should resolve to canonical names."""
        lexer = get_lexer(alias)
        assert lexer.name == expected

    def test_get_lexer_case_insensitive(self) -> None:
        """get_lexer() should be case-insensitive."""
        lexer1 = get_lexer("python")
        lexer2 = get_lexer("PYTHON")
        lexer3 = get_lexer("Python")
        assert lexer1.name == lexer2.name == lexer3.name == "python"

    def test_get_lexer_cached(self) -> None:
        """get_lexer() should return cached instances."""
        lexer1 = get_lexer("python")
        lexer2 = get_lexer("py")  # Alias
        # Should be same instance (cached)
        assert lexer1 is lexer2


class TestRegistryErrors:
    """Test error handling in registry."""

    def test_get_lexer_unknown_raises(self) -> None:
        """get_lexer() should raise LookupError for unknown languages."""
        with pytest.raises(BengalRenderingError) as exc_info:
            get_lexer("nonexistent-language-xyz")
        assert "Unknown language" in str(exc_info.value)
        assert "nonexistent-language-xyz" in str(exc_info.value)

    def test_get_lexer_empty_string_raises(self) -> None:
        """get_lexer() should raise error for empty string."""
        with pytest.raises(BengalRenderingError):
            get_lexer("")
