"""
Unit tests for content type template utilities.

Tests the template cascade resolution logic.
"""

from unittest.mock import Mock

from bengal.content_types.templates import resolve_template_cascade


class TestResolveTemplateCascade:
    """Test resolve_template_cascade utility function."""

    def test_returns_fallback_when_engine_is_none(self):
        """Should return fallback when template_engine is None."""
        result = resolve_template_cascade(
            ["blog/home.html", "home.html"],
            None,
            fallback="index.html",
        )

        assert result == "index.html"

    def test_returns_first_existing_template(self):
        """Should return the first template that exists."""
        engine = Mock()
        # First doesn't exist, second does
        engine.template_exists = Mock(side_effect=[False, True, False])

        result = resolve_template_cascade(
            ["blog/home.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        assert result == "home.html"

    def test_returns_fallback_when_no_template_exists(self):
        """Should return fallback when no candidates exist."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        result = resolve_template_cascade(
            ["blog/home.html", "home.html"],
            engine,
            fallback="single.html",
        )

        assert result == "single.html"

    def test_checks_candidates_in_order(self):
        """Should check candidates in the provided order."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        resolve_template_cascade(
            ["first.html", "second.html", "third.html"],
            engine,
            fallback="default.html",
        )

        # Verify call order
        calls = engine.template_exists.call_args_list
        assert calls[0][0][0] == "first.html"
        assert calls[1][0][0] == "second.html"
        assert calls[2][0][0] == "third.html"

    def test_stops_at_first_match(self):
        """Should stop checking once a match is found."""
        engine = Mock()
        # First template exists
        engine.template_exists = Mock(side_effect=[True, True, True])

        resolve_template_cascade(
            ["blog/home.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        # Should only call once since first one matches
        assert engine.template_exists.call_count == 1

    def test_with_empty_candidates_list(self):
        """Should return fallback when candidates list is empty."""
        engine = Mock()
        engine.template_exists = Mock(return_value=True)

        result = resolve_template_cascade(
            [],
            engine,
            fallback="default.html",
        )

        assert result == "default.html"
        engine.template_exists.assert_not_called()

    def test_default_fallback_is_single_html(self):
        """Should use 'single.html' as default fallback."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        result = resolve_template_cascade(
            ["nonexistent.html"],
            engine,
        )

        assert result == "single.html"

    def test_with_typical_blog_cascade(self):
        """Test with typical blog template cascade."""
        engine = Mock()
        # Only index.html exists
        engine.template_exists = Mock(side_effect=[False, False, False, True])

        result = resolve_template_cascade(
            ["blog/home.html", "blog/index.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        assert result == "index.html"

    def test_with_typical_docs_cascade(self):
        """Test with typical docs template cascade."""
        engine = Mock()
        # doc/list.html exists
        engine.template_exists = Mock(side_effect=[False, True])

        result = resolve_template_cascade(
            ["doc/home.html", "doc/list.html"],
            engine,
            fallback="doc/list.html",
        )

        assert result == "doc/list.html"
