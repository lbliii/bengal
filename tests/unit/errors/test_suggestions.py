"""
Unit tests for error suggestions module.

Tests the suggestion registry, lookup functions, and search functionality.

See Also:
- bengal/errors/suggestions.py
"""

from __future__ import annotations

import pytest

from bengal.errors.suggestions import (
    ActionableSuggestion,
    enhance_error_context,
    format_suggestion,
    format_suggestion_full,
    get_all_suggestions_for_category,
    get_attribute_error_suggestion,
    get_suggestion,
    get_suggestion_dict,
    search_suggestions,
)


class TestGetSuggestion:
    """Tests for get_suggestion function."""

    def test_valid_category_and_key(self) -> None:
        """Returns suggestion for valid category and key."""
        suggestion = get_suggestion("template", "not_found")
        assert suggestion is not None
        assert isinstance(suggestion, ActionableSuggestion)
        assert suggestion.fix
        assert suggestion.explanation

    def test_invalid_category(self) -> None:
        """Returns None for invalid category."""
        assert get_suggestion("nonexistent_category", "some_key") is None

    def test_invalid_key(self) -> None:
        """Returns None for invalid key in valid category."""
        assert get_suggestion("template", "nonexistent_key") is None

    def test_suggestion_has_all_fields(self) -> None:
        """Suggestions have expected fields populated."""
        suggestion = get_suggestion("directive", "since_empty")
        assert suggestion is not None
        assert suggestion.fix
        assert suggestion.explanation
        assert suggestion.docs_url
        assert suggestion.before_snippet
        assert suggestion.after_snippet
        assert suggestion.check_files
        assert suggestion.related_codes


class TestGetSuggestionDict:
    """Tests for get_suggestion_dict function."""

    def test_returns_dict_with_fix_and_explanation(self) -> None:
        """Returns dict with at least fix and explanation."""
        result = get_suggestion_dict("template", "not_found")
        assert result is not None
        assert "fix" in result
        assert "explanation" in result

    def test_includes_docs_url_when_available(self) -> None:
        """Includes docs_url in dict when suggestion has one."""
        result = get_suggestion_dict("directive", "since_empty")
        assert result is not None
        assert "docs_url" in result

    def test_invalid_lookup_returns_none(self) -> None:
        """Returns None for invalid category/key."""
        assert get_suggestion_dict("fake", "fake") is None


class TestSearchSuggestions:
    """Tests for search_suggestions function."""

    def test_search_returns_matching_suggestions(self) -> None:
        """Search finds suggestions matching query."""
        results = search_suggestions("template")
        assert len(results) > 0
        # Results are (category, key, suggestion) tuples
        for category, key, suggestion in results:
            assert isinstance(category, str)
            assert isinstance(key, str)
            assert isinstance(suggestion, ActionableSuggestion)

    def test_search_is_case_insensitive(self) -> None:
        """Search is case insensitive."""
        results_lower = search_suggestions("yaml")
        results_upper = search_suggestions("YAML")
        results_mixed = search_suggestions("YaML")

        # All should find the same results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty string search returns empty list, not all suggestions."""
        results = search_suggestions("")
        assert results == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Whitespace-only search returns empty list."""
        assert search_suggestions("   ") == []
        assert search_suggestions("\t\n") == []

    def test_no_matches_returns_empty_list(self) -> None:
        """Search with no matches returns empty list."""
        results = search_suggestions("xyznonexistent123456")
        assert results == []

    def test_search_checks_fix_and_explanation(self) -> None:
        """Search looks in fix and explanation fields."""
        # "Jinja2" appears in template suggestions
        results = search_suggestions("jinja2")
        assert len(results) > 0

    def test_search_checks_grep_patterns(self) -> None:
        """Search also checks grep_patterns field."""
        # "VersionDirective" is in grep_patterns for directive suggestions
        results = search_suggestions("VersionDirective")
        assert len(results) > 0


class TestGetAttributeErrorSuggestion:
    """Tests for get_attribute_error_suggestion function."""

    def test_page_url_migration(self) -> None:
        """Suggests .href for 'has no attribute url' errors."""
        result = get_attribute_error_suggestion("'Page' object has no attribute 'url'")
        assert result is not None
        assert ".href" in result

    def test_page_relative_url_migration(self) -> None:
        """Suggests ._path for 'has no attribute relative_url' errors."""
        result = get_attribute_error_suggestion(
            "'Page' object has no attribute 'relative_url'"
        )
        assert result is not None
        assert "._path" in result

    def test_page_site_path_migration(self) -> None:
        """Suggests ._path for 'has no attribute site_path' errors."""
        result = get_attribute_error_suggestion(
            "'Page' object has no attribute 'site_path'"
        )
        assert result is not None
        assert "._path" in result

    def test_page_permalink_migration(self) -> None:
        """Suggests .href for 'has no attribute permalink' errors."""
        result = get_attribute_error_suggestion(
            "'Page' object has no attribute 'permalink'"
        )
        assert result is not None
        assert ".href" in result

    def test_unrecognized_attribute_returns_none(self) -> None:
        """Returns None for unrecognized attribute errors."""
        result = get_attribute_error_suggestion(
            "'SomeObject' object has no attribute 'xyz'"
        )
        assert result is None


class TestGetAllSuggestionsForCategory:
    """Tests for get_all_suggestions_for_category function."""

    def test_returns_dict_of_suggestions(self) -> None:
        """Returns dict mapping keys to suggestions."""
        suggestions = get_all_suggestions_for_category("template")
        assert isinstance(suggestions, dict)
        assert len(suggestions) > 0
        for key, suggestion in suggestions.items():
            assert isinstance(key, str)
            assert isinstance(suggestion, ActionableSuggestion)

    def test_invalid_category_returns_empty_dict(self) -> None:
        """Returns empty dict for invalid category."""
        suggestions = get_all_suggestions_for_category("nonexistent")
        assert suggestions == {}

    def test_all_categories_exist(self) -> None:
        """All documented categories have suggestions."""
        expected_categories = [
            "directive",
            "config",
            "template",
            "attribute",
            "asset",
            "content",
            "parsing",
            "cache",
            "server",
            "autodoc",
            "validator",
            "build",
        ]
        for category in expected_categories:
            suggestions = get_all_suggestions_for_category(category)
            assert len(suggestions) > 0, f"Category {category!r} has no suggestions"


class TestEnhanceErrorContext:
    """Tests for enhance_error_context function."""

    def test_adds_suggestion_to_context(self) -> None:
        """Adds suggestion fix to context dict."""
        context: dict = {}
        enhanced = enhance_error_context(context, "template", "not_found")

        assert "suggestion" in enhanced
        assert enhanced["suggestion"]

    def test_adds_docs_url_when_available(self) -> None:
        """Adds docs_url to context when suggestion has one."""
        context: dict = {}
        enhanced = enhance_error_context(context, "directive", "since_empty")

        assert "docs_url" in enhanced

    def test_adds_check_files_when_available(self) -> None:
        """Adds check_files to context when suggestion has them."""
        context: dict = {}
        enhanced = enhance_error_context(context, "directive", "since_empty")

        assert "check_files" in enhanced
        assert len(enhanced["check_files"]) > 0

    def test_adds_grep_patterns_when_available(self) -> None:
        """Adds grep_patterns to context when suggestion has them."""
        context: dict = {}
        enhanced = enhance_error_context(context, "directive", "since_empty")

        assert "grep_patterns" in enhanced

    def test_preserves_existing_context(self) -> None:
        """Preserves existing context values."""
        context = {"existing_key": "existing_value"}
        enhanced = enhance_error_context(context, "template", "not_found")

        assert enhanced["existing_key"] == "existing_value"

    def test_invalid_lookup_returns_unchanged(self) -> None:
        """Returns unchanged context for invalid category/key."""
        context = {"key": "value"}
        enhanced = enhance_error_context(context, "fake", "fake")

        assert enhanced == context


class TestFormatSuggestion:
    """Tests for format_suggestion function."""

    def test_basic_format(self) -> None:
        """Returns formatted string with fix."""
        result = format_suggestion("template", "not_found")
        assert result is not None
        assert "Fix:" in result

    def test_includes_docs_url(self) -> None:
        """Includes docs URL in output."""
        result = format_suggestion("directive", "since_empty")
        assert result is not None
        assert "Docs:" in result

    def test_with_snippets(self) -> None:
        """Includes code snippets when requested."""
        result = format_suggestion("directive", "since_empty", include_snippets=True)
        assert result is not None
        assert "Before:" in result
        assert "After:" in result

    def test_without_snippets(self) -> None:
        """Excludes code snippets by default."""
        result = format_suggestion("directive", "since_empty", include_snippets=False)
        assert result is not None
        assert "Before:" not in result

    def test_invalid_lookup_returns_none(self) -> None:
        """Returns None for invalid category/key."""
        assert format_suggestion("fake", "fake") is None


class TestFormatSuggestionFull:
    """Tests for format_suggestion_full function."""

    def test_includes_all_details(self) -> None:
        """Full format includes all available details."""
        result = format_suggestion_full("directive", "since_empty")
        assert result is not None

        # Should have all sections
        assert "Fix:" in result
        assert "Explanation:" in result
        assert "Before:" in result or "❌" in result
        assert "After:" in result or "✅" in result
        assert "Files to check:" in result
        assert "Related error codes:" in result
        assert "Documentation:" in result

    def test_invalid_lookup_returns_none(self) -> None:
        """Returns None for invalid category/key."""
        assert format_suggestion_full("fake", "fake") is None


class TestActionableSuggestion:
    """Tests for ActionableSuggestion dataclass."""

    def test_to_dict_serialization(self) -> None:
        """Can serialize to dictionary."""
        suggestion = ActionableSuggestion(
            fix="Do this",
            explanation="Because of that",
            docs_url="/docs/test",
            before_snippet="before",
            after_snippet="after",
            check_files=["file1.py"],
            related_codes=["R001"],
            grep_patterns=["pattern"],
        )

        result = suggestion.to_dict()

        assert result["fix"] == "Do this"
        assert result["explanation"] == "Because of that"
        assert result["docs_url"] == "/docs/test"
        assert result["before_snippet"] == "before"
        assert result["after_snippet"] == "after"
        assert result["check_files"] == ["file1.py"]
        assert result["related_codes"] == ["R001"]
        assert result["grep_patterns"] == ["pattern"]

    def test_default_empty_lists(self) -> None:
        """Default values are empty lists, not None."""
        suggestion = ActionableSuggestion(
            fix="Do this",
            explanation="Because",
        )

        assert suggestion.check_files == []
        assert suggestion.related_codes == []
        assert suggestion.grep_patterns == []
