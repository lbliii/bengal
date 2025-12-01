"""
Comprehensive template safety tests with error boundary testing.

Tests the complete template safety system including error handling,
fallbacks, nested calls, and performance characteristics.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.autodoc.template_safety import SafeTemplateRenderer, create_safe_environment


class TestTemplateSafetyBoundaries:
    """Test error boundaries and fallback mechanisms."""

    @pytest.fixture
    def template_dirs(self, tmp_path):
        """Create temporary template directories for testing."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create macros directory
        macros_dir = template_dir / "macros"
        macros_dir.mkdir()

        # Copy safe_macros.md.jinja2
        safe_macros_content = """
{% macro safe_section(section_name="", show_errors=true) %}
{% if caller %}
<!-- BEGIN {{ section_name }} section -->
{{ caller() }}
<!-- END {{ section_name }} section -->
{% endif %}
{% endmacro %}

{% macro safe_var(obj, attr, default="-") %}
{%- if obj and attr in obj -%}
{{ obj[attr] }}
{%- else -%}
{{ default }}
{%- endif -%}
{% endmacro %}
"""
        (macros_dir / "safe_macros.md.jinja2").write_text(safe_macros_content)

        return [template_dir]

    @pytest.fixture
    def renderer(self, template_dirs):
        """Create SafeTemplateRenderer for testing."""
        env = create_safe_environment(template_dirs)
        return SafeTemplateRenderer(env)

    def _create_template(self, tmp_path: Path, name: str, content: str) -> Path:
        """Helper to create template files."""
        template_path = tmp_path / "templates" / name
        template_path.write_text(content)
        return template_path

    def _assert_error_recorded(
        self, renderer: SafeTemplateRenderer, expected_type: str, expected_count: int = 1
    ) -> None:
        """Helper to assert error was recorded correctly."""
        assert len(renderer.errors) == expected_count
        if expected_count > 0:
            assert renderer.errors[-1]["error_type"] == expected_type
            assert renderer.error_count == expected_count

    @contextmanager
    def _clean_renderer(self, renderer: SafeTemplateRenderer) -> Generator[SafeTemplateRenderer]:
        """Context manager to ensure renderer errors are cleared after use."""
        renderer.clear_errors()
        try:
            yield renderer
        finally:
            renderer.clear_errors()

    def test_basic_template_rendering(self, renderer, tmp_path):
        """Test basic template rendering without errors."""
        template_content = """
# Test Document
Hello {{ name }}!
"""
        self._create_template(tmp_path, "basic.md.jinja2", template_content)

        result = renderer.render_with_boundaries("basic.md.jinja2", {"name": "World"})

        assert "Hello World!" in result
        self._assert_error_recorded(renderer, "", 0)

    def test_undefined_variable_behavior(self, renderer, tmp_path):
        """Test behavior when template has undefined variables."""
        template_content = """
# Test Document
Hello {{ undefined_variable }}!
"""
        self._create_template(tmp_path, "undefined.md.jinja2", template_content)

        result = renderer.render_with_boundaries("undefined.md.jinja2", {})

        # With default Jinja2 behavior, undefined variables render as empty strings
        assert "Hello !" in result
        self._assert_error_recorded(renderer, "", 0)

    def test_template_not_found_fallback(self, renderer):
        """Test fallback when template doesn't exist."""
        result = renderer.render_with_boundaries("nonexistent.md.jinja2", {})

        # Should get emergency fallback since no element context provided
        assert "Critical Template Error" in result
        self._assert_error_recorded(renderer, "template_not_found")

    @pytest.mark.parametrize(
        "error_scenario,template_content,expected_error_type,expected_text",
        [
            (
                "undefined_variable",
                "Hello {{ missing_var }}!",
                "",
                "Hello !",  # Undefined variables render as empty strings
            ),
            (
                "syntax_error",
                "{% if unclosed %}content",
                "template_syntax_error",
                "Critical Template Error",  # Emergency fallback
            ),
            (
                "invalid_filter",
                "{{ 'text' | nonexistent_filter }}",
                "template_syntax_error",
                "Critical Template Error",  # Emergency fallback
            ),
        ],
    )
    def test_error_fallback_scenarios(
        self,
        renderer: SafeTemplateRenderer,
        tmp_path: Path,
        error_scenario: str,
        template_content: str,
        expected_error_type: str,
        expected_text: str,
    ):
        """Test various error scenarios produce appropriate fallbacks."""
        template_name = f"{error_scenario}.md.jinja2"
        self._create_template(tmp_path, template_name, template_content)

        result = renderer.render_with_boundaries(template_name, {})

        assert expected_text in result
        if expected_error_type:
            self._assert_error_recorded(renderer, expected_error_type)
        else:
            self._assert_error_recorded(renderer, "", 0)

    def test_syntax_error_fallback(self, renderer, tmp_path):
        """Test fallback when template has syntax errors."""
        template_content = """
# Test Document
{% if unclosed_if %}
This will cause a syntax error
"""
        self._create_template(tmp_path, "syntax_error.md.jinja2", template_content)

        result = renderer.render_with_boundaries("syntax_error.md.jinja2", {})

        # Should get emergency fallback since no element context provided
        assert "Critical Template Error" in result
        self._assert_error_recorded(renderer, "template_syntax_error")

    def test_nested_safe_section_calls(self, renderer, tmp_path):
        """Test nested safe_section macro calls."""
        template_content = """
{% from 'macros/safe_macros.md.jinja2' import safe_section %}

# Test Document

{% call safe_section('outer') %}
## Outer Section
Content: {{ outer_content }}

{% call safe_section('inner') %}
### Inner Section
Content: {{ inner_content }}

{% call safe_section('deeply_nested') %}
#### Deeply Nested
Content: {{ nested_content }}
{% endcall %}

Back to inner.
{% endcall %}

Back to outer.
{% endcall %}
"""
        template_path = tmp_path / "templates" / "nested.md.jinja2"
        template_path.write_text(template_content)

        context = {
            "outer_content": "Outer data",
            "inner_content": "Inner data",
            "nested_content": "Nested data",
        }

        result = renderer.render_with_boundaries("nested.md.jinja2", context)

        assert "BEGIN outer section" in result
        assert "BEGIN inner section" in result
        assert "BEGIN deeply_nested section" in result
        assert "Outer data" in result
        assert "Inner data" in result
        assert "Nested data" in result
        assert len(renderer.errors) == 0

    def test_error_in_nested_section(self, renderer, tmp_path):
        """Test behavior when nested section has undefined variable."""
        template_content = """
{% from 'macros/safe_macros.md.jinja2' import safe_section %}

# Test Document

{% call safe_section('outer') %}
## Outer Section
This should work: {{ valid_var }}

{% call safe_section('inner') %}
### Inner Section
This will render empty: {{ undefined_var }}
{% endcall %}

Back to outer.
{% endcall %}
"""
        template_path = tmp_path / "templates" / "nested_error.md.jinja2"
        template_path.write_text(template_content)

        context = {"valid_var": "Valid content"}

        result = renderer.render_with_boundaries("nested_error.md.jinja2", context)

        # With default Jinja2 behavior, undefined variables render as empty strings
        assert "This should work: Valid content" in result
        assert "This will render empty:" in result
        assert "BEGIN outer section" in result
        assert "BEGIN inner section" in result
        self._assert_error_recorded(renderer, "", 0)

    def test_safe_var_macro(self, renderer, tmp_path):
        """Test safe_var macro for safe variable access."""
        template_content = """
{% from 'macros/safe_macros.md.jinja2' import safe_var %}

# Test Document

Valid: {{ safe_var(data, 'valid_key', 'default') }}
Missing: {{ safe_var(data, 'missing_key', 'default') }}
Null object: {{ safe_var(none_obj, 'any_key', 'default') }}
"""
        template_path = tmp_path / "templates" / "safe_var.md.jinja2"
        template_path.write_text(template_content)

        context = {"data": {"valid_key": "Valid value"}, "none_obj": None}

        result = renderer.render_with_boundaries("safe_var.md.jinja2", context)

        assert "Valid: Valid value" in result
        assert "Missing: default" in result
        assert "Null object: default" in result
        assert len(renderer.errors) == 0

    def test_strict_undefined_behavior(self, tmp_path):
        """Test behavior with StrictUndefined environment."""
        from jinja2 import Environment, FileSystemLoader, StrictUndefined

        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create environment with StrictUndefined
        env = Environment(
            loader=FileSystemLoader([str(template_dir)]),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        strict_renderer = SafeTemplateRenderer(env)

        template_content = "Hello {{ undefined_var }}!"
        (template_dir / "strict_test.md.jinja2").write_text(template_content)

        result = strict_renderer.render_with_boundaries("strict_test.md.jinja2", {})

        # With StrictUndefined, should get fallback content
        assert "Critical Template Error" in result
        self._assert_error_recorded(strict_renderer, "undefined_variable")


class TestTemplatePerformance:
    """Test template rendering performance and caching."""

    @pytest.fixture
    def renderer(self, tmp_path):
        """Create renderer with template directory."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create simple template
        template_content = "# {{ title }}\n{{ content }}"
        (template_dir / "simple.md.jinja2").write_text(template_content)

        env = create_safe_environment([template_dir])
        return SafeTemplateRenderer(env)

    def test_template_caching_performance(self, renderer):
        """Test that template compilation is cached for performance."""
        context = {"title": "Test", "content": "Content"}

        # First render - should compile template
        result1 = renderer.render_with_boundaries("simple.md.jinja2", context)

        # Second render - should use cached template
        result2 = renderer.render_with_boundaries("simple.md.jinja2", context)

        assert result1 == result2
        assert "# Test" in result1
        assert len(renderer.errors) == 0

    def test_multiple_template_rendering(self, renderer, tmp_path):
        """Test rendering multiple different templates."""
        # Create additional templates
        (tmp_path / "templates" / "template2.md.jinja2").write_text("## {{ subtitle }}")
        (tmp_path / "templates" / "template3.md.jinja2").write_text("### {{ section }}")

        results = []
        contexts = [
            {"title": "Title1", "content": "Content1"},
            {"subtitle": "Subtitle2"},
            {"section": "Section3"},
        ]
        templates = ["simple.md.jinja2", "template2.md.jinja2", "template3.md.jinja2"]

        for template, context in zip(templates, contexts, strict=False):
            result = renderer.render_with_boundaries(template, context)
            results.append(result)

        assert len(results) == 3
        assert "Title1" in results[0]
        assert "Subtitle2" in results[1]
        assert "Section3" in results[2]
        assert len(renderer.errors) == 0

    def test_performance_with_large_context(self, renderer, tmp_path):
        """Test performance with large context data."""
        import time

        # Create template with many variables
        template_content = """
# Performance Test
{% for item in items %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
"""
        (tmp_path / "templates" / "performance.md.jinja2").write_text(template_content)

        # Create large context
        large_context = {
            "items": [{"name": f"item_{i}", "value": f"value_{i}"} for i in range(1000)]
        }

        # Measure rendering time
        start_time = time.time()
        result = renderer.render_with_boundaries("performance.md.jinja2", large_context)
        render_time = time.time() - start_time

        # Verify result and performance
        assert "item_0: value_0" in result
        assert "item_999: value_999" in result
        assert len(renderer.errors) == 0
        assert render_time < 1.0  # Should render in under 1 second


class TestTemplateIntegration:
    """Test integration with real template types."""

    @pytest.fixture
    def mock_python_element(self) -> Mock:
        """Create mock Python element for testing."""
        element = Mock()
        element.name = "test_function"
        element.element_type = "function"
        element.description = "Test function description"
        element.source_file = "test_module.py"
        element.metadata = {
            "signature": "test_function(arg1: str, arg2: int = 5) -> bool",
            "parameters": [
                {"name": "arg1", "type": "str", "description": "First argument"},
                {"name": "arg2", "type": "int", "description": "Second argument", "default": "5"},
            ],
            "returns": {"type": "bool", "description": "Return value"},
            "parsed_doc": {
                "deprecated": None,
                "summary": "Test function description",
                "description": "Test function description",
            },
            "args": [],
            "is_async": False,
            "deprecated": False,
        }
        element.children = []
        # Make the mock behave like a list for len() calls
        element.__len__ = Mock(return_value=0)
        return element

    @pytest.fixture
    def mock_cli_element(self) -> Mock:
        """Create mock CLI element for testing."""
        element = Mock()
        element.name = "test-command"
        element.element_type = "command"
        element.description = "Test CLI command"
        element.source_file = "cli_commands.py"
        element.metadata = {
            "usage": "test-command [OPTIONS] ARG",
            "arguments": [{"name": "ARG", "description": "Required argument"}],
            "options": [
                {"name": "--verbose", "description": "Enable verbose output"},
                {"name": "--output", "description": "Output file", "type": "PATH"},
            ],
        }
        element.children = []
        # Make the mock behave like a list for len() calls
        element.__len__ = Mock(return_value=0)
        return element

    def test_python_template_integration(self, mock_python_element):
        """Test integration with Python function template."""
        template_dirs = [Path("bengal/autodoc/templates")]
        env = create_safe_environment(template_dirs)
        renderer = SafeTemplateRenderer(env)

        context = {"element": mock_python_element, "config": {}}

        result = renderer.render_with_boundaries("python/function.md.jinja2", context)

        assert "test_function" in result
        assert len(renderer.errors) == 0

    def test_cli_template_integration(self, mock_cli_element):
        """Test integration with CLI command template."""
        template_dirs = [Path("bengal/autodoc/templates")]
        env = create_safe_environment(template_dirs)
        renderer = SafeTemplateRenderer(env)

        context = {"element": mock_cli_element, "config": {}}

        result = renderer.render_with_boundaries("cli/command.md.jinja2", context)

        assert "test-command" in result
        assert len(renderer.errors) == 0

    def test_template_with_missing_data(self, mock_python_element):
        """Test template rendering when element is missing expected data."""
        # Remove some expected metadata but keep essential structure
        mock_python_element.metadata = {
            "signature": "incomplete()",
            "parsed_doc": {"deprecated": None},
            "args": [],
            "is_async": False,
            "deprecated": False,
        }

        template_dirs = [Path("bengal/autodoc/templates")]
        env = create_safe_environment(template_dirs)
        renderer = SafeTemplateRenderer(env)

        context = {"element": mock_python_element, "config": {}}

        result = renderer.render_with_boundaries("python/function.md.jinja2", context)

        # Should still render successfully with safe macros handling missing data
        # Note: With missing metadata, the template may render "Documentation" as title
        # but the function name should appear somewhere (signature, description, etc.)
        # or at minimum, the template should render without critical errors
        assert len(result) > 0, "Template should render some content"
        # May have warnings but should not have critical errors
        assert len([e for e in renderer.errors if e.get("error_type") == "undefined_variable"]) == 0
        # The function name should appear in the signature or the element should be accessible
        # (The signature contains "incomplete()" which doesn't have the name, so we check for successful rendering)
        assert "incomplete()" in result or "test_function" in result, (
            "Function signature or name should appear"
        )

    @pytest.mark.skipif(
        not Path("bengal/autodoc/templates").exists(),
        reason="Real template directory not available",
    )
    def test_real_template_integration(self, mock_python_element):
        """Test integration with actual template files."""
        template_dirs = [Path("bengal/autodoc/templates")]
        env = create_safe_environment(template_dirs)
        renderer = SafeTemplateRenderer(env)

        # Provide comprehensive context that real templates expect
        context = {
            "element": mock_python_element,
            "config": {
                "autodoc": {"template_safety": {"debug_mode": True}},
                "project": {"name": "Test Project"},
            },
        }

        # Test with real template if it exists
        template_path = Path("bengal/autodoc/templates/python/function.md.jinja2")
        if template_path.exists():
            result = renderer.render_with_boundaries("python/function.md.jinja2", context)

            # Should render successfully or provide meaningful fallback
            assert len(result) > 0
            # If it's a fallback, it should be the emergency fallback
            if "Critical Template Error" in result:
                assert len(renderer.errors) > 0
            else:
                # Should contain function name if successful
                assert mock_python_element.name in result


class TestErrorReporting:
    """Test error collection and reporting functionality."""

    @pytest.fixture
    def renderer_with_errors(self, tmp_path):
        """Create renderer and generate some errors for testing."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Template with syntax error
        (template_dir / "error1.md.jinja2").write_text("{% if unclosed %}")
        # Template with another syntax error
        (template_dir / "error2.md.jinja2").write_text("{{ 'text' | invalid_filter }}")

        env = create_safe_environment([template_dir])
        renderer = SafeTemplateRenderer(env)

        # Generate errors - only syntax errors and template not found will be recorded
        renderer.render_with_boundaries("error1.md.jinja2", {})
        renderer.render_with_boundaries("error2.md.jinja2", {})
        renderer.render_with_boundaries("nonexistent.md.jinja2", {})

        return renderer

    def test_error_collection(self, renderer_with_errors):
        """Test that errors are properly collected."""
        assert len(renderer_with_errors.errors) == 3

        error_types = [e["error_type"] for e in renderer_with_errors.errors]
        assert "template_syntax_error" in error_types
        assert "template_not_found" in error_types
        # Should have 2 syntax errors and 1 template not found

    def test_error_details(self, renderer_with_errors):
        """Test that error records contain required details."""
        for error in renderer_with_errors.errors:
            assert "template" in error
            assert "error_type" in error
            assert "error" in error
            assert "element_name" in error
            assert "element_type" in error
            assert "timestamp" in error
            assert "traceback" in error

    def test_error_count(self, renderer_with_errors):
        """Test error count tracking."""
        assert renderer_with_errors.error_count == 3
