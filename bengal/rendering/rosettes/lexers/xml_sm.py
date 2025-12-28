"""Hand-written XML lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["XmlStateMachineLexer"]


class XmlStateMachineLexer(StateMachineLexer):
    """XML lexer with <!-- --> comments and tag parsing."""

    name = "xml"
    aliases = ()
    filenames = ("*.xml", "*.xsl", "*.xslt", "*.rss", "*.atom", "*.svg")
    mimetypes = ("text/xml", "application/xml", "image/svg+xml")

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = starttart

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # XML declaration or processing instruction <?...?>
            if char == "<" and pos + 1 < length and code[pos + 1] == "?":
                start = pos
                pos += 2
                start_line = line
                while pos < length:
                    if code[pos : pos + 2] == "?>":
                        pos += 2
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], start_line, col)
                continue

            # Comment <!-- -->
            if char == "<" and code[pos : pos + 4] == "<!--":
                start = pos
                pos += 4
                start_line = line
                while pos < length:
                    if code[pos : pos + 3] == "-->":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                continue

            # DOCTYPE
            if char == "<" and code[pos : pos + 9].upper() == "<!DOCTYPE":
                start = pos
                bracket_depth = 0
                while pos < length:
                    if code[pos] == "[":
                        bracket_depth += 1
                    elif code[pos] == "]":
                        bracket_depth -= 1
                    elif code[pos] == ">" and bracket_depth == 0:
                        pos += 1
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # CDATA
            if char == "<" and code[pos : pos + 9] == "<![CDATA[":
                start = pos
                pos += 9
                start_line = line
                while pos < length:
                    if code[pos : pos + 3] == "]]>":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], start_line, col)
                continue

            # Tags
            if char == "<":
                start = pos
                pos += 1

                # Closing tag
                if pos < length and code[pos] == "/":
                    pos += 1

                # Tag name (including namespace prefix)
                tag_start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "-_:."):
                    pos += 1
                tag_name = code[tag_start:pos]

                if tag_name:
                    yield Token(TokenType.PUNCTUATION, code[start:tag_start], line, col)
                    yield Token(TokenType.NAME_TAG, tag_name, line, col + (tag_start - start))

                    # Parse attributes
                    while pos < length:
                        # Whitespace
                        if code[pos] in " \t\n\r":
                            ws_start = pos
                            while pos < length and code[pos] in " \t\n\r":
                                if code[pos] == "\n":
                                    line += 1
                                    line_start = pos + 1
                                pos += 1
                            yield Token(TokenType.WHITESPACE, code[ws_start:pos], line, col)
                            continue

                        # End of tag
                        if code[pos] == ">":
                            yield Token(TokenType.PUNCTUATION, ">", line, pos - line_start + 1)
                            pos += 1
                            break

                        # Self-closing
                        if code[pos : pos + 2] == "/>":
                            yield Token(TokenType.PUNCTUATION, "/>", line, pos - line_start + 1)
                            pos += 2
                            break

                        # Namespace declaration xmlns:
                        if code[pos : pos + 5] == "xmlns":
                            attr_start = pos
                            pos += 5
                            if pos < length and code[pos] == ":":
                                pos += 1
                                while pos < length and (code[pos].isalnum() or code[pos] in "-_"):
                                    pos += 1
                            yield Token(
                                TokenType.NAME_NAMESPACE,
                                code[attr_start:pos],
                                line,
                                attr_start - line_start + 1,
                            )
                            continue

                        # Attribute name (including namespace prefix)
                        if code[pos].isalpha() or code[pos] in "_:":
                            attr_start = pos
                            while pos < length and (code[pos].isalnum() or code[pos] in "-_:."):
                                pos += 1
                            yield Token(
                                TokenType.NAME_ATTRIBUTE,
                                code[attr_start:pos],
                                line,
                                attr_start - line_start + 1,
                            )
                            continue

                        # Equals sign
                        if code[pos] == "=":
                            yield Token(TokenType.OPERATOR, "=", line, pos - line_start + 1)
                            pos += 1
                            continue

                        # Attribute value
                        if code[pos] in "\"'":
                            quote = code[pos]
                            val_start = pos
                            pos += 1
                            while pos < length and code[pos] != quote:
                                if code[pos] == "\n":
                                    line += 1
                                    line_start = pos + 1
                                pos += 1
                            if pos < length:
                                pos += 1
                            yield Token(
                                TokenType.STRING,
                                code[val_start:pos],
                                line,
                                val_start - line_start + 1,
                            )
                            continue

                        pos += 1
                else:
                    yield Token(TokenType.TEXT, "<", line, col)
                continue

            # Entity references &amp; &#123; &#x1F;
            if char == "&":
                start = pos
                pos += 1
                if pos < length and code[pos] == "#":
                    pos += 1
                    if pos < length and code[pos] in "xX":
                        pos += 1
                        while pos < length and code[pos] in "0123456789abcdefABCDEF":
                            pos += 1
                    else:
                        while pos < length and code[pos].isdigit():
                            pos += 1
                else:
                    while pos < length and code[pos].isalnum():
                        pos += 1
                if pos < length and code[pos] == ";":
                    pos += 1
                yield Token(TokenType.NAME_ENTITY, code[start:pos], line, col)
                continue

            # Text content
            if char != "<":
                start = pos
                while pos < length and code[pos] not in "<&":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                text = code[start:pos]
                if text.strip():
                    yield Token(TokenType.TEXT, text, line, col)
                elif text:
                    yield Token(TokenType.WHITESPACE, text, line, col)
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
