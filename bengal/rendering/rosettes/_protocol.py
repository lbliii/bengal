"""Protocol definitions for Rosettes.

Defines the contracts that lexers and formatters must implement.
All implementations must be thread-safe.
"""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ._config import FormatConfig, LexerConfig
from ._types import Token, TokenType

if TYPE_CHECKING:
    pass

__all__ = ["Lexer", "Formatter"]


@runtime_checkable
class Lexer(Protocol):
    """Protocol for tokenizers.

    Implementations must be thread-safe — no mutable shared state.
    The tokenize method should only use local variables.
    """

    @property
    def name(self) -> str:
        """The canonical name of this lexer (e.g., 'python')."""
        ...

    @property
    def aliases(self) -> tuple[str, ...]:
        """Alternative names for this lexer (e.g., ('py', 'python3'))."""
        ...

    @property
    def filenames(self) -> tuple[str, ...]:
        """Glob patterns for files this lexer handles (e.g., ('*.py',))."""
        ...

    @property
    def mimetypes(self) -> tuple[str, ...]:
        """MIME types this lexer handles."""
        ...

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
    ) -> Iterator[Token]:
        """Tokenize source code into a stream of tokens.

        Args:
            code: The source code to tokenize.
            config: Optional lexer configuration.

        Yields:
            Token objects in order of appearance.
        """
        ...

    def tokenize_fast(
        self,
        code: str,
    ) -> Iterator[tuple[TokenType, str]]:
        """Fast tokenization without position tracking.

        Yields minimal (type, value) tuples for maximum speed.
        Use when line/column info is not needed.

        Args:
            code: The source code to tokenize.

        Yields:
            (TokenType, value) tuples.
        """
        ...


@runtime_checkable
class Formatter(Protocol):
    """Protocol for output formatters.

    Implementations must be thread-safe.
    The format method should only use local variables.
    """

    @property
    def name(self) -> str:
        """The canonical name of this formatter (e.g., 'html')."""
        ...

    def format(
        self,
        tokens: Iterator[Token],
        config: FormatConfig | None = None,
    ) -> Iterator[str]:
        """Format tokens into output chunks.

        Args:
            tokens: Stream of tokens to format.
            config: Optional formatter configuration.

        Yields:
            String chunks of formatted output.
        """
        ...
