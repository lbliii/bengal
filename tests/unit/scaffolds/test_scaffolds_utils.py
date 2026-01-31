"""Tests for bengal.scaffolds.utils module."""

import re
from datetime import datetime

import pytest

from bengal.scaffolds.utils import (
    DATE_FORMAT,
    DATE_PLACEHOLDER,
    get_current_date,
    load_template_file,
    replace_date_placeholder,
)


class TestConstants:
    """Test module constants."""

    def test_date_format_is_iso(self):
        """DATE_FORMAT should produce ISO-style dates."""
        assert DATE_FORMAT == "%Y-%m-%d"

    def test_date_placeholder_is_mustache_style(self):
        """DATE_PLACEHOLDER should use mustache-style syntax."""
        assert DATE_PLACEHOLDER == "{{date}}"


class TestGetCurrentDate:
    """Tests for get_current_date function."""

    def test_returns_string(self):
        """Should return a string."""
        result = get_current_date()
        assert isinstance(result, str)

    def test_format_is_yyyy_mm_dd(self):
        """Should return date in YYYY-MM-DD format."""
        result = get_current_date()
        # Should match YYYY-MM-DD pattern
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result)

    def test_returns_today(self):
        """Should return today's date."""
        result = get_current_date()
        expected = datetime.now().strftime("%Y-%m-%d")
        assert result == expected


class TestReplaceDatePlaceholder:
    """Tests for replace_date_placeholder function."""

    def test_replaces_single_placeholder(self):
        """Should replace a single {{date}} placeholder."""
        content = "Published on: {{date}}"
        result = replace_date_placeholder(content)

        assert "{{date}}" not in result
        assert re.search(r"\d{4}-\d{2}-\d{2}", result)

    def test_replaces_multiple_placeholders(self):
        """Should replace all {{date}} placeholders."""
        content = "Created: {{date}}, Updated: {{date}}"
        result = replace_date_placeholder(content)

        assert result.count("{{date}}") == 0
        # Should have two dates
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", result)
        assert len(dates) == 2

    def test_preserves_other_content(self):
        """Should not modify other content."""
        content = "Title: My Post\nDate: {{date}}\nAuthor: Test"
        result = replace_date_placeholder(content)

        assert "Title: My Post" in result
        assert "Author: Test" in result

    def test_handles_no_placeholder(self):
        """Should return unchanged content if no placeholder present."""
        content = "No date placeholder here"
        result = replace_date_placeholder(content)

        assert result == content

    def test_handles_empty_string(self):
        """Should handle empty string input."""
        result = replace_date_placeholder("")
        assert result == ""

    def test_handles_similar_patterns(self):
        """Should only replace exact {{date}} pattern."""
        content = "{{date}} {date} {{ date }} {{DATE}}"
        result = replace_date_placeholder(content)

        # Only {{date}} should be replaced
        assert "{{date}}" not in result
        assert "{date}" in result
        assert "{{ date }}" in result
        assert "{{DATE}}" in result


class TestLoadTemplateFile:
    """Tests for load_template_file function."""

    def test_loads_file_content(self, tmp_path):
        """Should load file content from template directory."""
        # Set up test directory structure
        template_dir = tmp_path / "my_template"
        pages_dir = template_dir / "pages"
        pages_dir.mkdir(parents=True)

        test_file = pages_dir / "index.md"
        test_file.write_text("# Hello World")

        # Create a fake __file__ path
        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "index.md")
        assert result == "# Hello World"

    def test_loads_nested_file(self, tmp_path):
        """Should load files from nested directories."""
        template_dir = tmp_path / "my_template"
        nested_dir = template_dir / "pages" / "posts"
        nested_dir.mkdir(parents=True)

        test_file = nested_dir / "first-post.md"
        test_file.write_text("First post content")

        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "posts/first-post.md")
        assert result == "First post content"

    def test_custom_subdir(self, tmp_path):
        """Should load from custom subdirectory."""
        template_dir = tmp_path / "my_template"
        data_dir = template_dir / "data"
        data_dir.mkdir(parents=True)

        test_file = data_dir / "config.yaml"
        test_file.write_text("key: value")

        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "config.yaml", subdir="data")
        assert result == "key: value"

    def test_date_replacement_enabled(self, tmp_path):
        """Should replace {{date}} when replace_date=True."""
        template_dir = tmp_path / "my_template"
        pages_dir = template_dir / "pages"
        pages_dir.mkdir(parents=True)

        test_file = pages_dir / "post.md"
        test_file.write_text("---\ndate: {{date}}\n---\nContent")

        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "post.md", replace_date=True)

        assert "{{date}}" not in result
        assert re.search(r"\d{4}-\d{2}-\d{2}", result)
        assert "Content" in result

    def test_date_replacement_disabled_by_default(self, tmp_path):
        """Should not replace {{date}} by default."""
        template_dir = tmp_path / "my_template"
        pages_dir = template_dir / "pages"
        pages_dir.mkdir(parents=True)

        test_file = pages_dir / "post.md"
        test_file.write_text("date: {{date}}")

        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "post.md")

        assert "{{date}}" in result

    def test_file_not_found_raises_error(self, tmp_path):
        """Should raise FileNotFoundError for missing files."""
        template_dir = tmp_path / "my_template"
        template_dir.mkdir()
        (template_dir / "pages").mkdir()

        fake_module_file = str(template_dir / "template.py")

        with pytest.raises(FileNotFoundError):
            load_template_file(fake_module_file, "nonexistent.md")

    def test_reads_utf8_content(self, tmp_path):
        """Should correctly read UTF-8 encoded content."""
        template_dir = tmp_path / "my_template"
        pages_dir = template_dir / "pages"
        pages_dir.mkdir(parents=True)

        test_file = pages_dir / "unicode.md"
        test_file.write_text("日本語 • émojis 🎉 • symbols ™", encoding="utf-8")

        fake_module_file = str(template_dir / "template.py")

        result = load_template_file(fake_module_file, "unicode.md")
        assert "日本語" in result
        assert "🎉" in result
        assert "™" in result


class TestLoadTemplateFileIntegration:
    """Integration tests using real template files."""

    def test_loads_real_default_template(self):
        """Should load a file from the real default template."""
        # Get path to real template module
        from bengal.scaffolds.default import template as default_template

        module_file = default_template.__file__

        # Load the real index.md
        content = load_template_file(module_file, "index.md")

        # Should have markdown content
        assert len(content) > 0
        assert "---" in content  # Has frontmatter

    def test_loads_real_blog_template_with_date_replacement(self):
        """Should load blog template file with date replacement."""
        from bengal.scaffolds.blog import template as blog_template

        module_file = blog_template.__file__

        # Load with date replacement
        content = load_template_file(module_file, "index.md", replace_date=True)

        # Should not have raw placeholder
        assert "{{date}}" not in content
        assert len(content) > 0

    def test_loads_product_data_file(self):
        """Should load data file from product template."""
        from bengal.scaffolds.product import template as product_template

        module_file = product_template.__file__

        # Load data file
        content = load_template_file(module_file, "products.yaml", subdir="data")

        # Should have YAML content
        assert len(content) > 0
