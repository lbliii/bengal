"""
Unit tests for TemplateEngine.validate_templates() method.

Tests proactive template syntax validation functionality.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestValidateTemplates:
    """Tests for TemplateEngine.validate_templates()."""

    @pytest.fixture
    def valid_template_site(self, tmp_path: Path):
        """Create a site with valid templates."""
        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create valid templates
        (templates_dir / "page.html").write_text(
            """<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
    {% if page.content %}
        {{ page.content }}
    {% endif %}
</body>
</html>
"""
        )

        (templates_dir / "list.html").write_text(
            """<!DOCTYPE html>
<html>
<body>
    {% for item in items %}
        <div>{{ item.name }}</div>
    {% endfor %}
</body>
</html>
"""
        )

        # Create config
        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )

        return tmp_path

    @pytest.fixture
    def broken_template_site(self, tmp_path: Path):
        """Create a site with a broken template."""
        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create valid template
        (templates_dir / "page.html").write_text(
            """<!DOCTYPE html>
<html>
<body>{{ content }}</body>
</html>
"""
        )

        # Create broken template (missing endif)
        (templates_dir / "broken.html").write_text(
            """<!DOCTYPE html>
<html>
<body>
    {% if page.title %}
        <h1>{{ page.title }}</h1>
    {# Missing endif #}
</body>
</html>
"""
        )

        # Create config
        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )

        return tmp_path

    @pytest.fixture
    def multiple_broken_templates_site(self, tmp_path: Path):
        """Create a site with multiple broken templates."""
        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        partials_dir = templates_dir / "partials"
        partials_dir.mkdir()

        # Create broken template 1 (missing endif)
        (templates_dir / "broken1.html").write_text(
            """<html><body>
{% if test %}content
</body></html>
"""
        )

        # Create broken template 2 (unclosed tag)
        (templates_dir / "broken2.html").write_text(
            """<html><body>
{{ undefined_filter | bad_filter }}
{% for item in items
</body></html>
"""
        )

        # Create valid template
        (templates_dir / "valid.html").write_text(
            """<html><body>{{ content }}</body></html>
"""
        )

        # Create config
        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )

        return tmp_path

    def test_valid_templates_returns_empty_list(self, valid_template_site: Path):
        """Test that valid templates return an empty error list."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(valid_template_site, None)
        engine = create_engine(site)

        errors = engine.validate_templates()

        assert errors == [], f"Expected no errors, got: {errors}"

    def test_broken_template_returns_error(self, broken_template_site: Path):
        """Test that a broken template returns a TemplateError."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(broken_template_site, None)
        engine = create_engine(site)

        errors = engine.validate_templates()

        assert len(errors) >= 1, "Expected at least one error"

        # Check error properties (TemplateRenderError has message, template_context)
        error = errors[0]
        assert hasattr(error, "message")
        assert hasattr(error, "template_context")

    def test_multiple_broken_templates_returns_all_errors(
        self, multiple_broken_templates_site: Path
    ):
        """Test that multiple broken templates return all errors."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(multiple_broken_templates_site, None)
        engine = create_engine(site)

        errors = engine.validate_templates()

        # Should have at least 2 errors (one for each broken template)
        assert len(errors) >= 2, f"Expected at least 2 errors, got {len(errors)}"

        # All should have error messages and template_context
        for error in errors:
            assert hasattr(error, "message")
            assert hasattr(error, "template_context")

    def test_include_patterns_filters_validation(self, broken_template_site: Path):
        """Test that patterns limits which templates are validated."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(broken_template_site, None)
        engine = create_engine(site)

        # Validate only page.html (which is valid)
        errors = engine.validate_templates(include_patterns=["page.html"])

        assert len(errors) == 0, "Expected no errors when validating only page.html"

        # Validate only broken.html (which has syntax error)
        errors = engine.validate_templates(include_patterns=["broken.html"])

        assert len(errors) >= 1, "Expected error when validating broken.html"

    def test_error_includes_template_name(self, broken_template_site: Path):
        """Test that error includes the template name."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(broken_template_site, None)
        engine = create_engine(site)

        errors = engine.validate_templates()

        assert len(errors) >= 1

        # Find the error for our broken template (may be others from bundled theme)
        broken_error = None
        for error in errors:
            # validate_templates() returns TemplateRenderError objects, not TemplateError
            template_name = getattr(error.template_context, "template_name", None)
            if template_name and "broken.html" in template_name:
                broken_error = error
                break

        assert broken_error is not None, "Expected error for broken.html template"
        assert hasattr(broken_error, "template_context")
        assert "broken.html" in broken_error.template_context.template_name


class TestValidateTemplatesEdgeCases:
    """Edge case tests for validate_templates()."""

    @pytest.fixture
    def empty_templates_site(self, tmp_path: Path):
        """Create a site with no templates."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )

        return tmp_path

    def test_empty_templates_directory(self, empty_templates_site: Path):
        """Test that an empty custom templates directory doesn't cause errors."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(empty_templates_site, None)
        engine = create_engine(site)

        # Should not raise - validates bundled theme templates
        errors = engine.validate_templates()

        # All bundled theme templates should be valid (no syntax errors)
        # Note: This tests that our bundled theme has no syntax errors
        assert len(errors) == 0, f"Bundled theme has syntax errors: {errors}"

    def test_nonexistent_patterns_returns_empty(self, tmp_path: Path):
        """Test that patterns matching no files return empty list."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "page.html").write_text("<html>{{ content }}</html>")

        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )

        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine

        site = Site.from_config(tmp_path, None)
        engine = create_engine(site)

        # Pattern that matches nothing in custom templates
        errors = engine.validate(patterns=["nonexistent/*.html"])

        # May have bundled theme templates, but shouldn't have our custom ones
        assert len(errors) == 0, "Expected no errors for nonexistent pattern"
