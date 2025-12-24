"""Tests for collection filters in bengal.rendering.template_functions.collections module."""

from __future__ import annotations

from datetime import datetime

from bengal.rendering.template_functions.collections import (
    archive_years,
    group_by_month,
    group_by_year,
)


class MockPage:
    """Mock page for testing."""

    def __init__(self, title: str, date: datetime | None = None):
        self.title = title
        self.date = date


class TestGroupByYear:
    """Test group_by_year filter."""

    def test_group_by_year_basic(self):
        """group_by_year groups pages by year."""
        pages = [
            MockPage("Post 1", datetime(2024, 1, 15)),
            MockPage("Post 2", datetime(2024, 6, 20)),
            MockPage("Post 3", datetime(2023, 3, 10)),
        ]
        result = group_by_year(pages)

        assert 2024 in result
        assert 2023 in result
        assert len(result[2024]) == 2
        assert len(result[2023]) == 1

    def test_group_by_year_descending(self):
        """group_by_year returns years in descending order."""
        pages = [
            MockPage("Old", datetime(2020, 1, 1)),
            MockPage("New", datetime(2025, 1, 1)),
            MockPage("Mid", datetime(2022, 1, 1)),
        ]
        result = group_by_year(pages)
        years = list(result.keys())

        assert years == [2025, 2022, 2020]

    def test_group_by_year_empty(self):
        """group_by_year returns empty dict for empty list."""
        result = group_by_year([])
        assert result == {}

    def test_group_by_year_no_date(self):
        """group_by_year skips pages without date."""
        pages = [
            MockPage("Has Date", datetime(2024, 1, 15)),
            MockPage("No Date", None),
        ]
        result = group_by_year(pages)

        assert len(result) == 1
        assert 2024 in result
        assert len(result[2024]) == 1

    def test_group_by_year_custom_attr(self):
        """group_by_year uses custom date attribute."""

        class CustomPage:
            def __init__(self, published: datetime):
                self.published = published

        pages = [
            CustomPage(datetime(2024, 1, 1)),
            CustomPage(datetime(2023, 1, 1)),
        ]
        result = group_by_year(pages, date_attr="published")

        assert 2024 in result
        assert 2023 in result


class TestGroupByMonth:
    """Test group_by_month filter."""

    def test_group_by_month_basic(self):
        """group_by_month groups pages by year-month."""
        pages = [
            MockPage("Jan Post", datetime(2024, 1, 15)),
            MockPage("Jan Post 2", datetime(2024, 1, 20)),
            MockPage("Feb Post", datetime(2024, 2, 10)),
        ]
        result = group_by_month(pages)

        assert (2024, 1) in result
        assert (2024, 2) in result
        assert len(result[(2024, 1)]) == 2
        assert len(result[(2024, 2)]) == 1

    def test_group_by_month_descending(self):
        """group_by_month returns months in descending order."""
        pages = [
            MockPage("Old", datetime(2024, 1, 1)),
            MockPage("New", datetime(2024, 12, 1)),
            MockPage("Mid", datetime(2024, 6, 1)),
        ]
        result = group_by_month(pages)
        months = list(result.keys())

        assert months == [(2024, 12), (2024, 6), (2024, 1)]

    def test_group_by_month_empty(self):
        """group_by_month returns empty dict for empty list."""
        result = group_by_month([])
        assert result == {}


class TestArchiveYears:
    """Test archive_years filter."""

    def test_archive_years_basic(self):
        """archive_years returns year counts."""
        pages = [
            MockPage("Post 1", datetime(2024, 1, 15)),
            MockPage("Post 2", datetime(2024, 6, 20)),
            MockPage("Post 3", datetime(2023, 3, 10)),
        ]
        result = archive_years(pages)

        assert len(result) == 2
        assert result[0]["year"] == 2024
        assert result[0]["count"] == 2
        assert result[1]["year"] == 2023
        assert result[1]["count"] == 1

    def test_archive_years_descending(self):
        """archive_years returns years in descending order."""
        pages = [
            MockPage("Old", datetime(2020, 1, 1)),
            MockPage("New", datetime(2025, 1, 1)),
        ]
        result = archive_years(pages)

        assert result[0]["year"] == 2025
        assert result[1]["year"] == 2020

    def test_archive_years_empty(self):
        """archive_years returns empty list for empty input."""
        result = archive_years([])
        assert result == []

    def test_archive_years_no_date(self):
        """archive_years skips pages without date."""
        pages = [
            MockPage("Has Date", datetime(2024, 1, 15)),
            MockPage("No Date", None),
        ]
        result = archive_years(pages)

        assert len(result) == 1
        assert result[0]["year"] == 2024
        assert result[0]["count"] == 1
