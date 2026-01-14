"""
Property-based tests for date utilities using Hypothesis.

These tests verify that date parsing/formatting maintains critical invariants
across ALL possible inputs, including edge cases.
"""

from datetime import date, datetime, timedelta

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from bengal.utils.primitives.dates import (
    date_range_overlap,
    format_date_human,
    format_date_iso,
    format_date_rfc822,
    get_current_year,
    is_recent,
    parse_date,
    time_ago,
)


# Custom strategies for dates
def dates_strategy():
    """Generate reasonable datetime objects."""
    return st.datetimes(
        min_value=datetime(1900, 1, 1),
        max_value=datetime(2100, 12, 31),
    )


def iso_date_strings():
    """Generate ISO format date strings."""
    return st.dates(
        min_value=date(1900, 1, 1),
        max_value=date(2100, 12, 31),
    ).map(lambda d: d.isoformat())


class TestParseDateProperties:
    """Property tests for parse_date function."""

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_datetime_passthrough_idempotent(self, dt):
        """
        Property: Parsing a datetime returns the same datetime.

        parse_date(dt) == dt for all datetime objects.
        """
        result = parse_date(dt)
        assert result == dt, f"Datetime should pass through unchanged: {result} != {dt}"

    @pytest.mark.hypothesis
    @given(d=st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)))
    def test_date_converts_to_midnight(self, d):
        """
        Property: date objects convert to datetime at midnight.

        Hours, minutes, seconds should all be 0.
        """
        result = parse_date(d)

        assert result is not None, f"Date should parse: {d}"
        assert result.year == d.year, f"Year mismatch: {result.year} != {d.year}"
        assert result.month == d.month, f"Month mismatch: {result.month} != {d.month}"
        assert result.day == d.day, f"Day mismatch: {result.day} != {d.day}"
        assert result.hour == 0, f"Hour should be 0: {result.hour}"
        assert result.minute == 0, f"Minute should be 0: {result.minute}"
        assert result.second == 0, f"Second should be 0: {result.second}"

    @pytest.mark.hypothesis
    @given(iso_str=iso_date_strings())
    def test_iso_strings_always_parse(self, iso_str):
        """
        Property: Valid ISO date strings always parse successfully.

        YYYY-MM-DD format should never fail.
        """
        result = parse_date(iso_str)

        assert result is not None, f"ISO string should parse: {iso_str}"

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_parse_roundtrip_via_isoformat(self, dt):
        """
        Property: datetime → isoformat → parse_date should roundtrip.

        Date/time components should be preserved (ignoring microseconds).
        """
        iso_str = dt.isoformat()
        result = parse_date(iso_str)

        assert result is not None, f"Should parse ISO string: {iso_str}"
        # Compare without microseconds (not always preserved in string roundtrip)
        assert result.replace(microsecond=0) == dt.replace(microsecond=0), (
            f"Roundtrip failed: {result} != {dt}"
        )

    @pytest.mark.hypothesis
    @given(invalid=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20))
    def test_invalid_strings_return_none(self, invalid):
        """
        Property: Invalid strings return None (don't crash).

        Ensures robustness - bad input shouldn't cause exceptions.
        """
        # Avoid strings that might accidentally be valid dates
        assume(not any(char.isdigit() for char in invalid))

        result = parse_date(invalid)

        assert result is None, f"Invalid string should return None: '{invalid}' → {result}"

    @pytest.mark.hypothesis
    @given(invalid=st.text(min_size=1, max_size=20))
    def test_raise_mode_never_returns_none(self, invalid):
        """
        Property: on_error='raise' either succeeds or raises, never returns None.
        """
        # Skip valid date-like strings
        parsed_default = parse_date(invalid)
        assume(parsed_default is None)

        try:
            result = parse_date(invalid, on_error="raise")
            # If we get here, it parsed successfully
            assert result is not None, f"Successful parse should not return None: '{invalid}'"
        except ValueError:
            # Expected for invalid strings - primitives raise ValueError, not BengalError
            pass


class TestFormatDateIsoProperties:
    """Property tests for format_date_iso function."""

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_always_returns_string(self, dt):
        """
        Property: format_date_iso always returns a string.
        """
        result = format_date_iso(dt)

        assert isinstance(result, str), f"Should return string: {type(result)}"

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_output_is_parseable(self, dt):
        """
        Property: Output can be parsed back to datetime.

        format_date_iso(dt) should produce valid ISO strings.
        """
        formatted = format_date_iso(dt)

        if formatted:  # Empty string for None input
            reparsed = parse_date(formatted)
            assert reparsed is not None, f"Formatted string should be parseable: '{formatted}'"

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_iso_format_structure(self, dt):
        """
        Property: ISO format has expected structure.

        Should contain date separator and optionally time separator.
        """
        formatted = format_date_iso(dt)

        if formatted:
            # Should have at least YYYY-MM-DD
            assert "-" in formatted, f"ISO format should have date separators: '{formatted}'"
            # Should have year at start (4 digits)
            assert formatted[:4].isdigit(), f"ISO format should start with year: '{formatted}'"


class TestFormatDateRfc822Properties:
    """Property tests for format_date_rfc822 function."""

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_always_returns_string(self, dt):
        """
        Property: format_date_rfc822 always returns a string.
        """
        result = format_date_rfc822(dt)

        assert isinstance(result, str), f"Should return string: {type(result)}"

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_rfc822_has_weekday(self, dt):
        """
        Property: RFC 822 format includes weekday abbreviation.
        """
        formatted = format_date_rfc822(dt)

        if formatted:
            # Should start with 3-letter weekday abbreviation
            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            assert any(formatted.startswith(day) for day in weekdays), (
                f"RFC 822 should start with weekday: '{formatted}'"
            )


class TestFormatDateHumanProperties:
    """Property tests for format_date_human function."""

    @pytest.mark.hypothesis
    @given(dt=dates_strategy(), fmt=st.sampled_from(["%Y-%m-%d", "%B %d, %Y", "%d/%m/%Y", "%Y"]))
    def test_always_returns_string(self, dt, fmt):
        """
        Property: format_date_human always returns a string for valid formats.
        """
        result = format_date_human(dt, format=fmt)

        assert isinstance(result, str), f"Should return string: {type(result)}"

    @pytest.mark.hypothesis
    @given(dt=dates_strategy())
    def test_default_format_readable(self, dt):
        """
        Property: Default format produces human-readable output.
        """
        formatted = format_date_human(dt)

        if formatted:
            # Default format should have month name and comma
            assert "," in formatted, f"Default format should have comma: '{formatted}'"


class TestTimeAgoProperties:
    """Property tests for time_ago function."""

    @pytest.mark.hypothesis
    @given(
        offset_seconds=st.integers(min_value=0, max_value=365 * 24 * 60 * 60)  # Up to 1 year
    )
    def test_always_returns_string(self, offset_seconds):
        """
        Property: time_ago always returns a string.
        """
        now = datetime.now()
        past = now - timedelta(seconds=offset_seconds)

        result = time_ago(past, now=now)

        assert isinstance(result, str), f"Should return string: {type(result)}"

    @pytest.mark.hypothesis
    @given(
        offset_seconds=st.integers(min_value=61, max_value=3600)  # 1 min to 1 hour
    )
    def test_recent_past_mentions_unit(self, offset_seconds):
        """
        Property: Recent times mention appropriate unit (minute, hour, day).
        """
        now = datetime.now()
        past = now - timedelta(seconds=offset_seconds)

        result = time_ago(past, now=now)

        # Should mention a time unit
        units = ["minute", "hour", "day", "ago", "now"]
        assert any(unit in result.lower() for unit in units), (
            f"Should mention time unit: '{result}'"
        )

    @pytest.mark.hypothesis
    @given(offset_days=st.integers(min_value=1, max_value=30))
    def test_ordering_preserved(self, offset_days):
        """
        Property: More recent dates produce "smaller" time ago values.

        1 day ago should be more recent than 2 days ago.
        """
        now = datetime.now()
        recent = now - timedelta(days=offset_days)
        older = now - timedelta(days=offset_days + 1)

        recent_str = time_ago(recent, now=now)
        older_str = time_ago(older, now=now)

        # Both should mention "day" or "days"
        if "day" in recent_str and "day" in older_str:
            # Extract numbers (rough check)
            recent_num = int("".join(c for c in recent_str if c.isdigit()) or "0")
            older_num = int("".join(c for c in older_str if c.isdigit()) or "0")

            assert recent_num < older_num, (
                f"Recent should have smaller number: '{recent_str}' vs '{older_str}'"
            )


class TestIsRecentProperties:
    """Property tests for is_recent function."""

    @pytest.mark.hypothesis
    @given(
        days_threshold=st.integers(min_value=1, max_value=365),
        offset_days=st.integers(min_value=0, max_value=730),
    )
    def test_consistent_with_threshold(self, days_threshold, offset_days):
        """
        Property: is_recent returns True iff within threshold.
        """
        now = datetime.now()
        past = now - timedelta(days=offset_days)

        result = is_recent(past, days=days_threshold, now=now)
        expected = offset_days <= days_threshold

        assert result == expected, (
            f"is_recent({offset_days} days ago, threshold={days_threshold}) "
            f"should be {expected}, got {result}"
        )

    @pytest.mark.hypothesis
    @given(days=st.integers(min_value=1, max_value=365))
    def test_boundary_at_threshold(self, days):
        """
        Property: Date exactly N days ago is considered recent with threshold N.
        """
        now = datetime.now()
        boundary = now - timedelta(days=days)

        result = is_recent(boundary, days=days, now=now)

        assert result, f"Date exactly {days} days ago should be recent with threshold {days}"


class TestDateRangeOverlapProperties:
    """Property tests for date_range_overlap function."""

    @pytest.mark.hypothesis
    @given(
        start1=dates_strategy(),
        duration1=st.integers(min_value=1, max_value=365),
        start2=dates_strategy(),
        duration2=st.integers(min_value=1, max_value=365),
    )
    def test_symmetric(self, start1, duration1, start2, duration2):
        """
        Property: Overlap is symmetric.

        overlap(A, B) == overlap(B, A)
        """
        end1 = start1 + timedelta(days=duration1)
        end2 = start2 + timedelta(days=duration2)

        overlap1 = date_range_overlap(start1, end1, start2, end2)
        overlap2 = date_range_overlap(start2, end2, start1, end1)

        assert overlap1 == overlap2, f"Overlap should be symmetric: {overlap1} != {overlap2}"

    @pytest.mark.hypothesis
    @given(start=dates_strategy(), duration=st.integers(min_value=1, max_value=365))
    def test_range_overlaps_with_itself(self, start, duration):
        """
        Property: A range always overlaps with itself.
        """
        end = start + timedelta(days=duration)

        result = date_range_overlap(start, end, start, end)

        assert result, f"Range should overlap with itself: [{start}, {end}]"

    @pytest.mark.hypothesis
    @given(
        start1=dates_strategy(),
        duration1=st.integers(min_value=1, max_value=100),
        gap=st.integers(min_value=1, max_value=100),
    )
    def test_non_overlapping_ranges(self, start1, duration1, gap):
        """
        Property: Ranges with gap between them don't overlap.
        """
        end1 = start1 + timedelta(days=duration1)
        start2 = end1 + timedelta(days=gap)  # Gap after end1
        end2 = start2 + timedelta(days=duration1)

        result = date_range_overlap(start1, end1, start2, end2)

        assert not result, (
            f"Ranges with gap should not overlap: [{start1}, {end1}] and [{start2}, {end2}]"
        )


class TestGetCurrentYearProperties:
    """Property tests for get_current_year function."""

    @pytest.mark.hypothesis
    @given(st.just(None))  # Run once
    def test_returns_integer(self, _):
        """
        Property: get_current_year returns an integer.
        """
        result = get_current_year()

        assert isinstance(result, int), f"Should return int: {type(result)}"

    @pytest.mark.hypothesis
    @given(st.just(None))  # Run once
    def test_reasonable_year(self, _):
        """
        Property: Current year is within reasonable bounds.
        """
        result = get_current_year()

        assert 2000 <= result <= 2200, f"Year seems unreasonable: {result}"


# Example output documentation
"""
EXAMPLE HYPOTHESIS OUTPUT
-------------------------

Running these tests generates thousands of date examples like:

1. Date parsing:
   - "2025-10-09" → datetime(2025, 10, 9, 0, 0)
   - "2089-12-31T23:59:59" → datetime(...)
   - Edge years: 1900, 2100
   - Invalid: "not-a-date" → None

2. Formatting:
   - ISO: "2025-10-09T14:30:00"
   - RFC822: "Thu, 09 Oct 2025 14:30:00 +0000"
   - Human: "October 09, 2025"

3. Time ago:
   - 5 minutes → "5 minutes ago"
   - 2 days → "2 days ago"
   - 1 year → "1 year ago"
   - Future → "just now"

4. Date ranges:
   - Overlapping ranges
   - Adjacent ranges
   - Gaps between ranges
   - Edge boundaries

Each test runs 100+ times with different combinations,
automatically discovering edge cases like:
- Leap years
- Month boundaries
- Year boundaries
- Timezone handling
- Microsecond precision

To see statistics:
    pytest tests/unit/utils/test_dates_properties.py --hypothesis-show-statistics
"""
