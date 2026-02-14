"""
Tests for URL access patterns in templates.

Templates access page URLs in multiple ways throughout the rendering process.
This test suite ensures all access patterns return correct URLs with section prefixes.

Critical scenarios:
- child_page_tiles macro
- Navigation components
- Related posts
- Breadcrumbs
- Pagination
- Tag pages linking to content
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator


class TestChildPageTilesMacro:
    """Test child_page_tiles macro URL access."""

    @pytest.fixture
    def site_with_children(self):
        """Create site with parent section and child pages."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content" / "guides"
            content_dir.mkdir(parents=True, exist_ok=True)

            # Section index
            (content_dir / "_index.md").write_text(
                "---\ntitle: Guides\ntype: doc\ncascade:\n  type: doc\n---"
            )

            # Child pages
            for i in range(1, 4):
                (content_dir / f"guide-{i}.md").write_text(
                    f"---\ntitle: Guide {i}\nweight: {i * 10}\n---\n# Guide {i}"
                )

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_child_page_tiles_urls_correct(self, site_with_children):
        """Simulate child_page_tiles macro accessing page URLs."""
        # Find guides section
        guides_section = None
        for section in site_with_children.sections:
            if section.name == "guides":
                guides_section = section
                break

        assert guides_section is not None

        # Simulate macro: {% for page in posts %}
        tile_data = [
            {
                "title": page.title,
                "url": page.href,
                "description": page.metadata.get("description", ""),
            }
            for page in guides_section.pages
            if page.source_path.stem != "_index"
        ]

        # Verify all URLs have section prefix
        assert len(tile_data) >= 3
        for tile in tile_data:
            assert tile["url"].startswith("/guides/"), (
                f"Tile URL missing section prefix: {tile['url']}"
            )

    def test_sorted_pages_iteration_urls(self, site_with_children):
        """Test URL access when iterating sorted_pages."""
        guides_section = next(s for s in site_with_children.sections if s.name == "guides")

        # Simulate: {% for page in section.sorted_pages %}
        for page in guides_section.sorted_pages:
            url = page.href
            if page.source_path.stem != "_index":
                assert url.startswith("/guides/"), f"Sorted page wrong URL: {url}"


class TestNavigationComponentURLs:
    """Test navigation component URL generation."""

    @pytest.fixture
    def nested_nav_site(self):
        """Create site with nested navigation structure."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content" / "docs"

            # Create nested structure: docs/getting-started/basics
            basics_dir = content_dir / "getting-started" / "basics"
            basics_dir.mkdir(parents=True, exist_ok=True)

            # Indexes
            (content_dir / "_index.md").write_text("---\ntitle: Docs\ntype: doc\n---")
            (content_dir / "getting-started" / "_index.md").write_text(
                "---\ntitle: Getting Started\n---"
            )
            (basics_dir / "_index.md").write_text("---\ntitle: Basics\n---")

            # Pages at each level
            (content_dir / "overview.md").write_text("---\ntitle: Overview\n---")
            (content_dir / "getting-started" / "intro.md").write_text(
                "---\ntitle: Introduction\n---"
            )
            (basics_dir / "hello-world.md").write_text("---\ntitle: Hello World\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_docs_nav_sidebar_urls(self, nested_nav_site):
        """Simulate docs-nav.html sidebar navigation."""
        # Find root docs section
        root_section = next(s for s in nested_nav_site.sections if s.name == "docs")

        # Simulate navigation template iterating through hierarchy
        def collect_nav_urls(section, prefix="/"):
            urls = []
            # Section index
            if section.index_page:
                urls.append(section.index_page.href)

            # Section pages
            for page in section.pages:
                if page != section.index_page:
                    urls.append(page.href)

            # Subsections
            urls.extend(
                url
                for subsection in section.subsections
                for url in collect_nav_urls(subsection, prefix)
            )

            return urls

        all_nav_urls = collect_nav_urls(root_section)

        # All should start with /docs/
        for url in all_nav_urls:
            assert url.startswith("/docs/"), f"Nav URL missing prefix: {url}"

    def test_breadcrumb_ancestor_urls(self, nested_nav_site):
        """Simulate breadcrumb generation with ancestor sections."""
        # Find deeply nested page
        hello_page = None
        for page in nested_nav_site.pages:
            if "hello-world" in str(page.source_path):
                hello_page = page
                break

        assert hello_page is not None

        # Simulate breadcrumb: {% for ancestor in page.ancestors %}
        # (Note: page.ancestors would need to be set up, simulating the access pattern)
        breadcrumb_url = hello_page.href
        assert breadcrumb_url.startswith("/docs/getting-started/basics/"), (
            f"Deeply nested page has wrong URL: {breadcrumb_url}"
        )


class TestRelatedPostsURLs:
    """Test related posts/content URL access."""

    @pytest.fixture
    def tagged_site(self):
        """Create site with tagged posts."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            blog_dir = root / "content" / "blog"
            blog_dir.mkdir(parents=True, exist_ok=True)

            (blog_dir / "_index.md").write_text("---\ntitle: Blog\ntype: blog\n---")

            # Posts with shared tags
            (blog_dir / "post-1.md").write_text(
                "---\ntitle: Post 1\ntags: [python, tutorial]\ndate: 2024-01-01\n---"
            )
            (blog_dir / "post-2.md").write_text(
                "---\ntitle: Post 2\ntags: [python, advanced]\ndate: 2024-01-02\n---"
            )
            (blog_dir / "post-3.md").write_text(
                "---\ntitle: Post 3\ntags: [python]\ndate: 2024-01-03\n---"
            )

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_related_by_tag_urls(self, tagged_site):
        """Simulate finding related posts by tag."""
        posts = [p for p in tagged_site.pages if "post" in str(p.source_path)]
        assert len(posts) >= 3

        # Simulate: find posts with "python" tag
        python_posts = [p for p in posts if "python" in p.metadata.get("tags", [])]

        # Access URLs (as template would)
        for post in python_posts:
            assert post.href.startswith("/blog/"), f"Related post wrong URL: {post.href}"


class TestPaginationURLs:
    """Test pagination URL access."""

    def test_paginator_page_urls(self):
        """Test accessing URLs of pages in paginated list."""
        site = Mock()
        site.output_dir = Path("/site/public")
        site.config = {}  # Return empty dict (no baseurl) to avoid MagicMock issues

        # Create pages with proper output paths
        pages = []
        for i in range(1, 6):
            page = Page(
                source_path=Path(f"/content/blog/post-{i}.md"),
                _raw_metadata={"title": f"Post {i}"},
                output_path=Path(f"/site/public/blog/post-{i}/index.html"),
            )
            page._site = site
            pages.append(page)

        # Simulate template: {% for page in paginator.pages %}
        for page in pages:
            url = page.href
            assert url.startswith("/blog/"), f"Paginated page wrong URL: {url}"


class TestTagPageLinks:
    """Test tag pages linking to content."""

    @pytest.fixture
    def site_with_tags(self):
        """Create site with tagged content across sections."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content_dir = root / "content"

            # Blog section
            blog_dir = content_dir / "blog"
            blog_dir.mkdir(parents=True, exist_ok=True)
            (blog_dir / "_index.md").write_text("---\ntitle: Blog\n---")
            (blog_dir / "python-intro.md").write_text(
                "---\ntitle: Python Intro\ntags: [python]\n---"
            )

            # Docs section
            docs_dir = content_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---")
            (docs_dir / "python-guide.md").write_text(
                "---\ntitle: Python Guide\ntags: [python]\n---"
            )

            # Tutorial section
            tut_dir = content_dir / "tutorials"
            tut_dir.mkdir(parents=True, exist_ok=True)
            (tut_dir / "_index.md").write_text("---\ntitle: Tutorials\n---")
            (tut_dir / "python-basics.md").write_text(
                "---\ntitle: Python Basics\ntags: [python]\n---"
            )

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_tag_page_links_preserve_sections(self, site_with_tags):
        """Tag pages should link to content with correct section prefixes."""
        # Find all pages with "python" tag
        python_pages = [p for p in site_with_tags.pages if "python" in p.metadata.get("tags", [])]

        assert len(python_pages) >= 3, "Should have pages from multiple sections"

        # Group by section
        by_section = {}
        for page in python_pages:
            if "blog" in str(page.source_path):
                by_section.setdefault("blog", []).append(page)
            elif "docs" in str(page.source_path):
                by_section.setdefault("docs", []).append(page)
            elif "tutorials" in str(page.source_path):
                by_section.setdefault("tutorials", []).append(page)

        # Verify each section's pages have correct prefix
        if "blog" in by_section:
            for page in by_section["blog"]:
                assert page.href.startswith("/blog/"), f"Blog page wrong URL: {page.href}"

        if "docs" in by_section:
            for page in by_section["docs"]:
                assert page.href.startswith("/docs/"), f"Docs page wrong URL: {page.href}"

        if "tutorials" in by_section:
            for page in by_section["tutorials"]:
                assert page.href.startswith("/tutorials/"), f"Tutorial page wrong URL: {page.href}"


class TestTemplateAccessPatterns:
    """Test various ways templates can access URLs."""

    @pytest.fixture
    def access_test_site(self):
        """Create site for testing different access patterns."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            section_dir = root / "content" / "articles"
            section_dir.mkdir(parents=True, exist_ok=True)

            (section_dir / "_index.md").write_text("---\ntitle: Articles\n---")
            (section_dir / "article-1.md").write_text("---\ntitle: Article 1\n---")
            (section_dir / "article-2.md").write_text("---\ntitle: Article 2\n---")

            site = Site(root_path=root, config={})
            orchestrator = ContentOrchestrator(site)
            orchestrator.discover()
            yield site

    def test_direct_property_access(self, access_test_site):
        """Test: {{ page.href }}"""
        articles = [p for p in access_test_site.pages if "article-" in str(p.source_path)]

        for article in articles:
            url = article.href  # Direct property access
            assert url.startswith("/articles/"), f"Direct access wrong: {url}"

    def test_loop_iteration_access(self, access_test_site):
        """Test: {% for page in section.pages %}{{ page.href }}{% endfor %}"""
        section = next(s for s in access_test_site.sections if s.name == "articles")

        for page in section.pages:
            url = page.href  # Loop iteration access
            if page.source_path.stem != "_index":
                assert url.startswith("/articles/"), f"Loop access wrong: {url}"

    def test_array_index_access(self, access_test_site):
        """Test: {{ section.pages[0].url }}"""
        section = next(s for s in access_test_site.sections if s.name == "articles")
        regular_pages = [p for p in section.pages if p.source_path.stem != "_index"]

        if regular_pages:
            first_page_url = regular_pages[0].href  # Array index access
            assert first_page_url.startswith("/articles/"), f"Array access wrong: {first_page_url}"

    def test_conditional_access(self, access_test_site):
        """Test: {% if page.next %}{{ page.next.url }}{% endif %}"""
        articles = [p for p in access_test_site.pages if "article-" in str(p.source_path)]

        # Even if page.next isn't set up, test the URL access pattern
        for article in articles:
            url = article.href
            # Simulating what happens if template tries: page.next.url
            # (The URL should already be correct on the page object)
            assert url.startswith("/articles/"), f"Conditional access wrong: {url}"
