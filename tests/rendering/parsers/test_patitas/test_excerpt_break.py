"""Tests for the excerpt-break directive.

Verifies that :::{excerpt-break} controls excerpt extraction boundaries.
"""

from __future__ import annotations

import pytest

from bengal.parsing.backends.patitas.wrapper import PatitasParser


@pytest.fixture
def parser() -> PatitasParser:
    return PatitasParser()


class TestExcerptBreak:
    """Excerpt-break directive scopes excerpt extraction."""

    def test_excerpt_contains_only_content_above_break(self, parser: PatitasParser) -> None:
        """Content below excerpt-break is excluded from excerpt."""
        content = (
            "This is the summary.\n\n"
            ":::{excerpt-break}\n"
            ":::\n\n"
            "This is the rest of the post that should not appear in the excerpt."
        )
        _html, _toc, excerpt, _meta = parser.parse_with_toc(content, {})
        assert "summary" in excerpt
        assert "rest of the post" not in excerpt

    def test_no_break_uses_default_extraction(self, parser: PatitasParser) -> None:
        """Without excerpt-break, position-based extraction applies."""
        content = "First paragraph.\n\nSecond paragraph."
        _html, _toc, excerpt, _meta = parser.parse_with_toc(content, {})
        assert "First paragraph" in excerpt
        assert "Second paragraph" in excerpt

    def test_break_renders_nothing_in_html(self, parser: PatitasParser) -> None:
        """Excerpt-break produces no visible HTML output."""
        content = "Before.\n\n:::{excerpt-break}\n:::\n\nAfter."
        html, _toc, _excerpt, _meta = parser.parse_with_toc(content, {})
        assert "excerpt-break" not in html
        assert "Before" in html
        assert "After" in html

    def test_break_at_beginning_yields_empty_excerpt(self, parser: PatitasParser) -> None:
        """Excerpt-break at the top produces an empty excerpt."""
        content = ":::{excerpt-break}\n:::\n\nAll content is below the break."
        _html, _toc, excerpt, _meta = parser.parse_with_toc(content, {})
        assert excerpt == ""

    def test_break_with_multiple_paragraphs_above(self, parser: PatitasParser) -> None:
        """Multiple paragraphs above the break are all included."""
        content = (
            "First paragraph.\n\nSecond paragraph.\n\n:::{excerpt-break}\n:::\n\nThird paragraph."
        )
        _html, _toc, excerpt, _meta = parser.parse_with_toc(content, {})
        assert "First paragraph" in excerpt
        assert "Second paragraph" in excerpt
        assert "Third paragraph" not in excerpt

    def test_break_with_context_parsing(self, parser: PatitasParser) -> None:
        """Excerpt-break works through parse_with_toc_and_context path."""
        content = "Summary line.\n\n:::{excerpt-break}\n:::\n\nExtended content."
        context = {"config": {"content": {}}}
        _html, _toc, excerpt, _meta = parser.parse_with_toc_and_context(content, {}, context)
        assert "Summary" in excerpt
        assert "Extended" not in excerpt

    def test_break_ignores_max_chars(self, parser: PatitasParser) -> None:
        """When excerpt-break is present, excerpt_length config is ignored."""
        # Set a very short excerpt_length that would normally truncate
        content = (
            "This is a longer summary that exceeds ten characters easily.\n\n"
            ":::{excerpt-break}\n"
            ":::\n\n"
            "Below the fold."
        )
        metadata = {"_excerpt_length": 10}
        _html, _toc, excerpt, _meta = parser.parse_with_toc(content, metadata)
        # The full content above the break is included despite small excerpt_length
        assert "exceeds ten characters" in excerpt
        assert "Below the fold" not in excerpt
