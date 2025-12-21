"""
Tests for bengal.utils.dates module.
"""

from datetime import UTC, date, datetime

import pytest

from bengal.utils.dates import (
    date_range_overlap,
    format_date_human,
    format_date_iso,
    format_date_rfc822,
    get_current_year,
    is_recent,
    parse_date,
    time_ago,
)


class TestParseDate:
    """Tests for parse_date function."""

    def test_none_input(self):
        """Test None input returns None."""
        assert parse_date(None) is None

    def test_datetime_passthrough(self):
        """Test datetime objects pass through unchanged."""
        dt = datetime(2025, 10, 9, 14, 30, 0)
        assert parse_date(dt) == dt

    def test_date_to_datetime(self):
        """Test date objects convert to datetime at midnight."""
        d = date(2025, 10, 9)
        result = parse_date(d)
        assert result == datetime(2025, 10, 9, 0, 0, 0)

    def test_iso_string(self):
        """Test ISO 8601 string parsing."""
        result = parse_date("2025-10-09")
        assert result == datetime(2025, 10, 9, 0, 0, 0)

    def test_iso_string_with_time(self):
        """Test ISO 8601 string with time."""
        result = parse_date("2025-10-09T14:30:00")
        assert result == datetime(2025, 10, 9, 14, 30, 0)

    def test_iso_string_with_z_timezone(self):
        """Test ISO string with Z timezone suffix."""
        result = parse_date("2025-10-09T14:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 9

    def test_iso_string_with_timezone(self):
        """Test ISO string with timezone offset."""
        result = parse_date("2025-10-09T14:30:00+00:00")
        assert result is not None
        assert result.year == 2025

    def test_common_formats(self):
        """Test parsing of common date formats."""
        test_cases = [
            ("2025-10-09", datetime(2025, 10, 9, 0, 0)),
            ("2025/10/09", datetime(2025, 10, 9, 0, 0)),
            ("09-10-2025", datetime(2025, 10, 9, 0, 0)),
            ("09/10/2025", datetime(2025, 10, 9, 0, 0)),
            ("October 09, 2025", datetime(2025, 10, 9, 0, 0)),
            ("Oct 09, 2025", datetime(2025, 10, 9, 0, 0)),
        ]

        for date_str, expected in test_cases:
            result = parse_date(date_str)
            assert result == expected, f"Failed to parse: {date_str}"

    def test_custom_formats(self):
        """Test custom format strings."""
        result = parse_date("09.10.2025", formats=["%d.%m.%Y"])
        assert result == datetime(2025, 10, 9, 0, 0)

    def test_invalid_string_return_none(self):
        """Test invalid string returns None by default."""
        result = parse_date("not a date")
        assert result is None

    def test_invalid_string_raise(self):
        """Test invalid string raises BengalError when on_error='raise'."""
        from bengal.utils.exceptions import BengalError

        with pytest.raises(BengalError, match="Could not parse date"):
            parse_date("not a date", on_error="raise")

    def test_invalid_string_return_original(self):
        """Test invalid string returns original when on_error='return_original'."""
        result = parse_date("not a date", on_error="return_original")
        assert result == "not a date"

    def test_datetime_with_microseconds(self):
        """Test datetime with microseconds."""
        result = parse_date("2025-10-09T14:30:00.123456")
        assert result == datetime(2025, 10, 9, 14, 30, 0, 123456)


class TestFormatDateIso:
    """Tests for format_date_iso function."""

    def test_datetime_to_iso(self):
        """Test datetime formatting to ISO."""
        dt = datetime(2025, 10, 9, 14, 30, 0)
        result = format_date_iso(dt)
        assert result == "2025-10-09T14:30:00"

    def test_date_to_iso(self):
        """Test date formatting to ISO."""
        d = date(2025, 10, 9)
        result = format_date_iso(d)
        assert result == "2025-10-09T00:00:00"

    def test_string_to_iso(self):
        """Test string parsing and formatting to ISO."""
        result = format_date_iso("2025-10-09")
        assert result == "2025-10-09T00:00:00"

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert format_date_iso(None) == ""

    def test_invalid_returns_empty(self):
        """Test invalid input returns empty string."""
        assert format_date_iso("not a date") == ""


class TestFormatDateRfc822:
    """Tests for format_date_rfc822 function."""

    def test_datetime_to_rfc822(self):
        """Test datetime formatting to RFC 822."""
        dt = datetime(2025, 10, 9, 14, 30, 0)
        result = format_date_rfc822(dt)
        # Should be like: "Thu, 09 Oct 2025 14:30:00 "
        assert "Thu, 09 Oct 2025" in result
        assert "14:30:00" in result

    def test_string_to_rfc822(self):
        """Test string parsing and formatting to RFC 822."""
        result = format_date_rfc822("2025-10-09T14:30:00")
        assert "09 Oct 2025" in result

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert format_date_rfc822(None) == ""

    def test_invalid_returns_empty(self):
        """Test invalid input returns empty string."""
        assert format_date_rfc822("not a date") == ""


class TestFormatDateHuman:
    """Tests for format_date_human function."""

    def test_default_format(self):
        """Test default human-readable format."""
        dt = datetime(2025, 10, 9, 14, 30, 0)
        result = format_date_human(dt)
        assert result == "October 09, 2025"

    def test_custom_format(self):
        """Test custom format string."""
        dt = datetime(2025, 10, 9, 14, 30, 0)
        result = format_date_human(dt, format="%Y-%m-%d")
        assert result == "2025-10-09"

    def test_string_input(self):
        """Test string input."""
        result = format_date_human("2025-10-09")
        assert result == "October 09, 2025"

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert format_date_human(None) == ""

    def test_invalid_returns_empty(self):
        """Test invalid input returns empty string."""
        assert format_date_human("not a date") == ""


class TestTimeAgo:
    """Tests for time_ago function."""

    def test_just_now_seconds(self):
        """Test 'just now' for recent times."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        recent = datetime(2025, 10, 9, 14, 29, 30)  # 30 seconds ago
        result = time_ago(recent, now=now)
        assert result == "just now"

    def test_minutes_ago(self):
        """Test minutes ago."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 9, 14, 25, 0)  # 5 minutes ago
        result = time_ago(past, now=now)
        assert result == "5 minutes ago"

    def test_one_minute_ago(self):
        """Test singular 'minute'."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 9, 14, 29, 0)  # 1 minute ago
        result = time_ago(past, now=now)
        assert result == "1 minute ago"

    def test_hours_ago(self):
        """Test hours ago."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 9, 12, 30, 0)  # 2 hours ago
        result = time_ago(past, now=now)
        assert result == "2 hours ago"

    def test_one_hour_ago(self):
        """Test singular 'hour'."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 9, 13, 30, 0)  # 1 hour ago
        result = time_ago(past, now=now)
        assert result == "1 hour ago"

    def test_days_ago(self):
        """Test days ago."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 7, 14, 30, 0)  # 2 days ago
        result = time_ago(past, now=now)
        assert result == "2 days ago"

    def test_one_day_ago(self):
        """Test singular 'day'."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 10, 8, 14, 30, 0)  # 1 day ago
        result = time_ago(past, now=now)
        assert result == "1 day ago"

    def test_months_ago(self):
        """Test months ago."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2025, 8, 9, 14, 30, 0)  # ~2 months ago
        result = time_ago(past, now=now)
        assert "month" in result

    def test_years_ago(self):
        """Test years ago."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        past = datetime(2023, 10, 9, 14, 30, 0)  # 2 years ago
        result = time_ago(past, now=now)
        assert "year" in result

    def test_future_date(self):
        """Test future dates return 'just now'."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        future = datetime(2025, 10, 10, 14, 30, 0)
        result = time_ago(future, now=now)
        assert result == "just now"

    def test_string_input(self):
        """Test string input."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        result = time_ago("2025-10-07T14:30:00", now=now)
        assert "day" in result

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert time_ago(None) == ""

    def test_invalid_returns_empty(self):
        """Test invalid input returns empty string."""
        assert time_ago("not a date") == ""

    def test_timezone_aware(self):
        """Test timezone-aware datetime."""
        now = datetime(2025, 10, 9, 14, 30, 0, tzinfo=UTC)
        past = datetime(2025, 10, 9, 12, 30, 0, tzinfo=UTC)
        result = time_ago(past, now=now)
        assert result == "2 hours ago"


class TestGetCurrentYear:
    """Tests for get_current_year function."""

    def test_returns_current_year(self):
        """Test returns current year as integer."""
        result = get_current_year()
        assert isinstance(result, int)
        assert result >= 2025  # Should be current year or later


class TestIsRecent:
    """Tests for is_recent function."""

    def test_recent_date(self):
        """Test date within threshold is recent."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        recent = datetime(2025, 10, 7, 14, 30, 0)  # 2 days ago
        result = is_recent(recent, days=7, now=now)
        assert result is True

    def test_old_date(self):
        """Test date beyond threshold is not recent."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        old = datetime(2025, 9, 1, 14, 30, 0)  # >30 days ago
        result = is_recent(old, days=7, now=now)
        assert result is False

    def test_exact_threshold(self):
        """Test date exactly at threshold."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        exact = datetime(2025, 10, 2, 14, 30, 0)  # Exactly 7 days ago
        result = is_recent(exact, days=7, now=now)
        assert result is True

    def test_future_date(self):
        """Test future dates are not recent."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        future = datetime(2025, 10, 10, 14, 30, 0)
        result = is_recent(future, days=7, now=now)
        assert result is False

    def test_string_input(self):
        """Test string input."""
        now = datetime(2025, 10, 9, 14, 30, 0)
        result = is_recent("2025-10-07", days=7, now=now)
        assert result is True

    def test_none_returns_false(self):
        """Test None returns False."""
        assert is_recent(None) is False

    def test_invalid_returns_false(self):
        """Test invalid input returns False."""
        assert is_recent("not a date") is False


class TestDateRangeOverlap:
    """Tests for date_range_overlap function."""

    def test_overlapping_ranges(self):
        """Test ranges that overlap."""
        start1 = datetime(2025, 1, 1)
        end1 = datetime(2025, 1, 10)
        start2 = datetime(2025, 1, 5)
        end2 = datetime(2025, 1, 15)
        result = date_range_overlap(start1, end1, start2, end2)
        assert result is True

    def test_non_overlapping_ranges(self):
        """Test ranges that don't overlap."""
        start1 = datetime(2025, 1, 1)
        end1 = datetime(2025, 1, 10)
        start2 = datetime(2025, 1, 15)
        end2 = datetime(2025, 1, 20)
        result = date_range_overlap(start1, end1, start2, end2)
        assert result is False

    def test_adjacent_ranges(self):
        """Test ranges that touch but don't overlap."""
        start1 = datetime(2025, 1, 1)
        end1 = datetime(2025, 1, 10)
        start2 = datetime(2025, 1, 10)
        end2 = datetime(2025, 1, 20)
        result = date_range_overlap(start1, end1, start2, end2)
        assert result is True  # Touching counts as overlap

    def test_contained_range(self):
        """Test one range completely inside another."""
        start1 = datetime(2025, 1, 1)
        end1 = datetime(2025, 1, 31)
        start2 = datetime(2025, 1, 10)
        end2 = datetime(2025, 1, 20)
        result = date_range_overlap(start1, end1, start2, end2)
        assert result is True

    def test_string_inputs(self):
        """Test string inputs."""
        result = date_range_overlap("2025-01-01", "2025-01-10", "2025-01-05", "2025-01-15")
        assert result is True

    def test_invalid_dates_return_false(self):
        """Test invalid dates return False."""
        result = date_range_overlap("not a date", "2025-01-10", "2025-01-05", "2025-01-15")
        assert result is False

    def test_none_returns_false(self):
        """Test None dates return False."""
        result = date_range_overlap(
            None, datetime(2025, 1, 10), datetime(2025, 1, 5), datetime(2025, 1, 15)
        )
        assert result is False
