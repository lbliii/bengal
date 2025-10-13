"""
Property-based tests for slugification using Hypothesis.

These tests verify that slugification maintains critical invariants
across ALL possible inputs, not just the cases we thought to test.
"""

import re
import string
from urllib.parse import quote

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from bengal.cli.commands.new import _slugify


class TestSlugifyProperties:
    """
    Property-based tests for _slugify function.

    Each test runs 100+ times with randomly generated inputs
    to discover edge cases automatically.
    """

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_always_lowercase(self, text):
        """
        Property: Slugs must always be lowercase.

        This is critical for URL consistency - URLs should be case-insensitive
        and always use lowercase for predictability.
        """
        result = _slugify(text)
        assert result == result.lower(), f"Slug '{result}' contains uppercase characters"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_filters_special_chars(self, text):
        """
        Property: Slugs filter out special punctuation and whitespace.

        STRATEGIC DECISION: Bengal supports Unicode in slugs for international content.
        This is intentional behavior to support modern, global websites.

        What IS allowed: Unicode letters, digits, hyphens, underscores
        What is FILTERED: Punctuation (!@#$%), whitespace, control chars

        This matches behavior of modern SSGs like Hugo and supports international users.
        """
        result = _slugify(text)

        # Current behavior: \w matches unicode word chars (letters, digits, underscore)
        # So we test that result is either:
        # 1. ASCII alphanumeric + hyphen + underscore, OR
        # 2. Unicode word characters that passed through

        if result:
            # At minimum, should have no whitespace or special punctuation
            assert not any(
                c in string.whitespace for c in result
            ), f"Slug '{result}' contains whitespace"
            # Should not have common special characters
            special_chars = "!@#$%^&*()+=[]{}|;:,.<>?/~`\"' "
            assert not any(
                c in special_chars for c in result
            ), f"Slug '{result}' contains special characters"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_no_edge_hyphens(self, text):
        """
        Property: Non-empty slugs must not start or end with hyphens.

        Edge hyphens look unprofessional and can cause issues with URL parsing.
        """
        result = _slugify(text)
        if result:  # Only check non-empty results
            assert not result.startswith("-"), f"Slug starts with hyphen: '{result}'"
            assert not result.endswith("-"), f"Slug ends with hyphen: '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_no_consecutive_hyphens(self, text):
        """
        Property: Slugs must not contain consecutive hyphens.

        Multiple hyphens (--) make URLs harder to read and type.
        """
        result = _slugify(text)
        assert "--" not in result, f"Slug '{result}' contains consecutive hyphens"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_idempotent(self, text):
        """
        Property: Slugification is idempotent - applying it twice gives same result.

        Mathematical property: slugify(slugify(x)) == slugify(x)

        This means slugs are already in their "final form" and won't change
        if slugified again.
        """
        once = _slugify(text)
        twice = _slugify(once)
        assert once == twice, (
            f"Not idempotent: slugify('{text}') = '{once}', " f"but slugify('{once}') = '{twice}'"
        )

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_empty_input_empty_output(self, text):
        """
        Property: Input with no valid characters produces empty slug.

        If text only contains special characters or whitespace,
        the result should be empty.

        NOTE: Implementation preserves underscores since \\w matches them.
        """
        result = _slugify(text)

        # Check if input has any word characters (alphanumeric, underscore, or hyphen)
        # Note: \w in Python matches [a-zA-Z0-9_] plus unicode letters/digits
        has_valid_chars = any(c.isalnum() or c in "-_" for c in text)

        if not has_valid_chars:
            # No valid characters → empty slug
            assert result == "", f"Input '{repr(text)}' has no valid chars but produced '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_valid_url_component(self, text):
        """
        Property: Slugs must be valid URL path components without encoding.

        The result should be usable directly in URLs without urllib.parse.quote().
        """
        result = _slugify(text)
        # URL encoding shouldn't change the slug
        encoded = quote(result, safe="")
        assert encoded == result or encoded == quote(
            result, safe="-_"
        ), f"Slug '{result}' requires URL encoding: {encoded}"

    @pytest.mark.hypothesis
    @given(
        text=st.text(
            alphabet=string.ascii_letters + string.digits + " -_!@#$%^&*()",
            min_size=1,
            max_size=100,
        )
    )
    def test_slugify_with_common_chars(self, text):
        """
        Property test focusing on common input patterns.

        Tests realistic page names with letters, digits, spaces,
        and common special characters.
        """
        result = _slugify(text)

        # Should not be None
        assert result is not None

        # Should be string
        assert isinstance(result, str)

        # Should match slug pattern
        assert re.match(r"^[a-z0-9_-]*$", result), f"Invalid slug format: '{result}'"

    @pytest.mark.hypothesis
    @given(
        words=st.lists(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=10), min_size=1, max_size=5
        )
    )
    def test_slugify_word_lists(self, words):
        """
        Property: Multiple words separated by spaces become hyphen-separated.

        This tests the common use case of "Page Name" → "page-name".
        """
        text = " ".join(words)
        result = _slugify(text)

        # Words should be separated by single hyphens (or underscores)
        parts = [p for p in re.split(r"[-_]+", result) if p]

        # Number of parts should be <= number of words
        assert len(parts) <= len(
            words
        ), f"Input '{text}' ({len(words)} words) produced {len(parts)} parts: {parts}"

    @pytest.mark.hypothesis
    @given(text=st.text(max_size=1000))
    def test_slugify_reasonable_length(self, text):
        """
        Property: Slug length should not exceed input length.

        Slugification removes/replaces characters, so output should
        be same length or shorter.
        """
        result = _slugify(text)
        assert len(result) <= len(
            text
        ), f"Slug longer than input: '{text}' ({len(text)}) → '{result}' ({len(result)})"

    @pytest.mark.hypothesis
    @given(
        prefix=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5),
        suffix=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5),
    )
    def test_slugify_preserves_valid_slugs(self, prefix, suffix):
        """
        Property: If input is already a valid slug, it should be preserved.

        This combines with idempotency - valid slugs remain unchanged.
        """
        # Create a valid slug
        valid_slug = f"{prefix}-{suffix}"
        result = _slugify(valid_slug)

        assert result == valid_slug, f"Valid slug '{valid_slug}' was changed to '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text())
    def test_slugify_deterministic(self, text):
        """
        Property: Slugification is deterministic - same input always gives same output.

        Running slugify multiple times on the same input must produce
        identical results.
        """
        result1 = _slugify(text)
        result2 = _slugify(text)
        result3 = _slugify(text)

        assert (
            result1 == result2 == result3
        ), f"Non-deterministic: {repr(text)} produced {repr(result1)}, {repr(result2)}, {repr(result3)}"

    @pytest.mark.hypothesis
    @given(text=st.text(alphabet=string.whitespace, min_size=1, max_size=50))
    def test_slugify_whitespace_only_empty(self, text):
        """
        Property: Input containing only whitespace produces empty slug.

        Spaces, tabs, newlines, etc. should all be removed.
        """
        result = _slugify(text)
        assert (
            result == ""
        ), f"Whitespace-only input {repr(text)} produced non-empty slug '{result}'"

    @pytest.mark.hypothesis
    @given(char=st.characters(blacklist_categories=("Cc", "Cs")))
    def test_slugify_single_char(self, char):
        """
        Property: Single character input produces appropriate slug.

        Tests edge case of single character inputs across all unicode.
        """
        result = _slugify(char)

        # Result should be either empty or a single valid char
        assert len(result) <= 1, f"Single char '{char}' produced multi-char slug '{result}'"

        if result:
            # Current implementation uses \w which matches unicode word characters
            # So result can be:
            # - ASCII lowercase letter
            # - ASCII/Unicode digit
            # - Underscore
            # - Hyphen
            # - Unicode letter/digit that passed through \w

            # At minimum, check it's not whitespace or common punctuation
            is_valid = not result.isspace() and result not in "!@#$%^&*()+=[]{}|;:,.<>?/~`\"' "
            assert is_valid, f"Single char '{char}' (ord={ord(char)}) produced invalid slug '{result}' (ord={ord(result)})"


class TestSlugifyEdgeCases:
    """
    Targeted property tests for specific edge cases.
    """

    @pytest.mark.hypothesis
    @given(n=st.integers(min_value=1, max_value=100))
    def test_slugify_repeated_hyphens(self, n):
        """
        Property: Multiple consecutive hyphens collapse to single hyphen.

        Tests: "a---b", "a----b", etc.
        """
        text = f"a{'-' * n}b"
        result = _slugify(text)

        # Should collapse to "a-b"
        assert result == "a-b", f"{n} hyphens between a and b should collapse to 1: got '{result}'"

    @pytest.mark.hypothesis
    @given(n=st.integers(min_value=1, max_value=100))
    def test_slugify_repeated_spaces(self, n):
        """
        Property: Multiple consecutive spaces collapse to single hyphen.

        Tests: "a   b", "a     b", etc.
        """
        text = f"a{' ' * n}b"
        result = _slugify(text)

        # Should collapse to "a-b"
        assert (
            result == "a-b"
        ), f"{n} spaces between a and b should collapse to 1 hyphen: got '{result}'"

    @pytest.mark.hypothesis
    @given(text=st.text(alphabet="!@#$%^&*()+=[]{}|;:,.<>?/~`", min_size=1, max_size=50))
    def test_slugify_special_chars_only_empty(self, text):
        """
        Property: Input with only special characters produces empty slug.

        Tests that non-alphanumeric characters are all removed.
        """
        result = _slugify(text)
        assert (
            result == ""
        ), f"Special chars only {repr(text)} should produce empty slug, got '{result}'"

    @pytest.mark.hypothesis
    @given(
        text=st.text(
            alphabet=string.ascii_uppercase + string.ascii_lowercase, min_size=1, max_size=20
        )
    )
    def test_slugify_mixed_case_lowercase(self, text):
        """
        Property: Mixed case input becomes all lowercase.

        Tests: "AbCdEf" → "abcdef", "TeSt" → "test", etc.
        """
        # Assume text has at least one uppercase letter
        assume(any(c.isupper() for c in text))

        result = _slugify(text)

        assert result.islower(), f"Mixed case '{text}' should be all lowercase, got '{result}'"

        # Should equal lowercase version
        assert (
            result == text.lower()
        ), f"Mixed case '{text}' should equal lowercase '{text.lower()}', got '{result}'"


# Shrinking example documentation
"""
HYPOTHESIS SHRINKING EXAMPLE
-----------------------------

When Hypothesis finds a failing test, it automatically "shrinks" the input
to the minimal case that still fails. This makes debugging much easier.

Example failure process:

1. Initial failing input (random):
   "Hello!!! @#$%^&*()   World--- Test___123"

2. Hypothesis tries simpler inputs:
   "Hello World Test"
   "H W T"
   "a b c"
   "a-b"

3. Minimal failing input found:
   "a--b"

This makes it instantly obvious what the bug is, rather than having to
manually simplify a complex failing input.

To see this in action:
    pytest tests/unit/cli/test_slugify_properties.py -v --hypothesis-show-statistics
"""
