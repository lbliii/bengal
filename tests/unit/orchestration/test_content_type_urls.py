"""
Tests for URL generation across different content types.

Regression tests ensuring all content types (blog, tutorial, autodoc/python, etc.)
generate correct URLs for child pages, similar to the doc type bug fix.

Each content type might have different URL patterns, and we need to ensure
cascade and section prefixes work correctly for all of them.
"""

import pytest

from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator


class TestBlogContentTypeURLs:
    """Test URL generation for blog content type."""

    @pytest.fixture
    def blog_site(self, tmp_path):
        """Create test site with blog structure."""
        root = tmp_path / "blog_site"
        root.mkdir()
        content_dir = root / "content"

        # Create blog structure
        blog_dir = content_dir / "blog"
        blog_2024 = blog_dir / "2024"
        blog_2024.mkdir(parents=True, exist_ok=True)

        # Blog index
        (blog_dir / "_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---\n# Blog"
        )

        # Year index
        (blog_2024 / "_index.md").write_text("---\ntitle: 2024 Posts\n---\n# 2024")

        # Blog posts
        (blog_2024 / "first-post.md").write_text(
            "---\ntitle: First Post\ndate: 2024-01-01\n---\n# Post"
        )
        (blog_2024 / "second-post.md").write_text(
            "---\ntitle: Second Post\ndate: 2024-01-15\n---\n# Post"
        )

        site = Site(root_path=root, config={})
        return site

    def test_blog_posts_have_section_prefix(self, blog_site):
        """Blog posts should include /blog/ prefix in URLs."""
        orchestrator = ContentOrchestrator(blog_site)
        orchestrator.discover()

        # Find blog posts (not index pages)
        blog_posts = [
            p
            for p in blog_site.pages
            if "blog" in str(p.source_path) and p.source_path.stem not in ("_index", "index")
        ]

        assert len(blog_posts) >= 2, "Should have at least 2 blog posts"

        # All posts should have /blog/ prefix
        for post in blog_posts:
            assert post.href.startswith("/blog/"), (
                f"Blog post {post.source_path.name} has wrong URL: {post.href}"
            )

    def test_blog_nested_year_urls(self, blog_site):
        """Blog posts in year subdirectories should maintain full path."""
        orchestrator = ContentOrchestrator(blog_site)
        orchestrator.discover()

        # Find posts in 2024
        posts_2024 = [
            p
            for p in blog_site.pages
            if "2024" in str(p.source_path) and p.source_path.stem != "_index"
        ]

        assert len(posts_2024) >= 2

        for post in posts_2024:
            assert post.href.startswith("/blog/2024/"), (
                f"2024 post should have /blog/2024/ prefix, got: {post.href}"
            )

    def test_blog_cascade_preserves_urls(self, blog_site):
        """Blog cascade: type should not break URLs."""
        orchestrator = ContentOrchestrator(blog_site)
        orchestrator.discover()

        # Find cascaded posts
        cascaded_posts = [
            p
            for p in blog_site.pages
            if p.metadata.get("type") == "blog" and "cascade" not in p.metadata
        ]

        for post in cascaded_posts:
            assert "/blog/" in post.href, f"Cascaded post has wrong URL: {post.href}"


class TestTutorialContentTypeURLs:
    """Test URL generation for tutorial content type."""

    @pytest.fixture
    def tutorial_site(self, tmp_path):
        """Create test site with tutorial structure."""
        root = tmp_path / "tutorial_site"
        root.mkdir()
        content_dir = root / "content"

        # Create tutorial series structure
        python_dir = content_dir / "tutorials" / "python"
        python_dir.mkdir(parents=True, exist_ok=True)

        # Tutorial index
        (content_dir / "tutorials" / "_index.md").write_text(
            "---\ntitle: Tutorials\ntype: tutorial\ncascade:\n  type: tutorial\n---"
        )

        # Python series index
        (python_dir / "_index.md").write_text("---\ntitle: Python Tutorials\n---")

        # Tutorial lessons
        (python_dir / "basics.md").write_text("---\ntitle: Python Basics\nweight: 10\n---")
        (python_dir / "advanced.md").write_text("---\ntitle: Advanced Python\nweight: 20\n---")

        site = Site(root_path=root, config={})
        return site

    def test_tutorial_lessons_have_series_prefix(self, tutorial_site):
        """Tutorial lessons should include series path."""
        orchestrator = ContentOrchestrator(tutorial_site)
        orchestrator.discover()

        # Find tutorial lessons
        lessons = [
            p
            for p in tutorial_site.pages
            if "python" in str(p.source_path) and p.source_path.stem != "_index"
        ]

        assert len(lessons) >= 2

        for lesson in lessons:
            assert lesson.href.startswith("/tutorials/python/"), (
                f"Tutorial lesson should have /tutorials/python/ prefix, got: {lesson.href}"
            )


class TestAPIReferenceURLs:
    """Test URL generation for API reference content type."""

    @pytest.fixture
    def api_site(self, tmp_path):
        """Create test site with API reference structure."""
        root = tmp_path / "api_site"
        root.mkdir()
        content_dir = root / "content"

        # Create API structure
        api_core = content_dir / "api" / "core"
        api_core.mkdir(parents=True, exist_ok=True)

        # API index
        (content_dir / "api" / "_index.md").write_text(
            "---\ntitle: API Reference\ntype: autodoc/python\ncascade:\n  type: autodoc/python\n---"
        )

        # Core module index
        (api_core / "_index.md").write_text("---\ntitle: Core Module\n---")

        # API pages
        (api_core / "utils.md").write_text("---\ntitle: utils\ntype: python-module\n---")
        (api_core / "helpers.md").write_text("---\ntitle: helpers\ntype: python-module\n---")

        site = Site(root_path=root, config={})
        return site

    def test_api_reference_urls_include_module_path(self, api_site):
        """API reference pages should include module hierarchy."""
        orchestrator = ContentOrchestrator(api_site)
        orchestrator.discover()

        # Find API pages
        api_pages = [
            p
            for p in api_site.pages
            if "core" in str(p.source_path) and p.source_path.stem != "_index"
        ]

        assert len(api_pages) >= 2

        for page in api_pages:
            assert page.href.startswith("/api/core/"), (
                f"API page should have /api/core/ prefix, got: {page.href}"
            )


class TestChangelogURLs:
    """Test URL generation for changelog content type."""

    @pytest.fixture
    def changelog_site(self, tmp_path):
        """Create test site with changelog structure."""
        root = tmp_path / "changelog_site"
        root.mkdir()
        content_dir = root / "content"

        changelog_dir = content_dir / "changelog"
        v1_dir = changelog_dir / "v1.0"
        v1_dir.mkdir(parents=True, exist_ok=True)

        # Changelog index
        (changelog_dir / "_index.md").write_text(
            "---\ntitle: Changelog\ntype: changelog\ncascade:\n  type: changelog\n---"
        )

        # Version entries
        (v1_dir / "release.md").write_text("---\ntitle: v1.0 Release\ndate: 2024-01-01\n---")
        (v1_dir / "hotfix.md").write_text("---\ntitle: v1.0.1 Hotfix\ndate: 2024-01-15\n---")

        site = Site(root_path=root, config={})
        return site

    def test_changelog_entries_include_version_prefix(self, changelog_site):
        """Changelog entries should include version in URL."""
        orchestrator = ContentOrchestrator(changelog_site)
        orchestrator.discover()

        # Find changelog entries
        entries = [
            p
            for p in changelog_site.pages
            if "v1.0" in str(p.source_path) and p.source_path.stem != "_index"
        ]

        assert len(entries) >= 2

        for entry in entries:
            assert entry.href.startswith("/changelog/v1.0/"), (
                f"Changelog entry should have /changelog/v1.0/ prefix, got: {entry.href}"
            )


class TestMixedContentTypes:
    """Test sites with multiple content types."""

    @pytest.fixture
    def mixed_site(self, tmp_path):
        """Create test site with multiple content types."""
        root = tmp_path / "mixed_site"
        root.mkdir()
        content_dir = root / "content"

        # Docs
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "_index.md").write_text(
            "---\ntitle: Docs\ntype: doc\ncascade:\n  type: doc\n---"
        )
        (docs_dir / "guide.md").write_text("---\ntitle: Guide\n---")

        # Blog
        blog_dir = content_dir / "blog"
        blog_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "_index.md").write_text(
            "---\ntitle: Blog\ntype: blog\ncascade:\n  type: blog\n---"
        )
        (blog_dir / "post.md").write_text("---\ntitle: Post\ndate: 2024-01-01\n---")

        # Tutorials
        tutorial_dir = content_dir / "tutorials"
        tutorial_dir.mkdir(parents=True, exist_ok=True)
        (tutorial_dir / "_index.md").write_text(
            "---\ntitle: Tutorials\ntype: tutorial\ncascade:\n  type: tutorial\n---"
        )
        (tutorial_dir / "lesson.md").write_text("---\ntitle: Lesson\n---")

        site = Site(root_path=root, config={})
        return site

    def test_all_content_types_have_correct_prefixes(self, mixed_site):
        """All content types should maintain their section prefixes."""
        orchestrator = ContentOrchestrator(mixed_site)
        orchestrator.discover()

        # Find pages by type
        doc_pages = [p for p in mixed_site.pages if "docs" in str(p.source_path)]
        blog_pages = [p for p in mixed_site.pages if "blog" in str(p.source_path)]
        tutorial_pages = [p for p in mixed_site.pages if "tutorials" in str(p.source_path)]

        # Verify each type has correct prefix
        for page in doc_pages:
            assert page.href.startswith("/docs/"), f"Doc page wrong URL: {page.href}"

        for page in blog_pages:
            assert page.href.startswith("/blog/"), f"Blog page wrong URL: {page.href}"

        for page in tutorial_pages:
            assert page.href.startswith("/tutorials/"), f"Tutorial page wrong URL: {page.href}"

    def test_no_url_collisions_between_types(self, mixed_site):
        """Different content types should not have URL collisions."""
        orchestrator = ContentOrchestrator(mixed_site)
        orchestrator.discover()

        # Collect all URLs
        urls = [p.href for p in mixed_site.pages]

        # Check for duplicates
        assert len(urls) == len(set(urls)), f"Found duplicate URLs: {urls}"


class TestContentTypeURLConsistency:
    """Test URL consistency across content type operations."""

    def test_url_before_and_after_cascade(self, tmp_path):
        """URL should remain consistent before and after cascade application."""
        root = tmp_path / "consistency_test"
        root.mkdir()
        content_dir = root / "content" / "docs"
        content_dir.mkdir(parents=True, exist_ok=True)

        (content_dir / "_index.md").write_text(
            "---\ntitle: Docs\ntype: doc\ncascade:\n  type: doc\n---"
        )
        (content_dir / "page.md").write_text("---\ntitle: Page\n---")

        site = Site(root_path=root, config={})
        orchestrator = ContentOrchestrator(site)

        # Discover and get page
        orchestrator.discover()
        page = next(p for p in site.pages if p.source_path.stem == "page")

        # URL should be correct after full discovery
        assert page.href == "/docs/page/", f"URL wrong after cascade: {page.href}"

        # Type should be cascaded
        assert page.metadata.get("type") == "doc"
