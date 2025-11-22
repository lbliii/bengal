"""
Test that the legacy template system has been completely replaced.

Verifies that only SafeTemplateRenderer is used and no legacy code remains.
"""

from pathlib import Path
from unittest.mock import Mock

from bengal.autodoc.base import DocElement
from bengal.autodoc.generator import DocumentationGenerator


class MockExtractor:
    """Mock extractor for testing."""

    def get_output_path(self, element):
        return f"{element.name}.md"


class TestTemplateSystemReplacement:
    """Test complete replacement of legacy template system."""

    def test_no_legacy_template_fallbacks(self):
        """Test that no legacy template fallback mechanisms exist."""
        config = {"autodoc": {"template_safety": {}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Test template name resolution uses new structure
        element = DocElement(
            name="test_module",
            element_type="module",
            qualified_name="test.module",
            description="Test module",
        )

        template_name = generator._get_template_name(element)

        # Should use new unified structure
        assert template_name == "python/module.md.jinja2"
        assert "/" in template_name  # Indicates subdirectory structure

    def test_unified_template_directories(self):
        """Test that template directories use unified structure."""
        config = {"autodoc": {"template_safety": {}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        template_dirs = generator._get_template_directories()

        # Should include unified template directory
        # At least one directory should be the unified structure
        assert any("templates" in str(d) for d in template_dirs)

    def test_template_name_mapping_uses_subdirectories(self):
        """Test that all template names use subdirectory structure."""
        config = {"autodoc": {"template_safety": {}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        test_cases = [
            ("module", "python/module.md.jinja2"),
            ("class", "python/class.md.jinja2"),
            ("function", "python/function.md.jinja2"),
            ("command", "cli/command.md.jinja2"),
            ("command-group", "cli/command_group.md.jinja2"),
            ("endpoint", "openapi/endpoint.md.jinja2"),
            ("schema", "openapi/schema.md.jinja2"),
        ]

        # Mock the template existence check
        from unittest.mock import patch

        with patch.object(generator.env, "get_template") as mock_get_template:
            mock_get_template.return_value = Mock()  # Simulate template exists

            for element_type, expected_template in test_cases:
                element = DocElement(
                    name="test",
                    element_type=element_type,
                    qualified_name="test",
                    description="Test element",
                )

                template_name = generator._get_template_name(element)
                assert template_name == expected_template
                assert "/" in template_name  # Must use subdirectory structure

    def test_no_legacy_imports(self):
        """Test that generator doesn't import unnecessary Jinja2 components."""
        # Should only import TemplateNotFound, not Environment or FileSystemLoader
        import inspect

        import bengal.autodoc.generator as generator_module

        source = inspect.getsource(generator_module)

        assert "from jinja2 import TemplateNotFound" in source
        assert "from jinja2 import Environment" not in source
        assert "from jinja2 import FileSystemLoader" not in source

    def test_safe_template_renderer_exclusive_usage(self):
        """Test that only SafeTemplateRenderer is used for rendering."""
        config = {"autodoc": {"template_safety": {}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Should have SafeTemplateRenderer
        assert hasattr(generator, "safe_renderer")
        assert generator.safe_renderer is not None

        # Should not have direct Jinja2 environment usage for rendering
        assert not hasattr(generator, "jinja_env")
        assert not hasattr(generator, "template_env")

    def test_template_validation_discovery_uses_unified_structure(self):
        """Test that template discovery uses unified structure."""
        config = {"autodoc": {"template_safety": {"validate_templates": False}}}
        extractor = MockExtractor()
        generator = DocumentationGenerator(extractor, config)

        # Get discovered template names
        template_names = generator._discover_template_names()

        # All template names should use subdirectory structure
        for template_name in template_names:
            assert "/" in template_name, (
                f"Template {template_name} should use subdirectory structure"
            )
            # Allow doc type subdirectories and shared infrastructure directories
            assert template_name.startswith(("python/", "cli/", "openapi/", "base/", "macros/")), (
                f"Template {template_name} should start with doc type or infrastructure subdirectory"
            )

    def test_no_backward_compatibility_flags(self):
        """Test that no backward compatibility flags exist in configuration."""
        from bengal.autodoc.template_config import TemplateSafetyConfig

        config = TemplateSafetyConfig()
        config_dict = config.to_dict()

        # Should not have any legacy or compatibility flags
        legacy_flags = [
            "legacy_mode",
            "backward_compatibility",
            "old_template_support",
            "fallback_to_old",
            "enable_legacy",
            "compat_mode",
        ]

        for flag in legacy_flags:
            assert flag not in config_dict, f"Found legacy flag: {flag}"

    def test_clean_template_directory_structure(self):
        """Test that template directory has clean structure without legacy files."""
        template_dir = Path(__file__).parent.parent.parent / "bengal/autodoc/templates"

        if template_dir.exists():
            # Should have subdirectories for each doc type
            expected_subdirs = ["python", "cli", "openapi", "base", "macros"]

            for subdir in expected_subdirs:
                subdir_path = template_dir / subdir
                if subdir_path.exists():
                    assert subdir_path.is_dir(), f"{subdir} should be a directory"

            # Should not have any legacy template files in root
            root_templates = list(template_dir.glob("*.jinja2"))
            assert len(root_templates) == 0, f"Found legacy templates in root: {root_templates}"
