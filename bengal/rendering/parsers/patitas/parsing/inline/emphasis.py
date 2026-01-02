"""Emphasis parsing for Patitas parser.

Implements CommonMark delimiter stack algorithm for emphasis/strong.
See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis
"""

from __future__ import annotations


class EmphasisMixin:
    """Mixin for emphasis delimiter processing.

    Implements CommonMark flanking rules and delimiter matching algorithm.

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
        """Check if character is Unicode whitespace."""
        return char in " \t\n\r\f\v" or char == ""

    def _is_punctuation(self, char: str) -> bool:
        """Check if character is ASCII punctuation."""
        return char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

    def _process_emphasis(self, tokens: list[dict]) -> None:
        """Process delimiter stack to match emphasis openers/closers.

        Implements CommonMark emphasis algorithm.
        Modifies tokens in place to mark matched delimiters.
        """
        # Find delimiter tokens that can close
        closer_idx = 0
        while closer_idx < len(tokens):
            closer = tokens[closer_idx]
            if (
                closer.get("type") != "delimiter"
                or not closer.get("can_close")
                or not closer.get("active")
            ):
                closer_idx += 1
                continue

            # Look backwards for matching opener
            opener_idx = closer_idx - 1
            found_opener = False

            while opener_idx >= 0:
                opener = tokens[opener_idx]
                if opener.get("type") != "delimiter":
                    opener_idx -= 1
                    continue
                if not opener.get("can_open") or not opener.get("active"):
                    opener_idx -= 1
                    continue
                if opener.get("char") != closer.get("char"):
                    opener_idx -= 1
                    continue

                # Check "sum of delimiters" rule (CommonMark)
                # If either opener or closer can both open and close,
                # the sum of delimiter counts must not be multiple of 3
                both_can_open_close = (opener.get("can_open") and opener.get("can_close")) or (
                    closer.get("can_open") and closer.get("can_close")
                )
                sum_is_multiple_of_3 = (opener["count"] + closer["count"]) % 3 == 0
                neither_is_multiple_of_3 = opener["count"] % 3 != 0 or closer["count"] % 3 != 0
                if both_can_open_close and sum_is_multiple_of_3 and neither_is_multiple_of_3:
                    opener_idx -= 1
                    continue

                # Found matching opener
                found_opener = True

                # Determine how many delimiters to use
                use_count = 2 if (opener["count"] >= 2 and closer["count"] >= 2) else 1

                # Mark the match
                opener["matched_with"] = closer_idx
                opener["match_count"] = use_count
                closer["matched_with"] = opener_idx
                closer["match_count"] = use_count

                # Consume delimiters
                opener["count"] -= use_count
                closer["count"] -= use_count

                # Deactivate if exhausted
                if opener["count"] == 0:
                    opener["active"] = False
                if closer["count"] == 0:
                    closer["active"] = False

                # Remove any unmatched delimiters between opener and closer
                for i in range(opener_idx + 1, closer_idx):
                    if tokens[i].get("type") == "delimiter" and tokens[i].get("active"):
                        tokens[i]["active"] = False

                break

            if not found_opener:
                # No opener found, deactivate closer if it can't open
                if not closer.get("can_open"):
                    closer["active"] = False
                closer_idx += 1
            elif closer["count"] > 0:
                # Closer still has delimiters, continue from same position
                pass
            else:
                closer_idx += 1
