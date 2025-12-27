"""Template structure block parsing for Kida parser.

Provides mixin for parsing template structure statements (block, extends, include, from_import).
"""

from __future__ import annotations

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import Block, Extends, FromImport, Import, Include
from bengal.rendering.kida.parser.blocks.core import BlockStackMixin


class TemplateStructureBlockParsingMixin(BlockStackMixin):
    """Mixin for parsing template structure blocks.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_body: method
        - _parse_expression: method
        - _match: method
        - _advance: method
        - _expect: method
        - _error: method
    """

    def _parse_block_tag(self) -> Block:
        """Parse {% block name %}...{% end %} or {% endblock %}."""
        start = self._advance()  # consume 'block'
        self._push_block("block", start)

        if self._current.type != TokenType.NAME:
            raise self._error("Expected block name")
        name = self._advance().value

        self._expect(TokenType.BLOCK_END)
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("block")

        return Block(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            body=tuple(body),
        )

    def _parse_extends(self) -> Extends:
        """Parse {% extends "base.html" %}."""
        start = self._advance()  # consume 'extends'
        template = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Extends(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
        )

    def _parse_include(self) -> Include:
        """Parse {% include "partial.html" [with context] [ignore missing] %}."""
        start = self._advance()  # consume 'include'
        template = self._parse_expression()

        with_context = True
        ignore_missing = False

        # Parse optional modifiers
        while self._current.type == TokenType.NAME:
            keyword = self._current.value
            if keyword == "with":
                self._advance()  # consume 'with'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = True
                else:
                    raise self._error("Expected 'context' after 'with'")
            elif keyword == "without":
                self._advance()  # consume 'without'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = False
                else:
                    raise self._error("Expected 'context' after 'without'")
            elif keyword == "ignore":
                self._advance()  # consume 'ignore'
                if self._current.type == TokenType.NAME and self._current.value == "missing":
                    self._advance()  # consume 'missing'
                    ignore_missing = True
                else:
                    raise self._error("Expected 'missing' after 'ignore'")
            else:
                break

        self._expect(TokenType.BLOCK_END)

        return Include(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            with_context=with_context,
            ignore_missing=ignore_missing,
        )

    def _parse_import(self) -> Import:
        """Parse {% import "template.html" as f [with context] %}."""
        start = self._advance()  # consume 'import'

        template = self._parse_expression()

        # Expect 'as'
        if self._current.type != TokenType.NAME or self._current.value != "as":
            raise self._error("Expected 'as' after template name in import")
        self._advance()  # consume 'as'

        if self._current.type != TokenType.NAME:
            raise self._error("Expected alias name for import")
        target = self._advance().value

        with_context = False
        if self._current.type == TokenType.NAME and self._current.value == "with":
            self._advance()  # consume 'with'
            if self._current.type == TokenType.NAME and self._current.value == "context":
                self._advance()  # consume 'context'
                with_context = True
            else:
                raise self._error("Expected 'context' after 'with'")

        self._expect(TokenType.BLOCK_END)

        return Import(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            target=target,
            with_context=with_context,
        )

    def _parse_from_import(self) -> FromImport:
        """Parse {% from "template.html" import name1, name2 as alias %}."""
        start = self._advance()  # consume 'from'

        template = self._parse_expression()

        # Expect 'import'
        if self._current.type != TokenType.NAME or self._current.value != "import":
            raise self._error("Expected 'import' after template name")
        self._advance()  # consume 'import'

        # Parse imported names
        names: list[tuple[str, str | None]] = []
        with_context = False

        while True:
            if self._current.type != TokenType.NAME:
                raise self._error("Expected name to import")
            name = self._advance().value

            # Check for alias
            alias: str | None = None
            if self._current.type == TokenType.NAME and self._current.value == "as":
                self._advance()  # consume 'as'
                if self._current.type != TokenType.NAME:
                    raise self._error("Expected alias name")
                alias = self._advance().value

            names.append((name, alias))

            # Check for comma or end
            if self._match(TokenType.COMMA):
                self._advance()
            elif self._current.type == TokenType.NAME and self._current.value == "with":
                self._advance()  # consume 'with'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = True
                break
            elif self._match(TokenType.BLOCK_END):
                break
            else:
                break

        self._expect(TokenType.BLOCK_END)

        return FromImport(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            names=tuple(names),
            with_context=with_context,
        )
