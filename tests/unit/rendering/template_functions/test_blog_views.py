"""Tests for blog view filters (PostView, posts filter)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from bengal.rendering.template_functions.blog import (
    PostView,
    featured_posts_filter,
    post_view_filter,
    posts_filter,
)


class TestPostViewFromPage:
    """Tests for PostView.from_page()."""

    def test_extracts_basic_properties(self) -> None:
        """Should extract title, href, date from page."""
        page = MagicMock()
        page.title = "My Post"
        page.href = "/blog/my-post/"
        page.date = datetime(2024, 1, 15)
        page.metadata = {}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 5
        page.word_count = 1000
        page.tags = ["python", "testing"]
        page.draft = False

        view = PostView.from_page(page)

        assert view.title == "My Post"
        assert view.href == "/blog/my-post/"
        assert view.date == datetime(2024, 1, 15)
        assert view.reading_time == 5
        assert view.word_count == 1000
        assert view.tags == ("python", "testing")
        assert view.draft is False

    def test_extracts_image_from_metadata(self) -> None:
        """Should extract image from metadata.image."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {"image": "/images/hero.jpg"}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.image == "/images/hero.jpg"

    def test_falls_back_to_cover_for_image(self) -> None:
        """Should fall back to metadata.cover if image not set."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {"cover": "/images/cover.jpg"}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.image == "/images/cover.jpg"

    def test_extracts_description_from_metadata(self) -> None:
        """Should extract description from metadata."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {"description": "A great post about testing."}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.description == "A great post about testing."

    def test_falls_back_to_excerpt_for_description(self) -> None:
        """Should fall back to excerpt if description not set."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {}
        page.params = {}
        page.excerpt = "First paragraph of the post..."
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.description == "First paragraph of the post..."
        assert view.excerpt == "First paragraph of the post..."

    def test_extracts_author_info(self) -> None:
        """Should extract author info from metadata."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {
            "author": "Jane Doe",
            "author_avatar": "/avatars/jane.jpg",
            "author_title": "Senior Developer",
        }
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.author == "Jane Doe"
        assert view.author_avatar == "/avatars/jane.jpg"
        assert view.author_title == "Senior Developer"

    def test_extracts_featured_flag(self) -> None:
        """Should extract featured flag from metadata."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {"featured": True}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.featured is True

    def test_extracts_updated_date(self) -> None:
        """Should extract updated date from metadata."""
        updated_date = datetime(2024, 2, 20)
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = datetime(2024, 1, 15)
        page.metadata = {"updated": updated_date}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.updated == updated_date

    def test_handles_missing_metadata(self) -> None:
        """Should handle page with no metadata gracefully."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = None
        page.params = None
        page.excerpt = None
        page.reading_time = None
        page.word_count = None
        page.tags = None
        page.draft = False

        view = PostView.from_page(page)

        assert view.title == "Post"
        assert view.image == ""
        assert view.description == ""
        assert view.tags == ()

    def test_handles_params_as_fallback(self) -> None:
        """Should use params as fallback for metadata."""
        page = MagicMock()
        page.title = "Post"
        page.href = "/post/"
        page.date = None
        page.metadata = {}
        page.params = {
            "image": "/from-params.jpg",
            "author": "From Params",
        }
        page.excerpt = ""
        page.reading_time = 0
        page.word_count = 0
        page.tags = []
        page.draft = False

        view = PostView.from_page(page)

        assert view.image == "/from-params.jpg"
        assert view.author == "From Params"


class TestPostsFilter:
    """Tests for posts_filter()."""

    def test_converts_list_of_pages(self) -> None:
        """Should convert list of pages to PostViews."""
        page1 = MagicMock()
        page1.title = "Post 1"
        page1.href = "/post-1/"
        page1.date = None
        page1.metadata = {}
        page1.params = {}
        page1.excerpt = ""
        page1.reading_time = 3
        page1.word_count = 500
        page1.tags = []
        page1.draft = False

        page2 = MagicMock()
        page2.title = "Post 2"
        page2.href = "/post-2/"
        page2.date = None
        page2.metadata = {}
        page2.params = {}
        page2.excerpt = ""
        page2.reading_time = 5
        page2.word_count = 800
        page2.tags = []
        page2.draft = False

        result = posts_filter([page1, page2])

        assert len(result) == 2
        assert result[0].title == "Post 1"
        assert result[1].title == "Post 2"

    def test_returns_empty_list_for_none(self) -> None:
        """Should return empty list for None input."""
        result = posts_filter(None)
        assert result == []

    def test_returns_empty_list_for_empty_input(self) -> None:
        """Should return empty list for empty input."""
        result = posts_filter([])
        assert result == []


class TestPostViewFilter:
    """Tests for post_view_filter()."""

    def test_converts_single_page(self) -> None:
        """Should convert single page to PostView."""
        page = MagicMock()
        page.title = "Single Post"
        page.href = "/single/"
        page.date = None
        page.metadata = {}
        page.params = {}
        page.excerpt = ""
        page.reading_time = 2
        page.word_count = 300
        page.tags = []
        page.draft = False

        result = post_view_filter(page)

        assert result is not None
        assert result.title == "Single Post"

    def test_returns_none_for_none_input(self) -> None:
        """Should return None for None input."""
        result = post_view_filter(None)
        assert result is None


class TestFeaturedPostsFilter:
    """Tests for featured_posts_filter()."""

    def test_returns_only_featured_posts(self) -> None:
        """Should return only featured posts."""
        featured = MagicMock()
        featured.title = "Featured"
        featured.href = "/featured/"
        featured.date = None
        featured.metadata = {"featured": True}
        featured.params = {}
        featured.excerpt = ""
        featured.reading_time = 0
        featured.word_count = 0
        featured.tags = []
        featured.draft = False

        regular = MagicMock()
        regular.title = "Regular"
        regular.href = "/regular/"
        regular.date = None
        regular.metadata = {}
        regular.params = {}
        regular.excerpt = ""
        regular.reading_time = 0
        regular.word_count = 0
        regular.tags = []
        regular.draft = False

        result = featured_posts_filter([featured, regular])

        assert len(result) == 1
        assert result[0].title == "Featured"

    def test_respects_limit(self) -> None:
        """Should respect limit parameter."""
        posts = []
        for i in range(5):
            page = MagicMock()
            page.title = f"Featured {i}"
            page.href = f"/featured-{i}/"
            page.date = None
            page.metadata = {"featured": True}
            page.params = {}
            page.excerpt = ""
            page.reading_time = 0
            page.word_count = 0
            page.tags = []
            page.draft = False
            posts.append(page)

        result = featured_posts_filter(posts, limit=2)

        assert len(result) == 2
