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
        self, content: str, line_start: int, full_line: str
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_atx_heading(self, content: str, line_start: int) -> Token | None:
        raise NotImplementedError

    def _classify_block_quote(self, content: str, line_start: int) -> Iterator[Token]:
        raise NotImplementedError

    def _try_classify_thematic_break(self, content: str, line_start: int) -> Token | None:
        raise NotImplementedError

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_footnote_def(self, content: str, line_start: int) -> Token | None:
        raise NotImplementedError

    def _try_classify_link_reference_def(self, content: str, line_start: int) -> Token | None:
        raise NotImplementedError

    def _try_classify_directive_start(
        self, content: str, line_start: int
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _scan_block(self) -> Iterator[Token]:
        """Scan for block-level elements using window approach.

        Algorithm:
        1. Find end of current line (window)
        2. Classify the line content (pure logic)
        3. Emit token and commit position (always advances)

        Yields:
            Token objects for the current line.
        """
        # Save location BEFORE scanning (for O(1) location tracking)
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Calculate indent (spaces/tabs at start)
        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        # Apply text transformation (the "window thing")
        # This allows variables to resolve BEFORE classification, so {{ var }}
        # can contain block markers like headings or lists.
        if self._text_transformer:
            content = self._text_transformer(content)

        # Commit position now - we WILL consume this line
        self._commit_to(line_end)

        # Empty line or whitespace only = blank line
        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start))
            return

        # CommonMark: 4+ spaces indent creates an indented code block
        # This takes priority over most block types (except fenced code inside lists)
        # Must check BEFORE ATX headings, thematic breaks, and block quotes
        if indent >= 4:
            yield Token(
                TokenType.INDENTED_CODE,
                line[4:] + ("\n" if self._consumed_newline else ""),
                self._location_from(line_start),
            )
            return

        # Check for fenced code blocks
        # (fenced code can be indented inside list items, but indent < 4)
        # Fenced code: ``` or ~~~ (uses O(1) frozenset lookup)
        if content[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(content, line_start, indent)
            if token:
                yield token
                return

        # HTML block: <tag>, <!--, <?, <!, </tag>, etc.
        # Must be checked before most other block types
        # CommonMark 4.6 defines 7 types of HTML blocks
        if content[0] == "<":
            html_result = self._try_classify_html_block_start(content, line_start, line)
            if html_result:
                yield from html_result
                return

        # ATX Heading: # ## ### etc.
        # CommonMark: ATX heading cannot be indented 4+ spaces (already handled above)
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start)
            if token:
                yield token
                return

        # Block quote: > (cannot be indented 4+ spaces)
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start)
            return

        # Thematic break: ---, ***, ___ (must check BEFORE list markers)
        # A line like "- - -" or "* * *" could be either, but thematic break takes precedence
        # Uses O(1) frozenset lookup
        if content[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(content, line_start)
            if token:
                yield token
                return

        # List item: -, *, +, or 1. 1)
        # Pass indent so nested lists can be detected
        list_tokens = self._try_classify_list_marker(content, line_start, indent)
        if list_tokens is not None:
            yield from list_tokens
            return

        # Footnote definition: [^id]: content
        footnote_token = self._try_classify_footnote_def(content, line_start)
        if footnote_token is not None:
            yield footnote_token
            return

        # Link reference definition: [label]: url "title"
        if content.startswith("[") and not content.startswith("[^"):
            link_ref_token = self._try_classify_link_reference_def(content, line_start)
            if link_ref_token is not None:
                yield link_ref_token
                return

        # Directive: :::{name} or ::::{name} etc.
        if content.startswith(":"):
            directive_tokens = self._try_classify_directive_start(content, line_start)
            if directive_tokens is not None:
                yield from directive_tokens
                return

        # Default: paragraph line
        # Prefix with spaces to preserve indent (like list markers do)
        # This allows parser to detect non-indented paragraphs that terminate lists
        indented_content = " " * indent + content.rstrip("\n")
        yield Token(
            TokenType.PARAGRAPH_LINE,
            indented_content,
            self._location_from(line_start),
        )
