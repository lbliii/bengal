"""Match registry for emphasis delimiter tracking.

Decouples match state from token objects, enabling immutable tokens.
This is a prerequisite for using NamedTuples as inline tokens.

Thread Safety:
    MatchRegistry instances are single-use per _parse_inline() call.
    All state is instance-local; no shared mutable state.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DelimiterMatch:
    """Record of a matched opener-closer pair.

    Attributes:
        opener_idx: Index of the opener token in the token list.
        closer_idx: Index of the closer token in the token list.
        match_count: Number of delimiters matched (1 for emphasis, 2 for strong).
    """

    opener_idx: int
    closer_idx: int
    match_count: int


@dataclass(slots=True)
class MatchRegistry:
    """External tracking for delimiter matches.

    Decouples match state from token objects, enabling immutable tokens.
    All delimiter matching state is tracked here instead of mutating tokens.

    Usage:
        registry = MatchRegistry()
        registry.record_match(opener_idx=0, closer_idx=5, count=2)
        if registry.is_active(3):
            ...

    Complexity:
        - record_match(): O(1)
        - is_active(): O(1)
        - deactivate(): O(1)
        - remaining_count(): O(1)
        - get_matches_for_opener(): O(1) amortized
    """

    matches: list[DelimiterMatch] = field(default_factory=list)
    consumed: dict[int, int] = field(default_factory=dict)
    deactivated: set[int] = field(default_factory=set)
    # Cache opener -> list of matches for O(1) lookup in AST building
    # Multiple matches can exist for the same opener (e.g., ***text*** has 2 matches)
    _opener_matches_cache: dict[int, list[DelimiterMatch]] = field(default_factory=dict)

    def record_match(self, opener_idx: int, closer_idx: int, count: int) -> None:
        """Record a delimiter match.

        Args:
            opener_idx: Index of the opening delimiter token.
            closer_idx: Index of the closing delimiter token.
            count: Number of delimiters matched (1 or 2).
        """
        match = DelimiterMatch(opener_idx, closer_idx, count)
        self.matches.append(match)
        # Append to list of matches for this opener
        if opener_idx not in self._opener_matches_cache:
            self._opener_matches_cache[opener_idx] = []
        self._opener_matches_cache[opener_idx].append(match)
        # Track consumed delimiters
        self.consumed[opener_idx] = self.consumed.get(opener_idx, 0) + count
        self.consumed[closer_idx] = self.consumed.get(closer_idx, 0) + count

    def is_active(self, idx: int) -> bool:
        """Check if delimiter at idx is still active.

        Args:
            idx: Token index to check.

        Returns:
            True if the delimiter is still active (not deactivated).
        """
        return idx not in self.deactivated

    def deactivate(self, idx: int) -> None:
        """Mark delimiter as inactive.

        Args:
            idx: Token index to deactivate.
        """
        self.deactivated.add(idx)

    def remaining_count(self, idx: int, original_count: int) -> int:
        """Get remaining delimiter count after matches.

        Args:
            idx: Token index to check.
            original_count: Original delimiter count for this token.

        Returns:
            Number of remaining unused delimiters.
        """
        return original_count - self.consumed.get(idx, 0)

    def get_match_for_opener(self, idx: int) -> DelimiterMatch | None:
        """Get first match record where idx is the opener.

        For nested emphasis (***text***), use get_matches_for_opener() instead.

        Args:
            idx: Token index to check.

        Returns:
            First DelimiterMatch if this token is an opener, None otherwise.
        """
        matches = self._opener_matches_cache.get(idx)
        return matches[0] if matches else None

    def get_matches_for_opener(self, idx: int) -> list[DelimiterMatch]:
        """Get all match records where idx is the opener.

        Used for nested emphasis (e.g., ***text*** has 2 matches: strong and emphasis).

        Args:
            idx: Token index to check.

        Returns:
            List of DelimiterMatch records, empty if not an opener.
        """
        return self._opener_matches_cache.get(idx, [])
