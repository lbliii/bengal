"""
Tests for changelog view filters.

Tests the `releases` filter with simple, predictable defaults:
- Always sorts newest-first by default (what users expect)
- Opt-out with releases(false) for custom ordering
"""

from datetime import date, datetime

import pytest

from bengal.rendering.template_functions.changelog import (
    ReleaseView,
    _normalize_date,
    _sort_releases,
    releases_filter,
)


class TestNormalizeDate:
    """Tests for _normalize_date helper."""

    def test_datetime_passthrough(self):
        """datetime objects are returned as-is."""
        dt = datetime(2026, 1, 12, 15, 30)
        assert _normalize_date(dt) == dt

    def test_date_to_datetime(self):
        """date objects are converted to datetime at midnight."""
        d = date(2026, 1, 12)
        result = _normalize_date(d)
        assert result == datetime(2026, 1, 12, 0, 0, 0)

    def test_iso_string(self):
        """ISO format strings are parsed."""
        assert _normalize_date("2026-01-12") == datetime(2026, 1, 12)

    def test_none(self):
        """None is returned as None."""
        assert _normalize_date(None) is None

    def test_invalid_string(self):
        """Invalid strings return None."""
        assert _normalize_date("not-a-date") is None


class TestSortReleases:
    """Tests for _sort_releases helper."""

    def test_sorts_newest_first(self):
        """Releases are sorted by date, newest first."""
        releases = [
            ReleaseView("0.1.0", "", datetime(2025, 10, 13), "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.2", "", datetime(2026, 1, 12), "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.1", "", datetime(2025, 12, 1), "", "", "", (), (), (), (), (), (), (), False, ()),
        ]
        sorted_releases = _sort_releases(releases)
        assert [r.version for r in sorted_releases] == ["0.1.2", "0.1.1", "0.1.0"]

    def test_same_day_sorted_by_version(self):
        """Same-day releases are sorted by version descending."""
        releases = [
            ReleaseView("0.1.0", "", datetime(2025, 10, 13), "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.2", "", datetime(2025, 10, 13), "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.1", "", datetime(2025, 10, 13), "", "", "", (), (), (), (), (), (), (), False, ()),
        ]
        sorted_releases = _sort_releases(releases)
        # Same day, sorted by version descending
        assert [r.version for r in sorted_releases] == ["0.1.2", "0.1.1", "0.1.0"]

    def test_none_dates_at_end(self):
        """Releases with None dates are placed at the end."""
        releases = [
            ReleaseView("0.1.0", "", datetime(2025, 10, 13), "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("draft", "", None, "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.1", "", datetime(2026, 1, 12), "", "", "", (), (), (), (), (), (), (), False, ()),
        ]
        sorted_releases = _sort_releases(releases)
        assert [r.version for r in sorted_releases] == ["0.1.1", "0.1.0", "draft"]


class MockPage:
    """Mock page object for testing page-driven mode."""

    def __init__(self, title: str, date_val: datetime | None):
        self.title = title
        self.date = date_val
        self.metadata = {}
        self.href = f"/releases/{title.lower().replace(' ', '-')}/"


class TestReleasesFilter:
    """Tests for the main releases_filter function."""

    def test_default_sorts_newest_first(self):
        """By default, releases are sorted newest first."""
        data = [
            {"version": "0.1.0", "date": "2025-10-13"},
            {"version": "0.1.2", "date": "2026-01-12"},
            {"version": "0.1.1", "date": "2025-12-01"},
        ]
        releases = releases_filter(data)
        assert [r.version for r in releases] == ["0.1.2", "0.1.1", "0.1.0"]

    def test_pages_also_sorted_by_default(self):
        """Pages are also sorted by default (predictable behavior)."""
        # Input in wrong order (oldest first)
        pages = [
            MockPage("Bengal 0.1.0", datetime(2025, 10, 13)),
            MockPage("Bengal 0.1.1", datetime(2025, 12, 1)),
            MockPage("Bengal 0.1.2", datetime(2026, 1, 12)),
        ]
        releases = releases_filter(pages)
        # Should be sorted newest first
        assert [r.version for r in releases] == [
            "Bengal 0.1.2",
            "Bengal 0.1.1",
            "Bengal 0.1.0",
        ]

    def test_sorted_false_preserves_order(self):
        """sorted=False preserves input order for custom sorting."""
        data = [
            {"version": "0.1.0", "date": "2025-10-13"},
            {"version": "0.1.2", "date": "2026-01-12"},
        ]
        releases = releases_filter(data, sorted=False)
        # Input order preserved
        assert [r.version for r in releases] == ["0.1.0", "0.1.2"]

    def test_sorted_false_pages(self):
        """sorted=False works with pages too."""
        pages = [
            MockPage("Bengal 0.1.0", datetime(2025, 10, 13)),
            MockPage("Bengal 0.1.2", datetime(2026, 1, 12)),
        ]
        releases = releases_filter(pages, sorted=False)
        # Input order preserved
        assert [r.version for r in releases] == ["Bengal 0.1.0", "Bengal 0.1.2"]

    def test_empty_source(self):
        """Empty source returns empty list."""
        assert releases_filter([]) == []
        assert releases_filter(None) == []

    def test_none_dates_at_end(self):
        """Releases with None dates are placed at the end."""
        data = [
            {"version": "0.1.0", "date": "2025-10-13"},
            {"version": "draft", "date": None},
            {"version": "0.1.1", "date": "2026-01-12"},
        ]
        releases = releases_filter(data)
        # Dated items sorted newest first, None at end
        assert [r.version for r in releases] == ["0.1.1", "0.1.0", "draft"]


class TestReleaseViewFromData:
    """Tests for ReleaseView.from_data()."""

    def test_basic_fields(self):
        """Basic fields are extracted correctly."""
        data = {
            "version": "1.0.0",
            "name": "Initial Release",
            "date": "2025-10-13",
            "status": "stable",
            "summary": "First release",
        }
        view = ReleaseView.from_data(data)
        assert view.version == "1.0.0"
        assert view.name == "Initial Release"
        assert view.date == datetime(2025, 10, 13)
        assert view.status == "stable"
        assert view.summary == "First release"

    def test_change_lists(self):
        """Change lists are extracted as tuples."""
        data = {
            "version": "1.1.0",
            "added": ["Feature A", "Feature B"],
            "fixed": ["Bug X"],
        }
        view = ReleaseView.from_data(data)
        assert view.added == ("Feature A", "Feature B")
        assert view.fixed == ("Bug X",)
        assert view.changed == ()
        assert view.has_structured_changes is True
        assert "added" in view.change_types
        assert "fixed" in view.change_types


class TestReleaseViewFromPage:
    """Tests for ReleaseView.from_page()."""

    def test_extracts_from_page(self):
        """Page attributes are extracted correctly."""
        page = MockPage("Bengal 1.0.0", datetime(2025, 10, 13))
        page.metadata = {"description": "Initial release"}
        view = ReleaseView.from_page(page)
        assert view.version == "Bengal 1.0.0"
        assert view.date == datetime(2025, 10, 13)
        assert view.summary == "Initial release"

    def test_none_date_handled(self):
        """None date is handled gracefully."""
        page = MockPage("Draft", None)
        view = ReleaseView.from_page(page)
        assert view.date is None
