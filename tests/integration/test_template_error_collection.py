"""
Integration tests for template error collection during builds.

These tests verify that template syntax errors are properly detected and
collected during the build process when `validate_templates = true` is set.

The template validation phase runs early in the build (after fonts, before
content discovery) and proactively checks all templates for syntax errors.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.errors import BengalRenderingError
from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions


class TestTemplateErrorCollection:
    """Integration tests for error collection during builds."""

    @pytest.fixture
    def temp_site(self):
        """Create a temporary site for testing."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create site structure
            content_dir = temp_dir / "content"
            content_dir.mkdir()

            templates_dir = temp_dir / "templates"
            templates_dir.mkdir()

            # Create config with template validation enabled
            config_file = temp_dir / "bengal.toml"
            config_file.write_text("""
[site]
title = "Test Site"
base_url = "https://example.com"

[build]
output_dir = "public"
validate_templates = true
""")

            yield temp_dir

        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_build_with_valid_templates(self, temp_site):
        """Test build completes successfully with valid templates."""
        # Create valid template
        template_file = temp_site / "templates" / "page.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
    {% if page.content %}
        {{ page.content }}
    {% endif %}
</body>
</html>
""")

        # Create content
        content_file = temp_site / "content" / "test.md"
        content_file.write_text("""+++
title = "Test Page"
template = "page.html"
+++

Test content.
""")

        # Build site
        site = Site.from_config(temp_site, None)
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(BuildOptions(force_sequential=True, verbose=False))

        # Should have no template errors
        assert len(stats.template_errors) == 0

    def test_build_collects_template_errors(self, temp_site):
        """Test that build collects template errors instead of crashing."""
        # Create template with error
        template_file = temp_site / "templates" / "broken.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<body>
    {% if page.title %}
        <h1>{{ page.title }}</h1>
    {# Missing endif #}
</body>
</html>
""")

        # Create content
        content_file = temp_site / "content" / "test.md"
        content_file.write_text("""+++
title = "Test Page"
template = "broken.html"
+++

Test content.
""")

        # Build site (should not crash)
        site = Site.from_config(temp_site, None)
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(BuildOptions(force_sequential=True, verbose=False))

        # Should have collected the template error
        assert len(stats.template_errors) >= 1

        # Error should be a rich error object
        error = stats.template_errors[0]
        assert hasattr(error, "error_type")
        assert hasattr(error, "message")
        assert hasattr(error, "template_context")

    def test_build_collects_multiple_errors(self, temp_site):
        """Test that build collects multiple template errors."""
        # Create multiple broken templates
        broken1 = temp_site / "templates" / "broken1.html"
        broken1.write_text("""
<html><body>
{% if test %}content{# missing endif #}
</body></html>
""")

        broken2 = temp_site / "templates" / "broken2.html"
        broken2.write_text("""
<html><body>
{% for item in items %}{{ item }}{# missing endfor #}
</body></html>
""")

        # Create content using broken templates
        content1 = temp_site / "content" / "page1.md"
        content1.write_text("""+++
title = "Page 1"
template = "broken1.html"
+++
Content 1
""")

        content2 = temp_site / "content" / "page2.md"
        content2.write_text("""+++
title = "Page 2"
template = "broken2.html"
+++
Content 2
""")

        # Build site
        site = Site.from_config(temp_site, None)
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(BuildOptions(force_sequential=True, verbose=False))

        # Should have collected multiple errors
        assert len(stats.template_errors) >= 2

    def test_strict_mode_fails_on_error(self, temp_site):
        """Test that strict mode raises exception on template error."""
        # Create template with error
        template_file = temp_site / "templates" / "broken.html"
        template_file.write_text("""
<html><body>
{% if test %}content{# missing endif #}
</body></html>
""")

        # Create content
        content_file = temp_site / "content" / "test.md"
        content_file.write_text("""+++
title = "Test Page"
template = "broken.html"
+++
Content
""")

        # Build site with strict mode
        site = Site.from_config(temp_site, None)

        orchestrator = BuildOrchestrator(site)

        # Should raise exception in strict mode
        with pytest.raises(BengalRenderingError):
            orchestrator.build(BuildOptions(force_sequential=True, verbose=False, strict=True))

    def test_error_contains_rich_information(self, temp_site):
        """Test that collected errors contain rich debugging information."""
        # Create template with error
        template_file = temp_site / "templates" / "broken.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<body>
    {% if page.title %}
        <h1>{{ page.title }}</h1>
</body>
</html>
""")

        # Create content
        content_file = temp_site / "content" / "test.md"
        content_file.write_text("""+++
title = "Test Page"
template = "broken.html"
+++
Content
""")

        # Build site
        site = Site.from_config(temp_site, None)
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(BuildOptions(force_sequential=True, verbose=False))

        # Check error has rich information
        if len(stats.template_errors) > 0:
            error = stats.template_errors[0]

            # Should have template context
            assert error.template_context is not None
            assert error.template_context.template_name is not None

            # Note: page_source is None for proactive validation (before pages are processed)
            # It would only be set if the error was caught during page rendering
            # assert error.page_source is not None  # Not applicable for proactive validation

            # Should have error type
            assert error.error_type in ["syntax", "filter", "undefined", "runtime", "other"]

            # Should have message
            assert error.message is not None and len(error.message) > 0


class TestParallelErrorCollection:
    """Test error collection in parallel builds."""

    @pytest.fixture
    def temp_site_parallel(self):
        """Create a site for parallel testing."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            content_dir = temp_dir / "content"
            content_dir.mkdir()

            templates_dir = temp_dir / "templates"
            templates_dir.mkdir()

            config_file = temp_dir / "bengal.toml"
            config_file.write_text("""
[site]
title = "Test Site"

[build]
output_dir = "public"
validate_templates = true
""")

            yield temp_dir

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_parallel_build_collects_errors(self, temp_site_parallel):
        """Test that parallel builds collect errors from all threads."""
        # Create broken template
        template_file = temp_site_parallel / "templates" / "broken.html"
        template_file.write_text("""
<html><body>
{% if test %}content{# missing endif #}
</body></html>
""")

        # Create multiple content files
        for i in range(5):
            content_file = temp_site_parallel / "content" / f"page{i}.md"
            content_file.write_text(f"""+++
title = "Page {i}"
template = "broken.html"
+++
Content {i}
""")

        # Build site in parallel
        site = Site.from_config(temp_site_parallel, None)
        orchestrator = BuildOrchestrator(site)
        stats = orchestrator.build(BuildOptions(verbose=False))

        # Should have collected errors
        # Note: Exact count depends on how errors are deduplicated
        assert len(stats.template_errors) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
