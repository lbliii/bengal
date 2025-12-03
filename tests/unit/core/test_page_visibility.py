"""Unit tests for Page visibility system.

Tests the hidden/visibility frontmatter and related properties:
- hidden: true shorthand
- visibility object with granular controls
- in_listings, in_sitemap, in_search, in_rss properties
- robots_meta directive
- should_render_in_environment for render: local/never
"""

from pathlib import Path

import pytest

from bengal.core.page import Page


class TestHiddenShorthand:
    """Test the hidden: true frontmatter shorthand."""

    def test_hidden_false_by_default(self):
        """Pages are not hidden by default."""
        page = Page(
            source_path=Path("content/test.md"),
            content="Test content",
            metadata={"title": "Test"},
        )

        assert page.hidden is False

    def test_hidden_true_when_set(self):
        """Pages can be marked as hidden."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret content",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.hidden is True

    def test_hidden_expands_to_restrictive_visibility(self):
        """hidden: true expands to restrictive visibility defaults."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret content",
            metadata={"title": "Secret", "hidden": True},
        )

        visibility = page.visibility
        assert visibility["menu"] is False
        assert visibility["listings"] is False
        assert visibility["sitemap"] is False
        assert visibility["search"] is False
        assert visibility["rss"] is False
        assert visibility["robots"] == "noindex, nofollow"
        assert visibility["render"] == "always"


class TestVisibilityObject:
    """Test the visibility object with granular controls."""

    def test_visibility_defaults_to_permissive(self):
        """By default, all visibility settings are permissive."""
        page = Page(
            source_path=Path("content/test.md"),
            content="Test content",
            metadata={"title": "Test"},
        )

        visibility = page.visibility
        assert visibility["menu"] is True
        assert visibility["listings"] is True
        assert visibility["sitemap"] is True
        assert visibility["search"] is True
        assert visibility["rss"] is True
        assert visibility["robots"] == "index, follow"
        assert visibility["render"] == "always"

    def test_visibility_partial_override(self):
        """Can override individual visibility settings."""
        page = Page(
            source_path=Path("content/archive.md"),
            content="Archive content",
            metadata={
                "title": "Archive",
                "visibility": {
                    "listings": False,  # Exclude from listings
                    "sitemap": True,  # Keep in sitemap
                },
            },
        )

        visibility = page.visibility
        assert visibility["menu"] is True  # Default
        assert visibility["listings"] is False  # Overridden
        assert visibility["sitemap"] is True  # Explicitly set
        assert visibility["search"] is True  # Default

    def test_visibility_all_options(self):
        """Can set all visibility options."""
        page = Page(
            source_path=Path("content/internal.md"),
            content="Internal content",
            metadata={
                "title": "Internal",
                "visibility": {
                    "menu": False,
                    "listings": False,
                    "sitemap": False,
                    "search": True,
                    "rss": False,
                    "robots": "noindex",
                    "render": "local",
                },
            },
        )

        visibility = page.visibility
        assert visibility["menu"] is False
        assert visibility["listings"] is False
        assert visibility["sitemap"] is False
        assert visibility["search"] is True
        assert visibility["rss"] is False
        assert visibility["robots"] == "noindex"
        assert visibility["render"] == "local"


class TestInListingsProperty:
    """Test the in_listings property."""

    def test_regular_page_in_listings(self):
        """Regular pages are in listings."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.in_listings is True

    def test_hidden_page_not_in_listings(self):
        """Hidden pages are not in listings."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.in_listings is False

    def test_draft_page_not_in_listings(self):
        """Draft pages are not in listings."""
        page = Page(
            source_path=Path("content/draft.md"),
            content="Draft",
            metadata={"title": "Draft", "draft": True},
        )

        assert page.in_listings is False

    def test_visibility_listings_false_not_in_listings(self):
        """Pages with visibility.listings: false are not in listings."""
        page = Page(
            source_path=Path("content/archive.md"),
            content="Archive",
            metadata={
                "title": "Archive",
                "visibility": {"listings": False},
            },
        )

        assert page.in_listings is False


class TestInSitemapProperty:
    """Test the in_sitemap property."""

    def test_regular_page_in_sitemap(self):
        """Regular pages are in sitemap."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.in_sitemap is True

    def test_hidden_page_not_in_sitemap(self):
        """Hidden pages are not in sitemap."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.in_sitemap is False

    def test_draft_page_not_in_sitemap(self):
        """Draft pages are not in sitemap."""
        page = Page(
            source_path=Path("content/draft.md"),
            content="Draft",
            metadata={"title": "Draft", "draft": True},
        )

        assert page.in_sitemap is False


class TestInSearchProperty:
    """Test the in_search property."""

    def test_regular_page_in_search(self):
        """Regular pages are in search index."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.in_search is True

    def test_hidden_page_not_in_search(self):
        """Hidden pages are not in search index."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.in_search is False


class TestInRssProperty:
    """Test the in_rss property."""

    def test_regular_page_in_rss(self):
        """Regular pages are in RSS feeds."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.in_rss is True

    def test_hidden_page_not_in_rss(self):
        """Hidden pages are not in RSS feeds."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.in_rss is False


class TestRobotsMeta:
    """Test the robots_meta property."""

    def test_regular_page_robots_meta(self):
        """Regular pages have index, follow robots meta."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.robots_meta == "index, follow"

    def test_hidden_page_robots_meta(self):
        """Hidden pages have noindex, nofollow robots meta."""
        page = Page(
            source_path=Path("content/secret.md"),
            content="Secret",
            metadata={"title": "Secret", "hidden": True},
        )

        assert page.robots_meta == "noindex, nofollow"

    def test_custom_robots_meta(self):
        """Can set custom robots meta."""
        page = Page(
            source_path=Path("content/nofollow.md"),
            content="Content",
            metadata={
                "title": "NoFollow",
                "visibility": {"robots": "noindex"},
            },
        )

        assert page.robots_meta == "noindex"


class TestShouldRenderInEnvironment:
    """Test the should_render_in_environment method."""

    def test_always_renders_in_both_environments(self):
        """render: always (default) renders in both environments."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post content",
            metadata={"title": "Post"},
        )

        assert page.should_render_in_environment(is_production=False) is True
        assert page.should_render_in_environment(is_production=True) is True

    def test_local_only_renders_in_dev(self):
        """render: local only renders in dev server, not production."""
        page = Page(
            source_path=Path("content/wip.md"),
            content="WIP content",
            metadata={
                "title": "WIP",
                "visibility": {"render": "local"},
            },
        )

        assert page.should_render_in_environment(is_production=False) is True
        assert page.should_render_in_environment(is_production=True) is False

    def test_never_renders_nowhere(self):
        """render: never doesn't render in any environment."""
        page = Page(
            source_path=Path("content/template.md"),
            content="Template content",
            metadata={
                "title": "Template",
                "visibility": {"render": "never"},
            },
        )

        assert page.should_render_in_environment(is_production=False) is False
        assert page.should_render_in_environment(is_production=True) is False


class TestShouldRenderProperty:
    """Test the should_render property."""

    def test_always_should_render(self):
        """render: always should render."""
        page = Page(
            source_path=Path("content/post.md"),
            content="Post",
            metadata={"title": "Post"},
        )

        assert page.should_render is True

    def test_local_should_render(self):
        """render: local should render (environment-agnostic check)."""
        page = Page(
            source_path=Path("content/wip.md"),
            content="WIP",
            metadata={
                "title": "WIP",
                "visibility": {"render": "local"},
            },
        )

        assert page.should_render is True  # Not "never"

    def test_never_should_not_render(self):
        """render: never should not render."""
        page = Page(
            source_path=Path("content/template.md"),
            content="Template",
            metadata={
                "title": "Template",
                "visibility": {"render": "never"},
            },
        )

        assert page.should_render is False


class TestVisibilityWithDraft:
    """Test visibility interaction with draft status."""

    def test_draft_excludes_from_all_outputs(self):
        """Draft pages are excluded from all outputs regardless of visibility."""
        page = Page(
            source_path=Path("content/draft.md"),
            content="Draft",
            metadata={
                "title": "Draft",
                "draft": True,
                "visibility": {
                    "listings": True,
                    "sitemap": True,
                    "search": True,
                    "rss": True,
                },
            },
        )

        # Draft overrides visibility settings
        assert page.in_listings is False
        assert page.in_sitemap is False
        assert page.in_search is False
        assert page.in_rss is False

