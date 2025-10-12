"""
Tests for page URL generation in sections.

This test specifically covers the bug where pages in sections would have incorrect URLs
when accessed via section.pages before they were individually rendered.

Bug: Pages had output_path set lazily during rendering, causing page.url to fall back
to slug-based URLs without section prefix when accessed from navigation templates.

Fix: Pre-set output_path for all pages before rendering starts.
"""

from pathlib import Path

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


class TestPageURLsInSections:
    """Test that page URLs include section paths correctly."""

    def test_page_url_in_section_without_output_path(self):
        """Test page URL falls back correctly when output_path not set."""
        page = Page(
            source_path=Path("/content/docs/getting-started.md"),
            metadata={"title": "Getting Started"},
        )

        # Without output_path or site reference, should use slug
        # This is the fallback behavior
        assert page.url == "/getting-started/"

    def test_page_url_in_section_with_output_path(self):
        """Test page URL uses output_path when set."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/getting-started.md"),
            metadata={"title": "Getting Started"},
            output_path=Path("/site/public/docs/getting-started/index.html"),
        )
        page._site = site

        # Should correctly compute URL from output_path
        assert page.url == "/docs/getting-started/"

    def test_all_pages_in_section_have_correct_urls(self):
        """
        Test that ALL pages in a section have correct URLs.

        This is the critical test for the navigation bug:
        When building navigation for one page, all other pages in the section
        should have correct URLs even if they haven't been rendered yet.
        """
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site

        # Create multiple pages in the section
        pages = [
            Page(
                source_path=Path("/content/docs/intro.md"),
                metadata={"title": "Introduction"},
                output_path=Path("/site/public/docs/intro/index.html"),
            ),
            Page(
                source_path=Path("/content/docs/guide.md"),
                metadata={"title": "Guide"},
                output_path=Path("/site/public/docs/guide/index.html"),
            ),
            Page(
                source_path=Path("/content/docs/api.md"),
                metadata={"title": "API Reference"},
                output_path=Path("/site/public/docs/api/index.html"),
            ),
        ]

        # Add pages to section and set site reference
        for page in pages:
            page._site = site
            section.add_page(page)

        # All pages should have correct URLs with section prefix
        assert pages[0].url == "/docs/intro/"
        assert pages[1].url == "/docs/guide/"
        assert pages[2].url == "/docs/api/"

        # Accessing pages via section.pages should also work
        for page in section.pages:
            assert page.url.startswith("/docs/")

    def test_nested_section_page_urls(self):
        """Test page URLs in nested sections."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        parent = Section(name="api", path=Path("/content/api"))
        child = Section(name="v2", path=Path("/content/api/v2"))
        parent.add_subsection(child)

        parent._site = site
        child._site = site

        page = Page(
            source_path=Path("/content/api/v2/users.md"),
            metadata={"title": "Users API"},
            output_path=Path("/site/public/api/v2/users/index.html"),
        )
        page._site = site
        child.add_page(page)

        # Should include full path from nested sections
        assert page.url == "/api/v2/users/"

    def test_section_index_page_url(self):
        """Test that section index pages (_index.md) have correct URLs."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site

        index_page = Page(
            source_path=Path("/content/docs/_index.md"),
            metadata={"title": "Documentation"},
            output_path=Path("/site/public/docs/index.html"),
        )
        index_page._site = site
        section.add_page(index_page)

        # Index page should have section URL
        assert index_page.url == "/docs/"
        # Section should use index page's URL
        assert section.url == "/docs/"


class TestPageURLGenerationDuringRendering:
    """Test URL generation during the rendering phase."""

    def test_output_path_determines_url(self):
        """Test that output_path correctly determines the URL."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        # Test pretty URLs (default)
        page = Page(
            source_path=Path("/content/blog/post.md"),
            metadata={"title": "Post"},
            output_path=Path("/site/public/blog/post/index.html"),
        )
        page._site = site

        assert page.url == "/blog/post/"

        # Test index pages
        index_page = Page(
            source_path=Path("/content/blog/_index.md"),
            metadata={"title": "Blog"},
            output_path=Path("/site/public/blog/index.html"),
        )
        index_page._site = site

        assert index_page.url == "/blog/"

    def test_url_without_output_path_falls_back(self):
        """Test URL generation falls back to slug when no output_path."""
        page = Page(source_path=Path("/content/docs/guide.md"), metadata={"title": "Guide"})

        # Should fall back to slug-based URL
        fallback_url = page.url
        assert fallback_url == "/guide/"

        # This fallback is intentional but not ideal for sections
        # which is why we pre-set output_path before rendering


class TestNavigationLinkGeneration:
    """Test navigation link generation scenarios."""

    def test_navigation_links_in_template_context(self):
        """
        Simulate navigation template accessing section.pages.

        This mimics what happens in templates like docs-nav-section.html:
        {% for p in section.regular_pages %}
          <a href="{{ url_for(p) }}">{{ p.title }}</a>
        {% endfor %}
        """
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        section = Section(name="guides", path=Path("/content/guides"))
        section._site = site

        # Create pages with output_path pre-set (as done by RenderOrchestrator)
        pages = []
        for _i, name in enumerate(["intro", "basics", "advanced"]):
            page = Page(
                source_path=Path(f"/content/guides/{name}.md"),
                metadata={"title": name.title()},
                output_path=Path(f"/site/public/guides/{name}/index.html"),
            )
            page._site = site
            section.add_page(page)
            pages.append(page)

        # Simulate template iteration
        nav_links = []
        for p in section.regular_pages:
            # This is what url_for(p) does
            url = p.url
            nav_links.append({"title": p.title, "url": url})

        # All links should have correct section prefix
        assert nav_links[0]["url"] == "/guides/intro/"
        assert nav_links[1]["url"] == "/guides/basics/"
        assert nav_links[2]["url"] == "/guides/advanced/"

        # None should be missing the section prefix
        for link in nav_links:
            assert link["url"].startswith("/guides/")


class TestEdgeCases:
    """Test edge cases in URL generation."""

    def test_page_at_root_level(self):
        """Test pages at root level (no section)."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/about.md"),
            metadata={"title": "About"},
            output_path=Path("/site/public/about/index.html"),
        )
        page._site = site

        assert page.url == "/about/"

    def test_home_page_url(self):
        """Test home page (index.md at root) URL."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/index.md"),
            metadata={"title": "Home"},
            output_path=Path("/site/public/index.html"),
        )
        page._site = site

        assert page.url == "/"

    def test_deeply_nested_page_url(self):
        """Test pages in deeply nested sections."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/guides/advanced/optimization.md"),
            metadata={"title": "Optimization"},
            output_path=Path("/site/public/docs/guides/advanced/optimization/index.html"),
        )
        page._site = site

        assert page.url == "/docs/guides/advanced/optimization/"
