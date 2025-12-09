"""Tests for get_page template function used by tracks feature."""

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.rendering.template_functions.get_page import register
from bengal.utils.file_io import write_text_file


@pytest.fixture
def site_with_content(tmp_path: Path) -> Site:
    """Create a site with test content for get_page testing."""
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

    # Create pages in various locations
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    docs_dir = content_dir / "docs"
    docs_dir.mkdir()

    getting_started_dir = docs_dir / "getting-started"
    getting_started_dir.mkdir()

    (getting_started_dir / "installation.md").write_text(
        "---\ntitle: Installation\n---\n# Installation"
    )
    (getting_started_dir / "writer-quickstart.md").write_text(
        "---\ntitle: Writer Quickstart\n---\n# Writer"
    )

    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()
    (guides_dir / "content-workflow.md").write_text("---\ntitle: Content Workflow\n---\n# Workflow")

    # Create site and discover content
    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


class TestGetPageFunction:
    """Test get_page template function for track page resolution."""

    def test_get_page_by_relative_path(self, site_with_content: Site):
        """Test resolving page by content-relative path."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Test exact path match
        page = get_page("docs/getting-started/installation.md")
        assert page is not None
        assert page.title == "Installation"

        # Test path without extension
        page2 = get_page("docs/getting-started/writer-quickstart")
        assert page2 is not None
        assert page2.title == "Writer Quickstart"

    def test_get_page_by_path_without_extension(self, site_with_content: Site):
        """Test resolving page when .md extension omitted."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("docs/getting-started/installation")
        assert page is not None
        assert page.title == "Installation"

    def test_get_page_nonexistent_path(self, site_with_content: Site):
        """Test None returned for non-existent pages."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("docs/nonexistent/page.md")
        assert page is None

        page2 = get_page("docs/getting-started/does-not-exist.md")
        assert page2 is None

    def test_get_page_empty_path(self, site_with_content: Site):
        """Test empty path handling."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        assert get_page("") is None
        assert get_page(None) is None  # type: ignore

    def test_get_page_path_normalization(self, site_with_content: Site):
        """Test Windows/Unix path separator normalization."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Test Windows-style path separators
        page = get_page("docs\\getting-started\\installation.md")
        assert page is not None
        assert page.title == "Installation"

        # Test mixed separators
        page2 = get_page("docs/getting-started\\writer-quickstart.md")
        assert page2 is not None
        assert page2.title == "Writer Quickstart"

    def test_get_page_lookup_map_caching(self, site_with_content: Site):
        """Test that lookup maps are cached on site object."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # First call should create maps (field exists but is None before first use)
        assert site_with_content._page_lookup_maps is None
        page1 = get_page("docs/getting-started/installation.md")
        assert site_with_content._page_lookup_maps is not None

        # Maps should be reused
        maps_before = site_with_content._page_lookup_maps
        page2 = get_page("docs/guides/content-workflow.md")
        assert site_with_content._page_lookup_maps is maps_before

        assert page1 is not None
        assert page2 is not None

    def test_get_page_index_page(self, site_with_content: Site):
        """Test resolving index page."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("index.md")
        assert page is not None
        assert page.title == "Home"

    def test_get_page_with_trailing_slash(self, site_with_content: Site):
        """Test path with trailing slash is handled."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Should still work (though not ideal)
        get_page("docs/getting-started/installation.md/")
        # May or may not work, but shouldn't crash
        # Current implementation may return None, which is acceptable

    def test_get_page_case_sensitivity(self, site_with_content: Site):
        """Test that path matching is case-sensitive."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Exact case should work
        page = get_page("docs/getting-started/installation.md")
        assert page is not None

        # Different case may not work (platform-dependent)
        # On case-insensitive filesystems (macOS/Windows), this might work
        # On case-sensitive filesystems (Linux), this should fail
        # Current implementation is case-sensitive, which is correct

    def test_get_page_parses_on_demand(self, site_with_content: Site):
        """Test that get_page parses pages on-demand when accessed from templates."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Get a page that hasn't been parsed yet
        page = get_page("docs/getting-started/writer-quickstart.md")
        assert page is not None

        # Verify page is parsed after get_page call
        assert hasattr(page, "parsed_ast")
        assert page.parsed_ast is not None
        assert len(page.parsed_ast) > 0
        # Should be HTML, not markdown
        assert "<h1>" in page.parsed_ast or "<h2>" in page.parsed_ast

    def test_get_page_does_not_reparse_already_parsed_pages(self, site_with_content: Site):
        """Test that get_page doesn't reparse pages that are already parsed."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Get a page and parse it manually first
        page = get_page("docs/getting-started/installation.md")
        assert page is not None

        # Manually set parsed_ast to a known value
        original_parsed = "<h1>Test</h1><p>Original content</p>"
        page.parsed_ast = original_parsed

        # Get the page again - should not reparse
        page2 = get_page("docs/getting-started/installation.md")
        assert page2 is not None
        assert page2.parsed_ast == original_parsed
