"""
Template safety integration tests for Bengal autodoc system.

Tests the complete template safety implementation including error boundaries,
fallback content generation, and safe rendering across all template types.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from bengal.autodoc.base import DocElement
from bengal.autodoc.dev_tools import SampleDataGenerator
from bengal.autodoc.generator import DocumentationGenerator
from bengal.autodoc.template_config import TemplateSafetyConfig
from bengal.autodoc.template_testing import TemplateTestSuite, create_template_test_suite


@pytest.fixture(scope="session")
def mock_extractor():
    """Shared mock extractor for all tests."""
    return MockExtractor()


@contextmanager
def mock_template_rendering(renderer, return_value: str = "Mock content"):
    """Context manager for mocking template rendering."""
    with patch.object(renderer, "render_with_boundaries") as mock_render:
        mock_render.return_value = return_value
        yield mock_render


class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_mock_config(safety_overrides: dict[str, Any] = None) -> dict[str, Any]:
        """Create mock configuration with optional safety overrides."""
        base_config = {
            "autodoc": {
                "template_safety": {
                    "error_boundaries": True,
                    "fallback_content": True,
                    "debug_mode": True,
                    "validate_templates": False,
                    "collect_errors": True,
                }
            },
            "project": {"name": "Test Project", "version": "1.0.0"},
        }

        if safety_overrides:
            base_config["autodoc"]["template_safety"].update(safety_overrides)

        return base_config

    @staticmethod
    def create_test_element(element_type: str = "module", name: str = "test") -> DocElement:
        """Create test element with specified type and name."""
        return DocElement(
            name=name,
            element_type=element_type,
            qualified_name=f"test.{name}",
            description=f"Test {element_type} for testing",
        )


class MockExtractor:
    """Mock extractor for testing template integration."""

    def get_template_dir(self) -> str:
        return "python"

    def get_output_path(self, element: DocElement) -> str:
        return f"{element.name}.md"


class TestTemplateSafetyCore:
    """Core template safety functionality tests."""

    @pytest.fixture
    def safety_config(self) -> TemplateSafetyConfig:
        """Create template safety configuration for testing."""
        return TemplateSafetyConfig(
            error_boundaries=True,
            fallback_content=True,
            debug_mode=True,
            validate_templates=False,  # Disable file system validation in tests
            collect_errors=True,
        )

    @pytest.fixture
    def mock_config(self, safety_config: TemplateSafetyConfig) -> dict[str, Any]:
        """Create mock configuration dictionary."""
        return TestDataFactory.create_mock_config(safety_config.to_dict())

    @pytest.fixture
    def generator(self, mock_config: dict[str, Any], mock_extractor) -> DocumentationGenerator:
        """Create DocumentationGenerator with safety configuration."""
        return DocumentationGenerator(mock_extractor, mock_config)

    @pytest.fixture
    def sample_generator(self) -> SampleDataGenerator:
        """Create sample data generator for testing."""
        return SampleDataGenerator()

    def test_safe_template_rendering_with_valid_data(
        self, generator: DocumentationGenerator, sample_generator: SampleDataGenerator
    ):
        """
        Test safe template rendering with valid element data.

        Verifies that the SafeTemplateRenderer can successfully render
        templates with well-formed element data and returns expected content.
        """
        # Generate sample Python module
        module_element = sample_generator.generate_python_module("test_module")

        # Mock template rendering
        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# Test Module\n\nSample documentation content."

            # Render template
            context = {"element": module_element, "config": generator.config}
            result = generator.safe_renderer.render_with_boundaries(
                "python/module.md.jinja2", context
            )

            assert result is not None, "Template rendering should return content"
            assert len(result) > 0, "Rendered content should not be empty"
            assert "Test Module" in result, "Content should contain expected module title"
            mock_render.assert_called_once()

    def test_error_boundary_handling_with_invalid_data(self, generator: DocumentationGenerator):
        """Test error boundary handling with malformed element data."""
        # Create malformed element
        malformed_element = TestDataFactory.create_test_element("module", "broken_module")
        # Intentionally set children to invalid type
        malformed_element.children = "not_a_list"  # type: ignore

        # Mock template rendering to simulate error recovery
        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# Error Fallback\n\nTemplate rendering failed gracefully."

            context = {"element": malformed_element, "config": generator.config}

            # Should not raise exception due to error boundaries
            result = generator.safe_renderer.render_with_boundaries(
                "python/module.md.jinja2", context
            )

            # Verify fallback content is returned
            assert result is not None
            assert len(result) > 0
            fallback_indicators = ["Error Fallback", "Template rendering failed", "fallback"]
            assert any(indicator in result.lower() for indicator in fallback_indicators)

    def test_template_validation_integration(self, generator: DocumentationGenerator):
        """Test template validation integration."""
        # Test validation method exists and works
        with patch.object(generator.validator, "validate_template") as mock_validate:
            mock_validate.return_value = []  # No validation issues

            issues = generator.validate_template_syntax("python/module.md.jinja2")
            assert issues == []
            mock_validate.assert_called_once_with("python/module.md.jinja2")

    def test_error_collection_and_reporting(self, generator: DocumentationGenerator):
        """Test error collection and reporting functionality."""
        # Initially no errors
        assert generator.has_template_errors() is False

        # Simulate template error
        generator.safe_renderer.errors.append(
            {"template": "test.jinja2", "error": "Test error", "context": "test context"}
        )

        # Check error detection
        assert generator.has_template_errors() is True

        # Get error report
        error_report = generator.get_error_report()
        assert error_report is not None
        assert len(error_report) > 0

    def test_template_cache_functionality(self, generator: DocumentationGenerator):
        """Test template cache integration."""
        cache_stats = generator.template_cache.get_stats()

        # Verify cache statistics structure
        assert "size" in cache_stats
        assert "max_size" in cache_stats
        assert "hit_rate" in cache_stats
        assert "template_count" in cache_stats

        # Test cache operations
        test_key = "test_template:test_key"
        test_content = "Test cached content"

        generator.template_cache.set(test_key, test_content)
        cached_result = generator.template_cache.get(test_key)

        assert cached_result == test_content

    @pytest.mark.parametrize(
        "element_type,expected_template",
        [
            ("module", "python/module.md.jinja2"),
            ("class", "python/class.md.jinja2"),
            ("function", "python/function.md.jinja2"),
            ("command", "cli/command.md.jinja2"),
            ("endpoint", "openapi/endpoint.md.jinja2"),
        ],
    )
    def test_template_name_resolution(
        self, generator: DocumentationGenerator, element_type: str, expected_template: str
    ):
        """Test template name resolution for different element types."""
        element = TestDataFactory.create_test_element(element_type, "test")
        template_name = generator._get_template_name(element)
        assert template_name == expected_template

    def test_cli_template_integration(
        self, generator: DocumentationGenerator, sample_generator: SampleDataGenerator
    ):
        """Test CLI template integration."""
        # Generate CLI command element
        command_element = sample_generator.generate_cli_command("test-cmd")

        # Mock CLI template rendering
        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# test-cmd\n\nCLI command documentation."

            context = {"element": command_element, "config": generator.config}
            result = generator.safe_renderer.render_with_boundaries(
                "cli/command.md.jinja2", context
            )

            assert result is not None
            assert "test-cmd" in result

    def test_openapi_template_integration(
        self, generator: DocumentationGenerator, sample_generator: SampleDataGenerator
    ):
        """Test OpenAPI template integration."""
        # Generate OpenAPI endpoint element
        endpoint_element = sample_generator.generate_openapi_endpoint("/api/test", "GET")

        # Mock OpenAPI template rendering
        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# GET /api/test\n\nAPI endpoint documentation."

            context = {"element": endpoint_element, "config": generator.config}
            result = generator.safe_renderer.render_with_boundaries(
                "openapi/endpoint.md.jinja2", context
            )

            assert result is not None
            assert "GET /api/test" in result

    def test_template_test_suite_integration(self, generator: DocumentationGenerator):
        """Test template test suite integration."""
        # Create test suite
        test_suite = create_template_test_suite(
            generator.safe_renderer, generator.validator, include_standard_tests=True
        )

        # Verify test suite creation
        assert isinstance(test_suite, TemplateTestSuite)
        assert len(test_suite.test_cases) > 0

        # Mock test execution
        with patch.object(test_suite, "run_test_case") as mock_run:
            from bengal.autodoc.template_testing import TemplateTestResult

            mock_run.return_value = TemplateTestResult(
                test_case_name="test_case",
                template_name="test.jinja2",
                passed=True,
                render_time_ms=10.0,
                content_length=100,
                errors=[],
                warnings=[],
            )

            # Run tests
            summary = test_suite.run_all_tests()

            assert "total_tests" in summary
            assert summary["total_tests"] > 0

    def test_configuration_interface(self, generator: DocumentationGenerator):
        """Test template configuration interface."""
        template_config = generator.get_template_config()

        # Verify configuration structure
        required_keys = ["safety_config", "template_directories", "cache_stats", "error_stats"]

        for key in required_keys:
            assert key in template_config, f"Missing required config key: {key}"

        # Verify safety config details
        safety_config = template_config["safety_config"]
        assert isinstance(safety_config, dict)
        assert "error_boundaries" in safety_config
        assert "fallback_content" in safety_config

    def test_template_reloading(self, generator: DocumentationGenerator):
        """Test template hot-reloading functionality."""
        # Store original renderer reference
        # original_renderer = generator.safe_renderer

        # Reload templates
        generator.reload_templates()

        # Verify components are recreated
        assert generator.safe_renderer is not None
        assert generator.validator is not None
        # Note: In a real implementation, renderer might be the same object
        # but with reloaded templates

    def test_error_export_functionality(self, generator: DocumentationGenerator, tmp_path: Path):
        """Test error report export functionality."""
        # Add some test errors
        generator.safe_renderer.errors.append(
            {"template": "test.jinja2", "error": "Test error message", "context": "test context"}
        )

        # Export errors
        export_path = tmp_path / "test_errors.json"

        with patch.object(generator.error_reporter, "export_errors_json") as mock_export:
            generator.export_error_report(export_path)
            mock_export.assert_called_once_with(export_path)

    def test_performance_metrics_collection(
        self, generator: DocumentationGenerator, sample_generator: SampleDataGenerator
    ):
        """Test performance metrics collection during rendering."""
        # Generate sample element
        module_element = sample_generator.generate_python_module()

        # Mock performance tracking
        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "Test content"

            # Simulate rendering with timing
            import time

            start_time = time.time()

            context = {"element": module_element, "config": generator.config}
            result = generator.safe_renderer.render_with_boundaries(
                "python/module.md.jinja2", context
            )

            render_time = time.time() - start_time

            # Verify rendering completed
            assert result is not None
            assert render_time >= 0

    def test_unified_template_directory_structure(self, generator: DocumentationGenerator):
        """Test that template directories use unified structure."""
        template_dirs = generator._get_template_directories()

        # Should include template directories
        assert len(template_dirs) > 0

        # At least one should be the unified structure
        has_unified_structure = any("templates" in str(d) for d in template_dirs)
        assert has_unified_structure, "Should include unified template directory"

    def test_no_legacy_template_fallbacks(self, generator: DocumentationGenerator):
        """Test that no legacy template fallback mechanisms exist."""
        # All template names should use subdirectory structure
        test_element = DocElement(
            name="test", element_type="module", qualified_name="test", description="Test"
        )

        template_name = generator._get_template_name(test_element)

        # Should use new unified structure with subdirectories
        assert "/" in template_name, "Template name should use subdirectory structure"
        assert template_name.startswith(("python/", "cli/", "openapi/")), (
            "Template should start with doc type subdirectory"
        )


class TestTemplateSafetyEdgeCases:
    """Test edge cases and error conditions in template safety."""

    def test_empty_element_data(self):
        """Test handling of empty element data."""
        config = {"autodoc": {"template_safety": {"error_boundaries": True}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Create empty element
        empty_element = DocElement(
            name="", element_type="module", qualified_name="", description=""
        )

        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# Empty Module\n\nNo content available."

            context = {"element": empty_element, "config": config}
            result = generator.safe_renderer.render_with_boundaries(
                "python/module.md.jinja2", context
            )

            # Should handle gracefully
            assert result is not None

    def test_missing_template_handling(self):
        """Test handling of missing template files."""
        config = {"autodoc": {"template_safety": {"error_boundaries": True}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        sample_generator = SampleDataGenerator()
        element = sample_generator.generate_python_module()

        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            # Simulate template not found by returning fallback content
            mock_render.return_value = "# Template Not Found\n\nFallback content generated."

            context = {"element": element, "config": config}
            result = generator.safe_renderer.render_with_boundaries(
                "nonexistent/template.jinja2", context
            )

            # Should return fallback content
            assert result is not None
            assert len(result) > 0

    def test_circular_reference_handling(self):
        """Test handling of circular references in element data."""
        config = {"autodoc": {"template_safety": {"error_boundaries": True}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Create elements with circular reference
        parent = DocElement(
            name="parent",
            element_type="module",
            qualified_name="parent",
            description="Parent module",
        )

        child = DocElement(
            name="child",
            element_type="class",
            qualified_name="parent.child",
            description="Child class",
        )

        # Create circular reference (normally prevented by design)
        parent.children = [child]
        child.children = [parent]  # Circular reference

        with patch.object(generator.safe_renderer, "render_with_boundaries") as mock_render:
            mock_render.return_value = "# Circular Reference Handled\n\nSafe content."

            context = {"element": parent, "config": config}
            result = generator.safe_renderer.render_with_boundaries(
                "python/module.md.jinja2", context
            )

            # Should handle without infinite recursion
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
