"""Protocols for Patitas.

Defines the contracts for sub-lexers and delegates.
Used for zero-copy handoff (ZCLH) to external highlighters.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol


class LexerDelegate(Protocol):
    """Protocol for sub-lexers that process source ranges.

    Thread Safety:
        Implementations must be stateless or use only local variables.
        The source string is read-only shared state.

    """

    def tokenize_range(
        self,
        source: str,
        start: int,
        end: int,
        language: str,
    ) -> Iterator[Any]:
        """Tokenize a specific range of the source string.

        Args:
            source: The complete source buffer (read-only)
            start: Start index (inclusive)
            end: End index (exclusive)
            language: Language identifier for lexer selection

        Yields:
            Token objects (type depends on implementation)

        Complexity: O(end - start)
        """
        ...

    def supports_language(self, language: str) -> bool:
        """Check if this delegate can handle the given language."""
        ...
