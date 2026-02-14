"""
Unit tests for content type utility functions.

Tests sorting keys and detection helpers used across strategies.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from bengal.content_types.utils import (
    date_key,
    has_dated_pages,
    has_page_type_metadata,
    section_name_matches,
    weight_title_key,
)


class TestWeightTitleKey:
    """Test weight_title_key sorting utility."""

    def test_returns_weight_and_lowercase_title(self):
        """Should return tuple of (weight, lowercase_title)."""
        page = Mock()
        page.metadata = {"weight": 10}
        page.title = "My Page"

        result = weight_title_key(page)

        assert result == (10, "my page")

    def test_uses_default_weight_when_missing(self):
        """Should use 999999 as default weight when not in metadata."""
        page = Mock()
        page.metadata = {}
        page.title = "No Weight Page"

        result = weight_title_key(page)

        assert result == (999999, "no weight page")

    def test_sorting_by_weight_primary(self):
        """Pages should sort by weight first."""
        page1 = Mock(metadata={"weight": 20}, title="Zebra")
        page2 = Mock(metadata={"weight": 10}, title="Apple")
        page3 = Mock(metadata={"weight": 30}, title="Middle")

        pages = [page1, page2, page3]
        sorted_pages = sorted(pages, key=weight_title_key)

        assert sorted_pages[0].title == "Apple"  # weight 10
        assert sorted_pages[1].title == "Zebra"  # weight 20
        assert sorted_pages[2].title == "Middle"  # weight 30

    def test_sorting_by_title_secondary(self):
        """Pages with same weight should sort by title alphabetically."""
        page1 = Mock(metadata={"weight": 10}, title="Zebra")
        page2 = Mock(metadata={"weight": 10}, title="Apple")
        page3 = Mock(metadata={"weight": 10}, title="Middle")

        pages = [page1, page2, page3]
        sorted_pages = sorted(pages, key=weight_title_key)

        assert sorted_pages[0].title == "Apple"
        assert sorted_pages[1].title == "Middle"
        assert sorted_pages[2].title == "Zebra"

    def test_title_sorting_is_case_insensitive(self):
        """Title sorting should be case-insensitive."""
        page1 = Mock(metadata={"weight": 10}, title="apple")
        page2 = Mock(metadata={"weight": 10}, title="BANANA")
        page3 = Mock(metadata={"weight": 10}, title="Cherry")

        pages = [page3, page1, page2]
        sorted_pages = sorted(pages, key=weight_title_key)

        assert sorted_pages[0].title == "apple"
        assert sorted_pages[1].title == "BANANA"
        assert sorted_pages[2].title == "Cherry"


class TestDateKey:
    """Test date_key sorting utility."""

    def test_returns_page_date_when_present(self):
        """Should return the page's date when available."""
        test_date = datetime(2025, 6, 15, 12, 0, 0)
        page = Mock(date=test_date)

        result = date_key(page)

        assert result == test_date

    def test_returns_datetime_min_when_no_date(self):
        """Should return datetime.min when page has no date."""
        page = Mock(date=None)

        result = date_key(page)

        assert result == datetime.min

    def test_sorting_newest_first(self):
        """Pages should sort by date, newest first with reverse=True."""
        page1 = Mock(date=datetime(2025, 1, 1))
        page2 = Mock(date=datetime(2025, 12, 31))
        page3 = Mock(date=datetime(2025, 6, 15))
        page4 = Mock(date=None)  # Should go to end with reverse=True

        pages = [page1, page2, page3, page4]
        sorted_pages = sorted(pages, key=date_key, reverse=True)

        assert sorted_pages[0].date == datetime(2025, 12, 31)
        assert sorted_pages[1].date == datetime(2025, 6, 15)
        assert sorted_pages[2].date == datetime(2025, 1, 1)
        assert sorted_pages[3].date is None


class TestSectionNameMatches:
    """Test section_name_matches detection utility."""

    def _make_section(self, name: str) -> Mock:
        """Create a mock section with the given name."""
        section = Mock()
        section.name = name
        return section

    def test_matches_exact_name(self):
        """Should match when section name equals a pattern."""
        section = self._make_section("blog")

        assert section_name_matches(section, ("blog", "posts", "news")) is True

    def test_matches_case_insensitive(self):
        """Should match case-insensitively."""
        section = self._make_section("BLOG")

        assert section_name_matches(section, ("blog", "posts")) is True

    def test_no_match_when_not_in_patterns(self):
        """Should not match when name is not in patterns."""
        section = self._make_section("tutorials")

        assert section_name_matches(section, ("blog", "posts", "news")) is False

    def test_empty_patterns_never_matches(self):
        """Empty patterns should never match."""
        section = self._make_section("anything")

        assert section_name_matches(section, ()) is False

    def test_works_with_tuple_of_patterns(self):
        """Should work with tuple of patterns."""
        section = self._make_section("docs")

        assert section_name_matches(section, ("docs", "documentation")) is True

    def test_works_with_list_of_patterns(self):
        """Should work with list of patterns."""
        section = self._make_section("guides")

        assert section_name_matches(section, ["guides", "reference"]) is True


class TestHasDatedPages:
    """Test has_dated_pages detection utility."""

    def test_returns_false_for_empty_section(self):
        """Should return False when section has no pages."""
        section = Mock(pages=[])

        assert has_dated_pages(section) is False

    def test_returns_true_when_above_threshold(self):
        """Should return True when dated pages exceed threshold."""
        pages = [
            Mock(metadata={"date": "2025-01-01"}, date=datetime(2025, 1, 1)),
            Mock(metadata={"date": "2025-01-02"}, date=datetime(2025, 1, 2)),
            Mock(metadata={"date": "2025-01-03"}, date=datetime(2025, 1, 3)),
            Mock(metadata={}, date=None),  # One without date
        ]
        section = Mock(pages=pages)

        # 3/4 = 75% > 60% threshold
        assert has_dated_pages(section, threshold=0.6) is True

    def test_returns_false_when_below_threshold(self):
        """Should return False when dated pages are below threshold."""
        pages = [
            Mock(metadata={"date": "2025-01-01"}, date=datetime(2025, 1, 1)),
            Mock(metadata={}, date=None),
            Mock(metadata={}, date=None),
            Mock(metadata={}, date=None),
            Mock(metadata={}, date=None),
        ]
        section = Mock(pages=pages)

        # 1/5 = 20% < 60% threshold
        assert has_dated_pages(section, threshold=0.6) is False

    def test_samples_only_specified_number_of_pages(self):
        """Should only sample the specified number of pages."""
        # First 3 have dates, rest don't
        pages = [
            Mock(metadata={"date": "2025-01-01"}, date=datetime(2025, 1, 1)),
            Mock(metadata={"date": "2025-01-02"}, date=datetime(2025, 1, 2)),
            Mock(metadata={"date": "2025-01-03"}, date=datetime(2025, 1, 3)),
            Mock(metadata={}, date=None),
            Mock(metadata={}, date=None),
            Mock(metadata={}, date=None),
        ]
        section = Mock(pages=pages)

        # With sample_size=3, all sampled pages have dates (100% > 60%)
        assert has_dated_pages(section, threshold=0.6, sample_size=3) is True

    def test_detects_date_in_metadata(self):
        """Should detect dates from metadata dict."""
        page = Mock(metadata={"date": "2025-01-01"}, date=None)
        section = Mock(pages=[page])

        assert has_dated_pages(section, threshold=0.5, sample_size=1) is True

    def test_detects_date_attribute(self):
        """Should detect dates from page.date attribute."""
        page = Mock(metadata={}, date=datetime(2025, 1, 1))
        section = Mock(pages=[page])

        assert has_dated_pages(section, threshold=0.5, sample_size=1) is True

    def test_custom_threshold(self):
        """Should respect custom threshold value."""
        pages = [
            Mock(metadata={"date": "2025-01-01"}, date=datetime(2025, 1, 1)),
            Mock(metadata={}, date=None),
        ]
        section = Mock(pages=pages)

        # 1/2 = 50%
        assert has_dated_pages(section, threshold=0.5) is True
        assert has_dated_pages(section, threshold=0.6) is False


class TestHasPageTypeMetadata:
    """Test has_page_type_metadata detection utility."""

    def test_returns_false_for_empty_section(self):
        """Should return False when section has no pages."""
        section = Mock(pages=[])

        assert has_page_type_metadata(section, ("python-module",)) is False

    def test_exact_match_returns_true(self):
        """Should return True for exact type match."""
        page = Mock(metadata={"type": "python-module"})
        section = Mock(pages=[page])

        assert has_page_type_metadata(section, ("python-module", "cli-command")) is True

    def test_no_match_returns_false(self):
        """Should return False when no types match."""
        page = Mock(metadata={"type": "blog-post"})
        section = Mock(pages=[page])

        assert has_page_type_metadata(section, ("python-module", "cli-command")) is False

    def test_substring_match_when_enabled(self):
        """Should match substrings when substring_match=True."""
        page = Mock(metadata={"type": "python-module-class"})
        section = Mock(pages=[page])

        # "python-" is a substring of "python-module-class"
        assert has_page_type_metadata(section, ("python-",), substring_match=True) is True

    def test_no_substring_match_when_disabled(self):
        """Should not match substrings when substring_match=False."""
        page = Mock(metadata={"type": "python-module-class"})
        section = Mock(pages=[page])

        # Exact match required
        assert has_page_type_metadata(section, ("python-",), substring_match=False) is False

    def test_samples_specified_number_of_pages(self):
        """Should only check the specified sample size."""
        pages = [
            Mock(metadata={"type": "other"}),
            Mock(metadata={"type": "other"}),
            Mock(metadata={"type": "python-module"}),  # Third page has match
        ]
        section = Mock(pages=pages)

        # sample_size=2 won't find the match
        assert has_page_type_metadata(section, ("python-module",), sample_size=2) is False
        # sample_size=3 will find it
        assert has_page_type_metadata(section, ("python-module",), sample_size=3) is True

    def test_skips_pages_without_type(self):
        """Should skip pages that don't have type metadata."""
        pages = [
            Mock(metadata={}),  # No type
            Mock(metadata={"type": ""}),  # Empty type
            Mock(metadata={"type": "python-module"}),  # Valid type
        ]
        section = Mock(pages=pages)

        assert has_page_type_metadata(section, ("python-module",), sample_size=3) is True

    def test_multiple_type_values(self):
        """Should match any of multiple type values."""
        page = Mock(metadata={"type": "autodoc-python"})
        section = Mock(pages=[page])

        assert (
            has_page_type_metadata(section, ("python-module", "autodoc-python", "autodoc-rest"))
            is True
        )

    @pytest.mark.parametrize(
        ("page_type", "patterns", "substring", "expected"),
        [
            ("cli-command", ("cli-",), True, True),
            ("cli-command", ("command",), True, True),
            ("cli-command", ("cli-command",), False, True),
            ("cli-command", ("cli",), False, False),
            ("python-module", ("python-module", "autodoc-python"), False, True),
        ],
        ids=[
            "substring-prefix",
            "substring-suffix",
            "exact-match",
            "no-partial-exact",
            "multiple-values",
        ],
    )
    def test_various_matching_scenarios(self, page_type, patterns, substring, expected):
        """Test various type matching scenarios."""
        page = Mock(metadata={"type": page_type})
        section = Mock(pages=[page])

        result = has_page_type_metadata(section, patterns, substring_match=substring)
        assert result is expected
