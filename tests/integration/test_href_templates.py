"""
Integration tests for href property in template rendering.

Tests that templates using href produce correct output for:
- GitHub Pages deployment scenarios (baseurl="/bengal")
- Local dev server (baseurl="")
- Custom domain (baseurl="https://example.com")
"""

import pytest

from bengal.rendering.template_engine import TemplateEngine


@pytest.mark.bengal(testroot="test-basic")
class TestHrefTemplateRendering:
    """Test href property in template rendering scenarios."""

    def test_page_href_in_template(self, site, build_site):
        """Rendering ``page.href`` emits the page's resolved href, not just builds."""
        build_site()

        page = next(p for p in site.pages if p.source_path.name != "_index.md")
        engine = TemplateEngine(site)
        rendered = engine.render_string('<a href="{{ page.href }}">x</a>', {"page": page})

        # Discriminating: the rendered anchor must carry the page's *resolved*
        # href. A shim regression returning "" or a wrong path fails here, where
        # the old `assert True` only proved build_site() didn't raise.
        assert page.href, "page.href should be non-empty"
        assert f'<a href="{page.href}">' in rendered, (
            f"rendered template should contain the resolved page.href; "
            f"got {rendered!r} for href {page.href!r}"
        )
        # Shape: with no baseurl, a page href is a rooted, trailing-slashed path.
        # Catches a wrong-but-consistent href (e.g. a missing leading slash).
        assert page.href.startswith("/"), f"page.href should be rooted, got {page.href!r}"
        assert page.href.endswith("/"), f"page.href should be a directory path, got {page.href!r}"


@pytest.mark.bengal(testroot="test-navigation")
class TestHrefSectionAndNavRendering:
    """Test section.href and nav-item href in templates (needs a sectioned site)."""

    def test_section_href_in_template(self, site, build_site):
        """Rendering ``section.href`` emits the section's resolved href."""
        build_site()

        # test-navigation has docs/ and blog/ sections.
        assert site.sections, "test-navigation should discover sections"
        section = site.sections[0]
        engine = TemplateEngine(site)
        rendered = engine.render_string('<a href="{{ section.href }}">x</a>', {"section": section})

        # Discriminating: the rendered anchor must carry the section's resolved
        # href. A shim regression returning "" or a wrong path fails here.
        assert section.href, "section.href should be non-empty"
        assert f'<a href="{section.href}">' in rendered, (
            f"rendered template should contain the resolved section.href; "
            f"got {rendered!r} for href {section.href!r}"
        )
        # Shape: a section href is a rooted, trailing-slashed directory path.
        assert section.href.startswith("/"), f"section.href should be rooted, got {section.href!r}"
        assert section.href.endswith("/"), (
            f"section.href should be a directory path, got {section.href!r}"
        )

    def test_nav_item_href_in_template(self, site, build_site):
        """Rendering a nav tree emits non-empty hrefs for every nav item."""
        import re

        build_site()

        # A deep page so get_nav_tree returns a populated tree.
        page = next(p for p in site.pages if p.source_path.name not in ("_index.md", "index.md"))
        engine = TemplateEngine(site)
        template = (
            "{% for item in get_nav_tree(page) %}"
            '<a href="{{ item.href }}">{{ item.title }}</a>'
            "{% endfor %}"
        )
        rendered = engine.render_string(template, {"page": page})

        hrefs = re.findall(r'<a href="([^"]*)">', rendered)
        # Discriminating: a nav item that resolves to an empty href would surface
        # as href="" here and fail; the old `assert True` could not see it.
        assert hrefs, "nav tree should emit at least one anchor with an href"
        assert all(h.strip() for h in hrefs), (
            f"every nav item href must be non-empty; got {hrefs!r}"
        )


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
            assert page.href.startswith("/bengal/"), (
                f"href should include baseurl, got: {page.href}"
            )
            assert page._path.startswith("/"), (
                f"_path should not include baseurl, got: {page._path}"
            )
            assert not page._path.startswith("/bengal/"), "_path should not include baseurl"

    def test_section_href_includes_baseurl(self, site, build_site):
        """Test that section.href includes baseurl for GitHub Pages."""
        build_site()

        if site.sections:
            section = site.sections[0]
            assert section.href.startswith("/bengal/"), (
                f"href should include baseurl, got: {section.href}"
            )
            assert section._path.startswith("/"), (
                f"_path should not include baseurl, got: {section._path}"
            )
            assert not section._path.startswith("/bengal/"), "_path should not include baseurl"

    def test_href_filter_works(self, site, build_site):
        """The ``href`` filter applies baseurl to a manual path (here, /bengal)."""
        build_site()

        engine = TemplateEngine(site)
        rendered = engine.render_string("{{ '/about/' | href }}", {})

        # Discriminating: with baseurl="/bengal" the filter must prefix it.
        # A broken filter that returns the bare path or "" fails here.
        assert rendered.strip() == "/bengal/about/", (
            f"href filter should apply baseurl /bengal to /about/; got {rendered!r}"
        )


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
            assert page.href.startswith("https://example.com/"), (
                f"href should include absolute baseurl, got: {page.href}"
            )
            assert page._path.startswith("/"), (
                f"_path should not include baseurl, got: {page._path}"
            )
