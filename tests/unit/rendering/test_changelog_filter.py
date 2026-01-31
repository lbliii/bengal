"""
Tests for changelog view filters.

Tests the `releases` filter with smart version detection and sorting:
- Extracts version from filename, title, or metadata
- Sorts by version (semantic comparison: 0.1.10 > 0.1.9)
- Opt-out with releases(false) for custom ordering
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from bengal.rendering.template_functions.changelog import (
    ReleaseView,
    _extract_version,
    _normalize_date,
    _sort_releases,
    _version_sort_key,
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


class TestExtractVersion:
    """Tests for _extract_version helper."""

    def test_semver_direct(self):
        """Direct semver strings are recognized."""
        assert _extract_version("0.1.8") == "0.1.8"
        assert _extract_version("1.0.0") == "1.0.0"
        assert _extract_version("v1.2.3") == "1.2.3"

    def test_semver_with_suffix(self):
        """Semver with prerelease suffix."""
        assert _extract_version("1.0.0-beta") == "1.0.0-beta"
        assert _extract_version("2.0.0-rc.1") == "2.0.0-rc.1"

    def test_embedded_in_title(self):
        """Version extracted from title text."""
        assert _extract_version("Bengal 0.1.8") == "0.1.8"
        assert _extract_version("Release v1.2.3") == "1.2.3"
        assert _extract_version("Version 0.1.10 Released") == "0.1.10"

    def test_date_version(self):
        """Date-based versions are recognized."""
        assert _extract_version("26.01") == "26.01"
        assert _extract_version("2026.01.12") == "2026.01.12"

    def test_no_version(self):
        """Returns None when no version pattern found."""
        assert _extract_version("Some Random Title") is None
        assert _extract_version("Getting Started") is None


class TestVersionSortKey:
    """Tests for _version_sort_key helper."""

    def test_semver_numeric_comparison(self):
        """Semantic versions compare numerically, not lexically."""
        versions = ["0.1.9", "0.1.10", "0.1.2"]
        sorted_versions = sorted(versions, key=_version_sort_key, reverse=True)
        # 10 > 9 > 2 numerically
        assert sorted_versions == ["0.1.10", "0.1.9", "0.1.2"]

    def test_stable_before_prerelease(self):
        """Stable versions sort before prereleases."""
        versions = ["1.0.0-alpha", "1.0.0-beta", "1.0.0"]
        sorted_versions = sorted(versions, key=_version_sort_key, reverse=True)
        assert sorted_versions[0] == "1.0.0"  # Stable first


class TestSortReleases:
    """Tests for _sort_releases helper."""

    def test_sorts_by_version(self):
        """Releases are sorted by version (highest first)."""
        releases = [
            ReleaseView(
                "0.1.0",
                "",
                datetime(2025, 10, 13),
                "",
                "",
                "",
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                False,
                (),
            ),
            ReleaseView(
                "0.1.2",
                "",
                datetime(2026, 1, 12),
                "",
                "",
                "",
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                False,
                (),
            ),
            ReleaseView(
                "0.1.1",
                "",
                datetime(2025, 12, 1),
                "",
                "",
                "",
                (),
                (),
                (),
                (),
                (),
                (),
                (),
                False,
                (),
            ),
        ]
        sorted_releases = _sort_releases(releases)
        assert [r.version for r in sorted_releases] == ["0.1.2", "0.1.1", "0.1.0"]

    def test_semantic_version_order(self):
        """Versions 0.1.10 > 0.1.9 (numeric, not string comparison)."""
        releases = [
            ReleaseView("0.1.9", "", None, "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.10", "", None, "", "", "", (), (), (), (), (), (), (), False, ()),
            ReleaseView("0.1.2", "", None, "", "", "", (), (), (), (), (), (), (), False, ()),
        ]
        sorted_releases = _sort_releases(releases)
        assert [r.version for r in sorted_releases] == ["0.1.10", "0.1.9", "0.1.2"]


class MockPage:
    """Mock page object for testing page-driven mode."""

    def __init__(
        self, title: str, date_val: datetime | None = None, source_path: str | None = None
    ):
        self.title = title
        self.date = date_val
        self.metadata = {}
        self.href = f"/releases/{title.lower().replace(' ', '-')}/"
        # If source_path not provided, derive from title
        if source_path:
            self.source_path = Path(source_path)
        else:
            # Extract version from title for filename
            version = _extract_version(title) or title.lower().replace(" ", "-")
            self.source_path = Path(f"content/releases/{version}.md")


class TestReleasesFilter:
    """Tests for the main releases_filter function."""

    def test_default_sorts_by_version(self):
        """By default, releases are sorted by version (highest first)."""
        data = [
            {"version": "0.1.0"},
            {"version": "0.1.2"},
            {"version": "0.1.1"},
        ]
        releases = releases_filter(data)
        assert [r.version for r in releases] == ["0.1.2", "0.1.1", "0.1.0"]

    def test_semantic_version_sorting(self):
        """Semantic version comparison: 0.1.10 > 0.1.9."""
        data = [
            {"version": "0.1.9"},
            {"version": "0.1.10"},
            {"version": "0.1.2"},
        ]
        releases = releases_filter(data)
        assert [r.version for r in releases] == ["0.1.10", "0.1.9", "0.1.2"]

    def test_version_extracted_from_filename(self):
        """Version extracted from filename when not in metadata."""
        pages = [
            MockPage("Bengal 0.1.0", source_path="content/releases/0.1.0.md"),
            MockPage("Bengal 0.1.10", source_path="content/releases/0.1.10.md"),
            MockPage("Bengal 0.1.9", source_path="content/releases/0.1.9.md"),
        ]
        releases = releases_filter(pages)
        # Versions extracted from filenames, sorted semantically
        assert [r.version for r in releases] == ["0.1.10", "0.1.9", "0.1.0"]

    def test_sorted_false_preserves_order(self):
        """sorted=False preserves input order for custom sorting."""
        data = [
            {"version": "0.1.0"},
            {"version": "0.1.2"},
        ]
        releases = releases_filter(data, sorted=False)
        # Input order preserved
        assert [r.version for r in releases] == ["0.1.0", "0.1.2"]

    def test_empty_source(self):
        """Empty source returns empty list."""
        assert releases_filter([]) == []
        assert releases_filter(None) == []


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

    def test_version_from_metadata(self):
        """Explicit version in metadata takes priority."""
        page = MockPage("Bengal Release", source_path="content/releases/0.1.8.md")
        page.metadata = {"version": "custom-1.0"}
        view = ReleaseView.from_page(page)
        assert view.version == "custom-1.0"

    def test_version_from_filename(self):
        """Version extracted from filename when not in metadata."""
        page = MockPage("Bengal 0.1.8", source_path="content/releases/0.1.8.md")
        view = ReleaseView.from_page(page)
        assert view.version == "0.1.8"

    def test_version_from_title(self):
        """Version extracted from title when filename not versioned."""
        page = MockPage("Bengal 0.1.8", source_path="content/releases/latest.md")
        view = ReleaseView.from_page(page)
        assert view.version == "0.1.8"

    def test_version_priority_order(self):
        """Test version extraction priority: metadata > filename > title."""
        # Metadata wins even if filename has different version
        page = MockPage("Bengal 0.1.0", source_path="content/releases/0.1.5.md")
        page.metadata = {"version": "1.0.0"}
        view = ReleaseView.from_page(page)
        assert view.version == "1.0.0"

    def test_date_extraction(self):
        """Date is extracted from page."""
        page = MockPage("Bengal 1.0.0", datetime(2025, 10, 13))
        page.metadata = {"description": "Initial release"}
        view = ReleaseView.from_page(page)
        assert view.date == datetime(2025, 10, 13)
        assert view.summary == "Initial release"

    def test_none_date_handled(self):
        """None date is handled gracefully."""
        page = MockPage("Draft", None)
        view = ReleaseView.from_page(page)
        assert view.date is None

    def test_index_page_skipped_for_version(self):
        """_index.md filename is not used as version."""
        page = MockPage("Releases", source_path="content/releases/_index.md")
        view = ReleaseView.from_page(page)
        # Should use title since _index is not a version
        assert view.version == "Releases"
