"""
Tests for the highlighting backend registry.

Validates the registry functions: register_backend, get_highlighter,
list_backends, and highlight.
"""

from __future__ import annotations

import pytest

from bengal.errors import BengalConfigError
from bengal.rendering.highlighting import (
    get_highlighter,
    highlight,
    list_backends,
    register_backend,
)
from bengal.rendering.highlighting.pygments import PygmentsBackend


class TestRegistryFunctions:
    """Test the registry public API."""

    def test_pygments_backend_registered_by_default(self) -> None:
        """Pygments backend should be registered automatically."""
        backends = list_backends()
        assert "pygments" in backends

    def test_get_highlighter_default_is_pygments(self) -> None:
        """Default highlighter should be Pygments."""
        backend = get_highlighter()
        assert backend.name == "pygments"
        assert isinstance(backend, PygmentsBackend)

    def test_get_highlighter_by_name(self) -> None:
        """Should get backend by explicit name."""
        backend = get_highlighter("pygments")
        assert backend.name == "pygments"

    def test_get_highlighter_case_insensitive(self) -> None:
        """Backend names should be case-insensitive."""
        backend1 = get_highlighter("pygments")
        backend2 = get_highlighter("PYGMENTS")
        backend3 = get_highlighter("Pygments")

        assert backend1.name == backend2.name == backend3.name

    def test_get_highlighter_unknown_raises_error(self) -> None:
        """Unknown backend name should raise BengalConfigError."""
        with pytest.raises(BengalConfigError) as exc_info:
            get_highlighter("unknown-backend")

        assert "Unknown highlighting backend" in str(exc_info.value)
        assert "unknown-backend" in str(exc_info.value)

    def test_list_backends_returns_sorted_list(self) -> None:
        """list_backends() should return sorted list of names."""
        backends = list_backends()
        assert isinstance(backends, list)
        assert backends == sorted(backends)

    def test_highlight_function_uses_default_backend(self) -> None:
        """highlight() convenience function should work."""
        result = highlight("print('hello')", "python")

        assert isinstance(result, str)
        assert "hello" in result
        # Should have highlighting classes
        assert "highlight" in result.lower()

    def test_highlight_with_explicit_backend(self) -> None:
        """highlight() should accept backend parameter."""
        result = highlight("print('hello')", "python", backend="pygments")

        assert isinstance(result, str)
        assert "hello" in result


class TestRegisterBackend:
    """Test custom backend registration."""

    def test_register_custom_backend(self) -> None:
        """Should be able to register a custom backend."""

        class CustomBackend:
            @property
            def name(self) -> str:
                return "custom"

            def highlight(
                self,
                code: str,
                language: str,
                hl_lines: list[int] | None = None,
                show_linenos: bool = False,
            ) -> str:
                return f"<custom>{code}</custom>"

            def supports_language(self, language: str) -> bool:
                return True

        # Register the custom backend
        register_backend("custom", CustomBackend)

        # Should now be in the list
        assert "custom" in list_backends()

        # Should be retrievable
        backend = get_highlighter("custom")
        assert backend.name == "custom"

        # Should work via highlight()
        result = highlight("test", "python", backend="custom")
        assert "<custom>" in result

    def test_register_backend_requires_class(self) -> None:
        """register_backend() should require a class, not instance."""

        class ValidBackend:
            @property
            def name(self) -> str:
                return "valid"

            def highlight(self, code: str, language: str, **kwargs) -> str:
                return code

            def supports_language(self, language: str) -> bool:
                return True

        # Should work with class
        register_backend("valid", ValidBackend)

        # Should fail with instance
        with pytest.raises(TypeError):
            register_backend("invalid", ValidBackend())  # type: ignore


class TestAutoMode:
    """Test the 'auto' backend selection mode."""

    def test_auto_mode_falls_back_to_pygments(self) -> None:
        """'auto' mode should use pygments when tree-sitter unavailable."""
        backend = get_highlighter("auto")

        # Since tree-sitter is not installed, should fall back to pygments
        # (or use tree-sitter if it is installed)
        assert backend.name in ("pygments", "tree-sitter")

    def test_auto_mode_produces_valid_output(self) -> None:
        """'auto' mode should produce valid highlighted output."""
        result = highlight("print('hello')", "python", backend="auto")

        assert isinstance(result, str)
        assert "hello" in result
        assert "<" in result  # Should have HTML tags
