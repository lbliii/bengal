"""Tests for date filters in bengal.rendering.template_functions.dates module."""

from __future__ import annotations

from datetime import datetime, timedelta

from bengal.rendering.template_functions.dates import (
    days_ago,
    humanize_days,
    month_name,
    months_ago,
)


class TestDaysAgo:
    """Test days_ago filter."""

    def test_days_ago_today(self):
        """days_ago returns 0 for today's date."""
        now = datetime.now()
        assert days_ago(now, now=now) == 0

    def test_days_ago_yesterday(self):
        """days_ago returns 1 for yesterday."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        assert days_ago(yesterday, now=now) == 1

    def test_days_ago_week(self):
        """days_ago returns 7 for a week ago."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        assert days_ago(week_ago, now=now) == 7

    def test_days_ago_none(self):
        """days_ago returns 0 for None."""
        assert days_ago(None) == 0

    def test_days_ago_string_date(self):
        """days_ago handles ISO date strings."""
        now = datetime(2025, 10, 10)
        result = days_ago("2025-10-05", now=now)
        assert result == 5

    def test_days_ago_negative_clamped(self):
        """days_ago returns 0 for future dates."""
        now = datetime.now()
        future = now + timedelta(days=5)
        assert days_ago(future, now=now) == 0


class TestMonthsAgo:
    """Test months_ago filter."""

    def test_months_ago_same_month(self):
        """months_ago returns 0 for same month."""
        now = datetime(2025, 10, 15)
        same_month = datetime(2025, 10, 1)
        assert months_ago(same_month, now=now) == 0

    def test_months_ago_one_month(self):
        """months_ago returns 1 for previous month."""
        now = datetime(2025, 10, 15)
        one_month = datetime(2025, 9, 15)
        assert months_ago(one_month, now=now) == 1

    def test_months_ago_year(self):
        """months_ago returns 12 for one year ago."""
        now = datetime(2025, 10, 15)
        one_year = datetime(2024, 10, 15)
        assert months_ago(one_year, now=now) == 12

    def test_months_ago_none(self):
        """months_ago returns 0 for None."""
        assert months_ago(None) == 0


class TestMonthName:
    """Test month_name filter."""

    def test_month_name_full(self):
        """month_name returns full month names."""
        assert month_name(1) == "January"
        assert month_name(6) == "June"
        assert month_name(12) == "December"

    def test_month_name_abbreviated(self):
        """month_name returns abbreviated names."""
        assert month_name(1, abbrev=True) == "Jan"
        assert month_name(6, abbrev=True) == "Jun"
        assert month_name(12, abbrev=True) == "Dec"

    def test_month_name_invalid(self):
        """month_name returns empty string for invalid month."""
        assert month_name(0) == ""
        assert month_name(13) == ""
        assert month_name(-1) == ""

    def test_month_name_non_int(self):
        """month_name handles non-int input."""
        assert month_name("not an int") == ""  # type: ignore


class TestHumanizeDays:
    """Test humanize_days filter."""

    def test_humanize_today(self):
        """humanize_days returns 'today' for 0."""
        assert humanize_days(0) == "today"

    def test_humanize_yesterday(self):
        """humanize_days returns 'yesterday' for 1."""
        assert humanize_days(1) == "yesterday"

    def test_humanize_days_week(self):
        """humanize_days returns 'X days ago' for 2-6 days."""
        assert humanize_days(3) == "3 days ago"
        assert humanize_days(6) == "6 days ago"

    def test_humanize_one_week(self):
        """humanize_days returns '1 week ago' for 7-13 days."""
        assert humanize_days(7) == "1 week ago"
        assert humanize_days(10) == "1 week ago"

    def test_humanize_weeks(self):
        """humanize_days returns 'X weeks ago' for 14-29 days."""
        assert humanize_days(14) == "2 weeks ago"
        assert humanize_days(21) == "3 weeks ago"

    def test_humanize_one_month(self):
        """humanize_days returns '1 month ago' for 30-59 days."""
        assert humanize_days(30) == "1 month ago"
        assert humanize_days(45) == "1 month ago"

    def test_humanize_months(self):
        """humanize_days returns 'X months ago' for 60-364 days."""
        assert humanize_days(60) == "2 months ago"
        assert humanize_days(180) == "6 months ago"

    def test_humanize_one_year(self):
        """humanize_days returns '1 year ago' for 365-729 days."""
        assert humanize_days(365) == "1 year ago"
        assert humanize_days(500) == "1 year ago"

    def test_humanize_years(self):
        """humanize_days returns 'X years ago' for 730+ days."""
        assert humanize_days(730) == "2 years ago"
        assert humanize_days(1095) == "3 years ago"

    def test_humanize_negative(self):
        """humanize_days returns empty for negative."""
        assert humanize_days(-1) == ""

    def test_humanize_non_int(self):
        """humanize_days handles non-int input."""
        assert humanize_days("not an int") == ""  # type: ignore


