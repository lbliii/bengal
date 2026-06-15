"""Unit tests for Page visibility system.

Tests the hidden/visibility frontmatter and related properties:
- hidden: true shorthand
- visibility object with granular controls
- in_listings, in_sitemap, in_search, in_rss properties
- robots_meta directive
- should_render_in_environment for render: local/never
"""

from pathlib import Path

from bengal.core.page_visibility import (
    _is_page_draft,
    get_page_visibility,
    get_robots_meta,
    is_page_in_ai_input,
    is_page_in_ai_train,
    is_page_in_listings,
    is_page_in_rss,
    is_page_in_search,
    is_page_in_sitemap,
    should_render_page,
    should_render_page_in_environment,
)
from tests._testing.mocks import MockSite
from tests._testing.mocks import make_mock_page as _page


class TestHiddenShorthand:
    """Test the hidden: true frontmatter shorthand."""

    def test_hidden_false_by_default(self):
        """Pages are not hidden by default."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test content",
            _raw_metadata={"title": "Test"},
        )

        assert page.metadata.get("hidden", False) is False

    def test_hidden_true_when_set(self):
        """Pages can be marked as hidden."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret content",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert page.metadata["hidden"] is True

    def test_hidden_expands_to_restrictive_visibility(self):
        """hidden: true expands to restrictive visibility defaults."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret content",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        visibility = get_page_visibility(page)
        assert visibility["menu"] is False
        assert visibility["listings"] is False
        assert visibility["sitemap"] is False
        assert visibility["search"] is False
        assert visibility["rss"] is False
        assert visibility["robots"] == "noindex, nofollow"
        assert visibility["render"] == "always"
        assert visibility["ai_input"] is False
        assert visibility["ai_train"] is False


class TestVisibilityObject:
    """Test the visibility object with granular controls."""

    def test_visibility_defaults_to_permissive(self):
        """By default, legacy visibility settings are permissive."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test content",
            _raw_metadata={"title": "Test"},
        )

        visibility = get_page_visibility(page)
        assert visibility["menu"] is True
        assert visibility["listings"] is True
        assert visibility["sitemap"] is True
        assert visibility["search"] is True
        assert visibility["rss"] is True
        assert visibility["robots"] == "index, follow"
        assert visibility["render"] == "always"
        assert visibility["ai_input"] is True
        assert visibility["ai_train"] is False

    def test_visibility_partial_override(self):
        """Can override individual visibility settings."""
        page = _page(
            source_path=Path("content/archive.md"),
            _raw_content="Archive content",
            _raw_metadata={
                "title": "Archive",
                "visibility": {
                    "listings": False,  # Exclude from listings
                    "sitemap": True,  # Keep in sitemap
                },
            },
        )

        visibility = get_page_visibility(page)
        assert visibility["menu"] is True  # Default
        assert visibility["listings"] is False  # Overridden
        assert visibility["sitemap"] is True  # Explicitly set
        assert visibility["search"] is True  # Default

    def test_visibility_all_options(self):
        """Can set all visibility options."""
        page = _page(
            source_path=Path("content/internal.md"),
            _raw_content="Internal content",
            _raw_metadata={
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

        visibility = get_page_visibility(page)
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
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert is_page_in_listings(page) is True

    def test_hidden_page_not_in_listings(self):
        """Hidden pages are not in listings."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert is_page_in_listings(page) is False

    def test_draft_page_not_in_listings(self):
        """Draft pages are not in listings."""
        page = _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={"title": "Draft", "draft": True},
        )

        assert is_page_in_listings(page) is False

    def test_visibility_listings_false_not_in_listings(self):
        """Pages with visibility.listings: false are not in listings."""
        page = _page(
            source_path=Path("content/archive.md"),
            _raw_content="Archive",
            _raw_metadata={
                "title": "Archive",
                "visibility": {"listings": False},
            },
        )

        assert is_page_in_listings(page) is False


class TestInSitemapProperty:
    """Test the in_sitemap property."""

    def test_regular_page_in_sitemap(self):
        """Regular pages are in sitemap."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert is_page_in_sitemap(page) is True

    def test_hidden_page_not_in_sitemap(self):
        """Hidden pages are not in sitemap."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert is_page_in_sitemap(page) is False

    def test_draft_page_not_in_sitemap(self):
        """Draft pages are not in sitemap."""
        page = _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={"title": "Draft", "draft": True},
        )

        assert is_page_in_sitemap(page) is False


class TestInSearchProperty:
    """Test the in_search property."""

    def test_regular_page_in_search(self):
        """Regular pages are in search index."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert is_page_in_search(page) is True

    def test_hidden_page_not_in_search(self):
        """Hidden pages are not in search index."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert is_page_in_search(page) is False


class TestInRssProperty:
    """Test the in_rss property."""

    def test_regular_page_in_rss(self):
        """Regular pages are in RSS feeds."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert is_page_in_rss(page) is True

    def test_hidden_page_not_in_rss(self):
        """Hidden pages are not in RSS feeds."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert is_page_in_rss(page) is False


class TestRobotsMeta:
    """Test the robots_meta property."""

    def test_regular_page_robots_meta(self):
        """Regular pages have index, follow robots meta."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert get_robots_meta(page) == "index, follow"

    def test_hidden_page_robots_meta(self):
        """Hidden pages have noindex, nofollow robots meta."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )

        assert get_robots_meta(page) == "noindex, nofollow"

    def test_custom_robots_meta(self):
        """Can set custom robots meta."""
        page = _page(
            source_path=Path("content/nofollow.md"),
            _raw_content="Content",
            _raw_metadata={
                "title": "NoFollow",
                "visibility": {"robots": "noindex"},
            },
        )

        assert get_robots_meta(page) == "noindex"


class TestShouldRenderInEnvironment:
    """Test the should_render_in_environment method."""

    def test_always_renders_in_both_environments(self):
        """render: always (default) renders in both environments."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post content",
            _raw_metadata={"title": "Post"},
        )

        assert should_render_page_in_environment(page, is_production=False) is True
        assert should_render_page_in_environment(page, is_production=True) is True

    def test_local_only_renders_in_dev(self):
        """render: local only renders in dev server, not production."""
        page = _page(
            source_path=Path("content/wip.md"),
            _raw_content="WIP content",
            _raw_metadata={
                "title": "WIP",
                "visibility": {"render": "local"},
            },
        )

        assert should_render_page_in_environment(page, is_production=False) is True
        assert should_render_page_in_environment(page, is_production=True) is False

    def test_never_renders_nowhere(self):
        """render: never doesn't render in any environment."""
        page = _page(
            source_path=Path("content/template.md"),
            _raw_content="Template content",
            _raw_metadata={
                "title": "Template",
                "visibility": {"render": "never"},
            },
        )

        assert should_render_page_in_environment(page, is_production=False) is False
        assert should_render_page_in_environment(page, is_production=True) is False


class TestShouldRenderProperty:
    """Test the should_render property."""

    def test_always_should_render(self):
        """render: always should render."""
        page = _page(
            source_path=Path("content/post.md"),
            _raw_content="Post",
            _raw_metadata={"title": "Post"},
        )

        assert should_render_page(page) is True

    def test_local_should_render(self):
        """render: local should render (environment-agnostic check)."""
        page = _page(
            source_path=Path("content/wip.md"),
            _raw_content="WIP",
            _raw_metadata={
                "title": "WIP",
                "visibility": {"render": "local"},
            },
        )

        assert should_render_page(page) is True  # Not "never"

    def test_never_should_not_render(self):
        """render: never should not render."""
        page = _page(
            source_path=Path("content/template.md"),
            _raw_content="Template",
            _raw_metadata={
                "title": "Template",
                "visibility": {"render": "never"},
            },
        )

        assert should_render_page(page) is False


class TestVisibilityWithDraft:
    """Test visibility interaction with draft status."""

    def test_draft_excludes_from_all_outputs(self):
        """Draft pages are excluded from all outputs regardless of visibility."""
        page = _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={
                "title": "Draft",
                "draft": True,
                "visibility": {
                    "listings": True,
                    "sitemap": True,
                    "search": True,
                    "rss": True,
                    "ai_input": True,
                    "ai_train": True,
                },
            },
        )

        # Draft overrides visibility settings
        assert is_page_in_listings(page) is False
        assert is_page_in_sitemap(page) is False
        assert is_page_in_search(page) is False
        assert is_page_in_rss(page) is False
        assert is_page_in_ai_input(page) is False
        assert is_page_in_ai_train(page) is False


class TestDraftsPreview:
    """Test the build.drafts preview flag (bengal serve/build --drafts).

    The CLI flag sets ``site.config["build"]["drafts"] = True``; the
    visibility gate then treats draft pages as publishable so authors can
    preview unpublished content locally. Default behaviour (drafts hidden)
    must be unchanged.
    """

    def _draft_page(self, *, drafts_enabled: bool):
        site = MockSite(config={"build": {"drafts": drafts_enabled}})
        return _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={"title": "Draft", "draft": True},
            _site=site,
        )

    def test_default_hides_drafts(self):
        """Without --drafts, draft pages are excluded from every output."""
        page = self._draft_page(drafts_enabled=False)

        assert _is_page_draft(page) is True
        assert is_page_in_listings(page) is False
        assert is_page_in_sitemap(page) is False
        assert is_page_in_search(page) is False
        assert is_page_in_rss(page) is False

    def test_drafts_flag_includes_drafts(self):
        """With --drafts (build.drafts=True), draft pages become visible."""
        page = self._draft_page(drafts_enabled=True)

        assert _is_page_draft(page) is False
        assert is_page_in_listings(page) is True
        assert is_page_in_sitemap(page) is True
        assert is_page_in_search(page) is True
        assert is_page_in_rss(page) is True

    def test_drafts_flag_does_not_publish_hidden_pages(self):
        """--drafts only affects draft pages; hidden: true stays hidden."""
        site = MockSite(config={"build": {"drafts": True}})
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
            _site=site,
        )

        assert is_page_in_listings(page) is False
        assert is_page_in_sitemap(page) is False

    def test_non_draft_page_unaffected_by_flag(self):
        """Regular pages stay visible whether or not --drafts is set."""
        for drafts_enabled in (False, True):
            site = MockSite(config={"build": {"drafts": drafts_enabled}})
            page = _page(
                source_path=Path("content/post.md"),
                _raw_content="Post",
                _raw_metadata={"title": "Post"},
                _site=site,
            )
            assert is_page_in_listings(page) is True
