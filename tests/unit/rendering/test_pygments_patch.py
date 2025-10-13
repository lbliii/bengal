"""
Tests for PygmentsPatch - the performance optimization for Pygments lexer caching.

These tests verify that the patch can be safely applied, removed, and used
as a context manager without side effects.
"""

import pytest

from bengal.rendering.parsers.pygments_patch import PygmentsPatch


class TestPygmentsPatchApply:
    """Test applying the Pygments patch."""

    def test_patch_can_be_applied(self):
        """Test that patch can be applied successfully."""
        # Ensure we start clean
        PygmentsPatch.restore()

        result = PygmentsPatch.apply()

        try:
            assert result is True
            assert PygmentsPatch.is_patched() is True
        finally:
            PygmentsPatch.restore()

    def test_patch_is_idempotent(self):
        """Test that applying patch multiple times is safe."""
        # Ensure we start clean
        PygmentsPatch.restore()

        result1 = PygmentsPatch.apply()
        result2 = PygmentsPatch.apply()
        result3 = PygmentsPatch.apply()

        try:
            assert result1 is True  # First application succeeds
            assert result2 is False  # Already applied
            assert result3 is False  # Already applied
            assert PygmentsPatch.is_patched() is True
        finally:
            PygmentsPatch.restore()

    def test_patch_affects_codehilite_module(self):
        """Test that patch modifies the codehilite module."""
        PygmentsPatch.restore()  # Start clean

        try:
            from markdown.extensions import codehilite

            # Get original functions
            original_get_lexer = codehilite.get_lexer_by_name
            original_guess_lexer = codehilite.guess_lexer

            # Apply patch
            PygmentsPatch.apply()

            # Functions should be replaced
            assert codehilite.get_lexer_by_name != original_get_lexer
            assert codehilite.guess_lexer != original_guess_lexer

        except ImportError:
            pytest.skip("markdown.extensions.codehilite not available")
        finally:
            PygmentsPatch.restore()


class TestPygmentsPatchRestore:
    """Test restoring the original Pygments functions."""

    def test_patch_can_be_restored(self):
        """Test that patch can be cleanly removed."""
        PygmentsPatch.restore()  # Start clean

        PygmentsPatch.apply()
        assert PygmentsPatch.is_patched() is True

        result = PygmentsPatch.restore()

        assert result is True
        assert PygmentsPatch.is_patched() is False

    def test_restore_without_patch_is_safe(self):
        """Test that restoring when not patched is safe."""
        PygmentsPatch.restore()  # Ensure not patched

        result = PygmentsPatch.restore()

        assert result is False
        assert PygmentsPatch.is_patched() is False

    def test_restore_returns_original_functions(self):
        """Test that restore actually returns original functions."""
        PygmentsPatch.restore()  # Start clean

        try:
            from markdown.extensions import codehilite

            # Get originals
            original_get_lexer = codehilite.get_lexer_by_name
            original_guess_lexer = codehilite.guess_lexer

            # Apply and restore
            PygmentsPatch.apply()
            PygmentsPatch.restore()

            # Should be back to originals
            assert codehilite.get_lexer_by_name == original_get_lexer
            assert codehilite.guess_lexer == original_guess_lexer

        except ImportError:
            pytest.skip("markdown.extensions.codehilite not available")


class TestPygmentsPatchContextManager:
    """Test using PygmentsPatch as a context manager."""

    def test_context_manager_applies_patch(self):
        """Test that entering context applies patch."""
        PygmentsPatch.restore()  # Start clean

        with PygmentsPatch():
            assert PygmentsPatch.is_patched() is True

    def test_context_manager_removes_patch(self):
        """Test that exiting context removes patch."""
        PygmentsPatch.restore()  # Start clean

        with PygmentsPatch():
            assert PygmentsPatch.is_patched() is True

        # After exiting, patch should be removed
        assert PygmentsPatch.is_patched() is False

    def test_nested_context_managers(self):
        """Test that nested contexts work correctly."""
        PygmentsPatch.restore()  # Start clean

        with PygmentsPatch():
            assert PygmentsPatch.is_patched() is True

            with PygmentsPatch():
                assert PygmentsPatch.is_patched() is True

            # Inner context doesn't remove patch
            assert PygmentsPatch.is_patched() is True

        # Only outer context removes patch
        assert PygmentsPatch.is_patched() is False

    def test_context_manager_with_exception(self):
        """Test that patch is removed even if exception occurs."""
        PygmentsPatch.restore()  # Start clean

        try:
            with PygmentsPatch():
                assert PygmentsPatch.is_patched() is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Patch should be removed despite exception
        assert PygmentsPatch.is_patched() is False


class TestPygmentsPatchFunctionality:
    """Test that patched functions work correctly."""

    def test_patched_get_lexer_by_name_works(self):
        """Test that patched get_lexer_by_name returns lexers."""
        PygmentsPatch.restore()

        try:
            from markdown.extensions import codehilite

            with PygmentsPatch():
                # Should work with common languages
                lexer = codehilite.get_lexer_by_name("python")
                assert lexer is not None
                assert hasattr(lexer, "get_tokens")

        except ImportError:
            pytest.skip("markdown.extensions.codehilite not available")

    def test_patched_guess_lexer_works(self):
        """Test that patched guess_lexer returns lexers."""
        PygmentsPatch.restore()

        try:
            from markdown.extensions import codehilite

            with PygmentsPatch():
                # Should work with code samples
                lexer = codehilite.guess_lexer("print('hello')")
                assert lexer is not None
                assert hasattr(lexer, "get_tokens")

        except ImportError:
            pytest.skip("markdown.extensions.codehilite not available")

    def test_multiple_language_lookups(self):
        """Test looking up multiple languages."""
        PygmentsPatch.restore()

        try:
            from markdown.extensions import codehilite

            with PygmentsPatch():
                languages = ["python", "javascript", "html", "css"]

                for lang in languages:
                    lexer = codehilite.get_lexer_by_name(lang)
                    assert lexer is not None

        except ImportError:
            pytest.skip("markdown.extensions.codehilite not available")


class TestPygmentsPatchState:
    """Test patch state management."""

    def test_is_patched_returns_correct_state(self):
        """Test that is_patched accurately reflects state."""
        PygmentsPatch.restore()

        assert PygmentsPatch.is_patched() is False

        PygmentsPatch.apply()
        assert PygmentsPatch.is_patched() is True

        PygmentsPatch.restore()
        assert PygmentsPatch.is_patched() is False

    def test_state_persists_across_instances(self):
        """Test that patch state is class-level, not instance-level."""
        PygmentsPatch.restore()

        instance1 = PygmentsPatch()
        instance2 = PygmentsPatch()

        assert PygmentsPatch.is_patched() is False

        with instance1:
            assert PygmentsPatch.is_patched() is True
            # instance2 sees the same state
            assert instance2.is_patched() is True

        assert PygmentsPatch.is_patched() is False


class TestPygmentsPatchErrorHandling:
    """Test error handling in patch operations."""

    def test_missing_codehilite_is_handled_gracefully(self, monkeypatch):
        """Test that missing codehilite is handled without crashing."""
        PygmentsPatch.restore()

        # Mock the import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "markdown.extensions" in name or name == "markdown.extensions":
                raise ImportError("No module named 'markdown.extensions'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Should not raise, just return False
        result = PygmentsPatch.apply()
        assert result is False
        assert PygmentsPatch.is_patched() is False


class TestPygmentsPatchIntegration:
    """Integration tests with actual markdown parsing."""

    def test_patch_works_with_python_markdown_parser(self):
        """Test that patch works when used by PythonMarkdownParser."""
        PygmentsPatch.restore()

        try:
            from bengal.rendering.parsers import PythonMarkdownParser

            # Creating parser should apply patch
            parser = PythonMarkdownParser()
            assert PygmentsPatch.is_patched() is True

            # Parse some markdown with code blocks
            content = """
# Test Document

Here's some code:

```python
def hello():
    print("world")
```

And more text.
"""
            result = parser.parse(content, {})

            # Should work without errors
            assert "hello" in result
            assert "world" in result
            assert "<code" in result or "<pre" in result

        except ImportError:
            pytest.skip("PythonMarkdownParser dependencies not available")
        finally:
            PygmentsPatch.restore()

    def test_multiple_parsers_share_patch(self):
        """Test that multiple parser instances share the same patch."""
        PygmentsPatch.restore()

        try:
            from bengal.rendering.parsers import PythonMarkdownParser

            parser1 = PythonMarkdownParser()
            parser2 = PythonMarkdownParser()

            # Both should see the same patch state
            assert PygmentsPatch.is_patched() is True

            # Both should work
            result1 = parser1.parse("# Test 1\n\n```python\ncode1\n```", {})
            result2 = parser2.parse("# Test 2\n\n```python\ncode2\n```", {})

            assert "Test 1" in result1
            assert "Test 2" in result2

        except ImportError:
            pytest.skip("PythonMarkdownParser dependencies not available")
        finally:
            PygmentsPatch.restore()


class TestPygmentsPatchDocumentation:
    """Test that patch has proper documentation."""

    def test_class_has_docstring(self):
        """Test that PygmentsPatch class is documented."""
        assert PygmentsPatch.__doc__ is not None
        assert len(PygmentsPatch.__doc__) > 50

    def test_apply_method_has_docstring(self):
        """Test that apply method is documented."""
        assert PygmentsPatch.apply.__doc__ is not None

    def test_restore_method_has_docstring(self):
        """Test that restore method is documented."""
        assert PygmentsPatch.restore.__doc__ is not None

    def test_is_patched_method_has_docstring(self):
        """Test that is_patched method is documented."""
        assert PygmentsPatch.is_patched.__doc__ is not None
