"""
Unit tests for template engine utilities.

Tests the centralized helper functions for template operations.
"""

from unittest.mock import Mock

from bengal.rendering.engines.utils import safe_template_exists


class TestSafeTemplateExists:
    """Test safe_template_exists utility function."""

    def test_returns_false_when_engine_is_none(self):
        """Should return False when template_engine is None."""
        assert safe_template_exists(None, "any_template.html") is False

    def test_returns_true_when_template_exists(self):
        """Should return True when template exists."""
        engine = Mock()
        engine.template_exists = Mock(return_value=True)

        result = safe_template_exists(engine, "blog/home.html")

        assert result is True
        engine.template_exists.assert_called_once_with("blog/home.html")

    def test_returns_false_when_template_not_exists(self):
        """Should return False when template doesn't exist."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        result = safe_template_exists(engine, "nonexistent.html")

        assert result is False

    def test_delegates_to_protocol_method(self):
        """Should use the protocol's template_exists method."""
        engine = Mock()
        engine.template_exists = Mock(return_value=True)

        safe_template_exists(engine, "test.html")

        engine.template_exists.assert_called_once_with("test.html")

    def test_log_failures_disabled_by_default(self, caplog):
        """Should not log failures by default."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        safe_template_exists(engine, "missing.html")

        # No debug log should be generated
        assert "template_check_failed" not in caplog.text

    def test_log_failures_when_enabled(self):
        """Should log failures when log_failures=True without raising exceptions."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)
        type(engine).__name__ = "MockEngine"

        # Should not raise any exceptions even when logging
        result = safe_template_exists(engine, "missing.html", log_failures=True)

        # Verify the check was performed
        assert result is False
        engine.template_exists.assert_called_once_with("missing.html")

    def test_handles_various_template_names(self):
        """Should work with various template name formats."""
        engine = Mock()
        engine.template_exists = Mock(return_value=True)

        # Test various formats
        templates = [
            "simple.html",
            "blog/list.html",
            "autodoc/python/single.html",
            "nested/deep/path/template.html",
        ]

        for template in templates:
            result = safe_template_exists(engine, template)
            assert result is True
