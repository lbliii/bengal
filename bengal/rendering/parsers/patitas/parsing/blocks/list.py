"""List parsing for Patitas parser.

Handles ordered, unordered, and task lists with proper nesting support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    IndentedCode,
    List,
    ListItem,
    Paragraph,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.tokens import Token


class ListParsingMixin:
    """Mixin for list parsing.

    Handles nested lists, task lists, continuation paragraphs, and loose/tight detection.

    Required Host Attributes:
        - _source: str
        - _tokens: list[Token]
        - _pos: int
        - _current: Token | None

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_inline(text, location) -> tuple[Inline, ...]
        - _parse_block() -> Block | None
    """

    _source: str
    _tokens: list
    _pos: int
    _current: Token | None

    def _parse_list(self, parent_indent: int = -1) -> List:
        """Parse list (unordered or ordered) with nested list support.

        Args:
            parent_indent: Indent level of parent list (-1 for top-level)

        Handles:
        - Nested lists via indentation tracking
        - Task lists with [ ] and [x] markers
        - Multi-line list items (continuation paragraphs)
        - Loose lists (blank lines between items)
        """
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.LIST_ITEM_MARKER

        # Extract indent from marker value (spaces prefixed by lexer)
        start_indent = self._get_marker_indent(start_token.value)
        marker_stripped = start_token.value.lstrip()
        ordered = marker_stripped[0].isdigit()
        start = 1
        # Track marker character for CommonMark compliance
        # Different markers create separate lists:
        # - Unordered: -, *, + are different
        # - Ordered: . and ) are different
        bullet_char = "" if ordered else marker_stripped[0]
        ordered_marker_char = ""  # Track . or ) for ordered lists

        # Calculate content indent: marker indent + marker length + space
        # This is the minimum indent needed for continuation content
        marker_length = len(marker_stripped.split()[0]) if marker_stripped.split() else 1
        content_indent = start_indent + marker_length + 1  # +1 for space after marker

        if ordered:
            # Extract starting number and marker style
            num_str = ""
            for c in marker_stripped:
                if c.isdigit():
                    num_str += c
                else:
                    # Found marker character (. or ))
                    ordered_marker_char = c
                    break
            if num_str:
                start = int(num_str)

        items: list[ListItem] = []
        tight = True  # Will be set to False if blank lines between items

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type != TokenType.LIST_ITEM_MARKER:
                break

            # Get indent of this marker
            current_indent = self._get_marker_indent(token.value)
            current_marker = token.value.lstrip()

            # If less indented than our list, we're done
            if current_indent < start_indent:
                break

            # CommonMark: A list marker at indent < content_indent is a SIBLING, not nested.
            # For a marker to start a NESTED list, it must be at content_indent or more.
            # So markers at start_indent to content_indent-1 are all siblings in this list.
            if current_indent >= content_indent:
                # This marker could be nested - let parent handle
                break

            # Check if same list type (ordered vs unordered)
            is_ordered = current_marker[0].isdigit()
            if is_ordered != ordered:
                break

            # CommonMark: different markers create separate lists
            # - Unordered: -, *, + are different
            # - Ordered: . and ) are different
            if ordered:
                # Extract marker character from ordered list marker
                current_ordered_marker = ""
                for c in current_marker:
                    if not c.isdigit():
                        current_ordered_marker = c
                        break
                if current_ordered_marker != ordered_marker_char:
                    break
            else:
                current_bullet = current_marker[0]
                if current_bullet != bullet_char:
                    break

            self._advance()

            # Update content_indent for this item
            # This determines what indent is needed for nested content/lists
            current_marker_length = len(current_marker.split()[0]) if current_marker.split() else 1
            content_indent = current_indent + current_marker_length + 1  # +1 for space after marker

            # Collect item content, children (nested lists), and detect task list
            item_children: list[Block] = []
            content_lines: list[str] = []
            checked: bool | None = None
            # Track actual content indent from first content line
            actual_content_indent: int | None = None

            while not self._at_end():
                tok = self._current
                assert tok is not None

                if tok.type == TokenType.PARAGRAPH_LINE:
                    line = tok.value.lstrip()

                    # Calculate actual content indent from first line
                    if actual_content_indent is None:
                        # Get original line from source to calculate indent
                        line_start = tok.location.offset
                        line_start_pos = self._source.rfind("\n", 0, line_start) + 1
                        if line_start_pos == 0:
                            line_start_pos = 0
                        original_line = self._source[line_start_pos:].split("\n")[0]
                        # Find where content starts (after marker and spaces)
                        marker_end_pos = original_line.find(marker_stripped.split()[0]) + len(
                            marker_stripped.split()[0]
                        )
                        # Skip spaces after marker
                        content_start_pos = marker_end_pos
                        while (
                            content_start_pos < len(original_line)
                            and original_line[content_start_pos] == " "
                        ):
                            content_start_pos += 1
                        actual_content_indent = content_start_pos

                    # Check for task list marker at start of first line
                    if not content_lines and checked is None:
                        if line.startswith("[ ] "):
                            checked = False
                            line = line[4:]
                        elif line.startswith("[x] ") or line.startswith("[X] "):
                            checked = True
                            line = line[4:]

                    content_lines.append(line)
                    self._advance()
                elif tok.type == TokenType.INDENTED_CODE:
                    # INDENTED_CODE tokens are created for 4+ space indentation.
                    # Check if this is continuation (indent == actual_content_indent) vs code
                    line_start = tok.location.offset
                    # Find the start of the line containing this token
                    line_start_pos = self._source.rfind("\n", 0, line_start) + 1
                    if line_start_pos == 0:
                        line_start_pos = 0
                    line = self._source[line_start_pos:].split("\n")[0]
                    # Calculate original indent
                    original_indent = len(line) - len(line.lstrip())

                    # Use actual_content_indent if available
                    check_indent = (
                        actual_content_indent
                        if actual_content_indent is not None
                        else content_indent
                    )

                    if original_indent == check_indent and content_lines:
                        # This is a continuation line at content_indent, not code
                        code_content = tok.value.rstrip()
                        content_lines.append(code_content)
                        self._advance()
                    elif original_indent > check_indent:
                        # More indented than content_indent - this is actual code
                        break
                    else:
                        # Less indented - shouldn't happen, but break to be safe
                        break

                elif tok.type == TokenType.BLANK_LINE:
                    self._advance()
                    # Consume consecutive blank lines
                    while not self._at_end() and self._current.type == TokenType.BLANK_LINE:
                        self._advance()
                    # Check what comes next
                    if self._at_end():
                        break
                    next_tok = self._current
                    assert next_tok is not None

                    if next_tok.type == TokenType.LIST_ITEM_MARKER:
                        next_indent = self._get_marker_indent(next_tok.value)
                        if next_indent <= start_indent:
                            # Same or less indent - this blank separates items
                            tight = False
                            break
                        # More indent - could be nested list
                    elif next_tok.type == TokenType.PARAGRAPH_LINE:
                        # Check if paragraph is indented enough to continue list item
                        para_indent = self._get_marker_indent(next_tok.value)
                        if para_indent < content_indent:
                            # Not indented enough - terminates the list
                            break
                        # Indented enough - continuation (loose list)
                        tight = False
                        # Save current paragraph first
                        if content_lines:
                            content = "\n".join(content_lines)
                            inlines = self._parse_inline(content, token.location)
                            para = Paragraph(location=token.location, children=inlines)
                            item_children.append(para)
                            content_lines = []
                        continue
                    elif next_tok.type in (
                        TokenType.FENCED_CODE_START,
                        TokenType.BLOCK_QUOTE_MARKER,
                        TokenType.ATX_HEADING,
                        TokenType.THEMATIC_BREAK,
                    ):
                        # Block types that can appear in list items
                        # Save current paragraph first
                        if content_lines:
                            content = "\n".join(content_lines)
                            inlines = self._parse_inline(content, token.location)
                            para = Paragraph(location=token.location, children=inlines)
                            item_children.append(para)
                            content_lines = []
                        tight = False
                        # Parse the block and add to item_children
                        block = self._parse_block()
                        if block is not None:
                            item_children.append(block)
                        continue
                    elif next_tok.type == TokenType.INDENTED_CODE:
                        # Indented code after blank line
                        line_start = next_tok.location.offset
                        line_start_pos = self._source.rfind("\n", 0, line_start) + 1
                        if line_start_pos == 0:
                            line_start_pos = 0
                        line = self._source[line_start_pos:].split("\n")[0]
                        original_indent = len(line) - len(line.lstrip())

                        check_indent = (
                            actual_content_indent
                            if actual_content_indent is not None
                            else content_indent
                        )

                        if original_indent == check_indent:
                            # Content at same level - paragraph continuation
                            if content_lines:
                                content = "\n".join(content_lines)
                                inlines = self._parse_inline(content, token.location)
                                para = Paragraph(location=token.location, children=inlines)
                                item_children.append(para)
                                content_lines = []
                            tight = False
                            # Add as new paragraph content
                            # Strip leading spaces from INDENTED_CODE value (lexer already stripped 4)
                            code_content = next_tok.value.lstrip().rstrip()
                            content_lines.append(code_content)
                            self._advance()
                            continue
                        elif original_indent > check_indent:
                            # Code inside the list item (more indented)
                            if content_lines:
                                content = "\n".join(content_lines)
                                inlines = self._parse_inline(content, token.location)
                                para = Paragraph(location=token.location, children=inlines)
                                item_children.append(para)
                                content_lines = []
                            tight = False
                            # Parse indented code block inside list item
                            code_token = next_tok
                            self._advance()

                            # Collect all indented code lines
                            code_lines = [code_token.value]
                            while not self._at_end():
                                tok = self._current
                                if tok.type == TokenType.INDENTED_CODE:
                                    code_lines.append(tok.value)
                                    self._advance()
                                elif tok.type == TokenType.BLANK_LINE:
                                    if self._pos + 1 < len(self._tokens):
                                        next_tok_check = self._tokens[self._pos + 1]
                                        if next_tok_check.type == TokenType.INDENTED_CODE:
                                            code_lines.append("\n")
                                            self._advance()
                                            continue
                                    break
                                else:
                                    break

                            # Combine and strip content_indent
                            code_content = "".join(code_lines)
                            lines_list = code_content.split("\n")
                            stripped_lines = []
                            for code_line in lines_list:
                                if (
                                    code_line
                                    and len(code_line) >= check_indent
                                    and code_line[:check_indent] == " " * check_indent
                                ):
                                    stripped_lines.append(code_line[check_indent:])
                                else:
                                    stripped_lines.append(code_line)
                            adjusted_code = "\n".join(stripped_lines)

                            code_block = IndentedCode(
                                location=code_token.location, code=adjusted_code
                            )
                            item_children.append(code_block)
                            tight = False
                            continue
                        else:
                            # Not indented enough - terminates the list
                            break
                    else:
                        break

                elif tok.type == TokenType.LIST_ITEM_MARKER:
                    nested_indent = self._get_marker_indent(tok.value)
                    # Use actual_content_indent if we've determined it, otherwise use calculated
                    check_content_indent = (
                        actual_content_indent
                        if actual_content_indent is not None
                        else content_indent
                    )
                    if nested_indent >= check_content_indent:
                        # Nested list - marker is at or beyond content column
                        # First save current paragraph if any
                        if content_lines:
                            content = "\n".join(content_lines)
                            inlines = self._parse_inline(content, token.location)
                            para = Paragraph(location=token.location, children=inlines)
                            item_children.append(para)
                            content_lines = []

                        # Parse nested list
                        nested_list = self._parse_list(parent_indent=start_indent)
                        item_children.append(nested_list)
                    elif nested_indent >= 4 and nested_indent < check_content_indent:
                        # Marker at 4+ spaces but not enough for nesting - treat as literal content
                        # This handles cases like "    - e" being content of "   - d"
                        # The marker becomes literal text: "- e"
                        marker_stripped = tok.value.lstrip()
                        self._advance()
                        # Get the content after the marker
                        marker_content = marker_stripped
                        if not self._at_end():
                            next_tok = self._current
                            if next_tok.type == TokenType.PARAGRAPH_LINE:
                                marker_content += " " + next_tok.value.lstrip()
                                self._advance()
                        content_lines.append(marker_content)
                    else:
                        # Marker is between start_indent and content_indent - sibling item
                        break

                else:
                    break

            # Finalize item content
            if content_lines:
                content = "\n".join(content_lines)
                inlines = self._parse_inline(content, token.location)
                para = Paragraph(location=token.location, children=inlines)
                item_children.append(para)

            item = ListItem(
                location=token.location,
                children=tuple(item_children),
                checked=checked,
            )
            items.append(item)

        return List(
            location=start_token.location,
            items=tuple(items),
            ordered=ordered,
            start=start,
            tight=tight,
        )

    def _get_marker_indent(self, marker_value: str) -> int:
        """Extract indent level from list marker value.

        Marker values are prefixed with spaces by the lexer to encode indent.
        E.g., "  -" has indent 2, "1." has indent 0.
        """
        indent = 0
        for char in marker_value:
            if char == " ":
                indent += 1
            elif char == "\t":
                indent += 4 - (indent % 4)
            else:
                break
        return indent
