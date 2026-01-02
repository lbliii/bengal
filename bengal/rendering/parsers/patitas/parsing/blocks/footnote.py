"""Footnote parsing for Patitas parser.

Handles footnote definition parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import Block, FootnoteDef, Paragraph
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.tokens import Token


class FootnoteParsingMixin:
    """Mixin for footnote definition parsing.

    Required Host Attributes:
        - _current: Token | None

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_inline(text, location) -> tuple[Inline, ...]
    """

    _current: Token | None

    def _parse_footnote_def(self) -> FootnoteDef:
        """Parse footnote definition.

        Format: [^identifier]: content
        Token value format: identifier:content
        """
        token = self._current
        assert token is not None and token.type == TokenType.FOOTNOTE_DEF
        self._advance()

        # Parse token value (identifier:content)
        value = token.value
        colon_pos = value.find(":")
        if colon_pos == -1:
            # Shouldn't happen if lexer is correct
            return FootnoteDef(location=token.location, identifier="", children=())

        identifier = value[:colon_pos]
        content = value[colon_pos + 1 :].strip()

        # Parse content as inline if present
        if content:
            inlines = self._parse_inline(content, token.location)
            para = Paragraph(location=token.location, children=inlines)
            return FootnoteDef(location=token.location, identifier=identifier, children=(para,))

        # Collect continuation lines (indented content)
        children: list[Block] = []
        while not self._at_end():
            tok = self._current
            assert tok is not None

            if tok.type == TokenType.PARAGRAPH_LINE:
                # Continuation paragraph
                lines = [tok.value.lstrip()]
                self._advance()

                while not self._at_end():
                    next_tok = self._current
                    assert next_tok is not None
                    if next_tok.type == TokenType.PARAGRAPH_LINE:
                        lines.append(next_tok.value.lstrip())
                        self._advance()
                    else:
                        break

                para_content = "\n".join(lines)
                inlines = self._parse_inline(para_content, tok.location)
                children.append(Paragraph(location=tok.location, children=inlines))

            elif tok.type == TokenType.BLANK_LINE:
                self._advance()
            else:
                break

        return FootnoteDef(location=token.location, identifier=identifier, children=tuple(children))
