"""
Tests for template function convenience wrappers.

Tests the convenience functions added to simplify common template operations:
- get_section() and section_pages() in navigation.py
- page_exists() in get_page.py
- word_count filter in strings.py

See RFC: plan/active/rfc-template-function-improvements.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.rendering.template_functions.get_page import page_exists, register as register_get_page
from bengal.rendering.template_functions.navigation import (
    get_section,
    register as register_navigation,
    section_pages,
)
from bengal.rendering.template_functions.strings import word_count
from bengal.utils.file_io import write_text_file


@pytest.fixture
def site_with_sections(tmp_path: Path) -> Site:
    """Create a site with multiple sections for testing."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    # Create config
    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
    )

    # Create content structure
    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Create root index
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    # Create docs section with pages
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("---\ntitle: Documentation\nweight: 10\n---\n# Docs")
    (docs_dir / "getting-started.md").write_text(
        "---\ntitle: Getting Started\nweight: 1\n---\n# Getting Started"
    )
    (docs_dir / "installation.md").write_text(
        "---\ntitle: Installation\nweight: 2\n---\n# Installation"
    )

    # Create subsection in docs
    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()
    (guides_dir / "_index.md").write_text("---\ntitle: Guides\nweight: 100\n---\n# Guides")
    (guides_dir / "advanced.md").write_text("---\ntitle: Advanced Guide\n---\n# Advanced")

    # Create blog section
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "_index.md").write_text("---\ntitle: Blog\nweight: 20\n---\n# Blog")
    (blog_dir / "post-1.md").write_text("---\ntitle: First Post\n---\n# First Post")

    # Create site and discover content
    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


class TestGetSection:
    """Tests for get_section() convenience function."""

    def test_returns_section_by_path(self, site_with_sections: Site):
        """Test that get_section returns a section by path."""
        section = get_section("docs", site_with_sections)

        assert section is not None
        assert section.name == "docs"
        assert section.title == "Documentation"

    def test_returns_none_for_missing(self, site_with_sections: Site):
        """Test that get_section returns None for non-existent section."""
        section = get_section("nonexistent", site_with_sections)

        assert section is None

    def test_normalizes_path_leading_slash(self, site_with_sections: Site):
        """Test that get_section normalizes paths with leading slash."""
        section = get_section("/docs/", site_with_sections)

        assert section is not None
        assert section.name == "docs"

    def test_normalizes_path_trailing_slash(self, site_with_sections: Site):
        """Test that get_section normalizes paths with trailing slash."""
        section = get_section("docs/", site_with_sections)

        assert section is not None
        assert section.name == "docs"

    def test_finds_nested_section(self, site_with_sections: Site):
        """Test that get_section finds nested sections."""
        section = get_section("docs/guides", site_with_sections)

        assert section is not None
        assert section.name == "guides"
        assert section.title == "Guides"

    def test_empty_path_returns_none(self, site_with_sections: Site):
        """Test that get_section returns None for empty path."""
        assert get_section("", site_with_sections) is None

    def test_registered_in_environment(self, site_with_sections: Site):
        """Test that get_section is registered in Jinja2 environment."""
        from jinja2 import Environment

        env = Environment()
        register_navigation(env, site_with_sections)

        get_section_func = env.globals.get("get_section")
        assert get_section_func is not None

        section = get_section_func("docs")
        assert section is not None
        assert section.name == "docs"


class TestSectionPages:
    """Tests for section_pages() convenience function."""

    def test_returns_pages_in_section(self, site_with_sections: Site):
        """Test that section_pages returns pages in a section."""
        pages = section_pages("docs", site_with_sections)

        assert len(pages) > 0
        titles = [p.title for p in pages]
        assert "Getting Started" in titles
        assert "Installation" in titles

    def test_empty_for_missing_section(self, site_with_sections: Site):
        """Test that section_pages returns empty list for missing section."""
        pages = section_pages("nonexistent", site_with_sections)

        assert pages == []

    def test_empty_path_returns_empty_list(self, site_with_sections: Site):
        """Test that section_pages returns empty list for empty path."""
        pages = section_pages("", site_with_sections)

        assert pages == []

    def test_recursive_includes_subsection_pages(self, site_with_sections: Site):
        """Test that section_pages with recursive=True includes subsection pages."""
        pages_not_recursive = section_pages("docs", site_with_sections, recursive=False)
        pages_recursive = section_pages("docs", site_with_sections, recursive=True)

        # Recursive should have more pages (includes guides/advanced.md)
        assert len(pages_recursive) >= len(pages_not_recursive)

        # Non-recursive should NOT include Advanced Guide
        non_recursive_titles = [p.title for p in pages_not_recursive]
        assert "Advanced Guide" not in non_recursive_titles

    def test_registered_in_environment(self, site_with_sections: Site):
        """Test that section_pages is registered in Jinja2 environment."""
        from jinja2 import Environment

        env = Environment()
        register_navigation(env, site_with_sections)

        section_pages_func = env.globals.get("section_pages")
        assert section_pages_func is not None

        pages = section_pages_func("docs")
        assert len(pages) > 0


class TestPageExists:
    """Tests for page_exists() function."""

    def test_true_for_existing_page(self, site_with_sections: Site):
        """Test that page_exists returns True for existing page."""
        assert page_exists("docs/getting-started.md", site_with_sections) is True

    def test_true_without_extension(self, site_with_sections: Site):
        """Test that page_exists works without .md extension."""
        assert page_exists("docs/getting-started", site_with_sections) is True

    def test_false_for_missing(self, site_with_sections: Site):
        """Test that page_exists returns False for non-existent page."""
        assert page_exists("nonexistent/page.md", site_with_sections) is False

    def test_false_for_empty_path(self, site_with_sections: Site):
        """Test that page_exists returns False for empty path."""
        assert page_exists("", site_with_sections) is False

    def test_strips_content_prefix(self, site_with_sections: Site):
        """Test that page_exists strips 'content/' prefix if present."""
        assert page_exists("content/docs/getting-started.md", site_with_sections) is True

    def test_does_not_load_page(self, site_with_sections: Site):
        """Test that page_exists uses cached maps without loading page."""
        # Reset lookup maps to ensure fresh state
        site_with_sections._page_lookup_maps = None

        # Call page_exists - should build maps but not parse page
        result = page_exists("docs/getting-started.md", site_with_sections)

        assert result is True
        # Lookup maps should now exist
        assert site_with_sections._page_lookup_maps is not None

    def test_registered_in_environment(self, site_with_sections: Site):
        """Test that page_exists is registered in Jinja2 environment."""
        from jinja2 import Environment

        env = Environment()
        register_get_page(env, site_with_sections)

        page_exists_func = env.globals.get("page_exists")
        assert page_exists_func is not None

        assert page_exists_func("docs/getting-started.md") is True
        assert page_exists_func("nonexistent.md") is False


class TestWordCount:
    """Tests for word_count filter."""

    def test_counts_plain_text(self):
        """Test that word_count counts words in plain text."""
        assert word_count("Hello world") == 2
        assert word_count("One two three four five") == 5

    def test_strips_html(self):
        """Test that word_count strips HTML before counting."""
        assert word_count("<p>Hello <b>world</b></p>") == 2
        # Adjacent tags without whitespace get merged when stripped
        assert word_count("<div><p>One </p><p>Two</p></div>") == 2
        assert word_count("<p>Hello</p> <p>World</p>") == 2

    def test_empty_returns_zero(self):
        """Test that word_count returns 0 for empty text."""
        assert word_count("") == 0

    def test_none_returns_zero(self):
        """Test that word_count returns 0 for None."""
        assert word_count(None) == 0  # type: ignore

    def test_whitespace_only_returns_zero(self):
        """Test that word_count returns 0 for whitespace-only text."""
        assert word_count("   ") == 0
        assert word_count("\n\t") == 0

    def test_html_only_returns_zero(self):
        """Test that word_count returns 0 for HTML without text."""
        assert word_count("<br><hr>") == 0

    def test_counts_words_with_punctuation(self):
        """Test that word_count handles punctuation."""
        assert word_count("Hello, world!") == 2
        assert word_count("One. Two. Three.") == 3

    def test_filter_registered(self, site_with_sections: Site):
        """Test that word_count is registered as a filter."""
        from jinja2 import Environment

        from bengal.rendering.template_functions.strings import register as register_strings

        env = Environment()
        register_strings(env, site_with_sections)

        word_count_filter = env.filters.get("word_count")
        assert word_count_filter is not None
        assert word_count_filter("Hello world") == 2

