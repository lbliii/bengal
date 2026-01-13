"""Unit tests for MatchRegistry.

Tests the external delimiter match tracking system that enables
immutable inline tokens.
"""

from __future__ import annotations

from patitas.parsing.inline.match_registry import (
    DelimiterMatch,
    MatchRegistry,
)


class TestDelimiterMatch:
    """Tests for DelimiterMatch dataclass."""

    def test_create_match(self):
        """Test creating a delimiter match."""
        match = DelimiterMatch(opener_idx=0, closer_idx=5, match_count=2)
        assert match.opener_idx == 0
        assert match.closer_idx == 5
        assert match.match_count == 2

    def test_match_is_slotted(self):
        """Verify DelimiterMatch uses __slots__ for memory efficiency."""
        match = DelimiterMatch(opener_idx=0, closer_idx=5, match_count=1)
        assert hasattr(match, "__slots__")


class TestMatchRegistry:
    """Tests for MatchRegistry."""

    def test_empty_registry(self):
        """Test empty registry state."""
        registry = MatchRegistry()
        assert len(registry.matches) == 0
        assert len(registry.consumed) == 0
        assert len(registry.deactivated) == 0

    def test_record_match(self):
        """Test recording a match."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        assert len(registry.matches) == 1
        assert registry.matches[0].opener_idx == 0
        assert registry.matches[0].closer_idx == 5
        assert registry.matches[0].match_count == 2

    def test_consumed_tracking(self):
        """Test that consumed delimiters are tracked correctly."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        assert registry.consumed[0] == 2
        assert registry.consumed[5] == 2

    def test_remaining_count(self):
        """Test remaining delimiter count calculation."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        # Original count was 3, consumed 2
        assert registry.remaining_count(0, original_count=3) == 1
        assert registry.remaining_count(5, original_count=3) == 1

        # Fully consumed
        assert registry.remaining_count(0, original_count=2) == 0

    def test_is_active_default(self):
        """Test that delimiters are active by default."""
        registry = MatchRegistry()
        assert registry.is_active(0) is True
        assert registry.is_active(5) is True

    def test_deactivate(self):
        """Test deactivating a delimiter."""
        registry = MatchRegistry()
        registry.deactivate(3)

        assert registry.is_active(0) is True
        assert registry.is_active(3) is False

    def test_get_match_for_opener(self):
        """Test getting match by opener index."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        match = registry.get_match_for_opener(0)
        assert match is not None
        assert match.opener_idx == 0
        assert match.closer_idx == 5

        # Non-opener returns None
        assert registry.get_match_for_opener(5) is None
        assert registry.get_match_for_opener(99) is None

    def test_get_matches_for_opener_single(self):
        """Test getting all matches for opener with single match."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        matches = registry.get_matches_for_opener(0)
        assert len(matches) == 1
        assert matches[0].match_count == 2

    def test_get_matches_for_opener_multiple(self):
        """Test getting all matches for opener with multiple matches.

        This happens with ***text*** where both emphasis (1) and strong (2)
        are recorded for the same opener.
        """
        registry = MatchRegistry()
        # First match: strong (2 delimiters)
        registry.record_match(opener_idx=0, closer_idx=2, count=2)
        # Second match: emphasis (1 delimiter)
        registry.record_match(opener_idx=0, closer_idx=2, count=1)

        matches = registry.get_matches_for_opener(0)
        assert len(matches) == 2
        assert matches[0].match_count == 2  # Strong first
        assert matches[1].match_count == 1  # Emphasis second

    def test_get_matches_for_non_opener(self):
        """Test getting matches for non-opener returns empty list."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)

        matches = registry.get_matches_for_opener(99)
        assert matches == []

    def test_multiple_independent_matches(self):
        """Test multiple independent opener/closer pairs."""
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=2, count=1)  # *a*
        registry.record_match(opener_idx=4, closer_idx=6, count=2)  # **b**

        assert registry.get_match_for_opener(0).closer_idx == 2
        assert registry.get_match_for_opener(4).closer_idx == 6

        assert registry.remaining_count(0, 1) == 0
        assert registry.remaining_count(4, 2) == 0

    def test_is_slotted(self):
        """Verify MatchRegistry uses __slots__ for memory efficiency."""
        registry = MatchRegistry()
        assert hasattr(registry, "__slots__")


class TestMatchRegistryIntegration:
    """Integration tests simulating real emphasis processing."""

    def test_simple_emphasis(self):
        """Simulate: *italic*"""
        registry = MatchRegistry()

        # Opener at 0, closer at 2, use 1 delimiter
        registry.record_match(opener_idx=0, closer_idx=2, count=1)
        registry.deactivate(0)  # Exhausted
        registry.deactivate(2)  # Exhausted

        match = registry.get_match_for_opener(0)
        assert match is not None
        assert match.match_count == 1
        assert not registry.is_active(0)
        assert not registry.is_active(2)

    def test_triple_emphasis(self):
        """Simulate: ***bold and italic***"""
        registry = MatchRegistry()

        # First match: strong (2 delimiters)
        registry.record_match(opener_idx=0, closer_idx=2, count=2)
        # Second match: emphasis (1 delimiter)
        registry.record_match(opener_idx=0, closer_idx=2, count=1)
        # Both exhausted
        registry.deactivate(0)
        registry.deactivate(2)

        matches = registry.get_matches_for_opener(0)
        assert len(matches) == 2

        # Verify consumed count
        assert registry.consumed[0] == 3  # 2 + 1
        assert registry.consumed[2] == 3  # 2 + 1
        assert registry.remaining_count(0, 3) == 0

    def test_nested_emphasis(self):
        """Simulate: *outer **inner** outer*"""
        registry = MatchRegistry()

        # Outer emphasis: opener at 0, closer at 6
        registry.record_match(opener_idx=0, closer_idx=6, count=1)
        # Inner strong: opener at 2, closer at 4
        registry.record_match(opener_idx=2, closer_idx=4, count=2)

        # Deactivate unmatched delimiters between outer opener and closer
        # (In real algorithm, delimiters at indices 1, 3, 5 would be deactivated)

        assert registry.get_match_for_opener(0).closer_idx == 6
        assert registry.get_match_for_opener(2).closer_idx == 4
