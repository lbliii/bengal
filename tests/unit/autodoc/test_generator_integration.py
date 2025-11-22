"""
Test DocumentationGenerator integration with SafeTemplateRenderer.

Tests the complete integration between the generator and template safety system.
"""

from pathlib import Path
from unittest.mock import patch

from bengal.autodoc.generator import DocumentationGenerator, TemplateCache


class MockExtractor:
    """Mock extractor for testing."""

    def get_template_dir(self):
        return "python"

    def get_output_path(self, element):
        return f"{element.name}.md"


class TestDocumentationGeneratorIntegration:
    """Test DocumentationGenerator integration with template safety."""

    def test_generator_initialization_with_safety_config(self):
        """Test generator initializes with template safety configuration."""
        config = {
            "autodoc": {
                "template_safety": {
                    "error_boundaries": True,
                    "fallback_content": True,
                    "debug_mode": True,
                }
            }
        }

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        assert generator.safety_config.error_boundaries is True
        assert generator.safety_config.fallback_content is True
        assert generator.safety_config.debug_mode is True
        assert generator.safe_renderer is not None
        assert generator.validator is not None
        assert generator.error_reporter is not None

    def test_template_cache_integration(self):
        """Test template cache works with safety configuration."""
        config = {"autodoc": {"template_safety": {"cache_rendered_content": True}}}

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test cache functionality
        cache_stats = generator.template_cache.get_stats()
        assert "size" in cache_stats
        assert "max_size" in cache_stats
        assert "hit_rate" in cache_stats

    def test_error_collection_integration(self):
        """Test error collection works between SafeTemplateRenderer and DocumentationGenerator."""
        config = {
            "autodoc": {"template_safety": {"collect_errors": True, "fallback_content": True}}
        }

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test error reporting methods
        assert generator.has_template_errors() is False
        assert generator.get_error_report() is not None
        assert generator.get_detailed_error_report() is not None

    def test_template_validation_integration(self):
        """Test template validation integration."""
        config = {
            "autodoc": {
                "template_safety": {
                    "validate_templates": False  # Disable to avoid file system dependencies
                }
            }
        }

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test validation method exists
        assert hasattr(generator, "validate_template_syntax")

        # Test validation with mock template
        with patch.object(generator.validator, "validate_template", return_value=[]):
            issues = generator.validate_template_syntax("test.md.jinja2")
            assert issues == []

    def test_template_config_interface(self):
        """Test template configuration interface."""
        config = {"autodoc": {"template_safety": {"debug_mode": True, "cache_templates": True}}}

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test configuration interface
        template_config = generator.get_template_config()

        assert "safety_config" in template_config
        assert "template_directories" in template_config
        assert "cache_stats" in template_config
        assert "error_stats" in template_config

        # Verify safety config is included
        safety_config = template_config["safety_config"]
        assert safety_config["debug_mode"] is True
        assert safety_config["cache_templates"] is True

    def test_template_reloading(self):
        """Test template hot-reloading functionality."""
        config = {"autodoc": {"template_safety": {"validate_templates": False}}}

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test reload functionality
        generator.reload_templates()

        # Verify components are recreated
        assert generator.safe_renderer is not None
        assert generator.validator is not None

    def test_cache_lru_eviction(self):
        """Test LRU cache eviction works correctly."""
        cache = TemplateCache(max_size=3)

        # Fill cache beyond capacity
        cache.set("key1", "content1")
        cache.set("key2", "content2")
        cache.set("key3", "content3")
        cache.set("key4", "content4")  # Should trigger eviction

        # Verify cache size is maintained
        assert len(cache.cache) <= cache.max_size

        # Test cache stats
        stats = cache.get_stats()
        assert stats["size"] <= stats["max_size"]
        assert "hit_rate" in stats
        assert "template_count" in stats

        # Test access time tracking
        assert cache.get("key4") == "content4"  # Should update access time

        # Test cache clearing
        cache.clear()
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0

    def test_error_export_functionality(self):
        """Test error report export functionality."""
        config = {"autodoc": {"template_safety": {"export_error_reports": True}}}

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test export method exists
        assert hasattr(generator, "export_error_report")

        # Test with mock path
        with patch.object(generator.error_reporter, "export_errors_json") as mock_export:
            test_path = Path("/tmp/test_errors.json")
            generator.export_error_report(test_path)
            mock_export.assert_called_once_with(test_path)

    def test_clear_errors_integration(self):
        """Test error clearing works across all components."""
        config = {"autodoc": {"template_safety": {}}}

        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Clear errors should not raise exceptions
        generator.clear_errors()

        # Verify error counts are reset
        assert generator.error_reporter.get_error_count() == 0
        assert generator.safe_renderer.error_count == 0

    def test_template_cache_statistics(self):
        """Test template cache statistics and performance tracking."""
        cache = TemplateCache(max_size=5)

        # Test initial stats
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 5
        assert stats["hit_rate"] == 0.0
        assert stats["template_count"] == 0

        # Add some entries
        cache.set("template1:key1", "content1")
        cache.set("template1:key2", "content2")
        cache.set("template2:key1", "content3")

        # Test updated stats
        stats = cache.get_stats()
        assert stats["size"] == 3
        assert stats["template_count"] == 2  # Two unique templates

        # Test access tracking
        result = cache.get("template1:key1")
        assert result == "content1"

        # Test cache miss
        result = cache.get("nonexistent")
        assert result is None
