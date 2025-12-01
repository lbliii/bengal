"""
Test page name slugification.
"""

import pytest

from bengal.cli.commands.new import slugify


class TestSlugify:
    """Test slugify() function."""

    @pytest.mark.parametrize(
        "input_text,expected_slug",
        [
            # Basic conversions
            ("My Page", "my-page"),
            ("Test Page", "test-page"),
            # Lowercase conversion
            ("UPPERCASE", "uppercase"),
            ("MiXeD CaSe", "mixed-case"),
            # Special character removal
            ("Hello, World!", "hello-world"),
            ("Test@#$%Page", "testpage"),
            ("C++ Programming", "c-programming"),
            # Multiple spaces collapsed
            ("Test   Multiple   Spaces", "test-multiple-spaces"),
            ("A  B  C", "a-b-c"),
            # Multiple hyphens collapsed
            ("Test--Page", "test-page"),
            ("A---B", "a-b"),
            # Edge hyphens stripped
            ("-test-", "test"),
            ("--test--", "test"),
            (" test ", "test"),
            # Empty/whitespace strings
            ("", ""),
            ("   ", ""),
            # Only special characters
            ("!!!", ""),
            ("@#$%", ""),
        ],
        ids=[
            "basic_my_page",
            "basic_test_page",
            "uppercase",
            "mixed_case",
            "hello_world",
            "special_chars",
            "cpp_programming",
            "multiple_spaces",
            "abc_spaces",
            "double_hyphen",
            "triple_hyphen",
            "leading_trailing_hyphen",
            "multiple_edge_hyphens",
            "space_trim",
            "empty_string",
            "whitespace_only",
            "exclamation_marks",
            "special_only",
        ],
    )
    def testslugify_transformations(self, input_text, expected_slug):
        """
        Test core slugification transformations.

        Ensures that:
        - Spaces convert to hyphens
        - Text is lowercased
        - Special characters are removed
        - Multiple separators are collapsed
        - Leading/trailing hyphens are stripped
        - Empty/invalid inputs handled gracefully
        """
        result = slugify(input_text)
        assert result == expected_slug, (
            f"slugify('{input_text}') should produce '{expected_slug}', " f"but got '{result}'"
        )

    def test_unicode_handling(self):
        """Test unicode character handling."""
        # Unicode word characters are preserved by \w in regex
        assert slugify("café") == "café"  # é is a word character
        # Numbers preserved
        assert slugify("test123") == "test123"

    def test_existing_hyphenated_slugs(self):
        """Test that proper slugs pass through unchanged."""
        assert slugify("my-page") == "my-page"
        assert slugify("test-slug") == "test-slug"

    def test_mixed_separators(self):
        """Test various separator combinations."""
        assert slugify("test_page-slug name") == "test_page-slug-name"
        # Underscores preserved (word characters)
        assert slugify("test_name") == "test_name"

    def test_numbers_preserved(self):
        """Test that numbers are kept."""
        assert slugify("Test 123") == "test-123"
        assert slugify("Page 2.0") == "page-20"

    @pytest.mark.parametrize(
        "page_name,expected_slug",
        [
            ("Getting Started", "getting-started"),
            ("API Reference", "api-reference"),
            ("Quick Start Guide", "quick-start-guide"),
            ("v1.2.3 Release Notes", "v123-release-notes"),
            ("Test - Page", "test-page"),
            ("A - B - C", "a-b-c"),
            ("2025 Goals", "2025-goals"),
            ("101 Tips", "101-tips"),
            ("Test (Draft)", "test-draft"),
            ("API [v2]", "api-v2"),
            ("Guide {Advanced}", "guide-advanced"),
        ],
        ids=[
            "getting_started",
            "api_reference",
            "quick_start_guide",
            "version_release_notes",
            "hyphen_space_test_page",
            "hyphen_space_abc",
            "numeric_start_2025",
            "numeric_start_101",
            "parentheses",
            "brackets",
            "braces",
        ],
    )
    def test_real_world_page_names(self, page_name, expected_slug):
        """
        Test realistic page names that users would create.

        These examples cover:
        - Common documentation page names
        - Version numbers and release notes
        - Mixed separator styles (hyphens with spaces)
        - Numeric prefixes
        - Parentheses, brackets, and braces

        Critical for ensuring good user experience when creating pages.
        """
        result = slugify(page_name)
        assert result == expected_slug, (
            f"Page name '{page_name}' should slugify to '{expected_slug}', " f"but got '{result}'"
        )

    def test_long_names(self):
        """Test long page names."""
        long_name = "This Is A Very Long Page Name With Many Words"
        result = slugify(long_name)
        assert result == "this-is-a-very-long-page-name-with-many-words"
        assert " " not in result
        assert result.islower()
