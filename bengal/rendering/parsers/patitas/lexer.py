"""State-machine lexer with O(n) guaranteed performance.

Implements a window-based approach: scan entire lines, classify, then commit.
This eliminates position rewinds and guarantees forward progress.

No regex in the hot path. Zero ReDoS vulnerability by construction.

Thread Safety:
    Lexer instances are single-use. Create one per source string.
    All state is instance-local; no shared mutable state.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum, auto

from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.tokens import Token, TokenType


class LexerMode(Enum):
    """Lexer operating modes.

    The lexer switches between modes based on context:
    - BLOCK: Between blocks, scanning for block starts
    - CODE_FENCE: Inside fenced code block
    - DIRECTIVE: Inside directive block
    """

    BLOCK = auto()  # Between blocks
    CODE_FENCE = auto()  # Inside fenced code block
    DIRECTIVE = auto()  # Inside directive block


class Lexer:
    """State-machine lexer with O(n) guaranteed performance.

    Uses a window-based approach for block scanning:
    1. Scan to end of line (find window)
    2. Classify the line (pure logic, no position changes)
    3. Commit position (always advances)

    This eliminates rewinds and guarantees forward progress.

    Usage:
        >>> lexer = Lexer("# Hello\\n\\nWorld")
        >>> for token in lexer.tokenize():
        ...     print(token)
        Token(ATX_HEADING, '# Hello', 1:1)
        Token(BLANK_LINE, '', 2:1)
        Token(PARAGRAPH_LINE, 'World', 3:1)
        Token(EOF, '', 3:6)

    Thread Safety:
        Lexer instances are single-use. Create one per source string.
        All state is instance-local; no shared mutable state.
    """

    __slots__ = (
        "_source",
        "_source_len",  # Cached len(source) to avoid repeated calls
        "_pos",
        "_lineno",
        "_col",
        "_mode",
        "_source_file",
        "_fence_char",
        "_fence_count",
        "_consumed_newline",
        "_saved_lineno",
        "_saved_col",
        # Directive state
        "_directive_stack",  # Stack of (colon_count, name) for nested directives
    )

    def __init__(self, source: str, source_file: str | None = None) -> None:
        """Initialize lexer with source text.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
        """
        self._source = source
        self._source_len = len(source)  # Cache length
        self._pos = 0
        self._lineno = 1
        self._col = 1
        self._mode = LexerMode.BLOCK
        self._source_file = source_file

        # Fenced code state
        self._fence_char: str = ""
        self._fence_count: int = 0

        # Directive state: stack of (colon_count, name) for nested directives
        self._directive_stack: list[tuple[int, str]] = []

        # Line consumption tracking
        self._consumed_newline: bool = False

        # Saved location for efficient location tracking
        self._saved_lineno: int = 1
        self._saved_col: int = 1

    def tokenize(self) -> Iterator[Token]:
        """Tokenize source into token stream.

        Yields:
            Token objects one at a time

        Complexity: O(n) where n = len(source)
        Memory: O(1) iterator (tokens yielded, not accumulated)
        """
        source_len = self._source_len  # Local var for faster access
        while self._pos < source_len:
            yield from self._dispatch_mode()

        yield Token(TokenType.EOF, "", self._location())

    def _dispatch_mode(self) -> Iterator[Token]:
        """Dispatch to appropriate scanner based on current mode."""
        if self._mode == LexerMode.BLOCK:
            yield from self._scan_block()
        elif self._mode == LexerMode.CODE_FENCE:
            yield from self._scan_code_fence_content()
        elif self._mode == LexerMode.DIRECTIVE:
            yield from self._scan_directive_content()

    # =========================================================================
    # Window-based block scanning
    # =========================================================================

    def _scan_block(self) -> Iterator[Token]:
        """Scan for block-level elements using window approach.

        Algorithm:
        1. Find end of current line (window)
        2. Classify the line content (pure logic)
        3. Emit token and commit position (always advances)
        """
        # Save location BEFORE scanning (for O(1) location tracking)
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Calculate indent (spaces/tabs at start)
        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        # Commit position now - we WILL consume this line
        self._commit_to(line_end)

        # Empty line or whitespace only = blank line
        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start))
            return

        # Indented code block (4+ spaces, not in a list context)
        if indent >= 4:
            yield Token(
                TokenType.INDENTED_CODE,
                line[4:] + ("\n" if self._consumed_newline else ""),
                self._location_from(line_start),
            )
            return

        # ATX Heading: # ## ### etc.
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start)
            if token:
                yield token
                return

        # Fenced code: ``` or ~~~
        if content.startswith("`") or content.startswith("~"):
            token = self._try_classify_fence_start(content, line_start)
            if token:
                yield token
                return

        # Thematic break: ---, ***, ___
        if content[0] in "-*_":
            token = self._try_classify_thematic_break(content, line_start)
            if token:
                yield token
                return

        # Block quote: >
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start)
            return

        # List item: -, *, +, or 1. 1)
        list_tokens = self._try_classify_list_marker(content, line_start)
        if list_tokens is not None:
            yield from list_tokens
            return

        # Directive: :::{name} or ::::{name} etc.
        if content.startswith(":"):
            directive_tokens = self._try_classify_directive_start(content, line_start)
            if directive_tokens is not None:
                yield from directive_tokens
                return

        # Default: paragraph line
        yield Token(
            TokenType.PARAGRAPH_LINE,
            content.rstrip("\n"),
            self._location_from(line_start),
        )

    def _scan_code_fence_content(self) -> Iterator[Token]:
        """Scan content inside fenced code block using window approach."""
        # Save location BEFORE scanning (for O(1) location tracking)
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Check for closing fence
        if self._is_closing_fence(line):
            self._commit_to(line_end)
            # Return to DIRECTIVE mode if inside a directive, otherwise BLOCK
            if self._directive_stack:
                self._mode = LexerMode.DIRECTIVE
            else:
                self._mode = LexerMode.BLOCK
            # Reset fence state
            fence_char = self._fence_char
            self._fence_char = ""
            self._fence_count = 0
            yield Token(
                TokenType.FENCED_CODE_END,
                fence_char * 3,
                self._location_from(line_start),
            )
            return

        # Regular content line
        self._commit_to(line_end)

        # Include newline in content if we consumed one
        content = line
        if self._consumed_newline:
            content = line + "\n"

        yield Token(
            TokenType.FENCED_CODE_CONTENT,
            content,
            self._location_from(line_start),
        )

    # =========================================================================
    # Line classification helpers (pure logic, no position mutation)
    # =========================================================================

    def _try_classify_atx_heading(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as ATX heading.

        Returns Token if valid heading, None otherwise.
        """
        # Count leading #
        level = 0
        pos = 0
        while pos < len(content) and content[pos] == "#" and level < 6:
            level += 1
            pos += 1

        if level == 0:
            return None

        # Must be followed by space, tab, newline, or end
        if pos < len(content) and content[pos] not in " \t\n":
            return None

        # Skip space after #
        if pos < len(content) and content[pos] in " \t":
            pos += 1

        # Rest is heading content
        heading_content = content[pos:].rstrip("\n")

        # Remove trailing # sequence (if preceded by space)
        heading_content = heading_content.rstrip()
        if heading_content.endswith("#"):
            # Find where trailing #s start
            trailing_start = len(heading_content)
            while trailing_start > 0 and heading_content[trailing_start - 1] == "#":
                trailing_start -= 1
            # Must be preceded by space
            if trailing_start > 0 and heading_content[trailing_start - 1] in " \t":
                heading_content = heading_content[: trailing_start - 1].rstrip()
            elif trailing_start == 0:
                heading_content = ""

        value = "#" * level + (" " + heading_content if heading_content else "")
        return Token(TokenType.ATX_HEADING, value, self._location_from(line_start))

    def _try_classify_fence_start(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as fenced code start.

        Returns Token if valid fence, None otherwise.
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
        self._mode = LexerMode.CODE_FENCE

        value = fence_char * count + (info if info else "")
        return Token(TokenType.FENCED_CODE_START, value, self._location_from(line_start))

    def _try_classify_thematic_break(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as thematic break.

        Returns Token if valid break, None otherwise.
        """
        if not content:
            return None

        char = content[0]
        if char not in "-*_":
            return None

        # Count the marker characters (ignoring spaces/tabs)
        count = 0
        for c in content.rstrip("\n"):
            if c == char:
                count += 1
            elif c in " \t":
                continue
            else:
                # Invalid character
                return None

        if count >= 3:
            return Token(
                TokenType.THEMATIC_BREAK,
                char * 3,
                self._location_from(line_start),
            )

        return None

    def _classify_block_quote(self, content: str, line_start: int) -> Iterator[Token]:
        """Classify block quote marker and emit tokens."""
        # Yield the > marker
        yield Token(TokenType.BLOCK_QUOTE_MARKER, ">", self._location_from(line_start))

        # Content after > (skip optional space)
        pos = 1
        if pos < len(content) and content[pos] == " ":
            pos += 1

        remaining = content[pos:].rstrip("\n")
        if remaining:
            yield Token(
                TokenType.PARAGRAPH_LINE,
                remaining,
                self._location_from(line_start),
            )

    def _try_classify_list_marker(self, content: str, line_start: int) -> Iterator[Token] | None:
        """Try to classify content as list item marker.

        Yields marker token and content token if valid, returns None otherwise.
        """
        if not content:
            return None

        # Unordered: -, *, +
        if content[0] in "-*+":
            if len(content) > 1 and content[1] in " \t":
                return self._yield_list_marker_and_content(content[0], content[2:], line_start)
            return None

        # Ordered: 1. or 1)
        if content[0].isdigit():
            pos = 0
            while pos < len(content) and content[pos].isdigit():
                pos += 1

            if pos > 9:
                # Too many digits
                return None

            if pos < len(content) and content[pos] in ".)":
                marker_char = content[pos]
                if pos + 1 < len(content) and content[pos + 1] in " \t":
                    num = content[:pos]
                    marker = f"{num}{marker_char}"
                    remaining = content[pos + 2 :]  # Skip marker and space
                    return self._yield_list_marker_and_content(marker, remaining, line_start)

        return None

    def _yield_list_marker_and_content(
        self, marker: str, remaining: str, line_start: int
    ) -> Iterator[Token]:
        """Yield list marker token and optional content token."""
        yield Token(
            TokenType.LIST_ITEM_MARKER,
            marker,
            self._location_from(line_start),
        )
        remaining = remaining.rstrip("\n")
        if remaining:
            yield Token(
                TokenType.PARAGRAPH_LINE,
                remaining,
                self._location_from(line_start),
            )

    def _try_classify_directive_start(
        self, content: str, line_start: int
    ) -> Iterator[Token] | None:
        """Try to classify content as directive start.

        Detects :::{name} or ::::{name} syntax (MyST-style fenced directives).
        Supports:
        - Nested directives via colon count (:::: > :::)
        - Named closers (:::{/name})
        - Optional title after name

        Returns iterator of tokens if valid directive, None otherwise.
        """
        if not content.startswith(":::"):
            return None

        # Count opening colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Must have { immediately after colons
        if pos >= len(content) or content[pos] != "{":
            return None

        # Find matching }
        pos += 1  # Skip {
        brace_end = content.find("}", pos)
        if brace_end == -1:
            return None

        name = content[pos:brace_end].strip()

        # Check for named closer: {/name}
        is_closer = name.startswith("/")
        if is_closer:
            name = name[1:].strip()

        # Get optional title (rest of line after })
        title = content[brace_end + 1 :].rstrip("\n").strip()

        # Generate tokens
        return self._emit_directive_tokens(
            colon_count=colon_count,
            name=name,
            title=title,
            is_closer=is_closer,
            line_start=line_start,
        )

    def _emit_directive_tokens(
        self,
        colon_count: int,
        name: str,
        title: str,
        is_closer: bool,
        line_start: int,
    ) -> Iterator[Token]:
        """Emit directive tokens and update state."""
        location = self._location_from(line_start)

        if is_closer:
            # Named closer: :::{/name}
            yield Token(TokenType.DIRECTIVE_CLOSE, f":::{{{name}}}", location)

            # Pop from directive stack if matching
            if self._directive_stack:
                stack_count, stack_name = self._directive_stack[-1]
                if stack_name == name and colon_count >= stack_count:
                    self._directive_stack.pop()
                    if not self._directive_stack:
                        self._mode = LexerMode.BLOCK
        else:
            # Directive open
            yield Token(TokenType.DIRECTIVE_OPEN, ":" * colon_count, location)
            yield Token(TokenType.DIRECTIVE_NAME, name, location)
            if title:
                yield Token(TokenType.DIRECTIVE_TITLE, title, location)

            # Push to directive stack and switch mode
            self._directive_stack.append((colon_count, name))
            self._mode = LexerMode.DIRECTIVE

    def _scan_directive_content(self) -> Iterator[Token]:
        """Scan content inside a directive block.

        Handles:
        - Directive options (:key: value)
        - Nested directives (higher colon count)
        - Closing fence (matching or higher colon count)
        - All block-level elements (lists, headings, code, quotes, etc.)
        - Regular content (paragraph lines)
        """
        # Save location BEFORE scanning
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Calculate indent and content
        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        # Commit position
        self._commit_to(line_end)

        # Empty line
        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start))
            return

        # Check for directive close (matching colon count or higher)
        if content.startswith(":::"):
            close_result = self._try_classify_directive_close(content, line_start)
            if close_result is not None:
                yield from close_result
                return

            # Could be nested directive start
            nested_result = self._try_classify_directive_start(content, line_start)
            if nested_result is not None:
                yield from nested_result
                return

        # Check for directive option (:key: value)
        # Only at the start of directive content, before any blank line
        if content.startswith(":") and not content.startswith(":::"):
            option_token = self._try_classify_directive_option(content, line_start)
            if option_token:
                yield option_token
                return

        # Fenced code: ``` or ~~~
        if content.startswith("`") or content.startswith("~"):
            token = self._try_classify_fence_start(content, line_start)
            if token:
                yield token
                return

        # ATX Heading: # ## ### etc.
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start)
            if token:
                yield token
                return

        # Thematic break: ---, ***, ___
        if content[0] in "-*_":
            token = self._try_classify_thematic_break(content, line_start)
            if token:
                yield token
                return

        # Block quote: >
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start)
            return

        # List item: -, *, +, or 1. 1)
        list_tokens = self._try_classify_list_marker(content, line_start)
        if list_tokens is not None:
            yield from list_tokens
            return

        # Regular paragraph content
        yield Token(
            TokenType.PARAGRAPH_LINE,
            content.rstrip("\n"),
            self._location_from(line_start),
        )

    def _try_classify_directive_close(
        self, content: str, line_start: int
    ) -> Iterator[Token] | None:
        """Check if content is a directive closing fence.

        Valid closing:
        - ::: (simple close, 3+ colons matching or exceeding opener)
        - :::{/name} (named close)
        """
        if not content.startswith(":::"):
            return None

        # Count colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Check for named closer
        rest = content[pos:].strip().rstrip("\n")

        if rest.startswith("{/"):
            # Named closer: :::{/name}
            brace_end = rest.find("}")
            if brace_end != -1:
                name = rest[2:brace_end].strip()
                remaining = rest[brace_end + 1 :].strip()
                if not remaining:  # No extra content after }
                    return self._emit_directive_close(colon_count, name, line_start)

        elif rest == "" or rest.startswith("{"):
            # Simple close or check if it's a new directive
            if rest == "":
                # Simple close with just colons
                return self._emit_directive_close(colon_count, None, line_start)

        return None

    def _emit_directive_close(
        self, colon_count: int, name: str | None, line_start: int
    ) -> Iterator[Token]:
        """Emit directive close token and update state."""
        location = self._location_from(line_start)

        if not self._directive_stack:
            # No open directive, emit as plain text
            yield Token(TokenType.PARAGRAPH_LINE, ":" * colon_count, location)
            return

        stack_count, stack_name = self._directive_stack[-1]

        # Check if this closes the current directive
        if colon_count >= stack_count and (name is None or name == stack_name):
            # Valid close
            self._directive_stack.pop()
            yield Token(TokenType.DIRECTIVE_CLOSE, ":" * colon_count, location)

            # Switch mode back if no more directives
            if not self._directive_stack:
                self._mode = LexerMode.BLOCK
            return

        # Not a valid close for current directive, emit as content
        yield Token(TokenType.PARAGRAPH_LINE, ":" * colon_count, location)

    def _try_classify_directive_option(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as directive option.

        Format: :key: value
        """
        if not content.startswith(":"):
            return None

        # Find second colon
        colon_pos = content.find(":", 1)
        if colon_pos == -1:
            return None

        key = content[1:colon_pos].strip()
        value = content[colon_pos + 1 :].rstrip("\n").strip()

        # Key must be a valid identifier (alphanumeric + - + _)
        if not key or not all(c.isalnum() or c in "-_" for c in key):
            return None

        return Token(
            TokenType.DIRECTIVE_OPTION,
            f"{key}:{value}",
            self._location_from(line_start),
        )

    def _is_closing_fence(self, line: str) -> bool:
        """Check if line is a closing fence for current code block."""
        if not self._fence_char:
            return False

        # Strip up to 3 leading spaces
        content = line
        spaces = 0
        while spaces < 3 and content.startswith(" "):
            content = content[1:]
            spaces += 1

        if not content.startswith(self._fence_char):
            return False

        # Count fence characters
        count = 0
        pos = 0
        while pos < len(content) and content[pos] == self._fence_char:
            count += 1
            pos += 1

        if count < self._fence_count:
            return False

        # Rest must be whitespace only
        rest = content[pos:].rstrip("\n")
        return rest.strip() == ""

    # =========================================================================
    # Window navigation helpers
    # =========================================================================

    def _find_line_end(self) -> int:
        """Find the end of the current line (position of \\n or EOF).

        Uses str.find for O(n) with low constant factor (C implementation).
        """
        idx = self._source.find("\n", self._pos)
        return idx if idx != -1 else self._source_len

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level and content start position.

        Returns:
            (indent_spaces, content_start_index)
        """
        indent = 0
        pos = 0
        line_len = len(line)  # Cache length
        while pos < line_len:
            char = line[pos]
            if char == " ":
                indent += 1
                pos += 1
            elif char == "\t":
                indent += 4 - (indent % 4)
                pos += 1
            else:
                break
        return indent, pos

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end, consuming newline if present.

        Sets self._consumed_newline to indicate if a newline was consumed.
        Uses optimized string operations instead of character-by-character loop.
        """
        # Fast path: if no position change, skip
        if line_end == self._pos:
            self._consumed_newline = False
            if self._pos < self._source_len and self._source[self._pos] == "\n":
                self._pos += 1
                self._lineno += 1
                self._col = 1
                self._consumed_newline = True
            return

        # Count newlines in skipped segment using C-optimized str.count
        segment = self._source[self._pos : line_end]
        newline_count = segment.count("\n")

        if newline_count > 0:
            # Find position of last newline to calculate column
            last_nl = segment.rfind("\n")
            self._lineno += newline_count
            self._col = len(segment) - last_nl  # chars after last newline + 1
        else:
            self._col += len(segment)

        self._pos = line_end
        self._consumed_newline = False

        # Consume the newline if present
        if self._pos < self._source_len and self._source[self._pos] == "\n":
            self._pos += 1
            self._lineno += 1
            self._col = 1
            self._consumed_newline = True

    # =========================================================================
    # Character navigation helpers (kept for compatibility)
    # =========================================================================

    def _peek(self) -> str:
        """Peek at current character without advancing.

        Returns empty string at end of input.
        """
        if self._pos >= len(self._source):
            return ""
        return self._source[self._pos]

    def _advance(self) -> str:
        """Advance position by one character.

        Updates line/column tracking. Returns the consumed character.
        """
        if self._pos >= len(self._source):
            return ""

        char = self._source[self._pos]
        self._pos += 1

        if char == "\n":
            self._lineno += 1
            self._col = 1
        else:
            self._col += 1

        return char

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation.

        Call this at the START of scanning a line, before any position changes.
        """
        self._saved_lineno = self._lineno
        self._saved_col = self._col

    def _location(self) -> SourceLocation:
        """Get current source location."""
        return SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            source_file=self._source_file,
        )

    def _location_from(self, start_pos: int) -> SourceLocation:  # noqa: ARG002
        """Get source location from saved position.

        O(1) - uses pre-saved location from _save_location() call.
        The start_pos parameter is kept for API compatibility but not used.
        """
        return SourceLocation(
            lineno=self._saved_lineno,
            col_offset=self._saved_col,
            end_lineno=self._lineno,
            end_col_offset=self._col,
            source_file=self._source_file,
        )
