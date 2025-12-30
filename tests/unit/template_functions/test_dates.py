"""Tests for date template functions."""

from datetime import datetime, timedelta

from bengal.rendering.template_functions.dates import (
    date_add,
    date_diff,
    date_iso,
    date_rfc822,
    time_ago,
)


class TestTimeAgo:
    """Tests for time_ago filter."""

    def test_just_now(self):
        now = datetime.now()
        assert time_ago(now) == "just now"

    def test_minutes_ago(self):
        time = datetime.now() - timedelta(minutes=5)
        assert time_ago(time) == "5 minutes ago"

    def test_one_minute_ago(self):
        time = datetime.now() - timedelta(minutes=1)
        assert time_ago(time) == "1 minute ago"

    def test_hours_ago(self):
        time = datetime.now() - timedelta(hours=3)
        assert time_ago(time) == "3 hours ago"

    def test_one_hour_ago(self):
        time = datetime.now() - timedelta(hours=1)
        assert time_ago(time) == "1 hour ago"

    def test_days_ago(self):
        time = datetime.now() - timedelta(days=5)
        assert time_ago(time) == "5 days ago"

    def test_one_day_ago(self):
        time = datetime.now() - timedelta(days=1)
        assert time_ago(time) == "1 day ago"

    def test_months_ago(self):
        time = datetime.now() - timedelta(days=60)
        assert time_ago(time) == "2 months ago"

    def test_years_ago(self):
        time = datetime.now() - timedelta(days=400)
        assert time_ago(time) == "1 year ago"

    def test_empty_date(self):
        assert time_ago(None) == ""

    def test_future_date(self):
        future = datetime.now() + timedelta(days=1)
        assert time_ago(future) == "just now"

    def test_iso_string(self):
        time_str = (datetime.now() - timedelta(hours=2)).isoformat()
        result = time_ago(time_str)
        assert "hour" in result


class TestDateIso:
    """Tests for date_iso filter."""

    def test_format_datetime(self):
        date = datetime(2025, 10, 3, 14, 30, 0)
        result = date_iso(date)
        assert result.startswith("2025-10-03")
        assert "14:30:00" in result

    def test_empty_date(self):
        assert date_iso(None) == ""

    def test_parse_string(self):
        date_str = "2025-10-03T14:30:00"
        result = date_iso(date_str)
        assert "2025-10-03" in result

    def test_invalid_input(self):
        """Invalid input now returns empty string (safer behavior)."""
        result = date_iso("invalid")
        assert result == ""


class TestDateRfc822:
    """Tests for date_rfc822 filter."""

    def test_format_datetime(self):
        date = datetime(2025, 10, 3, 14, 30, 0)
        result = date_rfc822(date)
        # Should contain day, month, year
        assert "03 Oct 2025" in result
        assert "14:30:00" in result

    def test_empty_date(self):
        assert date_rfc822(None) == ""

    def test_parse_string(self):
        date_str = "2025-10-03T14:30:00"
        result = date_rfc822(date_str)
        assert "Oct 2025" in result


class TestDateAdd:
    """Tests for date_add filter."""

    def test_add_days(self):
        date = datetime(2025, 1, 1, 12, 0, 0)
        result = date_add(date, days=7)
        assert result.day == 8
        assert result.month == 1

    def test_subtract_days(self):
        date = datetime(2025, 1, 10, 12, 0, 0)
        result = date_add(date, days=-5)
        assert result.day == 5

    def test_add_weeks(self):
        date = datetime(2025, 1, 1, 12, 0, 0)
        result = date_add(date, weeks=2)
        assert result.day == 15

    def test_add_hours(self):
        date = datetime(2025, 1, 1, 10, 0, 0)
        result = date_add(date, hours=5)
        assert result.hour == 15

    def test_add_minutes(self):
        date = datetime(2025, 1, 1, 10, 30, 0)
        result = date_add(date, minutes=45)
        assert result.hour == 11
        assert result.minute == 15

    def test_add_multiple(self):
        date = datetime(2025, 1, 1, 0, 0, 0)
        result = date_add(date, days=1, hours=2, minutes=30)
        assert result.day == 2
        assert result.hour == 2
        assert result.minute == 30

    def test_iso_string_input(self):
        result = date_add("2025-01-01T12:00:00", days=1)
        assert result is not None
        assert result.day == 2

    def test_none_input(self):
        result = date_add(None, days=1)
        assert result is None

    def test_cross_month(self):
        date = datetime(2025, 1, 31, 12, 0, 0)
        result = date_add(date, days=1)
        assert result.month == 2
        assert result.day == 1


class TestDateDiff:
    """Tests for date_diff filter."""

    def test_days_difference(self):
        date1 = datetime(2025, 1, 10, 12, 0, 0)
        date2 = datetime(2025, 1, 1, 12, 0, 0)
        result = date_diff(date1, date2)
        assert result == 9

    def test_hours_difference(self):
        date1 = datetime(2025, 1, 1, 15, 0, 0)
        date2 = datetime(2025, 1, 1, 10, 0, 0)
        result = date_diff(date1, date2, unit="hours")
        assert result == 5

    def test_minutes_difference(self):
        date1 = datetime(2025, 1, 1, 10, 30, 0)
        date2 = datetime(2025, 1, 1, 10, 0, 0)
        result = date_diff(date1, date2, unit="minutes")
        assert result == 30

    def test_seconds_difference(self):
        date1 = datetime(2025, 1, 1, 10, 0, 45)
        date2 = datetime(2025, 1, 1, 10, 0, 0)
        result = date_diff(date1, date2, unit="seconds")
        assert result == 45

    def test_all_units(self):
        date1 = datetime(2025, 1, 2, 12, 30, 45)
        date2 = datetime(2025, 1, 1, 12, 0, 0)
        result = date_diff(date1, date2, unit="all")
        assert isinstance(result, dict)
        assert result["days"] == 1
        assert "hours" in result
        assert "minutes" in result
        assert "seconds" in result

    def test_iso_string_input(self):
        result = date_diff("2025-01-10T12:00:00", "2025-01-01T12:00:00")
        assert result == 9

    def test_none_input_first(self):
        result = date_diff(None, datetime(2025, 1, 1))
        assert result is None

    def test_none_input_second(self):
        result = date_diff(datetime(2025, 1, 1), None)
        assert result is None

    def test_negative_difference(self):
        date1 = datetime(2025, 1, 1, 12, 0, 0)
        date2 = datetime(2025, 1, 10, 12, 0, 0)
        result = date_diff(date1, date2)
        assert result == -9
