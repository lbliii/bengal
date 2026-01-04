"""Main list parsing mixin.

Provides the ListParsingMixin class that orchestrates list parsing
using the modular helper functions.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    List,
    ListItem,
    Paragraph,
)
from bengal.rendering.parsers.patitas.parsing.blocks.list.blank_line import (
    ContinueList,
    EndItem,
    EndList,
    ParseBlock,
    ParseContinuation,
    handle_blank_line,
)
from bengal.rendering.parsers.patitas.parsing.blocks.list.indent import (
    is_nested_list_indent,
)
from bengal.rendering.parsers.patitas.parsing.blocks.list.item_blocks import (
    handle_fenced_code_immediate,
    handle_thematic_break,
)
from bengal.rendering.parsers.patitas.parsing.blocks.list.marker import (
    extract_marker_info,
    extract_task_marker,
    get_marker_indent,
    is_list_marker,
    is_same_list_type,
)
from bengal.rendering.parsers.patitas.parsing.blocks.list.nested import (
    detect_nested_list_in_content,
    parse_nested_list_from_indented_code,
    parse_nested_list_inline,
)
from bengal.rendering.parsers.patitas.parsing.containers import (
    ContainerFrame,
    ContainerType,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.parsing.containers import ContainerStack
    from bengal.rendering.parsers.patitas.tokens import Token

# Shadow stack validation mode (Phase 2)
# Set BENGAL_PARSER_STRICT=1 to enable assertions that validate the container
# stack matches the locally-tracked indent values.
_STRICT_MODE = os.environ.get("BENGAL_PARSER_STRICT", "0") == "1"


class ListParsingMixin:
    """Mixin for list parsing.

    Handles nested lists, task lists, continuation paragraphs, and loose/tight detection.

    Required Host Attributes:
        - _source: str
        - _tokens: list[Token]
        - _pos: int
        - _current: Token | None
        - _containers: ContainerStack (Phase 2 shadow stack)

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_inline(text, location) -> tuple[Inline, ...]
        - _parse_block() -> Block | None
        - _get_line_at(offset) -> str
        - _strip_columns(text, count) -> str
    """

    _source: str
    _tokens: list
    _pos: int
    _current: Token | None
    _containers: ContainerStack

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

        # Extract marker info
        marker_info = extract_marker_info(start_token.value)
        start_indent = marker_info.indent
        ordered = marker_info.ordered
        bullet_char = marker_info.bullet_char
        ordered_marker_char = marker_info.ordered_marker_char
        start = marker_info.start

        # Calculate content indent
        content_indent = start_indent + marker_info.marker_length + 1

        # Phase 2 Shadow Stack: Push LIST container frame
        # This tracks the list's indent context for validation.
        # In Phase 3, this will become the source of truth.
        list_frame = ContainerFrame(
            container_type=ContainerType.LIST,
            start_indent=start_indent,
            content_indent=content_indent,
            marker_width=marker_info.marker_length,
            ordered=ordered,
            bullet_char=bullet_char,
            start_number=start,
        )
        self._containers.push(list_frame)

        items: list[ListItem] = []
        tight = True

        while not self._at_end():
            token = self._current
            assert token is not None

            # Handle blank lines between items (makes list loose)
            if token.type == TokenType.BLANK_LINE:
                tight = False
                while not self._at_end() and self._current.type == TokenType.BLANK_LINE:
                    self._advance()
                if self._at_end():
                    break
                token = self._current
                if token.type != TokenType.LIST_ITEM_MARKER:
                    break

            if token.type != TokenType.LIST_ITEM_MARKER:
                break

            current_indent = get_marker_indent(token.value)

            # If less indented than our list, we're done
            if current_indent < start_indent:
                break

            # If at or beyond content indent, it's nested
            if current_indent >= content_indent:
                break

            # Check if same list type
            if not is_same_list_type(token.value, ordered, bullet_char, ordered_marker_char):
                break

            self._advance()

            # Update content indent for this item
            current_marker = token.value.lstrip()
            current_marker_length = len(current_marker.split()[0]) if current_marker.split() else 1
            content_indent = current_indent + current_marker_length + 1

            # Parse item content
            item, item_tight = self._parse_list_item(
                token,
                start_indent,
                content_indent,
                ordered,
                bullet_char,
                ordered_marker_char,
                current_marker,
            )
            items.append(item)
            if not item_tight:
                tight = False

        # Phase 2 Shadow Stack: Pop the LIST container frame
        # If loose state was detected during parsing, mark it on the frame
        # before popping so it propagates correctly.
        if not tight:
            self._containers.mark_loose()
        self._containers.pop()

        return List(
            location=start_token.location,
            items=tuple(items),
            ordered=ordered,
            start=start,
            tight=tight,
        )

    def _parse_list_item(
        self,
        marker_token: Token,
        start_indent: int,
        content_indent: int,
        ordered: bool,
        bullet_char: str,
        ordered_marker_char: str,
        marker_stripped: str,
    ) -> tuple[ListItem, bool]:
        """Parse a single list item.

        Returns:
            Tuple of (ListItem, is_tight)
        """
        # Phase 2 Shadow Stack: Push LIST_ITEM container frame
        item_frame = ContainerFrame(
            container_type=ContainerType.LIST_ITEM,
            start_indent=start_indent,
            content_indent=content_indent,
        )
        self._containers.push(item_frame)

        # Phase 2 Validation: Assert stack matches local variables
        if _STRICT_MODE:
            current = self._containers.current()
            assert current.content_indent == content_indent, (
                f"Stack content_indent mismatch: {current.content_indent} != {content_indent}"
            )
            assert current.start_indent == start_indent, (
                f"Stack start_indent mismatch: {current.start_indent} != {start_indent}"
            )

        item_children: list[Block] = []
        content_lines: list[str] = []
        checked: bool | None = None
        actual_content_indent: int | None = None
        saw_paragraph_content = False
        tight = True

        while not self._at_end():
            tok = self._current
            assert tok is not None

            # Handle thematic break
            if tok.type == TokenType.THEMATIC_BREAK:
                block, should_continue = handle_thematic_break(
                    tok, saw_paragraph_content, bool(content_lines), self
                )
                if block:
                    item_children.append(block)
                if not should_continue:
                    break
                continue

            # Handle fenced code immediately after marker (no prior content)
            if (
                tok.type == TokenType.FENCED_CODE_START
                and not saw_paragraph_content
                and not content_lines
            ):
                block, should_continue = handle_fenced_code_immediate(
                    tok, saw_paragraph_content, bool(content_lines), content_indent, self
                )
                if block:
                    item_children.append(block)
                if not should_continue:
                    break
                continue

            # Handle paragraph content
            if tok.type == TokenType.PARAGRAPH_LINE:
                line = tok.value.lstrip()

                # Check for nested list marker at start of content
                if not content_lines and not saw_paragraph_content and line:
                    check_indent = (
                        actual_content_indent
                        if actual_content_indent is not None
                        else content_indent
                    )
                    if detect_nested_list_in_content(line, tok.line_indent, check_indent):
                        blocks = parse_nested_list_inline(
                            line + "\n",
                            tok.location,
                            self,
                            getattr(self, "_directive_registry", None),
                            getattr(self, "_strict_contracts", False),
                            getattr(self, "_tables_enabled", False),
                            getattr(self, "_strikethrough_enabled", False),
                            getattr(self, "_task_lists_enabled", False),
                        )
                        item_children.extend(blocks)
                        self._advance()
                        continue

                # Calculate actual content indent from first line
                if actual_content_indent is None:
                    actual_content_indent = self._calculate_actual_content_indent(
                        tok, marker_stripped
                    )

                # Check for task list marker
                if not content_lines and checked is None:
                    checked, line = extract_task_marker(line)

                content_lines.append(line)
                saw_paragraph_content = True
                self._advance()

            # Handle indented code
            elif tok.type == TokenType.INDENTED_CODE:
                result = self._handle_indented_code_in_item(
                    tok,
                    marker_token,
                    content_lines,
                    item_children,
                    start_indent,
                    content_indent,
                    actual_content_indent,
                    ordered,
                    bullet_char,
                    ordered_marker_char,
                )
                if result == "break":
                    break
                elif result == "continue":
                    continue
                elif isinstance(result, tuple):
                    content_lines, item_children = result

            # Handle blank line
            elif tok.type == TokenType.BLANK_LINE:
                self._advance()
                # Consume consecutive blank lines
                while not self._at_end() and self._current.type == TokenType.BLANK_LINE:
                    self._advance()

                if self._at_end():
                    break

                result = handle_blank_line(
                    self._current,
                    self._source,
                    start_indent,
                    content_indent,
                    actual_content_indent,
                )

                if isinstance(result, EndList):
                    break
                elif isinstance(result, EndItem):
                    tight = False
                    break
                elif isinstance(result, ContinueList):
                    if result.is_loose:
                        tight = False
                    if result.save_paragraph and content_lines:
                        content = "\n".join(content_lines)
                        inlines = self._parse_inline(content, marker_token.location)
                        item_children.append(
                            Paragraph(location=marker_token.location, children=inlines)
                        )
                        content_lines = []
                    self._advance()
                    continue
                elif isinstance(result, ParseBlock):
                    tight = False
                    if content_lines:
                        content = "\n".join(content_lines)
                        inlines = self._parse_inline(content, marker_token.location)
                        item_children.append(
                            Paragraph(location=marker_token.location, children=inlines)
                        )
                        content_lines = []
                    block = self._parse_block()
                    if block is not None:
                        item_children.append(block)
                    continue
                elif isinstance(result, ParseContinuation):
                    tight = False
                    if result.save_paragraph and content_lines:
                        content = "\n".join(content_lines)
                        inlines = self._parse_inline(content, marker_token.location)
                        item_children.append(
                            Paragraph(location=marker_token.location, children=inlines)
                        )
                        content_lines = []

                    # Handle continuation content directly
                    # INDENTED_CODE at content indent is paragraph content, not code
                    next_tok = self._current
                    if next_tok and next_tok.type == TokenType.INDENTED_CODE:
                        check_indent = (
                            actual_content_indent
                            if actual_content_indent is not None
                            else content_indent
                        )
                        orig_indent = next_tok.line_indent
                        indent_beyond = orig_indent - check_indent
                        # At content indent (not 4+ beyond) = paragraph content
                        # Must be AT or BEYOND content_indent to be continuation
                        if orig_indent >= check_indent and indent_beyond < 4:
                            content_lines.append(next_tok.value.rstrip())
                            self._advance()
                            continue
                    elif next_tok and next_tok.type == TokenType.PARAGRAPH_LINE:
                        # Continuation paragraph
                        content_lines.append(next_tok.value.lstrip())
                        self._advance()
                        continue

                    continue

            # Handle nested list markers
            elif tok.type == TokenType.LIST_ITEM_MARKER:
                nested_indent = get_marker_indent(tok.value)
                check_content_indent = (
                    actual_content_indent if actual_content_indent is not None else content_indent
                )

                # Check if different marker at same indent (new list)
                if nested_indent == start_indent and not is_same_list_type(
                    tok.value, ordered, bullet_char, ordered_marker_char
                ):
                    break

                if is_nested_list_indent(nested_indent, check_content_indent):
                    # Save current paragraph
                    if content_lines:
                        content = "\n".join(content_lines)
                        inlines = self._parse_inline(content, marker_token.location)
                        item_children.append(
                            Paragraph(location=marker_token.location, children=inlines)
                        )
                        content_lines = []

                    # Parse nested list
                    nested_list = self._parse_list(parent_indent=start_indent)
                    item_children.append(nested_list)

                    # After nested list, check if there's a blank line before the next token
                    # This makes the outer list loose
                    if not self._at_end():
                        next_tok = self._current
                        # Check if there was a blank line before current token by looking at source
                        if next_tok.location.offset > 0:
                            # Find the line start
                            line_start = self._source.rfind("\n", 0, next_tok.location.offset) + 1
                            if line_start > 1:
                                prev_char = self._source[line_start - 2 : line_start]
                                if prev_char == "\n\n" or (
                                    line_start >= 2
                                    and self._source[line_start - 1] == "\n"
                                    and self._source[line_start - 2] == "\n"
                                ):
                                    # There was a blank line before this token
                                    tight = False

                        if next_tok.type == TokenType.PARAGRAPH_LINE:
                            next_indent = next_tok.line_indent
                            # Content at outer item's content indent = continuation
                            # Use content_indent (not check_content_indent) for comparison
                            if next_indent >= start_indent and next_indent <= content_indent:
                                # Blank line occurred (nested list ended), making list loose
                                tight = False
                                content_lines.append(next_tok.value.lstrip())
                                self._advance()
                                continue
                elif nested_indent >= 4 and nested_indent < check_content_indent:
                    # Marker at 4+ spaces but not nested - literal content
                    marker_content = tok.value.lstrip()
                    self._advance()
                    if not self._at_end():
                        next_tok = self._current
                        if next_tok.type == TokenType.PARAGRAPH_LINE:
                            marker_content += " " + next_tok.value.lstrip()
                            self._advance()
                    content_lines.append(marker_content)
                else:
                    # Sibling item
                    break

            # Handle block-level elements at content indent
            elif tok.type in (
                TokenType.BLOCK_QUOTE_MARKER,
                TokenType.FENCED_CODE_START,
                TokenType.ATX_HEADING,
                TokenType.THEMATIC_BREAK,
            ):
                # Check if the block element is at content indent
                block_indent = tok.line_indent
                check_content_indent = (
                    actual_content_indent if actual_content_indent is not None else content_indent
                )
                if block_indent >= check_content_indent:
                    # Block element belongs to this item
                    if content_lines:
                        content = "\n".join(content_lines)
                        inlines = self._parse_inline(content, marker_token.location)
                        item_children.append(
                            Paragraph(location=marker_token.location, children=inlines)
                        )
                        content_lines = []
                    block = self._parse_block()
                    if block is not None:
                        item_children.append(block)
                    continue
                else:
                    # Block element is at list level - terminates item
                    break

            else:
                break

        # Finalize item content
        if content_lines:
            content = "\n".join(content_lines)
            inlines = self._parse_inline(content, marker_token.location)
            item_children.append(Paragraph(location=marker_token.location, children=inlines))

        # Phase 2 Shadow Stack: Pop the LIST_ITEM container frame
        # Mark as loose if tight=False (blank line detected)
        if not tight:
            self._containers.mark_loose()
        self._containers.pop()

        item = ListItem(
            location=marker_token.location,
            children=tuple(item_children),
            checked=checked,
        )
        return item, tight

    def _calculate_actual_content_indent(self, tok: Token, marker_stripped: str) -> int:
        """Calculate actual content indent from first content line.

        CommonMark: The content indent is the column position where the first
        non-space character appears after the marker. For continuation lines,
        content must be indented to at least this column.

        For example, in "1. a", the marker "1." ends at column 2, followed by
        a space, so content starts at column 3. Content indent = 3.
        """
        line_start = tok.location.offset
        line_start_pos = self._source.rfind("\n", 0, line_start) + 1
        if line_start_pos == 0:
            line_start_pos = 0
        original_line = self._source[line_start_pos:].split("\n")[0]

        marker_part = marker_stripped.split()[0] if marker_stripped.split() else marker_stripped
        marker_pos_in_line = original_line.find(marker_part)
        if marker_pos_in_line == -1:
            return get_marker_indent(tok.value) + len(marker_part) + 1

        # Calculate indent to start of marker (handles tabs correctly)
        marker_start_indent = get_marker_indent(original_line[:marker_pos_in_line])
        # Column position after marker = indent to marker + marker length
        marker_end_col = marker_start_indent + len(marker_part)

        rest_of_line = original_line[marker_pos_in_line + len(marker_part) :]
        if not rest_of_line or rest_of_line.isspace():
            return marker_end_col + 1

        spaces_after = len(rest_of_line) - len(rest_of_line.lstrip(" "))
        if spaces_after > 4:
            return marker_end_col + 1

        return marker_end_col + spaces_after

    def _handle_indented_code_in_item(
        self,
        tok: Token,
        marker_token: Token,
        content_lines: list[str],
        item_children: list[Block],
        start_indent: int,
        content_indent: int,
        actual_content_indent: int | None,
        ordered: bool,
        bullet_char: str,
        ordered_marker_char: str,
    ) -> str | tuple[list[str], list[Block]]:
        """Handle INDENTED_CODE token within a list item.

        Returns:
            "break" - break out of item loop
            "continue" - continue to next iteration
            (content_lines, item_children) - updated state
        """
        check_indent = (
            actual_content_indent if actual_content_indent is not None else content_indent
        )

        original_indent = tok.line_indent
        stripped_content = tok.value.lstrip()

        if original_indent >= check_indent:
            # Check for nested list marker
            if is_list_marker(stripped_content):
                if content_lines:
                    content = "\n".join(content_lines)
                    inlines = self._parse_inline(content, marker_token.location)
                    item_children.append(
                        Paragraph(location=marker_token.location, children=inlines)
                    )
                    content_lines = []

                nested_list = parse_nested_list_from_indented_code(
                    tok, original_indent, check_indent, self
                )
                if nested_list:
                    item_children.append(nested_list)
                return (content_lines, item_children)

            # Continuation at content indent
            if original_indent == check_indent and content_lines:
                content_lines.append(tok.value.rstrip())
                self._advance()
                return (content_lines, item_children)

            # More indented - actual code
            return "break"

        # original_indent < check_indent
        # Check if it's between start_indent and check_indent
        # In CommonMark, content at indentation between marker and content
        # column is literal content of the item (not a new marker or code)
        marker_indent = get_marker_indent(marker_token.value)
        if original_indent > marker_indent and original_indent < check_indent:
            # This is literal content of the item (e.g., "    - e" in example 312)
            content_lines.append(tok.value.rstrip())
            self._advance()
            return (content_lines, item_children)

        return "break"

    def _get_marker_indent(self, marker_value: str) -> int:
        """Extract indent level from list marker value.

        Marker values are prefixed with spaces by the lexer to encode indent.
        """
        return get_marker_indent(marker_value)

    def _parse_nested_list_from_indented_code(
        self, token: Token, original_indent: int, parent_content_indent: int
    ) -> List | None:
        """Parse a nested list from an INDENTED_CODE token containing a list marker."""
        return parse_nested_list_from_indented_code(
            token, original_indent, parent_content_indent, self
        )
