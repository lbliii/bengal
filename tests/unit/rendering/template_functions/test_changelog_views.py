"""Tests for changelog view filters (ReleaseView, releases filter)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from bengal.rendering.template_functions.changelog import (
    ReleaseView,
    release_view_filter,
    releases_filter,
)


class TestReleaseViewFromData:
    """Tests for ReleaseView.from_data() (data-driven mode)."""

    def test_extracts_basic_properties(self) -> None:
        """Should extract version, name, date, status from data."""
        data = {
            "version": "1.2.0",
            "name": "Feature Release",
            "date": "2024-01-15",
            "status": "stable",
            "summary": "A major feature release.",
        }

        view = ReleaseView.from_data(data)

        assert view.version == "1.2.0"
        assert view.name == "Feature Release"
        assert view.date == "2024-01-15"
        assert view.status == "stable"
        assert view.summary == "A major feature release."

    def test_extracts_change_lists(self) -> None:
        """Should extract all change category lists."""
        data = {
            "version": "1.0.0",
            "added": ["Feature A", "Feature B"],
            "changed": ["Updated API"],
            "fixed": ["Bug fix 1", "Bug fix 2"],
            "deprecated": ["Old method"],
            "removed": ["Legacy code"],
            "security": ["CVE-2024-001"],
            "breaking": ["API change"],
        }

        view = ReleaseView.from_data(data)

        assert view.added == ("Feature A", "Feature B")
        assert view.changed == ("Updated API",)
        assert view.fixed == ("Bug fix 1", "Bug fix 2")
        assert view.deprecated == ("Old method",)
        assert view.removed == ("Legacy code",)
        assert view.security == ("CVE-2024-001",)
        assert view.breaking == ("API change",)

    def test_detects_structured_changes(self) -> None:
        """Should detect when release has structured changes."""
        data_with_changes = {"version": "1.0.0", "added": ["Feature"]}
        data_without_changes = {"version": "1.0.0"}

        view_with = ReleaseView.from_data(data_with_changes)
        view_without = ReleaseView.from_data(data_without_changes)

        assert view_with.has_structured_changes is True
        assert view_without.has_structured_changes is False

    def test_tracks_change_types_present(self) -> None:
        """Should track which change types are present."""
        data = {
            "version": "1.0.0",
            "added": ["Feature"],
            "fixed": ["Bug"],
            "breaking": ["API"],
        }

        view = ReleaseView.from_data(data)

        assert "added" in view.change_types
        assert "fixed" in view.change_types
        assert "breaking" in view.change_types
        assert "changed" not in view.change_types

    def test_extracts_url_as_href(self) -> None:
        """Should extract url field as href."""
        data = {"version": "1.0.0", "url": "https://github.com/repo/releases/v1.0.0"}

        view = ReleaseView.from_data(data)

        assert view.href == "https://github.com/repo/releases/v1.0.0"

    def test_handles_missing_fields(self) -> None:
        """Should handle missing fields gracefully."""
        data = {}

        view = ReleaseView.from_data(data)

        assert view.version == "Unknown"
        assert view.name == ""
        assert view.date is None
        assert view.status == ""
        assert view.summary == ""
        assert view.added == ()


class TestReleaseViewFromPage:
    """Tests for ReleaseView.from_page() (page-driven mode)."""

    def test_extracts_from_page_metadata(self) -> None:
        """Should extract release data from page metadata."""
        page = MagicMock()
        page.title = "v1.5.0"
        page.href = "/changelog/v1.5.0/"
        page.date = datetime(2024, 2, 1)
        page.metadata = {
            "name": "February Release",
            "status": "stable",
            "added": ["New feature"],
            "fixed": ["Bug fix"],
        }
        page.excerpt = "Release summary..."

        view = ReleaseView.from_page(page)

        assert view.version == "v1.5.0"
        assert view.name == "February Release"
        assert view.date == datetime(2024, 2, 1)
        assert view.href == "/changelog/v1.5.0/"
        assert view.added == ("New feature",)
        assert view.fixed == ("Bug fix",)

    def test_uses_description_or_excerpt_for_summary(self) -> None:
        """Should use description or excerpt for summary."""
        page = MagicMock()
        page.title = "v1.0.0"
        page.href = "/release/"
        page.date = None
        page.metadata = {"description": "Description text"}
        page.excerpt = "Excerpt text"

        view = ReleaseView.from_page(page)

        assert view.summary == "Description text"

    def test_falls_back_to_excerpt_for_summary(self) -> None:
        """Should fall back to excerpt if no description."""
        page = MagicMock()
        page.title = "v1.0.0"
        page.href = "/release/"
        page.date = None
        page.metadata = {}
        page.excerpt = "Excerpt text"

        view = ReleaseView.from_page(page)

        assert view.summary == "Excerpt text"

    def test_uses_metadata_version_over_title(self) -> None:
        """Should prefer metadata.version over title."""
        page = MagicMock()
        page.title = "Release Title"
        page.href = "/release/"
        page.date = None
        page.metadata = {"version": "2.0.0"}
        page.excerpt = ""

        view = ReleaseView.from_page(page)

        assert view.version == "2.0.0"

    def test_handles_missing_metadata(self) -> None:
        """Should handle page with no metadata."""
        page = MagicMock()
        page.title = "v1.0.0"
        page.href = "/release/"
        page.date = None
        page.metadata = None
        page.excerpt = None

        view = ReleaseView.from_page(page)

        assert view.version == "v1.0.0"
        assert view.added == ()


class TestReleasesFilter:
    """Tests for releases_filter()."""

    def test_converts_data_driven_releases(self) -> None:
        """Should convert list of dicts to ReleaseViews."""
        releases = [
            {"version": "1.0.0", "added": ["Feature"]},
            {"version": "0.9.0", "fixed": ["Bug"]},
        ]

        result = releases_filter(releases)

        assert len(result) == 2
        assert result[0].version == "1.0.0"
        assert result[1].version == "0.9.0"

    def test_converts_page_driven_releases(self) -> None:
        """Should convert list of pages to ReleaseViews."""
        page1 = MagicMock()
        page1.title = "v2.0.0"
        page1.href = "/v2/"
        page1.date = None
        page1.metadata = {}
        page1.excerpt = ""

        page2 = MagicMock()
        page2.title = "v1.0.0"
        page2.href = "/v1/"
        page2.date = None
        page2.metadata = {}
        page2.excerpt = ""

        result = releases_filter([page1, page2])

        assert len(result) == 2
        assert result[0].version == "v2.0.0"
        assert result[1].version == "v1.0.0"

    def test_returns_empty_for_none(self) -> None:
        """Should return empty list for None input."""
        result = releases_filter(None)
        assert result == []

    def test_returns_empty_for_empty_list(self) -> None:
        """Should return empty list for empty input."""
        result = releases_filter([])
        assert result == []


class TestReleaseViewFilter:
    """Tests for release_view_filter()."""

    def test_converts_single_dict(self) -> None:
        """Should convert single dict to ReleaseView."""
        data = {"version": "1.0.0", "added": ["Feature"]}

        result = release_view_filter(data)

        assert result is not None
        assert result.version == "1.0.0"

    def test_converts_single_page(self) -> None:
        """Should convert single page to ReleaseView."""
        page = MagicMock()
        page.title = "v1.0.0"
        page.href = "/release/"
        page.date = None
        page.metadata = {}
        page.excerpt = ""

        result = release_view_filter(page)

        assert result is not None
        assert result.version == "v1.0.0"

    def test_returns_none_for_none_input(self) -> None:
        """Should return None for None input."""
        result = release_view_filter(None)
        assert result is None
