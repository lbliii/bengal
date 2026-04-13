"""Tests for directive warning system.

Verifies that unknown directive names and unknown option keys
produce warnings with fuzzy-match suggestions.
"""

from __future__ import annotations

import logging

from bengal.parsing.backends.patitas.directives.options import (
    AdmonitionOptions,
    StyledOptions,
)

# ---------------------------------------------------------------------------
# Unknown directive name warnings
# ---------------------------------------------------------------------------


class TestUnknownDirectiveWarnings:
    """Tests for warnings when an unregistered directive name is used."""

    def test_unknown_directive_includes_html_comment(self, parser):
        """Unknown directives should include an HTML comment marker in output."""
        result = parser.parse(":::{foobar}\ncontent\n:::", {})

        assert '<!-- bengal: unknown directive "foobar" -->' in result
        # Should still render as generic div (backwards compatible)
        assert 'class="directive directive-foobar"' in result

    def test_unknown_directive_preserves_content(self, parser):
        """Unknown directives should still render their content."""
        result = parser.parse(":::{foobar}\nHello world\n:::", {})

        assert "Hello world" in result
        assert 'class="directive directive-foobar"' in result

    def test_known_directive_no_html_comment(self, parser):
        """Registered directives should not have the unknown-directive HTML comment."""
        result = parser.parse(":::{note}\nThis is a note.\n:::", {})

        assert "<!-- bengal: unknown directive" not in result


# ---------------------------------------------------------------------------
# Unknown option key warnings
# ---------------------------------------------------------------------------


class TestUnknownOptionKeyWarnings:
    """Tests for warnings when unrecognized option keys are passed."""

    def test_unknown_option_emits_warning(self, caplog):
        """Unknown option keys should produce a warning log."""
        with caplog.at_level(logging.WARNING):
            AdmonitionOptions.from_raw({"clase": "custom"})

        assert "Unknown option" in caplog.text
        assert "clase" in caplog.text

    def test_unknown_option_suggests_close_match(self, caplog):
        """Typos close to a known field should include a suggestion."""
        with caplog.at_level(logging.WARNING):
            StyledOptions.from_raw({"clas": "my-class"})

        assert "class" in caplog.text

    def test_known_option_no_warning(self, caplog):
        """Known option keys should not produce warnings."""
        with caplog.at_level(logging.WARNING):
            AdmonitionOptions.from_raw({"collapsible": "true", "class": "custom"})

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        unknown_warnings = [m for m in warning_messages if "Unknown option" in str(m)]
        assert not unknown_warnings

    def test_alias_key_no_warning(self, caplog):
        """Alias keys (e.g., 'class' for 'class_') should not produce warnings."""
        with caplog.at_level(logging.WARNING):
            StyledOptions.from_raw({"class": "highlight"})

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        unknown_warnings = [m for m in warning_messages if "Unknown option" in str(m)]
        assert not unknown_warnings

    def test_multiple_unknown_options_warn_each(self, caplog):
        """Each unknown option should produce its own warning."""
        with caplog.at_level(logging.WARNING):
            AdmonitionOptions.from_raw({"foo": "1", "bar": "2"})

        assert "foo" in caplog.text
        assert "bar" in caplog.text
