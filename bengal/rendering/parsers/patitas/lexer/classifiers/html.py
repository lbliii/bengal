"""HTML block classifier mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.lexer.modes import (
    HTML_BLOCK_TYPE1_TAGS,
    HTML_BLOCK_TYPE6_TAGS,
    LexerMode,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class HtmlClassifierMixin:
    """Mixin providing HTML block classification.

    Implements CommonMark 4.6 HTML block types 1-7.
    """

    # These will be set by the Lexer class
    _mode: LexerMode
    _html_block_type: int
    _html_block_content: list[str]
    _html_block_start: int
    _pos: int
    _source_len: int
    _consumed_newline: bool

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_html_block_start(
        self, content: str, line_start: int, full_line: str
    ) -> Iterator[Token] | None:
        """Try to classify content as HTML block start.

        CommonMark 4.6 defines 7 types of HTML blocks.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            full_line: The full line including leading whitespace

        Returns:
            Iterator yielding HTML_BLOCK token, or None if not HTML block.
        """
        if not content or content[0] != "<":
            return None

        content_lower = content.lower()

        # Include newline in full_line if we consumed one
        full_line_nl = full_line + ("\n" if self._consumed_newline else "")

        # Type 1: <pre, <script, <style, <textarea (case-insensitive)
        # Ends with </pre>, </script>, </style>, </textarea>
        for tag in HTML_BLOCK_TYPE1_TAGS:
            if content_lower.startswith(f"<{tag}") and (
                len(content) == len(tag) + 1 or content[len(tag) + 1] in " \t\n>"
            ):
                self._html_block_type = 1
                self._html_block_content = [full_line_nl]
                self._html_block_start = line_start
                # Check if end condition on same line
                end_tag = f"</{tag}>"
                if end_tag in content_lower:
                    return self._emit_html_block()
                self._mode = LexerMode.HTML_BLOCK
                return iter([])  # Empty iterator, tokens come from scan

        # Type 2: <!-- (HTML comment)
        # Ends with -->
        if content.startswith("<!--"):
            self._html_block_type = 2
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            if "-->" in content[4:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 3: <? (processing instruction)
        # Ends with ?>
        if content.startswith("<?"):
            self._html_block_type = 3
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            if "?>" in content[2:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 4: <! followed by uppercase letter (declaration)
        # Ends with >
        if len(content) >= 3 and content[1] == "!" and content[2].isupper():
            self._html_block_type = 4
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            if ">" in content[2:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 5: <![CDATA[
        # Ends with ]]>
        if content.startswith("<![CDATA["):
            self._html_block_type = 5
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            if "]]>" in content[9:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 6: <tagname or </tagname where tagname is block-level
        # Ends with blank line (or EOF)
        tag_match = self._extract_html_tag_name(content)
        if tag_match and tag_match.lower() in HTML_BLOCK_TYPE6_TAGS:
            self._html_block_type = 6
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            # If at EOF, emit immediately
            if self._pos >= self._source_len:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 7: Complete open tag (not a type 6 tag) or closing tag
        # Must be the only thing on the line (possibly followed by whitespace)
        # Ends with blank line (or EOF)
        if self._is_complete_html_tag(content):
            self._html_block_type = 7
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            # If at EOF, emit immediately
            if self._pos >= self._source_len:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        return None

    def _extract_html_tag_name(self, content: str) -> str | None:
        """Extract tag name from HTML opening or closing tag.

        Args:
            content: Line content starting with <

        Returns:
            Tag name if found, None otherwise.
        """
        if not content or content[0] != "<":
            return None

        pos = 1
        # Handle closing tag </
        if pos < len(content) and content[pos] == "/":
            pos += 1

        # Tag name must start with letter
        if pos >= len(content) or not content[pos].isalpha():
            return None

        start = pos
        while pos < len(content) and (content[pos].isalnum() or content[pos] == "-"):
            pos += 1

        return content[start:pos] if pos > start else None

    def _is_complete_html_tag(self, content: str) -> bool:
        """Check if content is a complete single HTML open/close tag.

        Type 7 HTML blocks require a SINGLE complete tag that's the only content on line.
        This means: <tag>, <tag attr="value">, <tag/>, or </tag> - NOT <tag>content</tag>.

        The tag name must also NOT be one of the type 6 block-level tags.
        Must not match autolinks like <http://...> or <email@domain>.

        CommonMark strict attribute validation:
        - Attribute name: [a-zA-Z_:][a-zA-Z0-9_.:-]*
        - Attribute value: unquoted (no special chars), 'single', or "double" quoted
        - Space required between attributes (but not after final attribute before > or />)

        Args:
            content: Line content

        Returns:
            True if this is a complete HTML tag.
        """
        content = content.rstrip()
        if not content or content[0] != "<":
            return False

        # Must end with >
        if not content.endswith(">"):
            return False

        # Must have at least <x> (3 chars)
        if len(content) < 3:
            return False

        # Exclude autolinks: URIs contain "://" or ":" followed by path, emails contain "@"
        # If the content between < and > has "://" or "@", it's likely an autolink
        inner = content[1:-1]
        if "://" in inner or "@" in inner:
            return False

        # Check for closing tag </x>
        if content[1] == "/":
            # Closing tag: must have letter after /
            if len(content) < 4:
                return False
            if not content[2].isalpha():
                return False
            # Extract tag name
            pos = 2
            while pos < len(content) - 1 and (content[pos].isalnum() or content[pos] == "-"):
                pos += 1
            tag_name = content[2:pos].lower()
            # Must end with just > or whitespace then >
            rest = content[pos:-1]
            if rest.strip() != "":
                return False
            # Tag must NOT be a type 6 tag (those are handled by type 6)
            return tag_name not in HTML_BLOCK_TYPE6_TAGS

        # Opening tag: <tagname ...>
        if not content[1].isalpha():
            return False

        # Extract tag name - must be followed by whitespace, /, or >
        pos = 1
        while pos < len(content) and (content[pos].isalnum() or content[pos] == "-"):
            pos += 1
        tag_name = content[1:pos].lower()

        # Check tag name was followed by valid delimiter (not just more characters)
        # E.g., <localhost:5001> has tag_name="localhost" but then ":5001>" which isn't valid
        if pos < len(content) - 1:
            next_char = content[pos]
            if next_char not in " \t/>":
                return False

        # Tag must NOT be a type 6 tag
        if tag_name in HTML_BLOCK_TYPE6_TAGS:
            return False

        # Now validate the attributes portion strictly per CommonMark
        # rest is everything between tag name and final >
        rest = content[pos:-1]

        # Self-closing: <tag/> or <tag attr="val"/>
        if rest.endswith("/"):
            rest = rest[:-1]

        # Must not contain another < (which would indicate nested content)
        if "<" in rest:
            return False

        # Validate attributes strictly
        return self._validate_html_attributes(rest)

    def _validate_html_attributes(self, attrs_str: str) -> bool:
        """Validate HTML attribute string per CommonMark spec.

        Args:
            attrs_str: The portion after tag name and before > (without leading <tag or trailing >)

        Returns:
            True if attributes are valid per CommonMark 6.8.
        """
        i = 0
        length = len(attrs_str)

        while i < length:
            char = attrs_str[i]

            # Skip whitespace
            if char in " \t\n":
                i += 1
                continue

            # Must be start of attribute name: [a-zA-Z_:]
            if not (char.isalpha() or char in "_:"):
                return False

            # Parse attribute name: [a-zA-Z_:][a-zA-Z0-9_.:-]*
            i += 1
            while i < length:
                c = attrs_str[i]
                if c.isalnum() or c in "_.::-":
                    i += 1
                else:
                    break

            # Skip whitespace
            while i < length and attrs_str[i] in " \t\n":
                i += 1

            # Check for = (attribute value)
            if i < length and attrs_str[i] == "=":
                i += 1  # Skip =

                # Skip whitespace after =
                while i < length and attrs_str[i] in " \t\n":
                    i += 1

                if i >= length:
                    return False

                val_char = attrs_str[i]

                # Double-quoted value
                if val_char == '"':
                    i += 1
                    while i < length and attrs_str[i] != '"':
                        i += 1
                    if i >= length:
                        return False  # Unclosed quote
                    i += 1  # Skip closing "

                # Single-quoted value
                elif val_char == "'":
                    i += 1
                    while i < length and attrs_str[i] != "'":
                        i += 1
                    if i >= length:
                        return False  # Unclosed quote
                    i += 1  # Skip closing '

                # Unquoted value - cannot contain: " ' = < > ` or whitespace
                else:
                    if val_char in "\"'=<>`":
                        return False
                    while i < length and attrs_str[i] not in "\"'=<>` \t\n":
                        i += 1

            # After attribute: must be whitespace or end of string
            # If there's more content without whitespace, it's invalid
            # (e.g., <a href='bar'title=title> - no space before title)
            if i < length and attrs_str[i] not in " \t\n":
                return False

        return True

    def _emit_html_block(self) -> Iterator[Token]:
        """Emit accumulated HTML block as a single token.

        Yields:
            Single HTML_BLOCK token with accumulated content.
        """
        # Content already has newlines at the end of each line
        html_content = "".join(self._html_block_content)
        if html_content and not html_content.endswith("\n"):
            html_content += "\n"

        yield Token(
            TokenType.HTML_BLOCK,
            html_content,
            self._location_from(self._html_block_start),
        )

        # Reset state
        self._html_block_type = 0
        self._html_block_content = []
        self._html_block_start = 0
        self._mode = LexerMode.BLOCK
