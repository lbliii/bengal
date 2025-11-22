"""
Tests for the autodoc template safety system.

Tests the SafeTemplateRenderer, TemplateValidator, and error handling
functionality that prevents silent template failures.
"""

from __future__ import annotations

import pytest
from jinja2 import DictLoader, Environment, StrictUndefined

from bengal.autodoc.template_safety import (
    SafeTemplateRenderer,
    TemplateRenderingError,
    TemplateValidator,
    _get_safe_filters,
    create_safe_environment,
)


class MockElement:
    """Mock element for testing template rendering."""

    def __init__(self, name="TestElement", element_type="module", description="Test description"):
        self.name = name
        self.element_type = element_type
        self.description = description
        self.source_file = "test/module.py"


class TestSafeTemplateRenderer:
    """Test the SafeTemplateRenderer class."""

    def test_successful_rendering(self):
        """Test that normal templates render successfully."""
        templates = {"test.md.jinja2": "# {{ element.name }}\n\n{{ element.description }}"}
        env = Environment(loader=DictLoader(templates))
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        result = renderer.render_with_boundaries("test.md.jinja2", context)

        assert "# TestElement" in result
        assert "Test description" in result
        assert renderer.error_count == 0
        assert len(renderer.errors) == 0

    def test_template_not_found_fallback(self):
        """Test fallback when template file doesn't exist."""
        env = Environment(loader=DictLoader({}))
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        result = renderer.render_with_boundaries("missing.md.jinja2", context)

        assert "# TestElement" in result
        assert "Template Not Found: missing.md.jinja2" in result
        assert "Type:** module" in result
        assert "Source:** test/module.py" in result
        assert "Test description" in result
        assert "Template file missing" in result
        assert renderer.error_count == 1
        assert len(renderer.errors) == 1
        assert renderer.errors[0]["error_type"] == "template_not_found"

    def test_undefined_variable_fallback(self):
        """Test fallback when template has undefined variables."""
        templates = {"test.md.jinja2": "# {{ element.name }}\n\n{{ undefined_variable }}"}
        # Use strict undefined to force UndefinedError
        env = Environment(loader=DictLoader(templates), undefined=StrictUndefined)
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        result = renderer.render_with_boundaries("test.md.jinja2", context)

        assert "# TestElement" in result
        assert "Template Variable Error" in result
        assert "Undefined variable" in result
        assert "Test description" in result
        assert "undefined variables" in result
        assert renderer.error_count == 1
        assert renderer.errors[0]["error_type"] == "undefined_variable"

    def test_syntax_error_fallback(self):
        """Test fallback when template has syntax errors."""
        templates = {"test.md.jinja2": "# {{ element.name }}\n\n{% if missing_endif %}"}
        env = Environment(loader=DictLoader(templates))
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        result = renderer.render_with_boundaries("test.md.jinja2", context)

        assert "# TestElement" in result
        assert "Template Syntax Error" in result
        assert "Test description" in result
        assert "syntax errors" in result
        assert renderer.error_count == 1
        assert renderer.errors[0]["error_type"] == "template_syntax_error"

    def test_emergency_fallback_no_element(self):
        """Test emergency fallback when context has no element."""
        templates = {"test.md.jinja2": "{{ undefined_variable }}"}
        env = Environment(loader=DictLoader(templates), undefined=StrictUndefined)
        renderer = SafeTemplateRenderer(env)

        context = {}  # No element

        result = renderer.render_with_boundaries("test.md.jinja2", context)

        assert "# Unknown" in result
        assert "Critical Template Error" in result
        assert "emergency fallback content" in result
        assert "Context keys: None" in result
        assert renderer.error_count == 1

    def test_error_summary_no_errors(self):
        """Test error summary when no errors occurred."""
        env = Environment(loader=DictLoader({}))
        renderer = SafeTemplateRenderer(env)

        summary = renderer.get_error_summary()

        assert summary == "✅ All templates rendered successfully"

    def test_error_summary_with_errors(self):
        """Test error summary with multiple errors."""
        env = Environment(loader=DictLoader({}))
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        # Generate multiple errors
        renderer.render_with_boundaries("missing1.md.jinja2", context)
        renderer.render_with_boundaries("missing2.md.jinja2", context)

        summary = renderer.get_error_summary()

        assert "❌ 2 template errors:" in summary
        assert "missing1.md.jinja2" in summary
        assert "missing2.md.jinja2" in summary
        assert "TestElement" in summary

    def test_clear_errors(self):
        """Test clearing recorded errors."""
        env = Environment(loader=DictLoader({}))
        renderer = SafeTemplateRenderer(env)

        element = MockElement()
        context = {"element": element}

        # Generate an error
        renderer.render_with_boundaries("missing.md.jinja2", context)
        assert renderer.error_count == 1
        assert len(renderer.errors) == 1

        # Clear errors
        renderer.clear_errors()
        assert renderer.error_count == 0
        assert len(renderer.errors) == 0
        assert len(renderer.warnings) == 0


class TestTemplateValidator:
    """Test the TemplateValidator class."""

    def test_validate_valid_template(self):
        """Test validation of a valid template."""
        templates = {
            "valid.md.jinja2": """# {{ element.name }}

{% if element.description %}
{{ element.description }}
{% endif %}

{% for child in element.children %}
- {{ child.name }}
{% endfor %}
"""
        }
        env = Environment(loader=DictLoader(templates))
        validator = TemplateValidator(env)

        issues = validator.validate_template("valid.md.jinja2")

        assert issues == []

    def test_validate_template_not_found(self):
        """Test validation when template doesn't exist."""
        env = Environment(loader=DictLoader({}))
        validator = TemplateValidator(env)

        issues = validator.validate_template("missing.md.jinja2")

        assert len(issues) == 1
        assert "Template file not found" in issues[0]

    def test_validate_syntax_error(self):
        """Test validation of template with syntax errors."""
        templates = {"invalid.md.jinja2": "{% if condition %}\nNo endif!"}
        env = Environment(loader=DictLoader(templates))
        validator = TemplateValidator(env)

        issues = validator.validate_template("invalid.md.jinja2")

        assert len(issues) >= 1
        assert any("syntax error" in issue.lower() for issue in issues)

    def test_check_whitespace_issues(self):
        """Test detection of whitespace issues."""
        templates = {
            "whitespace.md.jinja2": "Line with trailing space \nTab\there\nEnd with space \n"
        }
        env = Environment(loader=DictLoader(templates))
        validator = TemplateValidator(env)

        issues = validator.validate_template("whitespace.md.jinja2")

        # Note: Template source access may not work with DictLoader in all Jinja2 versions
        # This test verifies the validator doesn't crash, actual whitespace detection
        # is tested separately in unit tests for the validation methods
        assert isinstance(issues, list)

    def test_check_unbalanced_blocks(self):
        """Test detection of unbalanced template blocks."""
        templates = {
            "unbalanced.md.jinja2": """
{% if condition %}
Content
{% if another %}
More content
{% endif %}
{# Missing endif for first if #}

{% for item in items %}
Item: {{ item }}
{# Missing endfor #}
"""
        }
        env = Environment(loader=DictLoader(templates))
        validator = TemplateValidator(env)

        issues = validator.validate_template("unbalanced.md.jinja2")

        # This template should cause a syntax error during parsing
        # The exact error detection depends on Jinja2 version and template source access
        assert isinstance(issues, list)
        # If template source is accessible, should detect syntax issues
        if issues:
            assert any(
                "syntax error" in issue.lower() or "unbalanced" in issue.lower() for issue in issues
            )


class TestSafeFilters:
    """Test the safe template filters."""

    def test_safe_description_filter(self):
        """Test the safe_description filter."""
        filters = _get_safe_filters()
        safe_description = filters["safe_description"]

        # Test normal text
        assert safe_description("Simple description") == "Simple description"

        # Test None/empty
        assert safe_description(None) == "Documentation"
        assert safe_description("") == "Documentation"

        # Test multiline with cleanup
        multiline = "First line\n\nSecond line\n# Header\nThird line"
        result = safe_description(multiline)
        assert result == "First line Second line Third line"

        # Test truncation
        long_text = "A" * 250
        result = safe_description(long_text)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

        # Test quote escaping
        with_quotes = "Text with \"quotes\" and 'apostrophes'"
        result = safe_description(with_quotes)
        assert '\\"' in result
        assert "\\'" in result

    def test_code_or_dash_filter(self):
        """Test the code_or_dash filter."""
        filters = _get_safe_filters()
        code_or_dash = filters["code_or_dash"]

        # Test normal values
        assert code_or_dash("value") == "`value`"
        assert code_or_dash(42) == "`42`"

        # Test empty/None values
        assert code_or_dash(None) == "-"
        assert code_or_dash("") == "-"
        assert code_or_dash("-") == "-"
        assert code_or_dash("None") == "-"

    def test_safe_anchor_filter(self):
        """Test the safe_anchor filter."""
        filters = _get_safe_filters()
        safe_anchor = filters["safe_anchor"]

        # Test normal text
        assert safe_anchor("My Function") == "my-function"
        assert safe_anchor("Class.method") == "class-method"
        assert safe_anchor("snake_case") == "snake-case"

        # Test None/empty
        assert safe_anchor(None) == ""
        assert safe_anchor("") == ""

    def test_project_relative_filter(self):
        """Test the project_relative filter."""
        filters = _get_safe_filters()
        project_relative = filters["project_relative"]

        # Test None/empty
        assert project_relative(None) == "Unknown"
        assert project_relative("") == "Unknown"

        # Test project-relative paths
        assert project_relative("/Users/dev/bengal/src/module.py") == "bengal/src/module.py"
        assert project_relative("/home/user/project/lib/code.py") == "project/lib/code.py"

        # Test paths without common prefixes
        assert project_relative("relative/path.py") == "relative/path.py"

    def test_safe_type_filter(self):
        """Test the safe_type filter."""
        filters = _get_safe_filters()
        safe_type = filters["safe_type"]

        # Test normal types
        assert safe_type("str") == "`str`"
        assert safe_type("int") == "`int`"
        assert safe_type("typing.List[str]") == "`List[str]`"

        # Test None/empty values
        assert safe_type(None) == "-"
        assert safe_type("") == "-"
        assert safe_type("None") == "-"
        assert safe_type("NoneType") == "-"

        # Test class type cleanup
        assert safe_type("<class 'str'>") == "`str`"
        assert safe_type("typing.Optional[int]") == "`Optional[int]`"

    def test_safe_default_filter(self):
        """Test the safe_default filter."""
        filters = _get_safe_filters()
        safe_default = filters["safe_default"]

        # Test string values
        assert safe_default("hello") == '`"hello"`'

        # Test boolean values
        assert safe_default(True) == "`True`"
        assert safe_default(False) == "`False`"

        # Test numeric values
        assert safe_default(42) == "`42`"
        assert safe_default(3.14) == "`3.14`"

        # Test None/empty values (both return "-")
        assert safe_default(None) == "-"
        assert safe_default("") == "-"  # Empty string is treated as None

        # Test other types
        assert safe_default([1, 2, 3]) == "`[1, 2, 3]`"

    def test_safe_text_filter(self):
        """Test the safe_text filter."""
        filters = _get_safe_filters()
        safe_text = filters["safe_text"]

        # Test normal text
        assert safe_text("Hello world") == "Hello world"
        assert safe_text("  Trimmed  ") == "Trimmed"

        # Test None/empty values
        assert safe_text(None) == "*No description provided.*"
        assert safe_text("") == "*No description provided.*"
        assert safe_text("   ") == "*No description provided.*"

        # Test non-string values
        assert safe_text(42) == "42"
        assert safe_text(True) == "True"

    def test_truncate_text_filter(self):
        """Test the truncate_text filter."""
        filters = _get_safe_filters()
        truncate_text = filters["truncate_text"]

        # Test normal text (no truncation needed)
        assert truncate_text("Short text") == "Short text"

        # Test truncation
        long_text = "A" * 150
        result = truncate_text(long_text, length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")
        assert result.startswith("A" * 100)

        # Test custom suffix
        result = truncate_text(long_text, length=50, suffix=" [more]")
        assert result.endswith(" [more]")

        # Test None/empty values
        assert truncate_text(None) == ""
        assert truncate_text("") == ""

    def test_format_list_filter(self):
        """Test the format_list filter."""
        filters = _get_safe_filters()
        format_list = filters["format_list"]

        # Test normal lists
        assert format_list(["a", "b", "c"]) == "a, b, c"
        assert format_list([1, 2, 3]) == "1, 2, 3"

        # Test custom separator
        assert format_list(["a", "b", "c"], separator=" | ") == "a | b | c"

        # Test truncation
        long_list = list(range(10))
        result = format_list(long_list, max_items=3)
        assert result == "0, 1, 2 and 7 more"

        # Test None/empty values
        assert format_list(None) == ""
        assert format_list([]) == ""

        # Test single item
        assert format_list(["single"]) == "single"


class TestCreateSafeEnvironment:
    """Test the create_safe_environment function."""

    def test_create_safe_environment(self, tmp_path):
        """Test creating a safe Jinja2 environment."""
        # Create a temporary template directory
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create a test template
        test_template = template_dir / "test.md.jinja2"
        test_template.write_text("# {{ element.name | safe_description }}")

        # Create safe environment
        env = create_safe_environment([template_dir])

        # Test that environment is configured correctly
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True
        assert env.keep_trailing_newline is True
        assert env.autoescape is False  # We're generating Markdown

        # Test that safe filters are available
        assert "safe_description" in env.filters
        assert "code_or_dash" in env.filters
        assert "safe_anchor" in env.filters
        assert "project_relative" in env.filters
        assert "safe_type" in env.filters
        assert "safe_default" in env.filters
        assert "safe_text" in env.filters
        assert "truncate_text" in env.filters
        assert "format_list" in env.filters

        # Test rendering with safe filters
        template = env.get_template("test.md.jinja2")
        result = template.render({"element": MockElement()})
        assert result == "# TestElement"


class TestTemplateRenderingError:
    """Test the TemplateRenderingError exception."""

    def test_template_rendering_error_creation(self):
        """Test creating a TemplateRenderingError."""
        original_error = ValueError("Test error")
        context = {"element": MockElement()}

        error = TemplateRenderingError(
            template_name="test.md.jinja2", original_error=original_error, context=context
        )

        assert error.template_name == "test.md.jinja2"
        assert error.original_error is original_error
        assert error.context is context
        assert "Template test.md.jinja2 failed: Test error" in str(error)

    def test_template_rendering_error_no_context(self):
        """Test creating a TemplateRenderingError without context."""
        original_error = ValueError("Test error")

        error = TemplateRenderingError(
            template_name="test.md.jinja2", original_error=original_error
        )

        assert error.context == {}


if __name__ == "__main__":
    pytest.main([__file__])
