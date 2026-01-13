"""HTML block mode scanner mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.lexer.modes import (
    HTML_BLOCK_TYPE1_TAGS,
    LexerMode,
)
from bengal.rendering.parsers.patitas.tokens import Token

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class HtmlScannerMixin:
    """Mixin providing HTML block mode scanning logic.
    
    Scans content inside HTML blocks until the appropriate end condition
    based on the HTML block type (1-7 per CommonMark spec).
        
    """

    # These will be set by the Lexer class
    _source: str
    _pos: int
    _source_len: int
    _mode: LexerMode
    _html_block_type: int
    _html_block_content: list[str]
    _html_block_start: int
    _consumed_newline: bool

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation."""
        raise NotImplementedError

    def _find_line_end(self) -> int:
        """Find end of current line."""
        raise NotImplementedError

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end."""
        raise NotImplementedError

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position."""
        raise NotImplementedError

    def _emit_html_block(self) -> Iterator[Token]:
        """Emit accumulated HTML block. Implemented by HtmlClassifierMixin."""
        raise NotImplementedError

    def _scan_html_block_content(self) -> Iterator[Token]:
        """Scan content inside HTML block until end condition.

        The end condition depends on the HTML block type:
        - Type 1: Ends with closing tag (</pre>, </script>, etc.)
        - Type 2: Ends with -->
        - Type 3: Ends with ?>
        - Type 4: Ends with >
        - Type 5: Ends with ]]>
        - Types 6, 7: End with blank line

        Yields:
            HTML_BLOCK token when end condition is met.
        """
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        self._commit_to(line_end)

        # Add line to content
        if self._consumed_newline:
            self._html_block_content.append(line + "\n")
        else:
            self._html_block_content.append(line)

        # Check end conditions based on type
        html_type = self._html_block_type
        line_lower = line.lower()

        # Type 1: ends with closing tag
        if html_type == 1:
            for tag in HTML_BLOCK_TYPE1_TAGS:
                if f"</{tag}>" in line_lower:
                    yield from self._emit_html_block()
                    return

        # Type 2: ends with -->
        elif html_type == 2:
            if "-->" in line:
                yield from self._emit_html_block()
                return

        # Type 3: ends with ?>
        elif html_type == 3:
            if "?>" in line:
                yield from self._emit_html_block()
                return

        # Type 4: ends with >
        elif html_type == 4:
            if ">" in line:
                yield from self._emit_html_block()
                return

        # Type 5: ends with ]]>
        elif html_type == 5:
            if "]]>" in line:
                yield from self._emit_html_block()
                return

        # Types 6 and 7: end with blank line
        elif html_type in (6, 7) and not line.strip():
            # Remove the blank line from content (it's just the delimiter)
            if self._html_block_content:
                self._html_block_content.pop()
            yield from self._emit_html_block()
            return

        # Check for EOF - emit what we have
        if self._pos >= self._source_len:
            yield from self._emit_html_block()
