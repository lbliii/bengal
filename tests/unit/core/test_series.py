"""Tests for bengal.core.series module."""

from __future__ import annotations

from bengal.core.series import Series


class TestSeriesBasic:
    """Test basic Series functionality."""

    def test_series_from_string(self):
        """Series can be created from a simple string."""
        series = Series.from_frontmatter("My Tutorial Series")
        assert series is not None
        assert series.name == "My Tutorial Series"
        assert series.part == 1
        assert series.total == 0
        assert series.slug == "my-tutorial-series"

    def test_series_from_dict(self):
        """Series can be created from a dict with full details."""
        data = {
            "name": "Building a Blog",
            "part": 2,
            "total": 5,
            "description": "A comprehensive guide",
        }
        series = Series.from_frontmatter(data)
        assert series is not None
        assert series.name == "Building a Blog"
        assert series.part == 2
        assert series.total == 5
        assert series.description == "A comprehensive guide"
        assert series.slug == "building-a-blog"

    def test_series_custom_slug(self):
        """Series can have a custom slug."""
        series = Series.from_frontmatter(
            {
                "name": "My Series",
                "slug": "custom-slug",
            }
        )
        assert series.slug == "custom-slug"

    def test_series_is_first(self):
        """Series.is_first detects first part."""
        series = Series(name="Test", part=1, total=5)
        assert series.is_first
        series2 = Series(name="Test", part=2, total=5)
        assert not series2.is_first

    def test_series_is_last(self):
        """Series.is_last detects last part."""
        series = Series(name="Test", part=5, total=5)
        assert series.is_last
        series2 = Series(name="Test", part=3, total=5)
        assert not series2.is_last
        # Unknown total - not last
        series3 = Series(name="Test", part=10, total=0)
        assert not series3.is_last

    def test_series_has_prev_next(self):
        """Series.has_prev and has_next work correctly."""
        first = Series(name="Test", part=1, total=3)
        assert not first.has_prev
        assert first.has_next

        middle = Series(name="Test", part=2, total=3)
        assert middle.has_prev
        assert middle.has_next

        last = Series(name="Test", part=3, total=3)
        assert last.has_prev
        assert not last.has_next

    def test_series_progress_percent(self):
        """Series calculates progress percentage."""
        series = Series(name="Test", part=2, total=4)
        assert series.progress_percent == 50

        series2 = Series(name="Test", part=1, total=5)
        assert series2.progress_percent == 20

        # Unknown total
        series3 = Series(name="Test", part=3, total=0)
        assert series3.progress_percent == 0

    def test_series_truthiness(self):
        """Series is truthy when name is set."""
        assert bool(Series(name="Test"))
        assert not bool(Series(name=""))

    def test_series_str(self):
        """Series string representation is the name."""
        series = Series(name="My Series")
        assert str(series) == "My Series"

    def test_series_to_dict(self):
        """Series can be serialized to dict."""
        series = Series(name="Test", part=2, total=5)
        d = series.to_dict()
        assert d["name"] == "Test"
        assert d["part"] == 2
        assert d["total"] == 5
        assert d["is_first"] is False
        assert d["is_last"] is False
        assert d["progress_percent"] == 40

    def test_series_hashable(self):
        """Series is hashable (frozen dataclass)."""
        series1 = Series(name="Test", part=1)
        series2 = Series(name="Test", part=1)
        assert hash(series1) == hash(series2)


class TestSeriesEdgeCases:
    """Test edge cases for Series parsing."""

    def test_series_empty_dict(self):
        """Empty dict returns None."""
        series = Series.from_frontmatter({})
        assert series is None

    def test_series_missing_name(self):
        """Dict without name returns None."""
        series = Series.from_frontmatter({"part": 2})
        assert series is None

    def test_series_alternative_name_keys(self):
        """Series accepts alternative name keys."""
        series = Series.from_frontmatter({"title": "My Series"})
        assert series is not None
        assert series.name == "My Series"

        series2 = Series.from_frontmatter({"series_name": "Another Series"})
        assert series2 is not None
        assert series2.name == "Another Series"

    def test_series_non_dict_non_string(self):
        """Non-dict/string value returns None."""
        series = Series.from_frontmatter(123)
        assert series is None


