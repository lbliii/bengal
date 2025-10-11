"""Tests for date template functions."""

from datetime import datetime, timedelta
from bengal.rendering.template_functions.dates import (
    time_ago,
    date_iso,
    date_rfc822,
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
        assert time_ago(None) == ''
    
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
        assert date_iso(None) == ''
    
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
        assert date_rfc822(None) == ''
    
    def test_parse_string(self):
        date_str = "2025-10-03T14:30:00"
        result = date_rfc822(date_str)
        assert "Oct 2025" in result

