"""Emphasis parsing for Patitas parser.

Implements CommonMark delimiter stack algorithm for emphasis/strong.
See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis

Thread Safety:
All methods are stateless or use instance-local state only.
Safe for concurrent use when each parser instance is used by one thread.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.charsets import (
    is_unicode_punctuation,
    is_unicode_whitespace,
)
from bengal.rendering.parsers.patitas.parsing.inline.match_registry import (
    MatchRegistry,
)
from bengal.rendering.parsers.patitas.parsing.inline.tokens import (
    DelimiterToken,
    InlineToken,
)

if TYPE_CHECKING:
    pass


class EmphasisMixin:
    """Mixin for emphasis delimiter processing.
    
    Implements CommonMark flanking rules and delimiter matching algorithm.
    Uses external MatchRegistry for match tracking (enables immutable tokens).
    
    Required Host Attributes: None
    
    Required Host Methods: None
        
    """

    def _is_left_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is left-flanking.

        Left-flanking: not followed by whitespace, and either:
        - not followed by punctuation, OR
        - preceded by whitespace or punctuation
        """
        if self._is_whitespace(after):
            return False
        if not self._is_punctuation(after):
            return True
        return self._is_whitespace(before) or self._is_punctuation(before)

    def _is_right_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is right-flanking.

        Right-flanking: not preceded by whitespace, and either:
        - not preceded by punctuation, OR
        - followed by whitespace or punctuation
        """
        if self._is_whitespace(before):
            return False
        if not self._is_punctuation(before):
            return True
        return self._is_whitespace(after) or self._is_punctuation(after)

    def _is_whitespace(self, char: str) -> bool:
        """Check if character is Unicode whitespace.

        CommonMark uses Unicode whitespace for emphasis flanking rules.
        Includes ASCII whitespace and Unicode category Zs.
        """
        return is_unicode_whitespace(char)

    def _is_punctuation(self, char: str) -> bool:
        """Check if character is Unicode punctuation.

        CommonMark uses Unicode punctuation for emphasis flanking rules.
        Includes ASCII punctuation and Unicode categories P* and S*.
        """
        return is_unicode_punctuation(char)

    def _process_emphasis(
        self,
        tokens: list[InlineToken],
        registry: MatchRegistry | None = None,
    ) -> MatchRegistry:
        """Process delimiter stack to match emphasis openers/closers.

        Implements CommonMark emphasis algorithm using external match tracking.
        Tokens are immutable; all state is tracked in the registry.

        Args:
            tokens: List of InlineToken NamedTuples from _tokenize_inline().
            registry: Optional MatchRegistry to use. If None, creates a new one.

        Returns:
            MatchRegistry containing all delimiter matches.
        """
        if registry is None:
            registry = MatchRegistry()

        closer_idx = 0
        while closer_idx < len(tokens):
            closer = tokens[closer_idx]

            # Skip non-delimiter tokens
            if not isinstance(closer, DelimiterToken):
                closer_idx += 1
                continue

            # Skip if can't close or already deactivated
            if not closer.can_close or not registry.is_active(closer_idx):
                closer_idx += 1
                continue

            # Check remaining count
            closer_remaining = registry.remaining_count(closer_idx, closer.count)
            if closer_remaining == 0:
                closer_idx += 1
                continue

            # Look backwards for matching opener
            opener_idx = closer_idx - 1
            found_opener = False

            while opener_idx >= 0:
                opener = tokens[opener_idx]

                # Skip non-delimiter tokens
                if not isinstance(opener, DelimiterToken):
                    opener_idx -= 1
                    continue

                # Skip if can't open or already deactivated
                if not opener.can_open or not registry.is_active(opener_idx):
                    opener_idx -= 1
                    continue

                # Must be same delimiter character
                if opener.char != closer.char:
                    opener_idx -= 1
                    continue

                # Check remaining count
                opener_remaining = registry.remaining_count(opener_idx, opener.count)
                if opener_remaining == 0:
                    opener_idx -= 1
                    continue

                # CommonMark "sum of delimiters" rule
                # If either opener or closer can both open and close,
                # the sum of delimiter counts must not be multiple of 3
                both_can_open_close = (opener.can_open and opener.can_close) or (
                    closer.can_open and closer.can_close
                )
                sum_is_multiple_of_3 = (opener_remaining + closer_remaining) % 3 == 0
                neither_is_multiple_of_3 = opener_remaining % 3 != 0 or closer_remaining % 3 != 0
                if both_can_open_close and sum_is_multiple_of_3 and neither_is_multiple_of_3:
                    opener_idx -= 1
                    continue

                # Found matching opener
                found_opener = True

                # Determine how many delimiters to use
                use_count = 2 if (opener_remaining >= 2 and closer_remaining >= 2) else 1

                # Record match in registry (tokens are immutable)
                registry.record_match(opener_idx, closer_idx, use_count)

                # Deactivate if exhausted
                if registry.remaining_count(opener_idx, opener.count) == 0:
                    registry.deactivate(opener_idx)
                if registry.remaining_count(closer_idx, closer.count) == 0:
                    registry.deactivate(closer_idx)

                # Deactivate unmatched delimiters between opener and closer
                for i in range(opener_idx + 1, closer_idx):
                    if isinstance(tokens[i], DelimiterToken) and registry.is_active(i):
                        registry.deactivate(i)

                break

            if not found_opener:
                # No opener found, deactivate closer if it can't open
                if not closer.can_open:
                    registry.deactivate(closer_idx)
                closer_idx += 1
            elif registry.remaining_count(closer_idx, closer.count) > 0:
                # Closer still has delimiters, continue from same position
                pass
            else:
                closer_idx += 1

        return registry
