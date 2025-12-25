"""
Tests for the TreeSitterBackend implementation.

These tests skip gracefully if tree-sitter or the required
language grammars are not available, or if running on free-threaded
Python (where tree-sitter would re-enable the GIL).
"""

from __future__ import annotations

import sysconfig

import pytest


def _is_free_threaded_python() -> bool:
    """Check if running on Python 3.13+ free-threaded build."""
    import sys

    # Check if this is a free-threaded build (Py_GIL_DISABLED=1)
    gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    if not gil_disabled:
        return False

    # Check if GIL is currently disabled (Python 3.13+)
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()

    # Free-threaded build but no runtime check available
    return True


def _tree_sitter_core_available() -> bool:
    """Check if tree-sitter core is installed and safe to import."""
    # Skip on free-threaded Python to avoid GIL re-enablement warning
    if _is_free_threaded_python():
        return False

    try:
        import tree_sitter  # noqa: F401

        return True
    except ImportError:
        return False


def _tree_sitter_python_available() -> bool:
    """Check if tree-sitter-python grammar is available and working."""
    try:
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        return backend.supports_language("python")
    except (ImportError, Exception):
        return False


@pytest.mark.skipif(
    not _tree_sitter_core_available(),
    reason="tree-sitter not installed",
)
class TestTreeSitterBackendBasics:
    """Test basic TreeSitterBackend functionality."""

    def test_name_property(self) -> None:
        """Backend name should be 'tree-sitter'."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        assert backend.name == "tree-sitter"

    def test_normalize_language_common_aliases(self) -> None:
        """Common language aliases should be normalized."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        normalize = TreeSitterBackend._normalize_language

        assert normalize("js") == "javascript"
        assert normalize("ts") == "typescript"
        assert normalize("py") == "python"
        assert normalize("rb") == "ruby"
        assert normalize("yml") == "yaml"
        assert normalize("sh") == "bash"
        assert normalize("shell") == "bash"
        assert normalize("c++") == "cpp"
        assert normalize("cxx") == "cpp"
        assert normalize("rs") == "rust"
        assert normalize("golang") == "go"

    def test_normalize_language_preserves_known(self) -> None:
        """Known languages should be preserved."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        normalize = TreeSitterBackend._normalize_language

        assert normalize("python") == "python"
        assert normalize("rust") == "rust"
        assert normalize("go") == "go"
        assert normalize("javascript") == "javascript"

    def test_normalize_language_lowercases(self) -> None:
        """Languages should be lowercased."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        normalize = TreeSitterBackend._normalize_language

        assert normalize("Python") == "python"
        assert normalize("RUST") == "rust"
        assert normalize("JavaScript") == "javascript"


@pytest.mark.skipif(
    not _tree_sitter_core_available(),
    reason="tree-sitter not installed",
)
class TestTreeSitterBackendCSSMapping:
    """Test CSS class mapping functionality."""

    def test_get_css_class_exact_match(self) -> None:
        """Exact capture names should map correctly."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        get_css = TreeSitterBackend._get_css_class

        assert get_css("keyword") == "k"
        assert get_css("function") == "nf"
        assert get_css("string") == "s"
        assert get_css("comment") == "c"

    def test_get_css_class_dotted_match(self) -> None:
        """Dotted capture names should map correctly."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        get_css = TreeSitterBackend._get_css_class

        assert get_css("keyword.control") == "k"
        assert get_css("function.method") == "fm"
        assert get_css("string.escape") == "se"
        assert get_css("comment.documentation") == "cs"

    def test_get_css_class_prefix_fallback(self) -> None:
        """Unknown dotted names should fall back to prefix."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        get_css = TreeSitterBackend._get_css_class

        # "keyword.control.unknown" should fall back to "keyword.control" then "keyword"
        assert get_css("keyword.control.unknown") == "k"
        assert get_css("function.unknown") == "nf"

    def test_get_css_class_unmapped_returns_empty(self) -> None:
        """Unmapped captures should return empty string."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        get_css = TreeSitterBackend._get_css_class

        # Completely unknown capture
        result = get_css("totally.unknown.capture.name")
        assert result == ""


@pytest.mark.skipif(
    not _tree_sitter_python_available(),
    reason="tree-sitter-python not available or not working",
)
class TestTreeSitterBackendPython:
    """Test TreeSitterBackend with Python language."""

    def test_supports_python(self) -> None:
        """Python should be supported when grammar is available."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        assert backend.supports_language("python")
        assert backend.supports_language("py")

    def test_highlight_python_simple(self) -> None:
        """Simple Python code should be highlighted."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = backend.highlight("def hello(): pass", "python")

        assert isinstance(result, str)
        assert "hello" in result
        # Should have some CSS classes
        assert "class=" in result or "<pre" in result

    def test_highlight_python_with_keywords(self) -> None:
        """Python keywords should get appropriate classes."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        code = """
def greet(name):
    if name:
        return f"Hello, {name}"
    return None
"""
        result = backend.highlight(code, "python")

        assert isinstance(result, str)
        # The code should be present
        assert "greet" in result
        assert "name" in result

    def test_highlight_python_with_linenos(self) -> None:
        """Line numbers should be added when requested."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", show_linenos=True)

        # Should have table structure for line numbers
        assert "table" in result.lower()

    def test_highlight_python_with_hl_lines(self) -> None:
        """Lines should be highlighted when requested."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", hl_lines=[2])

        # Should have hll class for highlighted line
        assert "hll" in result


@pytest.mark.skipif(
    not _tree_sitter_core_available(),
    reason="tree-sitter not installed",
)
class TestTreeSitterBackendFallback:
    """Test Pygments fallback behavior."""

    def test_unsupported_language_falls_back(self) -> None:
        """Unsupported languages should fall back to Pygments."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()

        # Use a language that definitely doesn't have a tree-sitter grammar
        result = backend.highlight("some code", "obscure-lang-xyz")

        # Should still produce output (via Pygments fallback)
        assert isinstance(result, str)
        assert "some code" in result or "some" in result

    def test_fallback_produces_valid_html(self) -> None:
        """Fallback should produce valid HTML."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()
        result = backend.highlight("print('hello')", "unknown-lang")

        # Should have proper HTML structure
        assert "<" in result
        assert ">" in result


@pytest.mark.skipif(
    not _tree_sitter_core_available(),
    reason="tree-sitter not installed",
)
class TestTreeSitterBackendThreadSafety:
    """Test thread safety of the backend."""

    def test_parser_is_thread_local(self) -> None:
        """Parser instances should be thread-local."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        backend = TreeSitterBackend()

        # Access the thread-local storage
        assert hasattr(backend, "_local")

    def test_language_cache_is_class_level(self) -> None:
        """Language cache should be shared across instances."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        # Language cache is class-level
        assert hasattr(TreeSitterBackend, "_languages")
        assert isinstance(TreeSitterBackend._languages, dict)

    def test_queries_cache_is_class_level(self) -> None:
        """Queries cache should be shared across instances."""
        from bengal.rendering.highlighting.tree_sitter import TreeSitterBackend

        # Queries cache is class-level
        assert hasattr(TreeSitterBackend, "_queries")
        assert isinstance(TreeSitterBackend._queries, dict)
