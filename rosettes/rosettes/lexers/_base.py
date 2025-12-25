"""Base lexer implementation for Rosettes.

Provides PatternLexer, a high-performance regex-based tokenizer that is
thread-safe by design — all instance state is immutable.

Performance Optimizations:
    1. Uses match.lastgroup for O(1) rule lookup (not O(n) iteration)
    2. Pre-indexed rule array (integer lookup, not dict lookup)
    3. Minimal token representation option for streaming
    4. Line tracking only when needed
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rosettes._types import Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from rosettes._config import LexerConfig

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

    Performance Design:
        - Combined regex with named groups for single-pass matching
        - O(1) rule lookup via match.lastgroup + pre-indexed array
        - Optional line/column tracking (disabled for max speed)
        - Minimal object allocation in hot path

    Subclasses define rules as a class variable (immutable tuple).
    The combined regex pattern is built once at class definition time.
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()
    filenames: tuple[str, ...] = ()
    mimetypes: tuple[str, ...] = ()

    # Subclasses define rules as class variable (immutable tuple)
    rules: tuple[Rule, ...] = ()

    # Combined pattern for fast matching (built once at class definition)
    _combined_pattern: re.Pattern[str] | None = None
    # Pre-indexed rule array for O(1) lookup by group name
    _rule_index: dict[str, int] = {}
    _rules_array: tuple[Rule, ...] = ()

    # Complexity guards to prevent regex pathology
    MAX_RULES = 50  # Prevent alternation explosion
    MAX_PATTERN_LENGTH = 10000  # Cap combined pattern size

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
        # Use short group names to reduce regex size
        parts: list[str] = []
        cls._rule_index = {}
        cls._rules_array = cls.rules

        for i, rule in enumerate(cls.rules):
            # Short group names: _0, _1, etc. (faster than r0, r1)
            group_name = f"_{i}"
            parts.append(f"(?P<{group_name}>{rule.pattern.pattern})")
            cls._rule_index[group_name] = i

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

        # Cache lookups in local variables for speed
        pattern = self._combined_pattern
        rule_index = self._rule_index
        rules_array = self._rules_array

        line = 1
        line_start = 0

        for match in pattern.finditer(code):
            # O(1) lookup: get matched group name directly
            group_name = match.lastgroup
            if group_name is None:
                continue

            # O(1) lookup: get rule by pre-computed index
            rule = rules_array[rule_index[group_name]]
            value = match.group()

            # Compute token type (inline or via callback)
            token_type = rule.token_type
            if callable(token_type):
                token_type = token_type(match)

            # Yield token with position info
            yield Token(
                type=token_type,
                value=value,
                line=line,
                column=match.start() - line_start + 1,
            )

            # Track line numbers - avoid double scan
            nl_idx = value.find("\n")
            if nl_idx >= 0:
                # Count from first newline position (single scan)
                newlines = value.count("\n", nl_idx)
                line += newlines
                # Find position after last newline
                last_nl = value.rfind("\n")
                line_start = match.start() + last_nl + 1

    def tokenize_fast(
        self,
        code: str,
    ) -> Iterator[tuple[TokenType, str]]:
        """Fast tokenization without position tracking.

        Yields minimal (type, value) tuples for maximum speed.
        Use this when line/column info is not needed.

        Args:
            code: The source code to tokenize.

        Yields:
            (TokenType, value) tuples.
        """
        if not self._combined_pattern:
            return

        # Cache lookups in local variables for speed
        pattern = self._combined_pattern
        rule_index = self._rule_index
        rules_array = self._rules_array

        for match in pattern.finditer(code):
            group_name = match.lastgroup
            if group_name is None:
                continue

            rule = rules_array[rule_index[group_name]]
            value = match.group()

            token_type = rule.token_type
            if callable(token_type):
                token_type = token_type(match)

            yield (token_type, value)
