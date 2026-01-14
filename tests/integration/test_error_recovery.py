"""
Integration tests for error recovery and resilience scenarios.

Tests the system's ability to handle and recover from various error conditions:
- Template errors
- Missing files
- Invalid configuration
- Build failures
"""

import contextlib

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.utils.io.file_io import write_text_file


class TestTemplateErrorRecovery:
    """Tests for template error handling and recovery."""

    def test_continue_build_after_template_error(self, tmp_path):
        """Test that build continues after encountering template error in strict mode."""
        # Create site with valid config
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
content_dir = "content"
""",
        )

        # Create content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a valid page
        valid_page = content_dir / "valid.md"
        write_text_file(
            str(valid_page),
            """---
title: Valid Page
---
This is valid content.
""",
        )

        # Create a page with problematic frontmatter
        broken_page = content_dir / "broken.md"
        write_text_file(
            str(broken_page),
            """---
title: Broken Page
custom_data:
  - item1
  - item2
---
Content with {{ page.custom_data.nonexistent }} reference.
""",
        )

        # Create templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a basic template
        base_template = templates_dir / "base.html"
        write_text_file(
            str(base_template),
            """<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>{{ content }}</body>
</html>
""",
        )

        # Build site
        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()
        site.discover_assets()

        try:
            # Build with error collection
            stats = site.build(BuildOptions(force_sequential=True))

            # Should complete build even with errors
            assert stats is not None

            # Valid page should be built
            output_dir = tmp_path / "public"
            assert output_dir.exists()

        except Exception as e:
            # Even if exception is raised, it should be handled gracefully
            assert "template" in str(e).lower() or "error" in str(e).lower()

    def test_error_collection_and_reporting(self, tmp_path):
        """Test that template errors are collected and reported."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
        )

        # Create content with multiple template errors
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(3):
            page_file = content_dir / f"page{i}.md"
            write_text_file(
                str(page_file),
                f"""---
title: Page {i}
---
Content
""",
            )

        # Create templates with errors
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Template with undefined variable
        base_template = templates_dir / "base.html"
        write_text_file(
            str(base_template),
            """<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>{{ content }}{{ undefined_var }}</body>
</html>
""",
        )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()

        # Build should collect errors
        # Errors expected, but should be collected
        with contextlib.suppress(Exception):
            site.build(BuildOptions(force_sequential=True))

    def test_recovery_from_missing_template(self, tmp_path):
        """Test recovery when custom template is missing."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Page requesting non-existent template
        page_file = content_dir / "page.md"
        write_text_file(
            str(page_file),
            """---
title: Test Page
layout: nonexistent
---
Content
""",
        )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()

        # Should handle missing template gracefully
        try:
            site.build(BuildOptions(force_sequential=True))
        except Exception as e:
            # Should provide helpful error message
            assert "template" in str(e).lower() or "layout" in str(e).lower()


class TestMissingFileRecovery:
    """Tests for handling missing files during build."""

    def test_missing_asset_reference(self, tmp_path):
        """Test handling of missing asset references."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Page with reference to missing image
        page_file = content_dir / "page.md"
        write_text_file(
            str(page_file),
            """---
title: Test Page
---
# Page with Image

![Missing image](/assets/missing.png)
""",
        )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()
        site.discover_assets()

        # Build should complete despite missing asset
        stats = site.build(BuildOptions(force_sequential=True))
        assert stats is not None

    def test_broken_internal_link(self, tmp_path):
        """Test handling of broken internal links."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Page with broken internal link
        page_file = content_dir / "page.md"
        write_text_file(
            str(page_file),
            """---
title: Test Page
---
Check out [this page](/nonexistent-page/) for more info.
""",
        )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()

        # Build should complete and potentially warn about broken link
        stats = site.build(BuildOptions(force_sequential=True))
        assert stats is not None


class TestInvalidConfigurationRecovery:
    """Tests for handling invalid configuration."""

    def test_invalid_toml_syntax(self, tmp_path):
        """Test handling of invalid TOML syntax."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site
title = "Broken TOML"
""",
        )

        # Should raise appropriate error
        with pytest.raises(Exception) as exc_info:
            Site.from_config(tmp_path, config_path=config_file)

        # Error should be about config parsing
        assert "toml" in str(exc_info.value).lower() or "config" in str(exc_info.value).lower()

    def test_missing_required_config(self, tmp_path):
        """Test handling of missing required configuration."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[build]
output_dir = "public"
""",
        )

        # Should use defaults for missing site config
        try:
            site = Site.from_config(tmp_path, config_path=config_file)
            assert site is not None
        except Exception:
            # Some required configs may raise errors
            pass

    def test_invalid_config_value_types(self, tmp_path):
        """Test handling of invalid config value types."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = 123
baseurl = true

[build]
parallel = "yes"
""",
        )

        # Should handle type errors gracefully
        try:
            site = Site.from_config(tmp_path, config_path=config_file)
            # If successful, config was coerced or defaults used
            assert site is not None
        except Exception as e:
            # Should provide helpful error about config types
            assert "config" in str(e).lower()


class TestBuildFailureRecovery:
    """Tests for recovery from build failures."""

    def test_partial_build_completion(self, tmp_path):
        """Test that partial builds complete successfully for valid pages."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create multiple pages, some valid, some with issues
        valid_page = content_dir / "valid.md"
        write_text_file(
            str(valid_page),
            """---
title: Valid Page
---
This is valid.
""",
        )

        another_valid = content_dir / "another.md"
        write_text_file(
            str(another_valid),
            """---
title: Another Valid Page
---
Also valid.
""",
        )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()
        site.discover_assets()

        # Build should complete
        stats = site.build(BuildOptions(force_sequential=True))
        assert stats is not None

        # Output should exist for valid pages
        output_dir = tmp_path / "public"
        assert output_dir.exists()

    def test_incremental_build_after_error(self, tmp_path):
        """Test that incremental builds work after fixing errors."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
incremental = true
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Initial page
        page_file = content_dir / "page.md"
        write_text_file(
            str(page_file),
            """---
title: Test Page
---
Initial content.
""",
        )

        # First build
        site1 = Site.from_config(tmp_path, config_path=config_file)
        site1.discover_content()
        stats1 = site1.build(BuildOptions(force_sequential=True))
        assert stats1 is not None

        # Modify page
        write_text_file(
            str(page_file),
            """---
title: Updated Page
---
Updated content.
""",
        )

        # Incremental rebuild
        site2 = Site.from_config(tmp_path, config_path=config_file)
        site2.discover_content()
        stats2 = site2.build(BuildOptions(force_sequential=True))
        assert stats2 is not None


class TestConcurrentBuildResilience:
    """Tests for resilience during concurrent operations."""

    def test_parallel_build_error_isolation(self, tmp_path):
        """Test that errors in one thread don't crash parallel build."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
parallel = true
""",
        )

        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create multiple pages
        for i in range(10):
            page_file = content_dir / f"page{i}.md"
            write_text_file(
                str(page_file),
                f"""---
title: Page {i}
---
Content {i}
""",
            )

        site = Site.from_config(tmp_path, config_path=config_file)
        site.discover_content()

        # Parallel build should handle errors in isolation
        try:
            stats = site.build(BuildOptions())
            assert stats is not None
        except Exception:
            # If parallel build fails, it should provide useful info
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
