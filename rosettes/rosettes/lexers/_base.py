"""Base lexer implementation for Rosettes.

Provides PatternLexer, a regex-based tokenizer that is thread-safe
by design — all instance state is immutable.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from rosettes._config import LexerConfig
from rosettes._types import Token, TokenType

__all__ = ["PatternLexer", "Rule"]


@dataclass(frozen=True, slots=True)
class Rule:
    """Immutable lexer rule.

    Attributes:
        pattern: Compiled regex pattern to match.
        token_type: Token type to assign, or a callable that
            determines the type from the match.
    """

    pattern: re.Pattern[str]
    token_type: TokenType | Callable[[re.Match[str]], TokenType]


class PatternLexer:
    """Base class for pattern-based lexers.

    Thread-safe: all instance state is immutable.
    Tokenize uses only local variables.

    Subclasses define rules as a class variable (immutable tuple).
    The combined regex pattern is built once at class definition time.

    Complexity Guards:
        MAX_RULES: Prevents regex explosion from too many alternations.
        MAX_PATTERN_LENGTH: Caps combined pattern size.

    These are validated at class definition time (fail-fast).
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()
    filenames: tuple[str, ...] = ()
    mimetypes: tuple[str, ...] = ()

    # Subclasses define rules as class variable (immutable tuple)
    rules: tuple[Rule, ...] = ()

    # Combined pattern for fast matching (built once at class definition)
    _combined_pattern: re.Pattern[str] | None = None
    _rule_map: dict[str, Rule] = {}

    # Complexity guards to prevent regex pathology
    MAX_RULES = 50  # Prevent alternation explosion
    MAX_PATTERN_LENGTH = 8000  # Cap combined pattern size

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Pre-compile combined regex pattern for the lexer."""
        super().__init_subclass__(**kwargs)

        if not cls.rules:
            return

        # Validate complexity bounds
        if len(cls.rules) > cls.MAX_RULES:
            raise ValueError(
                f"Lexer {cls.name!r} has {len(cls.rules)} rules, "
                f"exceeds MAX_RULES={cls.MAX_RULES}. Split into sublexers."
            )

        # Build combined pattern with named groups
        parts: list[str] = []
        cls._rule_map = {}
        for i, rule in enumerate(cls.rules):
            group_name = f"r{i}"
            parts.append(f"(?P<{group_name}>{rule.pattern.pattern})")
            cls._rule_map[group_name] = rule

        combined = "|".join(parts)

        # Validate pattern length
        if len(combined) > cls.MAX_PATTERN_LENGTH:
            raise ValueError(
                f"Lexer {cls.name!r} combined pattern is {len(combined)} chars, "
                f"exceeds MAX_PATTERN_LENGTH={cls.MAX_PATTERN_LENGTH}."
            )

        cls._combined_pattern = re.compile(combined, re.MULTILINE)

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
    ) -> Iterator[Token]:
        """Tokenize source code. Thread-safe (no shared mutable state).

        Args:
            code: The source code to tokenize.
            config: Optional lexer configuration.

        Yields:
            Token objects in order of appearance.
        """
        if not self._combined_pattern:
            return

        if config is None:
            config = LexerConfig()

        line = 1
        line_start = 0

        for match in self._combined_pattern.finditer(code):
            # Find which rule matched
            for group_name, rule in self._rule_map.items():
                value = match.group(group_name)
                if value is not None:
                    # Compute token type
                    token_type = (
                        rule.token_type(match) if callable(rule.token_type) else rule.token_type
                    )

                    # Yield token
                    yield Token(
                        type=token_type,
                        value=value,
                        line=line,
                        column=match.start() - line_start + 1,
                    )

                    # Track line numbers
                    newlines = value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = match.end() - len(value.rsplit("\n", 1)[-1])

                    break
