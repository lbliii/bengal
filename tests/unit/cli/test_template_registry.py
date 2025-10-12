"""Tests for CLI template registry."""

import pytest

from bengal.cli.templates.registry import (
    TemplateRegistry,
    get_template,
    list_templates,
    register_template,
)


class TestTemplateRegistry:
    """Test TemplateRegistry class."""

    def test_initialization(self):
        """Test creating registry instance."""
        registry = TemplateRegistry()

        assert registry is not None
        assert hasattr(registry, "_templates")
        assert isinstance(registry._templates, dict)

    def test_discovers_templates_on_init(self):
        """Test that templates are discovered on initialization."""
        registry = TemplateRegistry()

        # Should have discovered some templates
        assert len(registry._templates) > 0

    def test_discovers_known_templates(self):
        """Test that known templates are discovered."""
        registry = TemplateRegistry()

        # Known templates that should exist
        known_templates = ["default", "blog", "docs", "portfolio"]

        for template_id in known_templates:
            assert template_id in registry._templates

    def test_get_existing_template(self):
        """Test getting an existing template."""
        registry = TemplateRegistry()

        template = registry.get("default")

        assert template is not None
        assert template.id == "default"
        assert hasattr(template, "description")

    def test_get_missing_template_returns_none(self):
        """Test getting non-existent template returns None."""
        registry = TemplateRegistry()

        template = registry.get("nonexistent")

        assert template is None

    def test_list_returns_tuples(self):
        """Test list() returns list of (id, description) tuples."""
        registry = TemplateRegistry()

        templates = registry.list()

        assert isinstance(templates, list)
        assert len(templates) > 0

        for item in templates:
            assert isinstance(item, tuple)
            assert len(item) == 2
            template_id, description = item
            assert isinstance(template_id, str)
            assert isinstance(description, str)

    def test_list_includes_known_templates(self):
        """Test that list includes known templates."""
        registry = TemplateRegistry()

        templates = registry.list()
        template_ids = [t[0] for t in templates]

        assert "default" in template_ids
        assert "blog" in template_ids
        assert "docs" in template_ids

    def test_exists_for_existing_template(self):
        """Test exists() returns True for existing templates."""
        registry = TemplateRegistry()

        assert registry.exists("default") is True
        assert registry.exists("blog") is True

    def test_exists_for_missing_template(self):
        """Test exists() returns False for missing templates."""
        registry = TemplateRegistry()

        assert registry.exists("nonexistent") is False
        assert registry.exists("fake") is False


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_template_function(self):
        """Test get_template() global function."""
        template = get_template("default")

        assert template is not None
        assert template.id == "default"

    def test_get_template_missing(self):
        """Test get_template() with missing template."""
        template = get_template("nonexistent")

        assert template is None

    def test_list_templates_function(self):
        """Test list_templates() global function."""
        templates = list_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_list_templates_format(self):
        """Test list_templates() returns correct format."""
        templates = list_templates()

        for item in templates:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_register_template_function(self):
        """Test register_template() global function."""
        from bengal.cli.templates.base import SiteTemplate

        # Create a custom template
        custom_template = SiteTemplate(
            id="custom_test",
            name="Custom Test",
            description="A custom test template",
            files=[],
        )

        # Register it
        register_template(custom_template)

        # Should be retrievable
        retrieved = get_template("custom_test")
        assert retrieved is not None
        assert retrieved.id == "custom_test"

        # Should appear in list
        templates = list_templates()
        template_ids = [t[0] for t in templates]
        assert "custom_test" in template_ids


class TestTemplateObjects:
    """Test that templates have required attributes."""

    def test_template_has_id(self):
        """Test that templates have id attribute."""
        template = get_template("default")

        assert hasattr(template, "id")
        assert isinstance(template.id, str)
        assert len(template.id) > 0

    def test_template_has_description(self):
        """Test that templates have description attribute."""
        template = get_template("default")

        assert hasattr(template, "description")
        assert isinstance(template.description, str)

    def test_template_has_name(self):
        """Test that templates have name attribute."""
        template = get_template("blog")

        assert hasattr(template, "name")
        assert isinstance(template.name, str)

    def test_template_has_files(self):
        """Test that templates have files attribute."""
        template = get_template("default")

        assert hasattr(template, "files")
        # Files should be a list
        assert isinstance(template.files, list)

    def test_blog_template_structure(self):
        """Test blog template has expected structure."""
        template = get_template("blog")

        assert template.id == "blog"
        assert "blog" in template.description.lower() or "blog" in template.name.lower()
        # Should have some files defined
        assert len(template.files) > 0

    def test_docs_template_structure(self):
        """Test docs template has expected structure."""
        template = get_template("docs")

        assert template.id == "docs"
        assert (
            "doc" in template.description.lower()
            or "doc" in template.name.lower()
            or "documentation" in template.description.lower()
        )

    def test_portfolio_template_structure(self):
        """Test portfolio template has expected structure."""
        template = get_template("portfolio")

        assert template.id == "portfolio"
        assert "portfolio" in template.description.lower() or "portfolio" in template.name.lower()


class TestTemplateFiles:
    """Test template file structures."""

    def test_template_files_are_template_file_objects(self):
        """Test that template files have correct structure."""
        template = get_template("default")

        for file in template.files:
            # Should have relative_path and content
            assert hasattr(file, "relative_path")
            assert hasattr(file, "content")

    def test_template_file_paths_are_relative(self):
        """Test that template file paths are relative."""
        template = get_template("blog")

        for file in template.files:
            # Paths should not start with /
            assert not file.relative_path.startswith("/")

    def test_template_has_index_page(self):
        """Test that templates have an index page."""
        template = get_template("default")

        # Should have at least one index file
        paths = [f.relative_path for f in template.files]
        has_index = any("index" in path.lower() for path in paths)

        assert has_index


class TestRegistrySingleton:
    """Test that registry uses singleton pattern."""

    def test_get_template_uses_same_registry(self):
        """Test that multiple calls use same registry instance."""
        # Call multiple times
        template1 = get_template("default")
        template2 = get_template("default")

        # Should be the same object (same registry instance)
        assert template1 is template2

    def test_list_templates_consistent(self):
        """Test that list_templates() returns consistent results."""
        list1 = list_templates()
        list2 = list_templates()

        # Should return same data
        assert len(list1) == len(list2)
        assert set(t[0] for t in list1) == set(t[0] for t in list2)


class TestTemplateDiscovery:
    """Test template discovery mechanism."""

    def test_discovers_all_template_modules(self):
        """Test that all template modules are discovered."""
        templates = list_templates()
        template_ids = [t[0] for t in templates]

        # Check for known templates
        expected_templates = ["default", "blog", "docs", "portfolio", "landing", "resume"]

        for expected in expected_templates:
            assert expected in template_ids, f"Expected template '{expected}' not found"

    def test_skips_non_template_modules(self):
        """Test that non-template modules are skipped."""
        registry = TemplateRegistry()

        # Should not include internal modules
        template_ids = list(registry._templates.keys())
        assert "base" not in template_ids
        assert "registry" not in template_ids
        assert "__pycache__" not in template_ids


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_template_with_none(self):
        """Test getting template with None."""
        template = get_template(None)

        assert template is None

    def test_get_template_with_empty_string(self):
        """Test getting template with empty string."""
        template = get_template("")

        assert template is None

    def test_exists_with_none(self):
        """Test exists() with None."""
        registry = TemplateRegistry()

        # Should handle gracefully
        result = registry.exists(None)
        assert result is False

    def test_register_duplicate_template(self):
        """Test registering template with duplicate ID."""
        from bengal.cli.templates.base import SiteTemplate

        custom1 = SiteTemplate(id="duplicate_test", name="First", description="First", files=[])

        custom2 = SiteTemplate(id="duplicate_test", name="Second", description="Second", files=[])

        register_template(custom1)
        register_template(custom2)

        # Last one should win
        retrieved = get_template("duplicate_test")
        assert retrieved.name == "Second"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_list_available_templates_for_user(self):
        """Test listing templates for user selection."""
        templates = list_templates()

        # Should have multiple options
        assert len(templates) >= 4

        # Each should have meaningful description
        for template_id, description in templates:
            assert len(template_id) > 0
            assert len(description) > 0

    def test_get_specific_template_for_initialization(self):
        """Test getting a specific template for site initialization."""
        # User selects "blog" template
        template = get_template("blog")

        # Should get template with files
        assert template is not None
        assert len(template.files) > 0

        # Files should have content
        for file in template.files:
            assert file.content is not None

    def test_check_template_exists_before_using(self):
        """Test checking if template exists before using it."""
        user_choice = "blog"

        from bengal.cli.templates.registry import _get_registry

        registry = _get_registry()

        if registry.exists(user_choice):
            template = registry.get(user_choice)
            assert template is not None
        else:
            pytest.fail("Template should exist")
