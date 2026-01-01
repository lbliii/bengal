"""Tests for taxonomy view filters (TagView, tag_views filter)."""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.rendering.template_functions.taxonomies import (
    TagView,
    tag_views_filter,
)


class TestTagViewFromTaxonomyEntry:
    """Tests for TagView.from_taxonomy_entry()."""

    def test_extracts_basic_properties(self) -> None:
        """Should extract name, slug, href from taxonomy entry."""
        tag_data = {
            "name": "Python",
            "pages": ["page1", "page2", "page3"],
        }

        view = TagView.from_taxonomy_entry("python", tag_data, total_posts=10)

        assert view.name == "Python"
        assert view.slug == "python"
        assert view.href == "/tags/python/"
        assert view.count == 3

    def test_calculates_percentage(self) -> None:
        """Should calculate percentage of total posts."""
        tag_data = {"name": "Test", "pages": ["p1", "p2"]}

        view = TagView.from_taxonomy_entry("test", tag_data, total_posts=10)

        assert view.percentage == 20.0

    def test_handles_zero_total_posts(self) -> None:
        """Should handle zero total posts without division error."""
        tag_data = {"name": "Test", "pages": []}

        view = TagView.from_taxonomy_entry("test", tag_data, total_posts=0)

        assert view.percentage == 0.0

    def test_uses_slug_as_name_fallback(self) -> None:
        """Should use slug as name if name not provided."""
        tag_data = {"pages": ["p1"]}

        view = TagView.from_taxonomy_entry("my-tag", tag_data, total_posts=1)

        assert view.name == "my-tag"

    def test_extracts_description(self) -> None:
        """Should extract description if available."""
        tag_data = {
            "name": "Python",
            "description": "Posts about Python programming.",
            "pages": [],
        }

        view = TagView.from_taxonomy_entry("python", tag_data, total_posts=0)

        assert view.description == "Posts about Python programming."

    def test_handles_missing_pages(self) -> None:
        """Should handle missing pages list."""
        tag_data = {"name": "Empty"}

        view = TagView.from_taxonomy_entry("empty", tag_data, total_posts=0)

        assert view.count == 0


class TestTagViewsFilter:
    """Tests for tag_views_filter()."""

    def test_extracts_from_site_object(self) -> None:
        """Should extract tags from site.taxonomies."""
        site = MagicMock()
        site.taxonomies = {
            "tags": {
                "python": {"name": "Python", "pages": ["p1", "p2"]},
                "testing": {"name": "Testing", "pages": ["p1"]},
            }
        }
        site.pages = ["p1", "p2", "p3"]

        result = tag_views_filter(site)

        assert len(result) == 2
        # Default sort is by count (descending)
        assert result[0].name == "Python"
        assert result[0].count == 2
        assert result[1].name == "Testing"
        assert result[1].count == 1

    def test_extracts_from_dict(self) -> None:
        """Should extract tags from dict directly."""
        tags_dict = {
            "tags": {
                "python": {"name": "Python", "pages": ["p1"]},
            }
        }

        result = tag_views_filter(tags_dict)

        assert len(result) == 1
        assert result[0].name == "Python"

    def test_sorts_by_count_default(self) -> None:
        """Should sort by count descending by default."""
        site = MagicMock()
        site.taxonomies = {
            "tags": {
                "a": {"name": "A", "pages": ["p1"]},
                "b": {"name": "B", "pages": ["p1", "p2", "p3"]},
                "c": {"name": "C", "pages": ["p1", "p2"]},
            }
        }
        site.pages = []

        result = tag_views_filter(site)

        assert result[0].name == "B"  # 3 posts
        assert result[1].name == "C"  # 2 posts
        assert result[2].name == "A"  # 1 post

    def test_sorts_by_name(self) -> None:
        """Should sort by name when specified."""
        site = MagicMock()
        site.taxonomies = {
            "tags": {
                "zebra": {"name": "Zebra", "pages": ["p1"]},
                "apple": {"name": "Apple", "pages": ["p1", "p2"]},
            }
        }
        site.pages = []

        result = tag_views_filter(site, sort_by="name")

        assert result[0].name == "Apple"
        assert result[1].name == "Zebra"

    def test_sorts_by_percentage(self) -> None:
        """Should sort by percentage when specified."""
        site = MagicMock()
        site.taxonomies = {
            "tags": {
                "a": {"name": "A", "pages": ["p1"]},
                "b": {"name": "B", "pages": ["p1", "p2"]},
            }
        }
        site.pages = ["p1", "p2"]

        result = tag_views_filter(site, sort_by="percentage")

        assert result[0].name == "B"  # Higher percentage
        assert result[1].name == "A"

    def test_respects_limit(self) -> None:
        """Should respect limit parameter."""
        site = MagicMock()
        site.taxonomies = {
            "tags": {
                "a": {"name": "A", "pages": ["p1"]},
                "b": {"name": "B", "pages": ["p1"]},
                "c": {"name": "C", "pages": ["p1"]},
            }
        }
        site.pages = []

        result = tag_views_filter(site, limit=2)

        assert len(result) == 2

    def test_returns_empty_for_invalid_source(self) -> None:
        """Should return empty list for invalid source."""
        result = tag_views_filter(None)
        assert result == []

        result = tag_views_filter("not a dict")
        assert result == []

    def test_returns_empty_for_empty_taxonomies(self) -> None:
        """Should return empty list for empty taxonomies."""
        site = MagicMock()
        site.taxonomies = {"tags": {}}
        site.pages = []

        result = tag_views_filter(site)
        assert result == []
