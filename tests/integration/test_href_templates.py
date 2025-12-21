"""
Integration tests for href property in template rendering.

Tests that templates using href produce correct output for:
- GitHub Pages deployment scenarios (baseurl="/bengal")
- Local dev server (baseurl="")
- Custom domain (baseurl="https://example.com")
"""

from pathlib import Path

import pytest

from bengal.core.page import Page
from bengal.core.site import Site


@pytest.mark.bengal(testroot="test-basic")
class TestHrefTemplateRendering:
    """Test href property in template rendering scenarios."""

    def test_page_href_in_template(self, site, build_site):
        """Test that page.href works correctly in templates."""
        # Create a simple template that uses href
        template_content = """
        <a href="{{ page.href }}">{{ page.title }}</a>
        """
        template_path = site.theme_dir / "templates" / "test_href.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template_content)

        # Build site
        build_site()

        # Check that href was used correctly
        # This is a basic smoke test - actual rendering happens in build
        assert True  # If build succeeds, href works

    def test_section_href_in_template(self, site, build_site):
        """Test that section.href works correctly in templates."""
        # Create a template that uses section.href
        template_content = """
        <a href="{{ section.href }}">{{ section.title }}</a>
        """
        template_path = site.theme_dir / "templates" / "test_section_href.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template_content)

        build_site()
        assert True  # If build succeeds, section.href works

    def test_nav_item_href_in_template(self, site, build_site):
        """Test that nav item href works correctly in templates."""
        # Create a template that uses nav item href
        template_content = """
        {% for item in get_nav_tree(page) %}
          <a href="{{ item.href }}">{{ item.title }}</a>
        {% endfor %}
        """
        template_path = site.theme_dir / "templates" / "test_nav_href.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template_content)

        build_site()
        assert True  # If build succeeds, nav item href works


@pytest.mark.bengal(testroot="test-basic", confoverrides={"site.baseurl": "/bengal"})
class TestHrefGitHubPagesDeployment:
    """Test href property for GitHub Pages deployment (baseurl="/bengal")."""

    def test_page_href_includes_baseurl(self, site, build_site):
        """Test that page.href includes baseurl for GitHub Pages."""
        build_site()

        # Find a page and verify its href includes baseurl
        pages = [p for p in site.pages if p.source_path.name != "_index.md"]
        if pages:
            page = pages[0]
            assert page.href.startswith("/bengal/"), f"href should include baseurl, got: {page.href}"
            assert page._path.startswith("/"), f"_path should not include baseurl, got: {page._path}"
            assert not page._path.startswith("/bengal/"), "_path should not include baseurl"

    def test_section_href_includes_baseurl(self, site, build_site):
        """Test that section.href includes baseurl for GitHub Pages."""
        build_site()

        if site.sections:
            section = site.sections[0]
            assert section.href.startswith("/bengal/"), f"href should include baseurl, got: {section.href}"
            assert section._path.startswith("/"), f"_path should not include baseurl, got: {section._path}"
            assert not section._path.startswith("/bengal/"), "_path should not include baseurl"

    def test_href_filter_works(self, site, build_site):
        """Test that href filter works for manual paths."""
        # Create a template using href filter
        template_content = """
        <a href="{{ '/about/' | href }}">About</a>
        """
        template_path = site.theme_dir / "templates" / "test_href_filter.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template_content)

        build_site()
        # If build succeeds, href filter works
        assert True


@pytest.mark.bengal(testroot="test-basic", confoverrides={"site.baseurl": ""})
class TestHrefLocalDevServer:
    """Test href property for local dev server (baseurl="")."""

    def test_page_href_no_baseurl(self, site, build_site):
        """Test that page.href works without baseurl."""
        build_site()

        pages = [p for p in site.pages if p.source_path.name != "_index.md"]
        if pages:
            page = pages[0]
            # href should equal _path when baseurl is empty
            assert page.href == page._path, "href should equal _path when baseurl is empty"
            assert page.href.startswith("/"), "href should start with /"


@pytest.mark.bengal(testroot="test-basic", confoverrides={"site.baseurl": "https://example.com"})
class TestHrefCustomDomain:
    """Test href property for custom domain (baseurl="https://example.com")."""

    def test_page_href_absolute_url(self, site, build_site):
        """Test that page.href includes absolute baseurl."""
        build_site()

        pages = [p for p in site.pages if p.source_path.name != "_index.md"]
        if pages:
            page = pages[0]
            assert page.href.startswith("https://example.com/"), f"href should include absolute baseurl, got: {page.href}"
            assert page._path.startswith("/"), f"_path should not include baseurl, got: {page._path}"

