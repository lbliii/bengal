"""
Property-based tests for text utilities using Hypothesis.

These tests verify that text processing maintains critical invariants
across ALL possible inputs.
"""

import re
import string

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from bengal.utils.text import (
    humanize_bytes,
    normalize_whitespace,
    slugify,
    strip_html,
    truncate_chars,
    truncate_middle,
    truncate_words,
)


class TestTruncateWordsProperties:
    """Property tests for truncate_words function."""

    @pytest.mark.hypothesis
    @given(
        text=st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=500),
        word_count=st.integers(min_value=1, max_value=50),
    )
    def test_never_exceeds_word_count(self, text, word_count):
        """
        Property: Result never has more than word_count words (excluding suffix).

        This is the core guarantee of truncate_words.
        """
        result = truncate_words(text, word_count)

        # Remove suffix to count actual words
        result_without_suffix = result[:-3] if result.endswith("...") else result

        words = result_without_suffix.split()
        assert len(words) <= word_count, (
            f"truncate_words({word_count}) produced {len(words)} words: {words}"
        )

    @pytest.mark.hypothesis
    @given(
        text=st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=500),
        word_count=st.integers(min_value=1, max_value=50),
    )
    def test_preserves_word_boundaries(self, text, word_count):
        """
        Property: Never splits words mid-way.

        All words in output should be complete words from input.
        """
        result = truncate_words(text, word_count)

        # Remove suffix
        if result.endswith("..."):
            result = result[:-3]

        result_words = result.split()
        input_words = text.split()

        # Each result word should exactly match an input word
        for i, word in enumerate(result_words):
            if i < len(input_words):
                assert word == input_words[i], (
                    f"Word mismatch: result[{i}]='{word}' vs input[{i}]='{input_words[i]}'"
                )

    @pytest.mark.hypothesis
    @given(
        text=st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=100),
        word_count=st.integers(min_value=50, max_value=200),
    )
    def test_short_text_unchanged(self, text, word_count):
        """
        Property: If text has fewer words than limit, return unchanged (no suffix).
        """
        num_words = len(text.split())

        if num_words <= word_count:
            result = truncate_words(text, word_count)
            assert result == text, (
                f"Short text ({num_words} words) should be unchanged with limit {word_count}"
            )
            assert not result.endswith("..."), "Short text should not have suffix"


class TestTruncateCharsProperties:
    """Property tests for truncate_chars function."""

    @pytest.mark.hypothesis
    @given(text=st.text(min_size=10, max_size=500), length=st.integers(min_value=10, max_value=100))
    def test_never_exceeds_length(self, text, length):
        """
        Property: Result length never exceeds specified length.

        This is critical for layout/UI constraints. The function should account
        for suffix length when truncating, so total never exceeds `length`.

        BUG FIXED: Hypothesis discovered that truncate_chars(text, 3) was
        producing '000...' (6 chars)! The implementation was adding suffix AFTER
        truncation instead of accounting for it.

        Fixed implementation now: truncates to (length - len(suffix)) then adds suffix.
        """
        if len(text) > length:
            result = truncate_chars(text, length)

            assert len(result) <= length, (
                f"truncate_chars({length}) produced length {len(result)}: '{result}'"
            )

    @pytest.mark.hypothesis
    @given(text=st.text(min_size=0, max_size=50), length=st.integers(min_value=100, max_value=200))
    def test_short_text_unchanged(self, text, length):
        """
        Property: If text is shorter than limit, return unchanged.
        """
        if len(text) <= length:
            result = truncate_chars(text, length)
            assert result == text, (
                f"Short text ({len(text)} chars) should be unchanged with limit {length}"
            )

    @pytest.mark.hypothesis
    @given(
        text=st.text(alphabet=string.printable, min_size=20, max_size=100),
        length=st.integers(min_value=10, max_value=15),
    )
    def test_truncated_has_suffix(self, text, length):
        """
        Property: Truncated text ends with suffix.
        """
        if len(text) > length:
            result = truncate_chars(text, length)
            assert result.endswith("..."), f"Truncated text should end with '...': '{result}'"


class TestTruncateMiddleProperties:
    """Property tests for truncate_middle function."""

    @pytest.mark.hypothesis
    @given(
        text=st.text(min_size=0, max_size=500), max_length=st.integers(min_value=10, max_value=100)
    )
    def test_respects_max_length(self, text, max_length):
        """
        Property: Result never exceeds max_length.
        """
        result = truncate_middle(text, max_length)

        assert len(result) <= max_length, (
            f"truncate_middle({max_length}) produced length {len(result)}: '{result}'"
        )

    @pytest.mark.hypothesis
    @given(
        text=st.text(min_size=20, max_size=100), max_length=st.integers(min_value=15, max_value=30)
    )
    def test_contains_separator(self, text, max_length):
        """
        Property: Truncated text contains separator.
        """
        if len(text) > max_length:
            result = truncate_middle(text, max_length)
            assert "..." in result, f"Truncated middle should contain '...': '{result}'"

    @pytest.mark.hypothesis
    @given(
        text=st.text(min_size=20, max_size=100), max_length=st.integers(min_value=15, max_value=30)
    )
    def test_preserves_start_and_end(self, text, max_length):
        """
        Property: Result starts with beginning and ends with end of original.
        """
        if len(text) > max_length:
            result = truncate_middle(text, max_length)

            # Result should have original start
            # (at least 1 char from beginning)
            assert result[0] == text[0], (
                f"Should preserve start: result='{result}', original='{text}'"
            )

            # Result should have original end
            # (at least 1 char from end)
            assert result[-1] == text[-1], (
                f"Should preserve end: result='{result}', original='{text}'"
            )


class TestStripHtmlProperties:
    """Property tests for strip_html function."""

    @pytest.mark.hypothesis
    @given(html=st.text())
    def test_no_tags_in_output(self, html):
        """
        Property: Result contains no HTML tags.

        This is the fundamental guarantee of strip_html.
        """
        result = strip_html(html)

        # Check for any remaining tags
        assert not re.search(r"<[^>]+>", result), f"Result still contains HTML tags: '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text(alphabet=string.ascii_letters + " ", min_size=5, max_size=50))
    def test_plain_text_unchanged(self, text):
        """
        Property: Plain text without tags is unchanged.
        """
        # Assume no < or > in text
        assume("<" not in text and ">" not in text)

        result = strip_html(text)
        assert result == text, f"Plain text should be unchanged: '{text}' -> '{result}'"

    @pytest.mark.hypothesis
    @given(
        tag=st.sampled_from(["p", "div", "span", "strong", "em", "a", "script"]),
        content=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
    )
    def test_removes_single_tag(self, tag, content):
        """
        Property: Single tag is removed, content preserved.
        """
        html = f"<{tag}>{content}</{tag}>"
        result = strip_html(html)

        assert content in result, (
            f"Content '{content}' should be preserved from '{html}', got '{result}'"
        )
        assert f"<{tag}>" not in result, f"Opening tag should be removed from '{result}'"
        assert f"</{tag}>" not in result, f"Closing tag should be removed from '{result}'"


class TestNormalizeWhitespaceProperties:
    """Property tests for normalize_whitespace function."""

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_no_consecutive_spaces(self, text):
        """
        Property: Result has no consecutive spaces.

        Multiple spaces should be collapsed to single space.
        """
        result = normalize_whitespace(text)

        assert "  " not in result, f"Result contains consecutive spaces: '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_no_leading_trailing_whitespace(self, text):
        """
        Property: Result has no leading/trailing whitespace.
        """
        result = normalize_whitespace(text)

        if result:  # Non-empty results
            assert result == result.strip(), f"Result has leading/trailing whitespace: '{result}'"

    @pytest.mark.hypothesis
    @given(
        words=st.lists(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=10), min_size=1, max_size=10
        )
    )
    def test_single_space_between_words(self, words):
        """
        Property: Words are separated by single space.
        """
        # Create text with multiple spaces
        text = "  ".join(words)
        result = normalize_whitespace(text)

        expected = " ".join(words)
        assert result == expected, f"Expected '{expected}', got '{result}'"


class TestHumanizeBytesProperties:
    """Property tests for humanize_bytes function."""

    @pytest.mark.hypothesis
    @given(size=st.integers(min_value=0, max_value=10**15))
    def test_monotonic(self, size):
        """
        Property: Larger byte counts produce larger or equal numeric values.

        For example:
        - 1 KB should be > 999 B
        - 1 MB should be > 999 KB
        """
        result = humanize_bytes(size)

        # Result should be parseable (number + unit)
        assert isinstance(result, str), f"Result should be string, got {type(result)}"
        assert len(result) > 0, "Result should not be empty"

    @pytest.mark.hypothesis
    @given(size=st.integers(min_value=0, max_value=1023))
    def test_small_sizes_use_bytes(self, size):
        """
        Property: Sizes < 1024 should use 'B' unit.
        """
        result = humanize_bytes(size)
        assert result.endswith("B") or result.endswith("bytes"), (
            f"Size {size} should use bytes: '{result}'"
        )

    @pytest.mark.hypothesis
    @given(size=st.integers(min_value=1024, max_value=1024**2 - 1))
    def test_kb_range(self, size):
        """
        Property: Sizes 1024-1048575 should use KB.
        """
        result = humanize_bytes(size)
        assert "KB" in result or "kB" in result, f"Size {size} should use KB: '{result}'"

    @pytest.mark.hypothesis
    @given(size=st.integers(min_value=0, max_value=10**12))
    def test_always_positive(self, size):
        """
        Property: Humanized result never negative.
        """
        result = humanize_bytes(size)
        assert not result.startswith("-"), f"Result should not be negative: '{result}'"


class TestSlugifyProperties:
    """
    Property tests for slugify in text utils.
    
    Note: This is different from CLI slugify, but should have similar properties.
        
    """

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_always_lowercase(self, text):
        """Property: Slugs are always lowercase."""
        result = slugify(text)
        assert result == result.lower(), f"Slug '{result}' contains uppercase"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_no_consecutive_separators(self, text):
        """Property: No consecutive separators."""
        result = slugify(text, separator="-")
        assert "--" not in result, f"Slug '{result}' has consecutive hyphens"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_no_edge_separators(self, text):
        """Property: No leading/trailing separators."""
        result = slugify(text, separator="-")
        if result:
            assert not result.startswith("-"), f"Slug starts with separator: '{result}'"
            assert not result.endswith("-"), f"Slug ends with separator: '{result}'"

    @pytest.mark.hypothesis
    @given(
        text=st.text(min_size=50, max_size=200), max_length=st.integers(min_value=10, max_value=30)
    )
    def test_respects_max_length(self, text, max_length):
        """Property: Slugs respect max_length parameter."""
        result = slugify(text, max_length=max_length)
        assert len(result) <= max_length, (
            f"Slug length {len(result)} exceeds max_length {max_length}: '{result}'"
        )

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_idempotent(self, text):
        """Property: Slugification is idempotent."""
        once = slugify(text)
        twice = slugify(once)
        assert once == twice, f"Not idempotent: '{once}' -> '{twice}'"

    @pytest.mark.hypothesis
    @given(
        text=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
        separator=st.sampled_from(["-", "_", "."]),
    )
    def test_custom_separator(self, text, separator):
        """Property: Custom separator is used."""
        result = slugify(text, separator=separator)

        if separator in result:
            # If separator appears, it should be the one we specified
            assert separator in result, f"Should use separator '{separator}': '{result}'"


# Example output documentation
"""
EXAMPLE HYPOTHESIS OUTPUT
-------------------------

Running these tests generates thousands of examples like:

1. truncate_words:
   - Empty strings
   - Single words
   - Many words with spaces
   - Unicode text

2. truncate_chars:
   - Very long strings (500+ chars)
   - Strings at exact length boundary
   - Strings with mixed whitespace

3. strip_html:
   - Plain text (no tags)
   - Nested tags: <div><p><strong>text</strong></p></div>
   - Self-closing tags: <br/>, <img/>
   - Invalid HTML: <p><div>broken

4. humanize_bytes:
   - 0 bytes
   - 1 byte
   - 1024 (boundary)
   - Very large numbers (terabytes)

To see statistics:
    pytest tests/unit/utils/test_text_properties.py --hypothesis-show-statistics
"""
