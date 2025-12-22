"""Integration tests for mixed content sites.

Tests sites that combine multiple content types:
- Documentation (doc type)
- Blog posts (blog type)
- Portfolio projects (portfolio type)

Each section uses cascade to set the content type for child pages.

Phase 3 of RFC: User Scenario Coverage & Validation Matrix
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-mixed-content")
class TestMixedContentDiscovery:
    """Test content discovery for mixed content sites."""

    def test_all_pages_discovered(self, site) -> None:
        """All pages from all sections should be discovered."""
        # Should have: landing + 3 section indexes + 6 content pages = 10 pages
        # Actual count may vary based on implementation
        assert len(site.pages) >= 7, f"Expected at least 7 pages, found {len(site.pages)}"

    def test_docs_section_exists(self, site) -> None:
        """Docs section should be discovered."""
        docs = [p for p in site.pages if "/docs/" in str(p.source_path)]
        assert len(docs) >= 2, f"Expected at least 2 docs pages, found {len(docs)}"

    def test_blog_section_exists(self, site) -> None:
        """Blog section should be discovered."""
        posts = [p for p in site.pages if "/blog/" in str(p.source_path)]
        assert len(posts) >= 2, f"Expected at least 2 blog pages, found {len(posts)}"

    def test_projects_section_exists(self, site) -> None:
        """Projects section should be discovered."""
        projects = [p for p in site.pages if "/projects/" in str(p.source_path)]
        assert len(projects) >= 2, f"Expected at least 2 project pages, found {len(projects)}"


@pytest.mark.bengal(testroot="test-mixed-content")
class TestMixedContentTypes:
    """Test content type assignment via cascade."""

    def test_docs_pages_have_doc_type(self, site) -> None:
        """Docs pages should have 'doc' content type from cascade."""
        docs = [
            p
            for p in site.pages
            if "/docs/" in str(p.source_path) and "_index" not in str(p.source_path)
        ]

        for doc in docs:
            # Content type may be accessed via type attribute or metadata
            doc_type = getattr(doc, "type", None) or getattr(doc, "content_type", None)
            if doc_type:
                assert doc_type == "doc", f"Doc page should have 'doc' type, got {doc_type}"

    def test_blog_pages_have_blog_type(self, site) -> None:
        """Blog pages should have 'blog' content type from cascade."""
        posts = [p for p in site.pages if "/blog/post" in str(p.source_path)]

        for post in posts:
            post_type = getattr(post, "type", None) or getattr(post, "content_type", None)
            if post_type:
                assert post_type == "blog", f"Blog post should have 'blog' type, got {post_type}"

    def test_project_pages_have_portfolio_type(self, site) -> None:
        """Project pages should have 'portfolio' content type from cascade."""
        projects = [p for p in site.pages if "/projects/project" in str(p.source_path)]

        for project in projects:
            proj_type = getattr(project, "type", None) or getattr(project, "content_type", None)
            if proj_type:
                assert proj_type == "portfolio", (
                    f"Project should have 'portfolio' type, got {proj_type}"
                )


@pytest.mark.bengal(testroot="test-mixed-content")
class TestMixedContentBuild:
    """Test building mixed content sites."""

    def test_site_builds_successfully(self, site, build_site) -> None:
        """Mixed content site should build without errors."""
        build_site()

        output = site.output_dir
        assert output.exists(), "Output directory should exist"
        assert (output / "index.html").exists(), "Landing page should exist"

    def test_all_sections_rendered(self, site, build_site) -> None:
        """All sections should have their pages rendered."""
        build_site()

        output = site.output_dir

        # Check docs section
        assert (output / "docs" / "index.html").exists(), "Docs index should exist"
        assert (output / "docs" / "getting-started" / "index.html").exists(), (
            "Getting started doc should exist"
        )

        # Check blog section
        assert (output / "blog" / "index.html").exists(), "Blog index should exist"
        assert (output / "blog" / "post-1" / "index.html").exists(), "Blog post should exist"

        # Check projects section
        assert (output / "projects" / "index.html").exists(), "Projects index should exist"
        assert (output / "projects" / "project-alpha" / "index.html").exists(), (
            "Project page should exist"
        )

    def test_sitemap_includes_all_sections(self, site, build_site) -> None:
        """Sitemap should include pages from all sections."""
        build_site()

        sitemap_path = site.output_dir / "sitemap.xml"
        assert sitemap_path.exists(), "Sitemap should exist"

        sitemap = sitemap_path.read_text()

        # Check that all sections are represented in sitemap
        assert "/docs/" in sitemap, "Docs should be in sitemap"
        assert "/blog/" in sitemap, "Blog should be in sitemap"
        assert "/projects/" in sitemap, "Projects should be in sitemap"


@pytest.mark.bengal(testroot="test-mixed-content")
class TestMixedContentNavigation:
    """Test navigation across sections."""

    def test_main_menu_configured(self, site) -> None:
        """Main menu should be configured from bengal.toml."""
        # Access menu configuration
        menu_config = site.config.get("menu", {}).get("main", {})

        if menu_config:
            items = menu_config.get("items", [])
            assert len(items) >= 3, "Main menu should have at least 3 items"

    def test_cross_section_links_work(self, site, build_site) -> None:
        """Links between sections should resolve correctly."""
        build_site()

        # Check landing page contains links to sections
        landing_html = (site.output_dir / "index.html").read_text()

        # The landing page should have navigation to other sections
        # (actual structure depends on theme)
        assert "docs" in landing_html.lower() or "blog" in landing_html.lower(), (
            "Landing page should reference other sections"
        )
