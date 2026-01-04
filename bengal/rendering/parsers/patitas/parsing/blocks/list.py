"""List parsing for Patitas parser.

Handles ordered, unordered, and task lists with proper nesting support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    FencedCode,
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

            # Track if we've seen any content for this item yet.
            # Block elements (thematic break, fenced code) are only included in the list item
            # if they immediately follow the marker (no paragraph content first).
            saw_paragraph_content = False

            while not self._at_end():
                tok = self._current
                assert tok is not None

                # Handle block-level elements that can appear immediately after list marker
                # e.g., "- * * *" where * * * is a thematic break
                # Only valid if NO paragraph content has been seen (meaning same line as marker)
                if tok.type == TokenType.THEMATIC_BREAK:
                    if not saw_paragraph_content and not content_lines:
                        # Thematic break immediately after list marker - include in item
                        from bengal.rendering.parsers.patitas.nodes import ThematicBreak

                        item_children.append(ThematicBreak(location=tok.location))
                        self._advance()
                        continue
                    else:
                        # Thematic break after paragraph content - terminates this list
                        break

                if tok.type == TokenType.FENCED_CODE_START:
                    if not saw_paragraph_content and not content_lines:
                        # Fenced code block immediately after list marker
                        block = self._parse_block()
                        if block is not None:
                            item_children.append(block)
                        continue
                    else:
                        # After paragraph content - terminates list
                        break

                if tok.type == TokenType.PARAGRAPH_LINE:
                    line = tok.value.lstrip()

                    # CommonMark: Check if this is a nested list marker (e.g., "- - foo")
                    # If the first content after a list marker is itself a list marker,
                    # it should be parsed as a nested list.
                    if not content_lines and not saw_paragraph_content and line:
                        is_nested_list = False
                        first_char = line[0]
                        # Unordered: -, *, + followed by space/tab or end
                        if first_char in "-*+":
                            if len(line) == 1 or (len(line) > 1 and line[1] in " \t"):
                                is_nested_list = True
                        # Ordered: digits followed by . or ) and space/tab or end
                        elif first_char.isdigit():
                            pos = 0
                            while pos < len(line) and line[pos].isdigit():
                                pos += 1
                            if (
                                pos > 0
                                and pos < len(line)
                                and line[pos] in ".)"
                                and (
                                    pos + 1 == len(line)
                                    or (pos + 1 < len(line) and line[pos + 1] in " \t")
                                )
                            ):
                                is_nested_list = True

                        if is_nested_list:
                            # Re-lex the content as a nested list and parse it
                            from bengal.rendering.parsers.patitas.parser import Parser

                            nested_parser = Parser(
                                line + "\n",
                                directive_registry=getattr(self, "_directive_registry", None),
                                strict_contracts=getattr(self, "_strict_contracts", False),
                            )
                            # Copy plugin settings
                            nested_parser._tables_enabled = getattr(self, "_tables_enabled", False)
                            nested_parser._strikethrough_enabled = getattr(
                                self, "_strikethrough_enabled", False
                            )
                            nested_parser._task_lists_enabled = getattr(
                                self, "_task_lists_enabled", False
                            )
                            nested_blocks = nested_parser.parse()
                            item_children.extend(nested_blocks)
                            self._advance()
                            continue

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
                    saw_paragraph_content = True
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

                    # Get the content after stripping indent
                    stripped_content = tok.value.lstrip()

                    # Use actual_content_indent if available
                    check_indent = (
                        actual_content_indent
                        if actual_content_indent is not None
                        else content_indent
                    )

                    if original_indent >= check_indent:
                        # Check if this is actually a nested list marker
                        # CommonMark: A list marker at content_indent or deeper can be a nested list
                        is_list_marker = False
                        if stripped_content:
                            first_char = stripped_content[0]
                            if first_char in "-*+":
                                # Unordered list marker: must be followed by space or tab
                                if len(stripped_content) > 1 and stripped_content[1] in " \t":
                                    is_list_marker = True
                            elif first_char.isdigit():
                                # Ordered list marker: digits followed by . or ) and space
                                pos = 0
                                while (
                                    pos < len(stripped_content) and stripped_content[pos].isdigit()
                                ):
                                    pos += 1
                                if (
                                    pos > 0
                                    and pos < len(stripped_content)
                                    and stripped_content[pos] in ".)"
                                    and pos + 1 < len(stripped_content)
                                    and stripped_content[pos + 1] in " \t"
                                ):
                                    is_list_marker = True

                        if is_list_marker:
                            # This is a nested list - save current content and parse nested list
                            if content_lines:
                                content = "\n".join(content_lines)
                                inlines = self._parse_inline(content, token.location)
                                para = Paragraph(location=token.location, children=inlines)
                                item_children.append(para)
                                content_lines = []

                            # Create a pseudo LIST_ITEM_MARKER token and parse nested list
                            # We need to inject this as a list marker
                            nested_list = self._parse_nested_list_from_indented_code(
                                tok, original_indent, check_indent
                            )
                            if nested_list:
                                item_children.append(nested_list)
                        elif original_indent == check_indent and content_lines:
                            # Continuation line at content_indent (not a list marker)
                            code_content = tok.value.rstrip()
                            content_lines.append(code_content)
                            self._advance()
                        else:
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
                        if next_indent < content_indent:
                            # Less than content_indent - this is a sibling item
                            # (even with blank line separation, it's still in the same list)
                            tight = False
                            break
                        # At or beyond content_indent - could be nested list
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
                            # Content at same level - could be paragraph, block quote, or fenced code
                            code_content = next_tok.value.lstrip().rstrip()

                            # Check for block quote at content level
                            if code_content.startswith(">"):
                                # Save current paragraph first
                                if content_lines:
                                    content = "\n".join(content_lines)
                                    inlines = self._parse_inline(content, token.location)
                                    para = Paragraph(location=token.location, children=inlines)
                                    item_children.append(para)
                                    content_lines = []
                                tight = False
                                # Parse the block quote
                                # We need to re-lex this content as a block quote
                                # For now, parse inline content of the block quote
                                # Collect all block quote lines
                                bq_lines = []
                                while not self._at_end():
                                    bq_tok = self._current
                                    if bq_tok.type == TokenType.INDENTED_CODE:
                                        bq_line_start = bq_tok.location.offset
                                        bq_line_start_pos = (
                                            self._source.rfind("\n", 0, bq_line_start) + 1
                                        )
                                        if bq_line_start_pos == 0:
                                            bq_line_start_pos = 0
                                        bq_line = self._source[bq_line_start_pos:].split("\n")[0]
                                        bq_original_indent = len(bq_line) - len(bq_line.lstrip())
                                        bq_content = bq_tok.value.lstrip().rstrip()

                                        if (
                                            bq_original_indent == check_indent
                                            and bq_content.startswith(">")
                                        ):
                                            # Block quote continuation
                                            # Strip the > and optional space
                                            if bq_content.startswith("> "):
                                                bq_lines.append(bq_content[2:])
                                            elif bq_content.startswith(">"):
                                                bq_lines.append(bq_content[1:])
                                            self._advance()
                                        else:
                                            break
                                    elif bq_tok.type == TokenType.BLANK_LINE:
                                        # Check if next line continues the block quote
                                        self._advance()
                                        if self._at_end():
                                            break
                                        peek_tok = self._current
                                        if peek_tok.type == TokenType.INDENTED_CODE:
                                            peek_line_start = peek_tok.location.offset
                                            peek_line_start_pos = (
                                                self._source.rfind("\n", 0, peek_line_start) + 1
                                            )
                                            if peek_line_start_pos == 0:
                                                peek_line_start_pos = 0
                                            peek_line = self._source[peek_line_start_pos:].split(
                                                "\n"
                                            )[0]
                                            peek_original_indent = len(peek_line) - len(
                                                peek_line.lstrip()
                                            )
                                            peek_content = peek_tok.value.lstrip().rstrip()
                                            if (
                                                peek_original_indent == check_indent
                                                and peek_content.startswith(">")
                                            ):
                                                continue  # Continue block quote
                                        break
                                    else:
                                        break

                                # Parse block quote content
                                bq_text = "\n".join(bq_lines)
                                bq_inlines = self._parse_inline(bq_text, next_tok.location)
                                bq_para = Paragraph(location=next_tok.location, children=bq_inlines)
                                bq = BlockQuote(location=next_tok.location, children=(bq_para,))
                                item_children.append(bq)
                                continue

                            # Check for fenced code block at content level
                            if code_content.startswith("```") or code_content.startswith("~~~"):
                                # Save current paragraph first
                                if content_lines:
                                    content = "\n".join(content_lines)
                                    inlines = self._parse_inline(content, token.location)
                                    para = Paragraph(location=token.location, children=inlines)
                                    item_children.append(para)
                                    content_lines = []
                                tight = False

                                # Parse fenced code block
                                fence_char = code_content[0]
                                fence_count = 0
                                for c in code_content:
                                    if c == fence_char:
                                        fence_count += 1
                                    else:
                                        break

                                # Extract info string (language hint)
                                info_string = code_content[fence_count:].strip() or None

                                self._advance()  # Move past fence start

                                # Track source positions for zero-copy
                                source_start: int | None = None
                                source_end: int = 0

                                # Collect code lines until closing fence
                                while not self._at_end():
                                    fc_tok = self._current
                                    if fc_tok.type == TokenType.INDENTED_CODE:
                                        fc_content = fc_tok.value.lstrip().rstrip()

                                        # Check for closing fence (same or more chars, same char)
                                        if fc_content.startswith(fence_char * fence_count):
                                            closing_count = 0
                                            for c in fc_content:
                                                if c == fence_char:
                                                    closing_count += 1
                                                else:
                                                    break
                                            if (
                                                closing_count >= fence_count
                                                and fc_content[closing_count:].strip() == ""
                                            ):
                                                self._advance()  # Move past closing fence
                                                break

                                        # Track source positions
                                        if source_start is None:
                                            source_start = fc_tok.location.offset
                                        source_end = fc_tok.location.end_offset
                                        self._advance()
                                    elif fc_tok.type == TokenType.BLANK_LINE:
                                        # Blank lines in fenced code
                                        if source_start is not None:
                                            source_end = fc_tok.location.end_offset
                                        self._advance()
                                    else:
                                        break

                                fenced = FencedCode(
                                    location=next_tok.location,
                                    source_start=source_start if source_start is not None else 0,
                                    source_end=source_end,
                                    info=info_string,
                                    marker=fence_char,  # type: ignore[arg-type]
                                    fence_indent=check_indent,  # Use list content indent
                                )
                                item_children.append(fenced)
                                continue

                            # Regular paragraph continuation
                            if content_lines:
                                content = "\n".join(content_lines)
                                inlines = self._parse_inline(content, token.location)
                                para = Paragraph(location=token.location, children=inlines)
                                item_children.append(para)
                                content_lines = []
                            tight = False
                            # Add as new paragraph content
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

                            # Collect all indented code lines that are MORE indented than content level
                            code_lines = [code_token.value]
                            while not self._at_end():
                                tok = self._current
                                if tok.type == TokenType.INDENTED_CODE:
                                    # Check if this line is still at code level (> check_indent)
                                    tok_line_start = tok.location.offset
                                    tok_line_start_pos = (
                                        self._source.rfind("\n", 0, tok_line_start) + 1
                                    )
                                    if tok_line_start_pos == 0:
                                        tok_line_start_pos = 0
                                    tok_line = self._source[tok_line_start_pos:].split("\n")[0]
                                    tok_original_indent = len(tok_line) - len(tok_line.lstrip())

                                    if tok_original_indent > check_indent:
                                        # Still code level
                                        code_lines.append(tok.value)
                                        self._advance()
                                    else:
                                        # Back to content level - stop collecting code
                                        break
                                elif tok.type == TokenType.BLANK_LINE:
                                    if self._pos + 1 < len(self._tokens):
                                        next_tok_check = self._tokens[self._pos + 1]
                                        if next_tok_check.type == TokenType.INDENTED_CODE:
                                            # Check if the INDENTED_CODE after blank is still code level
                                            ntc_line_start = next_tok_check.location.offset
                                            ntc_line_start_pos = (
                                                self._source.rfind("\n", 0, ntc_line_start) + 1
                                            )
                                            if ntc_line_start_pos == 0:
                                                ntc_line_start_pos = 0
                                            ntc_line = self._source[ntc_line_start_pos:].split(
                                                "\n"
                                            )[0]
                                            ntc_original_indent = len(ntc_line) - len(
                                                ntc_line.lstrip()
                                            )

                                            if ntc_original_indent > check_indent:
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

    def _parse_nested_list_from_indented_code(
        self, token: Token, original_indent: int, parent_content_indent: int
    ) -> List | None:
        """Parse a nested list from an INDENTED_CODE token that contains a list marker.

        When the lexer produces INDENTED_CODE for 4+ space indented lines, those lines
        may actually be nested list markers in list context. This method handles that case.

        Args:
            token: The INDENTED_CODE token containing the list marker
            original_indent: The original indentation of the line in source
            parent_content_indent: The content indent of the parent list item

        Returns:
            A List node containing the nested list, or None if parsing fails.
        """
        # Extract the marker from the token value
        stripped = token.value.lstrip()

        # Determine if ordered or unordered
        first_char = stripped[0]
        if first_char in "-*+":
            ordered = False
            marker_char = first_char
            marker_len = 1
            remaining = stripped[2:] if len(stripped) > 2 else ""  # Skip marker and space
        else:
            # Ordered list marker
            ordered = True
            pos = 0
            while pos < len(stripped) and stripped[pos].isdigit():
                pos += 1
            marker_char = stripped[pos] if pos < len(stripped) else "."
            marker_len = pos + 1  # digits + . or )
            remaining = stripped[pos + 2 :] if pos + 2 < len(stripped) else ""

        # Calculate content indent for the nested list item
        nested_content_indent = original_indent + marker_len + 1

        # Create items for the nested list
        items: list[ListItem] = []
        tight = True
        start = 1

        if ordered:
            # Extract start number
            num_str = ""
            for c in stripped:
                if c.isdigit():
                    num_str += c
                else:
                    break
            if num_str:
                start = int(num_str)

        # Process first item (from current token)
        first_item_children: list[Block] = []
        if remaining.strip():
            first_item_inlines = self._parse_inline(remaining.strip(), token.location)
            first_item_children.append(
                Paragraph(
                    location=token.location,
                    children=first_item_inlines,
                )
            )

        self._advance()  # Move past the first INDENTED_CODE token

        # Collect continuation content and more nested items
        content_lines: list[str] = []

        while not self._at_end():
            tok = self._current
            assert tok is not None

            if tok.type == TokenType.INDENTED_CODE:
                # Check the original indentation
                tok_line_start = tok.location.offset
                tok_line_start_pos = self._source.rfind("\n", 0, tok_line_start) + 1
                if tok_line_start_pos == 0:
                    tok_line_start_pos = 0
                tok_line = self._source[tok_line_start_pos:].split("\n")[0]
                tok_original_indent = len(tok_line) - len(tok_line.lstrip())
                tok_content = tok.value.lstrip()

                # Check if this is another list marker at the same level
                is_sibling_marker = False
                if tok_content:
                    tc_first = tok_content[0]
                    if tc_first in "-*+" and len(tok_content) > 1 and tok_content[1] in " \t":
                        if (
                            not ordered
                            and tc_first == marker_char
                            and tok_original_indent == original_indent
                        ):
                            is_sibling_marker = True
                    elif tc_first.isdigit() and ordered:
                        p = 0
                        while p < len(tok_content) and tok_content[p].isdigit():
                            p += 1
                        if (
                            p < len(tok_content)
                            and tok_content[p] == marker_char
                            and tok_original_indent == original_indent
                        ):
                            is_sibling_marker = True

                if is_sibling_marker:
                    # Save current item
                    if content_lines:
                        cl_content = "\n".join(content_lines)
                        cl_inlines = self._parse_inline(cl_content, tok.location)
                        first_item_children.append(
                            Paragraph(
                                location=tok.location,
                                children=cl_inlines,
                            )
                        )
                        content_lines = []

                    # Finalize current item and start new one
                    items.append(
                        ListItem(
                            location=token.location,
                            children=tuple(first_item_children),
                            checked=None,
                        )
                    )

                    # Parse remaining content for new item
                    new_remaining = ""
                    if tc_first in "-*+":
                        new_remaining = tok_content[2:].strip() if len(tok_content) > 2 else ""
                    else:
                        p = 0
                        while p < len(tok_content) and tok_content[p].isdigit():
                            p += 1
                        new_remaining = (
                            tok_content[p + 2 :].strip() if p + 2 < len(tok_content) else ""
                        )

                    first_item_children = []
                    if new_remaining:
                        new_inlines = self._parse_inline(new_remaining, tok.location)
                        first_item_children.append(
                            Paragraph(
                                location=tok.location,
                                children=new_inlines,
                            )
                        )
                    self._advance()
                    token = tok  # Update token reference for location
                    continue

                # Check if this is a more deeply nested list
                if tok_original_indent >= nested_content_indent:
                    # Check for nested list marker
                    is_nested_marker = False
                    if tok_content:
                        tc_first = tok_content[0]
                        if tc_first in "-*+" and len(tok_content) > 1 and tok_content[1] in " \t":
                            is_nested_marker = True
                        elif tc_first.isdigit():
                            p = 0
                            while p < len(tok_content) and tok_content[p].isdigit():
                                p += 1
                            if (
                                p < len(tok_content)
                                and tok_content[p] in ".)"
                                and p + 1 < len(tok_content)
                                and tok_content[p + 1] in " \t"
                            ):
                                is_nested_marker = True

                    if is_nested_marker:
                        # Save current content first
                        if content_lines:
                            cl_content = "\n".join(content_lines)
                            cl_inlines = self._parse_inline(cl_content, tok.location)
                            first_item_children.append(
                                Paragraph(
                                    location=tok.location,
                                    children=cl_inlines,
                                )
                            )
                            content_lines = []

                        # Recursively parse nested list
                        nested = self._parse_nested_list_from_indented_code(
                            tok, tok_original_indent, nested_content_indent
                        )
                        if nested:
                            first_item_children.append(nested)
                        continue
                    else:
                        # Continuation content
                        content_lines.append(tok_content.rstrip())
                        self._advance()
                        continue
                elif tok_original_indent >= parent_content_indent:
                    # At parent content level - continuation
                    content_lines.append(tok_content.rstrip())
                    self._advance()
                else:
                    break
            elif tok.type == TokenType.PARAGRAPH_LINE:
                # Paragraph continuation
                content_lines.append(tok.value.lstrip().rstrip())
                self._advance()
            elif tok.type == TokenType.BLANK_LINE:
                tight = False
                self._advance()
            else:
                break

        # Finalize content for last item
        if content_lines:
            cl_content = "\n".join(content_lines)
            cl_inlines = self._parse_inline(cl_content, token.location)
            first_item_children.append(
                Paragraph(
                    location=token.location,
                    children=cl_inlines,
                )
            )

        # Add the last item
        items.append(
            ListItem(
                location=token.location,
                children=tuple(first_item_children),
                checked=None,
            )
        )

        return List(
            location=token.location,
            items=tuple(items),
            ordered=ordered,
            start=start,
            tight=tight,
        )
