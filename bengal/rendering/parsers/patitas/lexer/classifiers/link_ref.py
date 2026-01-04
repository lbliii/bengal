"""Link reference definition classifier mixin.

Handles multi-line definitions, escaped characters, and strict validation
according to CommonMark 0.31.2 spec.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class LinkRefClassifierMixin:
    """Mixin providing link reference definition classification."""

    _source: str
    _source_len: int
    _pos: int
    _lineno: int
    _col: int

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _find_line_end(self) -> int:
        """Find end of current line. Implemented by Lexer."""
        raise NotImplementedError

    def _commit_to(self, line_end: int) -> None:
        """Commit position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_link_reference_def(
        self, first_line_content: str, line_start: int
    ) -> Token | None:
        """Try to classify content as link reference definition.

        CommonMark 4.7:
        A link reference definition consists of:
        1. A link label (indented by up to 3 spaces)
        2. A colon (:)
        3. Optional whitespace (including up to one line change)
        4. A link destination
        5. Optional whitespace (including up to one line change)
        6. An optional link title

        Args:
            first_line_content: Content of the first line (indents < 4 stripped)
            line_start: Source position where the first line starts

        Returns:
            LINK_REFERENCE_DEF token if valid, None otherwise.
            Token value format: label|url|title (pipe-separated)
        """
        if not first_line_content.startswith("["):
            return None

        # Save Lexer state in case we need to backtrack (though we don't really backtrack
        # because we only commit if we are sure, but we might have multiple lines to peek)
        saved_pos = self._pos
        saved_lineno = self._lineno
        saved_col = self._col

        # 1. Parse Label
        # We start at line_start. The '[' is at line_start + (original_line - first_line_content).
        # But we can just use first_line_content to start.

        # We need to find the matching ']:'
        # Labels can span multiple lines, but no blank lines allowed.

        label_content, next_pos, success = self._parse_label_multiline(
            first_line_content, line_start
        )
        if not success or not label_content:
            return None

        # next_pos is at the ':' after ']'
        # Advance current position to next_pos + 1

        # 2. Parse Destination
        # Optional whitespace (at most one newline)
        dest_start_pos = next_pos + 1
        url, next_pos, success = self._parse_destination_multiline(dest_start_pos)
        if not success:
            return None

        # 3. Parse Optional Title
        # Optional whitespace (at most one newline)
        title_start_pos = next_pos
        title, next_pos, success = self._parse_title_multiline(title_start_pos)
        if not success:
            # If title parsing failed but it looked like a title attempt, it might invalidate
            # the whole link ref def. CommonMark says if junk follows, it's invalid.
            return None

        # Ensure no trailing junk on the same line as title (or destination if no title)
        line_end = self._source.find("\n", next_pos)
        if line_end == -1:
            line_end = self._source_len

        trailing = self._source[next_pos:line_end]
        if trailing.strip():
            return None

        # Successfully parsed!
        # Commit to the end of the line where we stopped
        self._commit_to(line_end)

        # Value format: label|url|title
        value = f"{label_content}|{url}|{title}"
        return Token(TokenType.LINK_REFERENCE_DEF, value, self._location_from(line_start))

    def _parse_label_multiline(self, first_line: str, line_start: int) -> tuple[str, int, bool]:
        """Parse link label, possibly spanning multiple lines."""
        # We start at line_start + indent
        # The '[' is at index 0 of first_line.

        # We'll use a local pointer into self._source
        # Find where the '[' is actually located
        indent_len = self._source[line_start:].find("[")
        if indent_len == -1 or indent_len > 3:
            return "", 0, False

        start_search = line_start + indent_len + 1  # After '['

        label_parts = []
        curr = start_search
        bracket_count = 1

        while curr < self._source_len:
            char = self._source[curr]
            if char == "\\":
                # Escaped char - consume two
                label_parts.append(self._source[curr : curr + 2])
                curr += 2
            elif char == "[":
                # Nested unescaped '[' is NOT allowed in link labels
                return "", 0, False
            elif char == "]":
                # Potential end
                if curr + 1 < self._source_len and self._source[curr + 1] == ":":
                    # Found it!
                    label = "".join(label_parts).strip()
                    # Label length cannot exceed 999
                    if len(label) > 999:
                        return "", 0, False
                    return label, curr + 1, True
                else:
                    # ']' not followed by ':' - is this allowed in label?
                    # Spec 4.7: "A link label ... may not contain an unescaped ]"
                    # Wait, so the search should be for the FIRST unescaped ] followed by :?
                    # No, it's just the FIRST unescaped ]. If it's not followed by :, it's NOT a link ref def.
                    return "", 0, False
            elif char == "\n":
                # Line break in label. Check for blank line.
                if curr + 1 < self._source_len and self._source[curr + 1] == "\n":
                    return "", 0, False
                label_parts.append(char)
                curr += 1
            else:
                label_parts.append(char)
                curr += 1

        return "", 0, False

    def _parse_destination_multiline(self, start_pos: int) -> tuple[str, int, bool]:
        """Parse link destination, possibly after one newline."""
        curr = start_pos

        # Skip whitespace (at most one newline)
        newline_found = False
        while curr < self._source_len:
            char = self._source[curr]
            if char in " \t":
                curr += 1
            elif char == "\n":
                if newline_found:
                    break  # Only one newline allowed
                newline_found = True
                curr += 1
                # Check for blank line
                if curr < self._source_len and self._source[curr] == "\n":
                    return "", 0, False
                # Skip leading whitespace on next line
                while curr < self._source_len and self._source[curr] in " \t":
                    curr += 1
            else:
                break

        if curr >= self._source_len:
            return "", 0, False

        dest_start = curr
        char = self._source[curr]

        if char == "<":
            # Angle-bracketed destination
            curr += 1
            dest_parts = []
            while curr < self._source_len:
                c = self._source[curr]
                if c == "\\":
                    dest_parts.append(self._source[curr : curr + 2])
                    curr += 2
                elif c == "\n":
                    # Newline NOT allowed in angle brackets
                    return "", 0, False
                elif c == "<":
                    # Unescaped < NOT allowed in angle brackets
                    return "", 0, False
                elif c == ">":
                    # End of destination
                    return "".join(dest_parts), curr + 1, True
                else:
                    dest_parts.append(c)
                    curr += 1
            return "", 0, False
        else:
            # Bare destination (no spaces, no unescaped control chars)
            dest_parts = []
            while curr < self._source_len:
                c = self._source[curr]
                if c == "\\":
                    dest_parts.append(self._source[curr : curr + 2])
                    curr += 2
                elif c in " \t\n" or ord(c) < 32:
                    break
                else:
                    dest_parts.append(c)
                    curr += 1

            url = "".join(dest_parts)
            if not url:
                return "", 0, False
            return url, curr, True

    def _parse_title_multiline(self, start_pos: int) -> tuple[str, int, bool]:
        """Parse optional link title, possibly after one newline."""
        curr = start_pos

        # Skip whitespace (at most one newline)
        newline_found = False
        whitespace_count = 0
        while curr < self._source_len:
            char = self._source[curr]
            if char in " \t":
                curr += 1
                whitespace_count += 1
            elif char == "\n":
                if newline_found:
                    break
                newline_found = True
                curr += 1
                whitespace_count += 1
                # Check for blank line
                if curr < self._source_len and self._source[curr] == "\n":
                    # Blank line terminates search for title
                    return "", start_pos, True
                # Skip leading whitespace on next line
                while curr < self._source_len and self._source[curr] in " \t":
                    curr += 1
            else:
                break

        if curr >= self._source_len or whitespace_count == 0:
            # No whitespace found, so no title possible on this line
            # Wait, if there was a newline, that counts as whitespace.
            # If no whitespace and no newline, then no title.
            return "", start_pos, True

        title_start_char = self._source[curr]
        if title_start_char not in "\"'(":
            # Not a title start
            return "", start_pos, True

        end_char = ")" if title_start_char == "(" else title_start_char
        curr += 1
        title_parts = []

        while curr < self._source_len:
            c = self._source[curr]
            if c == "\\":
                title_parts.append(self._source[curr : curr + 2])
                curr += 2
            elif c == title_start_char == "(" and c == "(":  # Wait, nested parens allowed in title?
                # CommonMark says for titles in parens, nested parens are allowed if escaped
                # Wait, let me check spec...
                # 4.7: "a sequence of zero or more characters ... enclosed in parentheses (())."
                # "The title ... may not contain a blank line."
                # It doesn't explicitly mention nested parens for titles, unlike destinations.
                # But it's safer to just look for the end char.
                title_parts.append(c)
                curr += 1
            elif c == end_char:
                # End of title
                return "".join(title_parts), curr + 1, True
            elif c == "\n":
                # Line break in title. Check for blank line.
                if curr + 1 < self._source_len and self._source[curr + 1] == "\n":
                    # Blank line in title makes it invalid
                    return "", 0, False
                title_parts.append(c)
                curr += 1
            else:
                title_parts.append(c)
                curr += 1

        return "", 0, False
