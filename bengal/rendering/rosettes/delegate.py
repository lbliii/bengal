"""LexerDelegate implementation using rosettes.

Enables Zero-Copy Lexer Handoff (ZCLH) by bridging Patitas coordinate handoff
to Rosettes state-machine lexers.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.rosettes import get_lexer, supports_language

if TYPE_CHECKING:
    from bengal.rendering.rosettes._types import Token


class RosettesDelegate:
    """LexerDelegate implementation using rosettes.

    Thread-safe: All state is local to method calls.
    Designed for Python 3.14t free-threading.
    """

    def tokenize_range(
        self,
        source: str,
        start: int,
        end: int,
        language: str,
    ) -> Iterator[Token]:
        """Tokenize range using rosettes state-machine lexer.

        O(end - start) guaranteed. Zero allocations for code content.
        """
        lexer = get_lexer(language)
        return lexer.tokenize(source, start=start, end=end)

    def supports_language(self, language: str) -> bool:
        """Check if rosettes supports the given language."""
        return supports_language(language)
