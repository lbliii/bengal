"""Tests for taxonomy helper template functions."""

from __future__ import annotations

from bengal.rendering.template_functions.taxonomies import (
    has_tag,
    popular_tags,
    related_posts,
    tag_url,
)
from tests._testing.mocks import MockPage


class TestRelatedPosts:
    """Tests for related_posts function."""

    def test_find_related(self):
        current = MockPage(title="Current", tags=["python", "web"])
        all_pages = [
            MockPage(title="Post 1", tags=["python", "django"]),
            MockPage(title="Post 2", tags=["javascript"]),
            MockPage(title="Post 3", tags=["python", "web", "flask"]),
        ]

        result = related_posts(current, all_pages, limit=5)
        assert len(result) == 2
        # Post 3 should be first (shares 2 tags)
        assert result[0].title == "Post 3"

    def test_no_tags(self):
        current = MockPage(title="Current", tags=[])
        all_pages = [MockPage(title="Post 1", tags=["python"])]

        result = related_posts(current, all_pages)
        assert result == []

    def test_limit_results(self):
        current = MockPage(title="Current", tags=["python"])
        all_pages = [MockPage(title=f"Post {i}", tags=["python"]) for i in range(10)]

        result = related_posts(current, all_pages, limit=3)
        assert len(result) == 3


class TestPopularTags:
    """Tests for popular_tags function."""

    def test_count_tags(self):
        tags_dict = {
            "python": [1, 2, 3],
            "web": [1, 2],
            "javascript": [1],
        }

        result = popular_tags(tags_dict, limit=10)
        assert len(result) == 3
        assert result[0] == ("python", 3)  # Most popular
        assert result[1] == ("web", 2)

    def test_limit_tags(self):
        tags_dict = {
            "tag1": [1, 2, 3],
            "tag2": [1, 2],
            "tag3": [1],
        }

        result = popular_tags(tags_dict, limit=2)
        assert len(result) == 2

    def test_empty_dict(self):
        result = popular_tags({})
        assert result == []


class TestTagUrl:
    """Tests for tag_url function."""

    def test_basic_tag(self):
        result = tag_url("python")
        assert result == "/tags/python/"

    def test_tag_with_spaces(self):
        result = tag_url("web development")
        assert result == "/tags/web-development/"

    def test_tag_with_special_chars(self):
        result = tag_url("C++")
        assert result == "/tags/c/"

    def test_empty_tag(self):
        result = tag_url("")
        assert result == "/tags/"


class TestHasTag:
    """Tests for has_tag filter."""

    def test_has_tag(self):
        page = MockPage(title="Test", tags=["python", "web"])
        assert has_tag(page, "python") is True

    def test_no_tag(self):
        page = MockPage(title="Test", tags=["python"])
        assert has_tag(page, "javascript") is False

    def test_case_insensitive(self):
        page = MockPage(title="Test", tags=["Python"])
        assert has_tag(page, "python") is True

    def test_no_tags(self):
        page = MockPage(title="Test", tags=[])
        assert has_tag(page, "python") is False
