"""
Tests for computed free functions in bengal.core.page.computed.

These test the pure functions directly (not through Page property wrappers),
verifying correctness of age calculations, author parsing, series parsing,
and series navigation.

Completes Track 4b of the free-threading migration epic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from bengal.core.page.computed import (
    compute_age_days,
    compute_age_months,
    compute_excerpt,
    compute_meta_description,
    compute_reading_time,
    compute_word_count,
    get_all_authors,
    get_primary_author,
    get_series_info,
    get_series_neighbor,
)


# -----------------------------------------------------------------------
# compute_word_count
# -----------------------------------------------------------------------


class TestComputeWordCount:
    """Direct tests for compute_word_count free function."""

    def test_basic_counting(self):
        assert compute_word_count("one two three") == 3

    def test_empty_string(self):
        assert compute_word_count("") == 0

    def test_whitespace_only(self):
        assert compute_word_count("   \n\t  ") == 0

    def test_markdown_tokens_counted(self):
        assert compute_word_count("# Hello **world**") == 3


# -----------------------------------------------------------------------
# compute_meta_description
# -----------------------------------------------------------------------


class TestComputeMetaDescription:
    """Direct tests for compute_meta_description free function."""

    def test_explicit_description_preferred(self):
        result = compute_meta_description(
            {"description": "Explicit desc"},
            "Some long content",
        )
        assert result == "Explicit desc"

    def test_generated_from_content(self):
        result = compute_meta_description({}, "Short content here.")
        assert result == "Short content here."

    def test_empty_content_no_description(self):
        assert compute_meta_description({}, "") == ""

    def test_max_160_chars(self):
        long = "This is a sentence. " * 30
        result = compute_meta_description({}, long)
        assert len(result) <= 160


# -----------------------------------------------------------------------
# compute_reading_time
# -----------------------------------------------------------------------


class TestComputeReadingTime:
    """Direct tests for compute_reading_time free function."""

    def test_200_wpm(self):
        assert compute_reading_time(400) == 2

    def test_minimum_one(self):
        assert compute_reading_time(0) == 1
        assert compute_reading_time(10) == 1

    def test_rounds(self):
        assert compute_reading_time(250) == 1   # 1.25 -> 1
        assert compute_reading_time(350) == 2   # 1.75 -> 2


# -----------------------------------------------------------------------
# compute_excerpt
# -----------------------------------------------------------------------


class TestComputeExcerpt:
    """Direct tests for compute_excerpt free function."""

    def test_short_content_unchanged(self):
        assert compute_excerpt("Hello world.") == "Hello world."

    def test_empty_string(self):
        assert compute_excerpt("") == ""

    def test_truncates_long(self):
        long = "word " * 100
        result = compute_excerpt(long)
        assert len(result) <= 203  # 200 + "..."

    def test_strips_html(self):
        assert compute_excerpt("<p>Hello <b>world</b></p>") == "Hello world"


# -----------------------------------------------------------------------
# compute_age_days
# -----------------------------------------------------------------------


class TestComputeAgeDays:
    """Tests for compute_age_days free function."""

    def test_none_date_returns_zero(self):
        assert compute_age_days(None) == 0

    def test_today_returns_zero(self):
        now = datetime.now(UTC)
        assert compute_age_days(now) == 0

    def test_past_date_positive(self):
        past = datetime.now(UTC) - timedelta(days=10)
        assert compute_age_days(past) == 10

    def test_one_day_ago(self):
        yesterday = datetime.now(UTC) - timedelta(days=1)
        assert compute_age_days(yesterday) == 1

    def test_large_age(self):
        old = datetime.now(UTC) - timedelta(days=365)
        assert compute_age_days(old) == 365

    def test_naive_datetime(self):
        """Naive datetimes use datetime.now() (no tz)."""
        past = datetime.now() - timedelta(days=5)
        assert compute_age_days(past) == 5

    def test_timezone_aware_date(self):
        """Timezone-aware datetimes use datetime.now(UTC)."""
        past = datetime.now(UTC) - timedelta(days=7)
        assert compute_age_days(past) == 7

    def test_non_utc_timezone(self):
        """Non-UTC timezone-aware dates still work correctly."""
        est = timezone(timedelta(hours=-5))
        past = datetime.now(est) - timedelta(days=3)
        result = compute_age_days(past)
        assert result in (2, 3, 4)  # Allow for timezone edge cases

    def test_never_negative(self):
        """Future dates clamp to 0."""
        future = datetime.now(UTC) + timedelta(days=10)
        assert compute_age_days(future) == 0


# -----------------------------------------------------------------------
# compute_age_months
# -----------------------------------------------------------------------


class TestComputeAgeMonths:
    """Tests for compute_age_months free function."""

    def test_none_date_returns_zero(self):
        assert compute_age_months(None) == 0

    def test_same_month_returns_zero(self):
        # First of the current month to avoid edge cases
        now = datetime.now(UTC)
        same_month = now.replace(day=1)
        assert compute_age_months(same_month) == 0

    def test_one_month_ago(self):
        now = datetime.now(UTC)
        # Go back one month manually
        if now.month == 1:
            one_month_ago = now.replace(year=now.year - 1, month=12, day=1)
        else:
            one_month_ago = now.replace(month=now.month - 1, day=1)
        assert compute_age_months(one_month_ago) == 1

    def test_twelve_months_one_year(self):
        now = datetime.now(UTC)
        one_year_ago = now.replace(year=now.year - 1, day=1)
        assert compute_age_months(one_year_ago) == 12

    def test_multiple_years(self):
        now = datetime.now(UTC)
        two_years_ago = now.replace(year=now.year - 2, day=1)
        assert compute_age_months(two_years_ago) == 24

    def test_naive_datetime(self):
        now = datetime.now()
        if now.month == 1:
            past = now.replace(year=now.year - 1, month=12, day=1)
        else:
            past = now.replace(month=now.month - 1, day=1)
        assert compute_age_months(past) == 1

    def test_never_negative(self):
        """Future dates clamp to 0."""
        now = datetime.now(UTC)
        future = now.replace(year=now.year + 1)
        assert compute_age_months(future) == 0

    def test_uses_calendar_months_not_days(self):
        """Jan 31 to Mar 1 should be 2 months, not based on 30-day periods."""
        now = datetime.now(UTC)
        # Create a date exactly 3 calendar months back
        month = now.month - 3
        year = now.year
        if month < 1:
            month += 12
            year -= 1
        past = datetime(year, month, 1, tzinfo=UTC)
        assert compute_age_months(past) == 3


# -----------------------------------------------------------------------
# get_primary_author
# -----------------------------------------------------------------------


class TestGetPrimaryAuthor:
    """Tests for get_primary_author free function."""

    def test_no_author_returns_none(self):
        assert get_primary_author({}) is None

    def test_string_author(self):
        author = get_primary_author({"author": "Jane Smith"})
        assert author is not None
        assert author.name == "Jane Smith"

    def test_dict_author(self):
        author = get_primary_author({
            "author": {
                "name": "Jane Smith",
                "email": "jane@example.com",
            },
        })
        assert author is not None
        assert author.name == "Jane Smith"
        assert author.email == "jane@example.com"

    def test_dict_author_with_social(self):
        author = get_primary_author({
            "author": {
                "name": "Jane Smith",
                "social": {"twitter": "janesmith", "github": "janedev"},
            },
        })
        assert author is not None
        assert author.social == {"github": "janedev", "twitter": "janesmith"}

    def test_fallback_to_authors_list(self):
        """When 'author' key missing, falls back to first in 'authors' list."""
        author = get_primary_author({
            "authors": [
                {"name": "First Author"},
                {"name": "Second Author"},
            ],
        })
        assert author is not None
        assert author.name == "First Author"

    def test_author_preferred_over_authors(self):
        """'author' key takes priority over 'authors' list."""
        author = get_primary_author({
            "author": "Primary Author",
            "authors": [{"name": "List Author"}],
        })
        assert author is not None
        assert author.name == "Primary Author"

    def test_empty_authors_list(self):
        assert get_primary_author({"authors": []}) is None

    def test_authors_not_a_list(self):
        """Non-list 'authors' value is ignored."""
        assert get_primary_author({"authors": "not a list"}) is None


# -----------------------------------------------------------------------
# get_all_authors
# -----------------------------------------------------------------------


class TestGetAllAuthors:
    """Tests for get_all_authors free function."""

    def test_no_authors_returns_empty(self):
        assert get_all_authors({}) == []

    def test_single_author_string(self):
        authors = get_all_authors({"author": "Jane Smith"})
        assert len(authors) == 1
        assert authors[0].name == "Jane Smith"

    def test_single_author_dict(self):
        authors = get_all_authors({
            "author": {"name": "Jane Smith", "email": "jane@example.com"},
        })
        assert len(authors) == 1
        assert authors[0].name == "Jane Smith"

    def test_authors_list_only(self):
        authors = get_all_authors({
            "authors": [
                {"name": "Alice"},
                {"name": "Bob"},
            ],
        })
        assert len(authors) == 2
        assert authors[0].name == "Alice"
        assert authors[1].name == "Bob"

    def test_combined_author_and_authors(self):
        """Both 'author' and 'authors' are combined."""
        authors = get_all_authors({
            "author": "Primary",
            "authors": [{"name": "Secondary"}],
        })
        assert len(authors) == 2
        assert authors[0].name == "Primary"
        assert authors[1].name == "Secondary"

    def test_deduplication_by_name(self):
        """Duplicate names are removed."""
        authors = get_all_authors({
            "author": "Jane Smith",
            "authors": [
                {"name": "Jane Smith", "email": "jane@example.com"},
                {"name": "Bob Jones"},
            ],
        })
        assert len(authors) == 2
        names = [a.name for a in authors]
        assert names == ["Jane Smith", "Bob Jones"]

    def test_empty_authors_list(self):
        assert get_all_authors({"authors": []}) == []

    def test_authors_not_a_list_ignored(self):
        """Non-list 'authors' is ignored, only 'author' is processed."""
        authors = get_all_authors({
            "author": "Jane",
            "authors": "not a list",
        })
        assert len(authors) == 1
        assert authors[0].name == "Jane"


# -----------------------------------------------------------------------
# get_series_info
# -----------------------------------------------------------------------


class TestGetSeriesInfo:
    """Tests for get_series_info free function."""

    def test_no_series_returns_none(self):
        assert get_series_info({}) is None

    def test_string_series(self):
        series = get_series_info({"series": "My Tutorial"})
        assert series is not None
        assert series.name == "My Tutorial"
        assert series.part == 1

    def test_dict_series(self):
        series = get_series_info({
            "series": {"name": "My Tutorial", "part": 3, "total": 5},
        })
        assert series is not None
        assert series.name == "My Tutorial"
        assert series.part == 3
        assert series.total == 5

    def test_dict_series_with_description(self):
        series = get_series_info({
            "series": {
                "name": "Advanced Bengal",
                "part": 1,
                "total": 3,
                "description": "Deep dive into Bengal internals",
            },
        })
        assert series is not None
        assert series.description == "Deep dive into Bengal internals"

    def test_dict_series_no_name_returns_none(self):
        """Series dict without name returns None."""
        assert get_series_info({"series": {"part": 1}}) is None

    def test_series_properties(self):
        """Verify Series object properties work correctly."""
        series = get_series_info({
            "series": {"name": "Tutorial", "part": 1, "total": 3},
        })
        assert series is not None
        assert series.is_first is True
        assert series.is_last is False
        assert series.has_next is True
        assert series.has_prev is False
        assert series.progress_percent == 33

    def test_last_in_series(self):
        series = get_series_info({
            "series": {"name": "Tutorial", "part": 3, "total": 3},
        })
        assert series is not None
        assert series.is_last is True
        assert series.has_next is False


# -----------------------------------------------------------------------
# get_series_neighbor
# -----------------------------------------------------------------------


def _make_mock_page(metadata: dict[str, Any]) -> SimpleNamespace:
    """Create a minimal mock page with metadata for series tests."""
    return SimpleNamespace(metadata=metadata)


def _make_mock_site(
    series_pages: dict[str, list[str]],
    page_map: dict[str, Any],
) -> SimpleNamespace:
    """Create a minimal mock site with series index and page map.

    Args:
        series_pages: Maps series name -> list of page paths
        page_map: Maps page path -> mock page object
    """
    series_index = SimpleNamespace(get=lambda name: series_pages.get(name))
    indexes = SimpleNamespace(series=series_index)
    return SimpleNamespace(
        indexes=indexes,
        get_page_path_map=lambda: page_map,
    )


class TestGetSeriesNeighbor:
    """Tests for get_series_neighbor free function."""

    def test_no_series_data_returns_none(self):
        assert get_series_neighbor({}, None, 1) is None

    def test_no_site_returns_none(self):
        metadata = {"series": {"name": "Tutorial", "part": 2, "total": 3}}
        assert get_series_neighbor(metadata, None, 1) is None

    def test_prev_from_first_returns_none(self):
        """Part 1 has no previous."""
        metadata = {"series": {"name": "Tutorial", "part": 1, "total": 3}}
        site = _make_mock_site({}, {})
        assert get_series_neighbor(metadata, site, -1) is None

    def test_get_next(self):
        """Part 1 -> next -> Part 2."""
        page2 = _make_mock_page({
            "series": {"name": "Tutorial", "part": 2, "total": 3},
        })
        site = _make_mock_site(
            series_pages={"Tutorial": ["p1.md", "p2.md", "p3.md"]},
            page_map={
                "p1.md": _make_mock_page(
                    {"series": {"name": "Tutorial", "part": 1, "total": 3}},
                ),
                "p2.md": page2,
                "p3.md": _make_mock_page(
                    {"series": {"name": "Tutorial", "part": 3, "total": 3}},
                ),
            },
        )

        metadata = {"series": {"name": "Tutorial", "part": 1, "total": 3}}
        result = get_series_neighbor(metadata, site, 1)
        assert result is page2

    def test_get_prev(self):
        """Part 2 -> prev -> Part 1."""
        page1 = _make_mock_page({
            "series": {"name": "Tutorial", "part": 1, "total": 3},
        })
        site = _make_mock_site(
            series_pages={"Tutorial": ["p1.md", "p2.md"]},
            page_map={
                "p1.md": page1,
                "p2.md": _make_mock_page(
                    {"series": {"name": "Tutorial", "part": 2, "total": 3}},
                ),
            },
        )

        metadata = {"series": {"name": "Tutorial", "part": 2, "total": 3}}
        result = get_series_neighbor(metadata, site, -1)
        assert result is page1

    def test_target_page_not_found(self):
        """Returns None when target part doesn't exist in series."""
        site = _make_mock_site(
            series_pages={"Tutorial": ["p1.md"]},
            page_map={
                "p1.md": _make_mock_page(
                    {"series": {"name": "Tutorial", "part": 1, "total": 3}},
                ),
            },
        )

        metadata = {"series": {"name": "Tutorial", "part": 1, "total": 3}}
        # Part 2 doesn't exist
        assert get_series_neighbor(metadata, site, 1) is None

    def test_series_name_not_in_index(self):
        """Returns None when series name isn't in the site index."""
        site = _make_mock_site(series_pages={}, page_map={})
        metadata = {"series": {"name": "Unknown Series", "part": 1}}
        assert get_series_neighbor(metadata, site, 1) is None

    def test_string_series_format(self):
        """String series data means part=1, series_name=string."""
        page2 = _make_mock_page(
            {"series": {"name": "My Series", "part": 2, "total": 2}},
        )
        site = _make_mock_site(
            series_pages={"My Series": ["p1.md", "p2.md"]},
            page_map={
                "p1.md": _make_mock_page({"series": "My Series"}),
                "p2.md": page2,
            },
        )

        # String format: name="My Series", part defaults to 1
        metadata: dict[str, Any] = {"series": "My Series"}
        result = get_series_neighbor(metadata, site, 1)
        assert result is page2

    def test_no_indexes_on_site(self):
        """Returns None if site has no indexes attribute."""
        site = SimpleNamespace()
        metadata = {"series": {"name": "Tutorial", "part": 1}}
        assert get_series_neighbor(metadata, site, 1) is None

    def test_no_series_index(self):
        """Returns None if indexes has no series attribute."""
        site = SimpleNamespace(indexes=SimpleNamespace())
        metadata = {"series": {"name": "Tutorial", "part": 1}}
        assert get_series_neighbor(metadata, site, 1) is None

    def test_page_path_missing_from_map(self):
        """Gracefully skips paths that aren't in the page map."""
        page2 = _make_mock_page(
            {"series": {"name": "Tutorial", "part": 2}},
        )
        site = _make_mock_site(
            series_pages={"Tutorial": ["missing.md", "p2.md"]},
            page_map={"p2.md": page2},  # missing.md not in map
        )

        metadata = {"series": {"name": "Tutorial", "part": 1}}
        result = get_series_neighbor(metadata, site, 1)
        assert result is page2

    def test_invalid_series_type_returns_none(self):
        """Non-string, non-dict series data returns None."""
        site = _make_mock_site({}, {})
        metadata: dict[str, Any] = {"series": 12345}
        assert get_series_neighbor(metadata, site, 1) is None

    def test_empty_series_name_returns_none(self):
        """Dict with empty name returns None."""
        site = _make_mock_site({}, {})
        metadata = {"series": {"name": "", "part": 1}}
        assert get_series_neighbor(metadata, site, 1) is None


# -----------------------------------------------------------------------
# Integration: Page property wrappers for untested properties
# -----------------------------------------------------------------------


class TestPageAgeDaysProperty:
    """Test Page.age_days property wrapper."""

    def test_age_days_with_date(self, tmp_path):
        from bengal.core.page import Page

        past = datetime.now(UTC) - timedelta(days=5)
        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={"date": past.isoformat()},
        )

        assert page.age_days == 5

    def test_age_days_no_date(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={},
        )

        assert page.age_days == 0


class TestPageAgeMonthsProperty:
    """Test Page.age_months property wrapper."""

    def test_age_months_with_date(self, tmp_path):
        from bengal.core.page import Page

        now = datetime.now(UTC)
        if now.month <= 2:
            past = now.replace(year=now.year - 1, month=now.month + 10, day=1)
        else:
            past = now.replace(month=now.month - 2, day=1)

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={"date": past.isoformat()},
        )

        assert page.age_months == 2

    def test_age_months_no_date(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={},
        )

        assert page.age_months == 0


class TestPageAuthorProperty:
    """Test Page.author property wrapper."""

    def test_author_from_metadata(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={"author": "Jane Smith"},
        )

        assert page.author is not None
        assert page.author.name == "Jane Smith"

    def test_no_author(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={},
        )

        assert page.author is None


class TestPageAuthorsProperty:
    """Test Page.authors property wrapper."""

    def test_authors_from_metadata(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={
                "authors": [
                    {"name": "Alice"},
                    {"name": "Bob"},
                ],
            },
        )

        assert len(page.authors) == 2
        assert page.authors[0].name == "Alice"
        assert page.authors[1].name == "Bob"


class TestPageSeriesProperty:
    """Test Page.series property wrapper."""

    def test_series_from_metadata(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={
                "series": {"name": "Tutorial", "part": 2, "total": 5},
            },
        )

        assert page.series is not None
        assert page.series.name == "Tutorial"
        assert page.series.part == 2

    def test_no_series(self, tmp_path):
        from bengal.core.page import Page

        page = Page(
            source_path=tmp_path / "test.md",
            _raw_content="",
            _raw_metadata={},
        )

        assert page.series is None
