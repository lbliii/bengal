"""Unit tests for template context validation (Kida validate_context)."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestValidateTemplateContexts:
    """Tests for validate_template_contexts() using Kida's validate_context()."""

    @pytest.fixture
    def site_with_missing_var_template(self, tmp_path: Path) -> Path:
        """Create a site with a template that references an undefined variable."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        # Template references custom_var which won't be in sample context
        (templates_dir / "needs_custom.html").write_text(
            """<!DOCTYPE html>
<html>
<body>
  <h1>{{ page.title }}</h1>
  <p>Custom: {{ custom_var }}</p>
</body>
</html>
"""
        )

        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
        )
        return tmp_path

    def test_validates_context_and_reports_missing_vars(self, site_with_missing_var_template: Path):
        """validate_template_contexts reports templates with missing context vars."""
        from bengal.core.site import Site
        from bengal.rendering.engines import create_engine
        from bengal.rendering.template_context_validation import (
            validate_template_contexts,
        )

        site = Site.from_config(site_with_missing_var_template, None)
        engine = create_engine(site)

        errors = validate_template_contexts(engine, site, template_names=["needs_custom.html"])

        assert len(errors) >= 1
        err = errors[0]
        assert err.template == "needs_custom.html"
        assert "custom_var" in err.missing_vars
        assert "custom_var" in err.message

    def test_context_errors_to_template_errors(self):
        """context_errors_to_template_errors converts to TemplateError list."""
        from bengal.rendering.template_context_validation import (
            TemplateContextError,
            context_errors_to_template_errors,
        )

        context_errors = [
            TemplateContextError(
                template="test.html",
                missing_vars=["foo", "bar"],
                message="Missing context variables: bar, foo",
            )
        ]
        template_errors = context_errors_to_template_errors(context_errors)

        assert len(template_errors) == 1
        assert template_errors[0].template == "test.html"
        assert template_errors[0].message == "Missing context variables: bar, foo"
        assert template_errors[0].error_type == "undefined"
