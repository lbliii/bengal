"""
Additional comprehensive tests for template error handling.

Extends test_template_errors.py with edge cases and error recovery scenarios
to improve coverage from 54% to 70%.
"""

from unittest.mock import Mock

import pytest
from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateAssertionError, TemplateRuntimeError

from bengal.rendering.errors import (
    TemplateRenderError,
    _extract_dict_attribute,
    _extract_filter_name,
    _extract_variable_name,
    _generate_enhanced_suggestions,
)


class TestErrorMessageExtraction:
    """Tests for error message parsing and extraction."""

    def test_extract_variable_name_is_undefined(self):
        """Test extracting variable name from 'is undefined' pattern."""
        error_msg = "'page.title' is undefined"
        var_name = _extract_variable_name(error_msg)
        assert var_name == "page.title"

    def test_extract_variable_name_no_such_element(self):
        """Test extracting variable name from 'no such element' pattern."""
        error_msg = "no such element: metadata.weight"
        var_name = _extract_variable_name(error_msg)
        assert var_name == "metadata.weight"

    def test_extract_variable_name_undefined_variable(self):
        """Test extracting variable name from 'undefined variable' pattern."""
        error_msg = "undefined variable: custom_var"
        var_name = _extract_variable_name(error_msg)
        assert var_name == "custom_var"

    def test_extract_variable_name_no_match(self):
        """Test extracting variable name when pattern doesn't match."""
        error_msg = "Some other error message"
        var_name = _extract_variable_name(error_msg)
        assert var_name is None

    def test_extract_filter_name_single_quotes(self):
        """Test extracting filter name with single quotes."""
        error_msg = "No filter named 'custom_filter'"
        filter_name = _extract_filter_name(error_msg)
        assert filter_name == "custom_filter"

    def test_extract_filter_name_double_quotes(self):
        """Test extracting filter name with double quotes."""
        error_msg = 'No filter named "another_filter"'
        filter_name = _extract_filter_name(error_msg)
        assert filter_name == "another_filter"

    def test_extract_filter_name_case_insensitive(self):
        """Test filter name extraction is case-insensitive."""
        error_msg = "no filter named 'CaseSensitive'"
        filter_name = _extract_filter_name(error_msg)
        assert filter_name == "CaseSensitive"

    def test_extract_filter_name_no_match(self):
        """Test extracting filter name when pattern doesn't match."""
        error_msg = "Some other error message"
        filter_name = _extract_filter_name(error_msg)
        assert filter_name is None

    def test_extract_dict_attribute_standard_pattern(self):
        """Test extracting attribute from dict access error."""
        error_msg = "'dict object' has no attribute 'custom_key'"
        attr_name = _extract_dict_attribute(error_msg)
        assert attr_name == "custom_key"

    def test_extract_dict_attribute_no_match(self):
        """Test extracting dict attribute when pattern doesn't match."""
        error_msg = "Different error message"
        attr_name = _extract_dict_attribute(error_msg)
        assert attr_name is None


class TestEnhancedSuggestions:
    """Tests for enhanced suggestion generation."""

    def test_dict_access_error_suggestions(self):
        """Test suggestions for unsafe dict access errors."""
        error = Mock()
        error.error_type = "undefined"
        error.message = "'dict object' has no attribute 'weight'"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should detect unsafe dict access and provide specific guidance
        assert len(suggestions) > 0
        assert any("unsafe dict access" in s.lower() for s in suggestions)
        assert any("weight" in s for s in suggestions)

    def test_common_typo_suggestions(self):
        """Test suggestions for common typos."""
        error = Mock()
        error.error_type = "undefined"
        error.message = "'titel' is undefined"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest the correct spelling
        assert any("title" in s.lower() for s in suggestions)

    def test_metadata_access_suggestions(self):
        """Test suggestions for metadata access patterns."""
        error = Mock()
        error.error_type = "undefined"
        error.message = "'page.metadata.custom' is undefined"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest safe dict access
        assert any("get(" in s for s in suggestions)

    def test_filter_error_suggestions(self):
        """Test suggestions for filter errors."""
        error = Mock()
        error.error_type = "filter"
        error.message = "No filter named 'date_format'"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest checking documentation
        assert any("documentation" in s.lower() or "help" in s.lower() for s in suggestions)

    def test_date_filter_specific_suggestion(self):
        """Test specific suggestion for date filters."""
        error = Mock()
        error.error_type = "filter"
        error.message = "No filter named 'format_date'"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest date filter syntax
        assert any("date" in s.lower() for s in suggestions)

    def test_syntax_error_missing_tags_suggestion(self):
        """Test suggestions for missing closing tags."""
        error = Mock()
        error.error_type = "syntax"
        error.message = "unexpected end of template"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest checking for missing tags
        assert any("%}" in s or "}}" in s for s in suggestions)

    def test_syntax_error_expected_token_suggestion(self):
        """Test suggestions for expected token errors."""
        error = Mock()
        error.error_type = "syntax"
        error.message = "expected token 'end of print statement'"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest verifying Jinja2 syntax
        assert any("jinja2" in s.lower() or "syntax" in s.lower() for s in suggestions)

    def test_syntax_error_missing_endfor_suggestion(self):
        """Test suggestions for missing endfor/endif."""
        error = Mock()
        error.error_type = "syntax"
        error.message = "Encountered unknown tag 'endfor'"
        error.suggestion = None
        error.available_alternatives = []
        error.template_context = Mock()

        suggestions = _generate_enhanced_suggestions(error)

        # Should suggest matching tags
        assert any("endfor" in s.lower() or "endif" in s.lower() for s in suggestions)


class TestErrorClassificationEdgeCases:
    """Tests for error classification edge cases."""

    def test_classify_filter_error_in_runtime(self):
        """Test classifying filter error that appears as runtime error."""
        error = TemplateRuntimeError("No filter named 'custom' found")
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=None)
        mock_engine.env = Mock()
        mock_engine.env.filters = {}

        tre = TemplateRenderError.from_jinja2_error(error, "test.html", None, mock_engine)
        assert tre.error_type == "filter"

    def test_classify_unknown_filter_in_assertion(self):
        """Test classifying unknown filter in assertion error."""
        error = TemplateAssertionError("unknown filter: custom_filter", 1)
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=None)
        mock_engine.env = Mock()
        mock_engine.env.filters = {}

        tre = TemplateRenderError.from_jinja2_error(error, "test.html", None, mock_engine)
        assert tre.error_type == "filter"

    def test_classify_non_filter_assertion_error(self):
        """Test classifying assertion error that's not about filters."""
        error = TemplateAssertionError("Some assertion failed", 1)
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=None)
        mock_engine.env = Mock()
        mock_engine.env.filters = {}

        tre = TemplateRenderError.from_jinja2_error(error, "test.html", None, mock_engine)
        assert tre.error_type == "syntax"

    def test_classify_generic_exception(self):
        """Test classifying generic exception."""
        error = Exception("Generic error")
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=None)
        mock_engine.env = Mock()
        mock_engine.env.filters = {}

        tre = TemplateRenderError.from_jinja2_error(error, "test.html", None, mock_engine)
        assert tre.error_type == "other"


class TestContextExtractionEdgeCases:
    """Tests for template context extraction edge cases."""

    def test_extract_context_missing_line_number(self):
        """Test extracting context when error has no line number."""
        error = TemplateSyntaxError("Error without line number", 1)
        # Simulate missing line number; TemplateSyntaxError requires an int at construction
        error.lineno = None
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=None)

        context = TemplateRenderError._extract_context(error, "test.html", mock_engine)

        assert context.template_name == "test.html"
        assert context.line_number is None
        assert context.surrounding_lines == []

    def test_extract_context_file_not_found(self, tmp_path):
        """Test extracting context when template file doesn't exist."""
        error = TemplateSyntaxError("Error", 10)
        mock_engine = Mock()
        # Return path that doesn't exist
        mock_engine._find_template_path = Mock(return_value=tmp_path / "nonexistent.html")

        context = TemplateRenderError._extract_context(error, "test.html", mock_engine)

        assert context.surrounding_lines == []

    def test_extract_context_invalid_line_number(self, tmp_path):
        """Test extracting context with line number beyond file length."""
        # Create template with only 5 lines
        template_file = tmp_path / "test.html"
        template_file.write_text("\n".join([f"line {i}" for i in range(5)]))

        error = TemplateSyntaxError("Error", 100)  # Line 100 doesn't exist
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=template_file)

        context = TemplateRenderError._extract_context(error, "test.html", mock_engine)

        # Should handle gracefully
        assert context.source_line is None

    def test_extract_context_with_surrounding_lines(self, tmp_path):
        """Test extracting context with surrounding lines."""
        # Create template file
        template_file = tmp_path / "test.html"
        lines = [f"line {i}" for i in range(20)]
        template_file.write_text("\n".join(lines))

        error = TemplateSyntaxError("Error", 10)
        mock_engine = Mock()
        mock_engine._find_template_path = Mock(return_value=template_file)

        context = TemplateRenderError._extract_context(error, "test.html", mock_engine)

        # Should have error line and surrounding context
        assert context.line_number == 10
        assert context.source_line == "line 9"  # 0-indexed
        assert len(context.surrounding_lines) > 0
        # Should have ~3 lines before and after
        assert 5 <= len(context.surrounding_lines) <= 8


class TestSuggestionGenerationEdgeCases:
    """Tests for suggestion generation edge cases."""

    def test_generate_suggestion_in_section_filter(self):
        """Test generating suggestion for in_section filter."""
        error = TemplateAssertionError("No filter named 'in_section'", 1)
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "filter", mock_engine)

        assert suggestion is not None
        assert "page.parent" in suggestion

    def test_generate_suggestion_is_ancestor_filter(self):
        """Test generating suggestion for is_ancestor filter."""
        error = TemplateAssertionError("No filter named 'is_ancestor'", 1)
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "filter", mock_engine)

        assert suggestion is not None
        assert "page.url" in suggestion

    def test_generate_suggestion_metadata_weight(self):
        """Test generating suggestion for metadata.weight undefined."""
        error = UndefinedError("'metadata.weight' is undefined")
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "undefined", mock_engine)

        assert suggestion is not None
        assert "get(" in suggestion

    def test_generate_suggestion_with_keyword(self):
        """Test generating suggestion for 'with' syntax error."""
        error = TemplateSyntaxError("'with' is not valid here", 1)
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "syntax", mock_engine)

        assert suggestion is not None
        assert "set" in suggestion.lower()

    def test_generate_suggestion_default_parameter(self):
        """Test generating suggestion for default parameter error."""
        error = TemplateSyntaxError("unknown parameter: default=", 1)
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "syntax", mock_engine)

        assert suggestion is not None
        assert "default" in suggestion.lower()

    def test_generate_suggestion_no_match(self):
        """Test suggestion generation when no pattern matches."""
        error = Exception("Generic error message")
        mock_engine = Mock()

        suggestion = TemplateRenderError._generate_suggestion(error, "other", mock_engine)

        assert suggestion is None


class TestAlternativesFinderEdgeCases:
    """Tests for alternative filter finding edge cases."""

    def test_find_alternatives_close_match(self):
        """Test finding close matches for filter names."""
        error = TemplateAssertionError("No filter named 'makrdown'", 1)
        mock_engine = Mock()
        mock_engine.env = Mock()
        mock_engine.env.filters = {
            "markdown": lambda x: x,
            "truncate": lambda x, y: x,
            "uppercase": lambda x: x,
        }

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should suggest markdown (close match)
        assert "markdown" in alternatives

    def test_find_alternatives_multiple_suggestions(self):
        """Test finding multiple alternative suggestions."""
        error = TemplateAssertionError("No filter named 'trunc'", 1)
        mock_engine = Mock()
        mock_engine.env = Mock()
        mock_engine.env.filters = {
            "truncate": lambda x, y: x,
            "truncate_chars": lambda x, y: x,
            "truncate_words": lambda x, y: x,
        }

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should suggest multiple truncate variants
        assert len(alternatives) > 0
        assert any("truncate" in alt for alt in alternatives)

    def test_find_alternatives_no_close_match(self):
        """Test finding alternatives when no close match exists."""
        error = TemplateAssertionError("No filter named 'xyz123abc'", 1)
        mock_engine = Mock()
        mock_engine.env = Mock()
        mock_engine.env.filters = {
            "markdown": lambda x: x,
            "truncate": lambda x, y: x,
        }

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should return empty or very few results
        assert len(alternatives) <= 3

    def test_find_alternatives_non_filter_error(self):
        """Test that alternatives are only found for filter errors."""
        error = UndefinedError("'var' is undefined")
        mock_engine = Mock()

        alternatives = TemplateRenderError._find_alternatives(error, "undefined", mock_engine)

        # Should return empty for non-filter errors
        assert alternatives == []

    def test_find_alternatives_malformed_error(self):
        """Test handling malformed filter error message."""
        error = TemplateAssertionError("Something went wrong with filters", 1)
        mock_engine = Mock()
        mock_engine.env = Mock()
        mock_engine.env.filters = {"markdown": lambda x: x}

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should handle gracefully
        assert alternatives == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
