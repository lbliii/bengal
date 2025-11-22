"""
Test template development tools.

Tests the development tools for template validation, debugging, and testing.
"""

from pathlib import Path
from unittest.mock import Mock

from bengal.autodoc.dev_tools import (
    SampleDataGenerator,
    TemplateDebugger,
    TemplateHotReloader,
    TemplateProfiler,
    create_development_tools,
)
from bengal.autodoc.template_safety import SafeTemplateRenderer, TemplateValidator
from bengal.autodoc.template_testing import TemplateTestSuite, create_template_test_suite


class TestSampleDataGenerator:
    """Test sample data generation for template testing."""

    def test_generate_python_module(self):
        """Test Python module sample generation."""
        generator = SampleDataGenerator()
        module = generator.generate_python_module("test_module")

        assert module.name == "test_module"
        assert module.element_type == "module"
        assert module.qualified_name == "sample.test_module"
        assert module.description is not None
        assert len(module.children) >= 2  # Should have classes and functions

        # Check class structure
        sample_class = module.children[0]
        assert sample_class.element_type == "class"
        assert sample_class.name == "SampleClass"
        assert len(sample_class.children) >= 2  # Methods and properties

    def test_generate_cli_command(self):
        """Test CLI command sample generation."""
        generator = SampleDataGenerator()
        command = generator.generate_cli_command("test-cmd")

        assert command.name == "test-cmd"
        assert command.element_type == "command"
        assert command.description is not None
        assert len(command.children) >= 2  # Arguments and options

        # Check for expected child types
        child_types = [child.element_type for child in command.children]
        assert "argument" in child_types
        assert "option" in child_types

    def test_generate_openapi_endpoint(self):
        """Test OpenAPI endpoint sample generation."""
        generator = SampleDataGenerator()
        endpoint = generator.generate_openapi_endpoint("/test", "POST")

        assert endpoint.name == "POST /test"
        assert endpoint.element_type == "endpoint"
        assert endpoint.metadata["method"] == "post"
        assert endpoint.metadata["path"] == "/test"
        assert "responses" in endpoint.metadata
        assert "request_body" in endpoint.metadata

    def test_generate_sample_config(self):
        """Test sample configuration generation."""
        generator = SampleDataGenerator()
        config = generator.generate_sample_config()

        assert "autodoc" in config
        assert "template_safety" in config["autodoc"]
        assert "project" in config
        assert config["autodoc"]["template_safety"]["error_boundaries"] is True


class TestTemplateDebugger:
    """Test template debugging functionality."""

    def test_debug_template_with_valid_template(self):
        """Test debugging with a valid template."""
        # Create mock environment and components
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        # Setup mocks
        validator.validate_template.return_value = []  # No issues
        renderer.render_with_boundaries.return_value = "# Test Content\n\nSample output"
        renderer.errors = []

        debugger = TemplateDebugger(renderer, validator)

        # Create sample context
        generator = SampleDataGenerator()
        element = generator.generate_python_module()
        context = {"element": element, "config": {}}

        # Debug template
        debug_info = debugger.debug_template("test.md.jinja2", context)

        # Verify debug information
        assert debug_info["template_name"] == "test.md.jinja2"
        assert debug_info["validation"]["is_valid"] is True
        assert debug_info["rendering"]["success"] is True
        assert debug_info["context_analysis"]["element_type"] == "module"

    def test_debug_template_with_validation_errors(self):
        """Test debugging with template validation errors."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        # Setup validation errors
        validator.validate_template.return_value = ["Syntax error", "Missing variable"]
        renderer.render_with_boundaries.return_value = "Fallback content"
        renderer.errors = []

        debugger = TemplateDebugger(renderer, validator)

        generator = SampleDataGenerator()
        element = generator.generate_python_module()
        context = {"element": element, "config": {}}

        debug_info = debugger.debug_template("bad_template.md.jinja2", context)

        assert debug_info["validation"]["is_valid"] is False
        assert len(debug_info["validation"]["issues"]) == 2

    def test_get_debug_report(self):
        """Test debug report generation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        validator.validate_template.return_value = []
        renderer.render_with_boundaries.return_value = "Test content"
        renderer.errors = []

        debugger = TemplateDebugger(renderer, validator)

        # Run a debug session
        generator = SampleDataGenerator()
        element = generator.generate_python_module()
        context = {"element": element, "config": {}}
        debugger.debug_template("test.md.jinja2", context)

        # Get report
        report = debugger.get_debug_report()

        assert "Template Debug Report" in report
        assert "test.md.jinja2" in report
        assert "SUCCESS" in report


class TestTemplateProfiler:
    """Test template performance profiling."""

    def test_profile_template(self):
        """Test template performance profiling."""
        renderer = Mock(spec=SafeTemplateRenderer)
        renderer.render_with_boundaries.return_value = "Test content"
        renderer.error_count = 0

        profiler = TemplateProfiler()

        generator = SampleDataGenerator()
        element = generator.generate_python_module()
        context = {"element": element, "config": {}}

        # Profile template
        metrics = profiler.profile_template("test.md.jinja2", renderer, context)

        assert metrics.template_name == "test.md.jinja2"
        assert metrics.render_time_ms >= 0
        assert metrics.content_size_bytes > 0
        assert metrics.error_count == 0

    def test_get_performance_summary(self):
        """Test performance summary generation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        renderer.render_with_boundaries.return_value = "Test content"
        renderer.error_count = 0

        profiler = TemplateProfiler()

        generator = SampleDataGenerator()
        element = generator.generate_python_module()
        context = {"element": element, "config": {}}

        # Profile multiple times
        for i in range(3):
            profiler.profile_template(f"test{i}.md.jinja2", renderer, context)

        summary = profiler.get_performance_summary()

        assert summary["total_renders"] == 3
        assert "avg_render_time_ms" in summary
        assert "cache_hit_rate" in summary
        assert summary["templates_profiled"] == 3


class TestTemplateHotReloader:
    """Test template hot-reloading functionality."""

    def test_hot_reloader_initialization(self):
        """Test hot reloader initialization."""
        template_dirs = [Path("/tmp/templates")]
        reloader = TemplateHotReloader(template_dirs)

        assert reloader.template_dirs == template_dirs
        assert len(reloader.reload_callbacks) == 0

    def test_register_reload_callback(self):
        """Test callback registration."""
        reloader = TemplateHotReloader([Path("/tmp")])

        callback = Mock()
        reloader.register_reload_callback(callback)

        assert len(reloader.reload_callbacks) == 1
        assert callback in reloader.reload_callbacks

    def test_trigger_reload(self):
        """Test reload triggering."""
        reloader = TemplateHotReloader([Path("/tmp")])

        callback = Mock()
        reloader.register_reload_callback(callback)

        changed_files = ["template1.jinja2", "template2.jinja2"]
        reloader.trigger_reload(changed_files)

        callback.assert_called_once_with(changed_files)


class TestTemplateTestSuite:
    """Test template testing framework."""

    def test_create_template_test_suite(self):
        """Test test suite creation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        suite = create_template_test_suite(renderer, validator, include_standard_tests=False)

        assert isinstance(suite, TemplateTestSuite)
        assert suite.renderer == renderer
        assert suite.validator == validator
        assert len(suite.test_cases) == 0

    def test_generate_standard_test_cases(self):
        """Test standard test case generation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        suite = TemplateTestSuite(renderer, validator)
        suite.generate_standard_test_cases()

        # Should have generated test cases for different template types
        assert len(suite.test_cases) > 0

        # Check for different test types
        test_names = [tc.name for tc in suite.test_cases]
        assert any("python_module" in name for name in test_names)
        assert any("cli_command" in name for name in test_names)
        assert any("openapi_endpoint" in name for name in test_names)

    def test_run_test_case_success(self):
        """Test successful test case execution."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        # Setup successful rendering
        renderer.render_with_boundaries.return_value = "# Test Output\n\nContent here"
        renderer.errors = []
        renderer.clear_errors.return_value = None
        validator.validate_template.return_value = []

        suite = TemplateTestSuite(renderer, validator)

        # Create test case
        generator = SampleDataGenerator()
        element = generator.generate_python_module()

        from bengal.autodoc.template_testing import TemplateTestCase

        test_case = TemplateTestCase(
            name="test_success",
            template_name="test.md.jinja2",
            element_data=element.to_dict(),
            config_data={},
        )

        # Run test
        result = suite.run_test_case(test_case)

        assert result.passed is True
        assert result.content_length > 0
        assert len(result.errors) == 0

    def test_get_test_summary(self):
        """Test test summary generation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)

        suite = TemplateTestSuite(renderer, validator)

        # Add mock results
        from bengal.autodoc.template_testing import TemplateTestResult

        suite.results = [
            TemplateTestResult(
                test_case_name="test1",
                template_name="template1.jinja2",
                passed=True,
                render_time_ms=10.0,
                content_length=100,
                errors=[],
                warnings=[],
            ),
            TemplateTestResult(
                test_case_name="test2",
                template_name="template2.jinja2",
                passed=False,
                render_time_ms=5.0,
                content_length=0,
                errors=["Template error"],
                warnings=[],
            ),
        ]

        summary = suite.get_test_summary()

        assert summary["total_tests"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 50.0


class TestDevelopmentToolsIntegration:
    """Test development tools integration."""

    def test_create_development_tools(self):
        """Test development tools creation."""
        renderer = Mock(spec=SafeTemplateRenderer)
        validator = Mock(spec=TemplateValidator)
        template_dirs = [Path("/tmp/templates")]

        tools = create_development_tools(renderer, validator, template_dirs)

        assert "sample_generator" in tools
        assert "debugger" in tools
        assert "profiler" in tools
        assert "hot_reloader" in tools

        assert isinstance(tools["sample_generator"], SampleDataGenerator)
        assert isinstance(tools["debugger"], TemplateDebugger)
        assert isinstance(tools["profiler"], TemplateProfiler)
        assert isinstance(tools["hot_reloader"], TemplateHotReloader)
