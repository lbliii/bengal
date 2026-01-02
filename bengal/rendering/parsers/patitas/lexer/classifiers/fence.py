"""Fenced code block classifier mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.lexer.modes import LexerMode
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class FenceClassifierMixin:
    """Mixin providing fenced code block classification."""

    # These will be set by the Lexer class
    _fence_char: str
    _fence_count: int
    _fence_info: str
    _fence_indent: int
    _mode: LexerMode

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as fenced code start.

        Fenced code blocks start with 3+ backticks or tildes.
        Backtick fences cannot have backticks in the info string.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for CommonMark indent stripping)

        Returns:
            Token if valid fence, None otherwise.
        """
        if not content:
            return None

        fence_char = content[0]
        if fence_char not in "`~":
            return None

        # Count fence characters
        count = 0
        pos = 0
        while pos < len(content) and content[pos] == fence_char:
            count += 1
            pos += 1

        if count < 3:
            return None

        # Rest is info string (language hint)
        info = content[pos:].rstrip("\n").strip()

        # Backtick fences cannot have backticks in info string
        if fence_char == "`" and "`" in info:
            return None

        # Valid fence - update state
        self._fence_char = fence_char
        self._fence_count = count
        self._fence_info = info.split()[0] if info else ""
        self._fence_indent = indent  # Store indent for content stripping
        self._mode = LexerMode.CODE_FENCE

        # Encode indent in token value: "I{indent}:{fence}{info}"
        # Parser will extract this to set fence_indent on FencedCode node
        value = f"I{indent}:" + fence_char * count + (info if info else "")
        return Token(TokenType.FENCED_CODE_START, value, self._location_from(line_start))

    def _is_closing_fence(self, line: str) -> bool:
        """Check if line is a closing fence for current code block.

        CommonMark 4.5: Closing fences may be indented 0-3 spaces.
        If indented 4+ spaces, it's NOT a closing fence (it's code content).

        Args:
            line: Full line content including leading whitespace

        Returns:
            True if this is a valid closing fence.
        """
        if not self._fence_char:
            return False

        # Count leading spaces (CommonMark allows 0-3 spaces of indentation)
        indent = 0
        pos = 0
        while pos < len(line) and line[pos] == " ":
            indent += 1
            pos += 1

        # 4+ spaces of indent means NOT a closing fence
        if indent >= 4:
            return False

        content = line[pos:]

        if not content.startswith(self._fence_char):
            return False

        # Count fence characters
        count = 0
        fence_pos = 0
        while fence_pos < len(content) and content[fence_pos] == self._fence_char:
            count += 1
            fence_pos += 1

        if count < self._fence_count:
            return False

        # Rest must be whitespace only
        rest = content[fence_pos:].rstrip("\n")
        return rest.strip() == ""
