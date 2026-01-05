"""Block mode scanner mixin."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.charsets import (
    FENCE_CHARS,
    THEMATIC_BREAK_CHARS,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class BlockScannerMixin:
    """Mixin providing block mode scanning logic.

    Scans for block-level elements using window approach:
    1. Find end of current line (window)
    2. Classify the line content (pure logic)
    3. Emit token and commit position (always advances)
    """

    # These will be set by the Lexer class or other mixins
    _source: str
    _pos: int
    _consumed_newline: bool
    _text_transformer: Callable[[str], str] | None

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation."""
        raise NotImplementedError

    def _find_line_end(self) -> int:
        """Find end of current line."""
        raise NotImplementedError

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level and content start position."""
        raise NotImplementedError

    def _chars_for_indent(self, line: str, target_indent: int) -> int:
        """Calculate how many characters to skip to consume target_indent spaces."""
        col = 0
        pos = 0
        while pos < len(line) and col < target_indent:
            char = line[pos]
            if char == " ":
                col += 1
                pos += 1
            elif char == "\t":
                # Tab expands to next multiple of 4
                tab_width = 4 - (col % 4)
                col += tab_width
                pos += 1
            else:
                break
        return pos

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end."""
        raise NotImplementedError

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position."""
        raise NotImplementedError

    # Classifier methods (provided by classifier mixins)
    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_html_block_start(
        self, content: str, line_start: int, full_line: str, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_atx_heading(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _classify_block_quote(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        raise NotImplementedError

    def _try_classify_thematic_break(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_footnote_def(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_link_reference_def(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_directive_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _scan_block(self) -> Iterator[Token]:
        """Scan for block-level elements using window approach."""
        self._save_location()
        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        if self._text_transformer:
            content = self._text_transformer(content)

        self._commit_to(line_end)

        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start), line_indent=0)
            return

        if indent >= 4:
            chars_for_4_spaces = self._chars_for_indent(line, 4)
            code_content = line[chars_for_4_spaces:]
            yield Token(
                TokenType.INDENTED_CODE,
                code_content + ("\n" if self._consumed_newline else ""),
                self._location_from(line_start),
                line_indent=indent,
            )
            return

        if content[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(content, line_start, indent)
            if token:
                yield token
                return

        if content[0] == "<":
            html_result = self._try_classify_html_block_start(content, line_start, line, indent)
            if html_result:
                yield from html_result
                return

        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start, indent)
            if token:
                yield token
                return

        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start, indent)
            return

        if content[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(content, line_start, indent)
            if token:
                yield token
                return

        list_tokens = self._try_classify_list_marker(content, line_start, indent)
        if list_tokens is not None:
            yield from list_tokens
            return

        footnote_token = self._try_classify_footnote_def(content, line_start, indent)
        if footnote_token is not None:
            yield footnote_token
            return

        if content.startswith("[") and not content.startswith("[^"):
            link_ref_token = self._try_classify_link_reference_def(content, line_start, indent)
            if link_ref_token is not None:
                yield link_ref_token
                return

        if content.startswith(":"):
            directive_tokens = self._try_classify_directive_start(content, line_start, indent)
            if directive_tokens is not None:
                yield from directive_tokens
                return

        indented_content = " " * indent + content.rstrip("\n")
        yield Token(
            TokenType.PARAGRAPH_LINE,
            indented_content,
            self._location_from(line_start),
            line_indent=indent,
        )
